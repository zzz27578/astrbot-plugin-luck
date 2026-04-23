import os
import json
import random
import re
import asyncio
from datetime import datetime
import time 
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Plain, Image, At
from ..core.card_engine import CardEngine
from ..core.dice_engine import DiceEngine
from ..core.title_engine import TitleEngine
from ..core.logic_gate import (
    find_gate_block,
    format_gate_block_message,
    GATE_DRAW_FUNC_CARD,
    GATE_USE_CARD,
    GATE_TOGGLE_CARD,
)
from ..core.lazy_engine import (
    is_func_super_lazy_enabled,
    generate_super_lazy_func_card,
    resolve_func_card,
)


# ================= 🎲 骰局会话状态（全局单局） =================
PENDING_DUEL = {
    "active": False,
    "group_id": "",
    "session_id": "",
    "challenger_uid": "",
    "challenger_name": "",
    "target_uid": "",
    "target_name": "",
    "card_name": "",
    "stake": 0,
    "min_stake": 0,
    "max_stake": 0,
    "source_kind": "",
    "phase": "",
    "confirmed": False,
    "response_action": "",
    "response_stake": 0,
    "confirm_event": None,
    "created_at": 0,
    "expire_at": 0,
}
PENDING_DUEL_LOCK = asyncio.Lock()
DUEL_CONFIRM_WINDOW_SEC = 60
DUEL_STAGE_DELAY_SEC = 1.6


def _format_title_effect_desc(title_name: str, config: dict | None = None) -> str:
    info = TitleEngine.get_title_info(title_name, config)
    effects = TitleEngine.describe_effects(info.get("effects", []))
    return "；".join(effects) if effects else (info.get("desc") or "无特殊效果")


async def handle_view_titles(event: AstrMessageEvent, bank, config: dict):
    user_id = event.get_sender_id()
    user_name = event.get_sender_name()
    user_data = await bank.get_user_data(user_id, user_name)
    TitleEngine.ensure_user_title_fields(user_data)
    sync_events = TitleEngine.sync_titles(user_data, config)
    owned = user_data.get("titles", [])
    equipped = set(TitleEngine.get_equipped_titles(user_data, config))
    max_count = TitleEngine.get_max_equipped_titles(config)
    lines = [f"🏅 【{user_name} 的称号列表】", f"当前佩戴：{len(equipped)}/{max_count}", f"拥有总称号：{len(owned)}"]
    if sync_events:
        lines.extend(TitleEngine.format_title_event_lines(sync_events, config))
    if not owned:
        lines.append("你目前还没有获得任何称号。")
    else:
        for idx, title_name in enumerate(owned, 1):
            status = "🟢已佩戴" if title_name in equipped else "⚪未佩戴"
            lines.append(f"{idx}. [{title_name}] {status}")
            lines.append(f"   效果：{_format_title_effect_desc(title_name, config)}")
    await bank.save_user_data()
    yield event.plain_result("\n".join(lines))


async def handle_equip_title(event: AstrMessageEvent, bank, config: dict, title_name: str):
    user_id = event.get_sender_id()
    user_name = event.get_sender_name()
    user_data = await bank.get_user_data(user_id, user_name)
    TitleEngine.ensure_user_title_fields(user_data)
    owned = user_data.get("titles", [])
    equipped = user_data.get("equipped_titles", [])
    max_count = TitleEngine.get_max_equipped_titles(config)
    if title_name not in owned:
        yield event.plain_result(f"⚠️ 你尚未拥有称号【{title_name}】。可先发送 /luck 查看称号")
        return
    if title_name in equipped:
        yield event.plain_result(f"ℹ️ 称号【{title_name}】已在佩戴中。")
        return
    if len(equipped) >= max_count:
        yield event.plain_result(f"⚠️ 当前最多只能佩戴 {max_count} 个称号，请先卸下其他称号。")
        return
    equipped.append(title_name)
    await bank.save_user_data()
    yield event.plain_result(f"✅ 已佩戴称号【{title_name}】\n当前：{len(equipped)}/{max_count}")


async def handle_unequip_title(event: AstrMessageEvent, bank, config: dict, title_name: str):
    user_id = event.get_sender_id()
    user_name = event.get_sender_name()
    user_data = await bank.get_user_data(user_id, user_name)
    TitleEngine.ensure_user_title_fields(user_data)
    equipped = user_data.get("equipped_titles", [])
    if title_name not in equipped:
        yield event.plain_result(f"ℹ️ 称号【{title_name}】当前未佩戴。")
        return
    equipped.remove(title_name)
    await bank.save_user_data()
    yield event.plain_result(f"✅ 已卸下称号【{title_name}】")



def _is_dice_card_by_tags(tags: list) -> bool:
    return any(str(t).startswith("dice_") or str(t).startswith("dice_rule:") for t in (tags or []))


def _consume_target_shield_for_duel(target_data: dict) -> bool:
    for i, st in enumerate(target_data.get("statuses", [])):
        if st.get("name") == "无懈可击":
            target_data["statuses"].pop(i)
            for card in target_data.get("inventory", []):
                if card.get("card_name") == "无懈可击" and card.get("is_active"):
                    card["is_active"] = False
                    card["is_broken"] = True
                    break
            return True
    return False


def _consume_lowest_reroll_status(user_data: dict, final_total: int) -> bool:
    # 默认最低点按 1 判定（即便有修正，仍以最终总点数判最低触发）
    if final_total != 1:
        return False

    now_ts = int(time.time())
    statuses = user_data.get("statuses", [])
    for i, st in enumerate(statuses):
        if st.get("name") != "天命重投":
            continue
        if st.get("expire_time") and int(st.get("expire_time", 0)) <= now_ts:
            continue
        statuses.pop(i)
        return True
    return False


def _apply_reroll_status(user_data: dict, hours: int = 24):
    expire_time = int(time.time()) + hours * 3600
    statuses = user_data.setdefault("statuses", [])
    for st in statuses:
        if st.get("name") == "天命重投":
            st["expire_time"] = expire_time
            st["desc"] = "下次掷到最低点时自动重投1次"
            return
    statuses.append({
        "name": "天命重投",
        "expire_time": expire_time,
        "desc": "下次掷到最低点时自动重投1次",
    })


def load_func_cards_config(config: dict = None, include_disabled_dice: bool = False):
    storage_paths = (config or {}).get("_storage_paths", {})
    config_path = storage_paths.get("func_cards_file")
    if config_path is None or not config_path.exists():
        return []

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_cards = json.load(f)
    except Exception:
        return []

    valid_cards = []
    for card in raw_cards if isinstance(raw_cards, list) else []:
        if not isinstance(card, dict):
            continue

        card_name = str(card.get("card_name", "")).strip()
        if not card_name:
            continue

        rarity_raw = card.get("rarity", 1)
        rarity = int(rarity_raw) if str(rarity_raw).lstrip("-").isdigit() else 1

        entry = {
            "card_name": card_name,
            "type": card.get("type", "unknown"),
            "description": card.get("description", "一张神秘的战术卡"),
            "filename": card.get("filename", ""),
            "tags": card.get("tags", []),
            "rarity": rarity,
        }

        dice_enabled = True if config is None else config.get("func_cards_settings", {}).get("enable_dice_cards", True)
        if not include_disabled_dice and not dice_enabled and _is_dice_card_by_tags(entry.get("tags", [])):
            continue

        valid_cards.append(entry)

    return valid_cards


# ---- 默认稀有度权重 (rarity 1~5) ----
_DEFAULT_RARITY_WEIGHTS = {1: 30, 2: 30, 3: 28, 4: 11, 5: 1}
# 同档去重窗口与降权系数（后台隐藏逻辑，不对外展示）
_DEDUP_WINDOW = 5
_DEDUP_PENALTY = 0.15


def _pick_func_card(cards_config: list, config: dict, user_data: dict) -> dict | None:
    """
    按稀有度权重从卡池中挑选一张牌。
    - 先按稀有度权重抽档位（支持 default / custom 两种模式）
    - 同档内对近期出过的牌静默降权，降低重复概率
    """
    if not cards_config:
        return None

    func_cfg = (config or {}).get("func_cards_settings", {})
    mode = str(func_cfg.get("rarity_mode", "default")).strip().lower()

    if mode == "custom":
        raw_weights = func_cfg.get("custom_rarity_weights", {})
        weights = {}
        for r in range(1, 6):
            key = f"rarity_{r}"
            val = raw_weights.get(key, _DEFAULT_RARITY_WEIGHTS.get(r, 0))
            try:
                weights[r] = max(0, int(val))
            except (TypeError, ValueError):
                weights[r] = _DEFAULT_RARITY_WEIGHTS.get(r, 0)
    else:
        weights = dict(_DEFAULT_RARITY_WEIGHTS)

    # 只保留卡池里实际存在的稀有度档位
    available_rarities = {c.get("rarity", 1) for c in cards_config}
    weights = {r: w for r, w in weights.items() if r in available_rarities and w > 0}

    if not weights:
        return random.choice(cards_config)

    # 按权重随机抽稀有度
    rarity_list = list(weights.keys())
    weight_list = [weights[r] for r in rarity_list]
    target_rarity = random.choices(rarity_list, weights=weight_list, k=1)[0]

    pool = [c for c in cards_config if c.get("rarity", 1) == target_rarity]
    # 同档降级兜底
    if not pool:
        for fallback in sorted(weights.keys(), reverse=True):
            pool = [c for c in cards_config if c.get("rarity", 1) == fallback]
            if pool:
                break
    if not pool:
        pool = cards_config

    # 同档去重：若配置开启，对近期出过的牌静默降权
    enable_dedup = bool(func_cfg.get("enable_rarity_dedup", True))
    if enable_dedup:
        recent = user_data.get("recent_drawn_cards", [])[-_DEDUP_WINDOW:]
        recent_names = set(recent)
        card_weights = [_DEDUP_PENALTY if c.get("card_name") in recent_names else 1.0 for c in pool]
        return random.choices(pool, weights=card_weights, k=1)[0]
    else:
        return random.choice(pool)


def _get_public_duel_settings(config: dict | None) -> dict:
    func_cfg = (config or {}).get("func_cards_settings", {})
    enabled = bool(func_cfg.get("enable_public_duel_mode", func_cfg.get("enable_pure_dice_mode", False)))
    daily_limit = int(func_cfg.get("public_duel_daily_limit", func_cfg.get("pure_dice_daily_limit", 3)) or 3)
    min_stake = max(1, int(func_cfg.get("public_duel_min_stake", 10) or 10))
    max_stake = max(min_stake, int(func_cfg.get("public_duel_max_stake", 200) or 200))
    return {
        "enabled": enabled,
        "daily_limit": daily_limit,
        "min_stake": min_stake,
        "max_stake": max_stake,
    }


def _reset_pending_duel():
    PENDING_DUEL.update({
        "active": False,
        "group_id": "",
        "session_id": "",
        "challenger_uid": "",
        "challenger_name": "",
        "target_uid": "",
        "target_name": "",
        "card_name": "",
        "stake": 0,
        "min_stake": 0,
        "max_stake": 0,
        "source_kind": "",
        "phase": "",
        "confirmed": False,
        "response_action": "",
        "response_stake": 0,
        "confirm_event": None,
        "created_at": 0,
        "expire_at": 0,
    })


def _extract_duel_stake(raw_text: str) -> int | None:
    text_wo_at = re.sub(r"@\S+", "", raw_text).strip()
    match = re.search(r"(-?\d+)\s*$", text_wo_at)
    return int(match.group(1)) if match else None


def _extract_group_id_from_event(event: AstrMessageEvent) -> str:
    candidates = []

    for attr in ("get_group_id", "get_chat_id"):
        getter = getattr(event, attr, None)
        if callable(getter):
            try:
                value = getter()
                if value:
                    candidates.append(value)
            except Exception:
                pass

    for attr in ("group_id", "chat_id", "session_id"):
        value = getattr(event, attr, None)
        if value:
            candidates.append(value)

    message_obj = getattr(event, "message_obj", None)
    if message_obj is not None:
        for attr in ("group_id", "group_openid", "peer_id"):
            value = getattr(message_obj, attr, None)
            if value:
                candidates.append(value)

    session = getattr(event, "session", None)
    if session is not None:
        for attr in ("group_id",):
            value = getattr(session, attr, None)
            if value:
                candidates.append(value)

    for value in candidates:
        text = str(value).strip()
        if not text:
            continue
        if text.isdigit():
            return text
        match = re.search(r"(\d{5,})", text)
        if match:
            return match.group(1)

    return ""


async def _has_enough_gold(bank, user_id: str, user_name: str, stake: int) -> bool:
    user_data = await bank.get_user_data(user_id, user_name)
    return int(user_data.get("total_gold", 0)) >= int(stake)


def _format_aoe_chain(user_id: str, user_name: str, card_name: str, aoe_events: list, aoe_kind: str, karma_report: str, slot_len: int):
    action_line = {
        "heal": "🌿 范围援护落下，受益名单：",
        "cleanse": "✨ 范围净化扩散，影响名单：",
        "damage": "🏹 范围轰炸命中，受创名单：",
    }.get(aoe_kind, "🏹 范围轰炸命中，受创名单：")
    components = [Plain(f"⚡ {user_name} 打出了 [{card_name}]！\n━━━━━━━━\n{action_line}")]

    if not aoe_events:
        components.append(Plain("无人被波及。"))
    else:
        for idx, aoe_event in enumerate(aoe_events):
            if idx > 0:
                components.append(Plain("、"))

            target_uid_evt = str(aoe_event.get("target_uid", ""))
            target_name_evt = aoe_event.get("target_name", f"群友({target_uid_evt})")
            if target_uid_evt == str(user_id):
                components.append(Plain(f"{target_name_evt}(自己)"))
            elif target_uid_evt.isdigit():
                components.append(At(qq=int(target_uid_evt)))
                components.append(Plain(target_name_evt))
            else:
                components.append(Plain(target_name_evt))

            amount = int(aoe_event.get("amount", 0))
            blocked = bool(aoe_event.get("blocked", False))
            if aoe_kind == "heal":
                components.append(Plain(f"（+{amount}）"))
            elif aoe_kind == "cleanse":
                removed_status = aoe_event.get("removed_status", "")
                components.append(Plain(f"（净化 {removed_status}）" if removed_status else "（无负面可净化）"))
            elif blocked:
                components.append(Plain("（🛡️护盾挡下）"))
            else:
                components.append(Plain(f"（-{amount}）"))

    tail = f"\n{karma_report}" if karma_report else ""
    tail += f"\n🎴 当前卡槽：{slot_len}/3"
    components.append(Plain(tail))
    return components



def _build_karma_title_report(user_data: dict, config: dict | None = None) -> str:
    sync_events = TitleEngine.sync_titles(user_data, config)
    lines = TitleEngine.format_title_event_lines(sync_events, config)
    return "".join(f"\n{line}" for line in lines)


def _sync_expired_defense_cards(user_data: dict, config: dict | None = None) -> bool:
    inventory = user_data.get("inventory", [])
    if not inventory:
        return False

        cards_config = load_func_cards_config(config)
    status_names = {str(st.get("name", "")) for st in user_data.get("statuses", [])}
    changed = False

    for card in inventory:
        if card.get("is_broken", False) or not card.get("is_active", False):
            continue



        card_name = card.get("card_name", "")
        card_cfg = next((c for c in cards_config if c.get("card_name") == card_name), None)

        if not card_cfg or card_cfg.get("type") != "defense":
            continue


        required_statuses = []
        for tag in card_cfg.get("tags", []):

            if tag == "add_shield":
                required_statuses.append("无懈可击")
            elif tag.startswith("thorn_armor:"):
                required_statuses.append("反甲")

        if required_statuses and not any(name in status_names for name in required_statuses):
            card["is_active"] = False
            card["is_broken"] = True
            card["broken_reason"] = "状态到期"
            changed = True




    return changed






def _roll_duel_side(dice_engine: DiceEngine, user_data: dict, player_name: str) -> dict:
    roll_ret = dice_engine.roll(count=1, sides=6)
    first_total = int(roll_ret.get("final_total", 0))
    final_total = first_total
    reroll_triggered = False
    reroll_text = ""

    if _consume_lowest_reroll_status(user_data, first_total):
        reroll_triggered = True
        reroll_ret = dice_engine.roll(count=1, sides=6)
        final_total = int(reroll_ret.get("final_total", 0))
        reroll_text = f"🍀 {player_name} 触发【天命重投】！最低点作废，重投后翻出 {final_total} 点！"

    return {
        "first_total": first_total,
        "final_total": final_total,
        "reroll_triggered": reroll_triggered,
        "reroll_text": reroll_text,
    }


async def _resolve_public_duel_result(bank, session: dict, config: dict) -> dict:
    challenger_uid = session["challenger_uid"]
    target_uid = session["target_uid"]
    challenger_name = session["challenger_name"]
    target_name = session["target_name"]
    stake = int(session.get("stake", 0))

    challenger_data = await bank.get_user_data(challenger_uid, challenger_name)
    target_data = await bank.get_user_data(target_uid, target_name)

    dice_engine = DiceEngine()
    challenger_roll = _roll_duel_side(dice_engine, challenger_data, challenger_name)
    target_roll = _roll_duel_side(dice_engine, target_data, target_name)

    c_final = int(challenger_roll["final_total"])
    t_final = int(target_roll["final_total"])

    if c_final > t_final:
        transfer = min(stake, max(0, target_data.get("total_gold", 0)))
        target_data["total_gold"] -= transfer
        c_bonus_pct = int(TitleEngine.calculate_effects(challenger_data, config).get("duel_stake_bonus", 0) or 0)
        bonus_gold = int(transfer * c_bonus_pct / 100) if c_bonus_pct > 0 else 0
        challenger_data["total_gold"] += (transfer + bonus_gold)
        bonus_msg = f"（含称号加成 +{bonus_gold}）" if bonus_gold > 0 else ""
        result_line = f"🏆 {challenger_name} 一把掀翻赌桌，卷走 {transfer}{bonus_msg} 金币！"
        winner_uid = challenger_uid
        loser_uid = target_uid
    elif t_final > c_final:
        transfer = min(stake, max(0, challenger_data.get("total_gold", 0)))
        challenger_data["total_gold"] -= transfer
        t_bonus_pct = int(TitleEngine.calculate_effects(target_data, config).get("duel_stake_bonus", 0) or 0)
        bonus_gold = int(transfer * t_bonus_pct / 100) if t_bonus_pct > 0 else 0
        target_data["total_gold"] += (transfer + bonus_gold)
        bonus_msg = f"（含称号加成 +{bonus_gold}）" if bonus_gold > 0 else ""
        result_line = f"🏆 {target_name} 当场反杀，反卷 {transfer}{bonus_msg} 金币！"
        winner_uid = target_uid
        loser_uid = challenger_uid
    else:
        transfer = 0
        result_line = "🤝 双方点数相同，赌桌僵住，这一局和了。"
        winner_uid = ""
        loser_uid = ""


    await bank.save_user_data()

    return {
        "challenger_roll": challenger_roll,
        "target_roll": target_roll,
        "stake": stake,
        "result_line": result_line,
        "transfer": transfer,
        "winner_uid": winner_uid,
        "loser_uid": loser_uid,
    }


async def calculate_rank(bank, user_id):
    all_users = await bank.get_all_users()
    sorted_users = sorted(all_users.items(), key=lambda x: x[1].get("total_gold", 0), reverse=True)
    for rank, (uid, _) in enumerate(sorted_users):
        if uid == user_id:
            return rank + 1
    return 999


async def _resolve_duel(bank, session: dict, is_active_accept: bool, config: dict) -> str:
    """执行一场骰子对赌并返回播报文本。"""
    challenger_uid = session["challenger_uid"]

    target_uid = session["target_uid"]
    challenger_name = session["challenger_name"]
    target_name = session["target_name"]
    stake = int(session.get("stake", 20))
    card_name = session.get("card_name", "对赌契约")

    challenger_data = await bank.get_user_data(challenger_uid, challenger_name)
    target_data = await bank.get_user_data(target_uid, target_name)

    if not is_active_accept:
        # 超时自动迎战：可被护盾拦截
        if _consume_target_shield_for_duel(target_data):
            await bank.save_user_data()
            await bank.log_battle(challenger_uid, f"使用了 [{card_name}]。结果：对方护盾触发，自动迎战阶段被拦截。")
            await bank.log_battle(target_uid, f"遭到 {challenger_name} 使用了 [{card_name}]。结果：你触发了无懈可击，成功拒绝自动迎战。")
            return (
                f"🎰【盘口播报】{target_name} 半天没接话，系统刚想替他上桌！\n"
                f"🛡️ 结果【无懈可击】当场炸开，把这口被迫应战直接拍飞。\n"
                f"💥 围观的人一阵起哄：这桌没打起来，先散场！"
            )

    dice_engine = DiceEngine()
    c_roll = dice_engine.roll(count=1, sides=6)
    t_roll = dice_engine.roll(count=1, sides=6)

    c_final = int(c_roll.get("final_total", 0))
    t_final = int(t_roll.get("final_total", 0))

    reroll_msgs = []
    if _consume_lowest_reroll_status(challenger_data, c_final):
        c_roll = dice_engine.roll(count=1, sides=6)
        c_final = int(c_roll.get("final_total", 0))
        reroll_msgs.append(f"🍀 {challenger_name} 触发【天命重投】！重投后点数：{c_final}")

    if _consume_lowest_reroll_status(target_data, t_final):
        t_roll = dice_engine.roll(count=1, sides=6)
        t_final = int(t_roll.get("final_total", 0))
        reroll_msgs.append(f"🍀 {target_name} 触发【天命重投】！重投后点数：{t_final}")

    # 结算：平局不转移；纯水局（stake<=0）只播报胜负
        result_line = ""
    if c_final > t_final:
        if stake <= 0:
            result_line = f"🏆 {challenger_name} 胜出！"
        else:
            transfer = min(stake, max(0, target_data.get("total_gold", 0)))
            target_data["total_gold"] -= transfer
            c_bonus_pct = int(TitleEngine.calculate_effects(challenger_data, config).get("duel_stake_bonus", 0) or 0)
            bonus_gold = int(transfer * c_bonus_pct / 100) if c_bonus_pct > 0 else 0
            challenger_data["total_gold"] += (transfer + bonus_gold)
            bonus_msg = f"（含加成+{bonus_gold}）" if bonus_gold > 0 else ""
            result_line = f"🏆 {challenger_name} 胜出，卷走 {transfer}{bonus_msg} 金币！"
    elif t_final > c_final:
        if stake <= 0:
            result_line = f"🏆 {target_name} 反杀成功！"
        else:
            transfer = min(stake, max(0, challenger_data.get("total_gold", 0)))
            challenger_data["total_gold"] -= transfer
            t_bonus_pct = int(TitleEngine.calculate_effects(target_data, config).get("duel_stake_bonus", 0) or 0)
            bonus_gold = int(transfer * t_bonus_pct / 100) if t_bonus_pct > 0 else 0
            target_data["total_gold"] += (transfer + bonus_gold)
            bonus_msg = f"（含加成+{bonus_gold}）" if bonus_gold > 0 else ""
            result_line = f"🏆 {target_name} 反杀成功，反卷 {transfer}{bonus_msg} 金币！"
    else:
        result_line = "🤝 双方点数相同，本局和局。"


    await bank.save_user_data()

    mode_text = "主动应战（防御失效）" if is_active_accept else "超时自动迎战（可被防御）"
    lines = [
        f"🎰【赌场播报】{challenger_name} vs {target_name}",
        f"🧾 对局模式：{mode_text}",
        f"🎲 {challenger_name} 掷出：{c_final} | {target_name} 掷出：{t_final}",
    ]
    lines.extend(reroll_msgs)
    lines.append(result_line)

    report = "\n".join(lines)
    await bank.log_battle(challenger_uid, f"使用了 [{card_name}]。结果：{report}")
    await bank.log_battle(target_uid, f"遭到 {challenger_name} 使用了 [{card_name}]。结果：{report}")
    return report


async def handle_confirm_duel(event: AstrMessageEvent, bank):
    user_id = event.get_sender_id()
    group_id = _extract_group_id_from_event(event)

    async with PENDING_DUEL_LOCK:
        if not PENDING_DUEL.get("active") or (group_id and str(PENDING_DUEL.get("group_id", "")) != group_id):
            yield event.plain_result("🎲 当前没有待确认的对赌局。")
            return

        phase = PENDING_DUEL.get("phase")
        source_kind = PENDING_DUEL.get("source_kind")
        challenger_uid = PENDING_DUEL.get("challenger_uid")
        challenger_name = PENDING_DUEL.get("challenger_name")
        target_uid = PENDING_DUEL.get("target_uid")
        target_name = PENDING_DUEL.get("target_name")
        stake = int(PENDING_DUEL.get("stake", 0))

        if phase == "await_target":
            if user_id != target_uid:
                yield event.plain_result("⚠️ 现在轮到被挑战者表态，旁人别替人上头。")
                return

            if not await _has_enough_gold(bank, challenger_uid, challenger_name, stake):
                yield event.plain_result(f"⚠️ 发起者 {challenger_name} 当前金币不足 {stake}，这桌赌注开不起来。")
                return
            if not await _has_enough_gold(bank, target_uid, target_name, stake):
                yield event.plain_result(f"⚠️ {target_name} 当前金币不足 {stake}，接不起这口锅。")
                return

            PENDING_DUEL["confirmed"] = True
            PENDING_DUEL["response_action"] = "accept"
            PENDING_DUEL["response_stake"] = stake
            confirm_event = PENDING_DUEL.get("confirm_event")
            if confirm_event:
                confirm_event.set()

            if source_kind == "free":
                msg = (
                    f"🔥【盘口播报】{target_name} 直接拍板接战！\n"
                    f"💰 当前赌注锁定：{stake} 金币\n"
                    f"📢 周围已经有人开始起哄，这局马上开摇！"
                )
            else:
                msg = f"🔥【盘口播报】{target_name} 点头应战！\n人都围上来了，骰子马上落桌。"
        elif phase == "await_challenger_raise_confirm":
            if user_id != challenger_uid:
                yield event.plain_result("⚠️ 现在轮到发起者决定接不接这口加注。")
                return

            if not await _has_enough_gold(bank, challenger_uid, challenger_name, stake):
                yield event.plain_result(f"⚠️ 你的金币不足 {stake}，接不起对方抬到天上的赌注。")
                return
            if not await _has_enough_gold(bank, target_uid, target_name, stake):
                yield event.plain_result(f"⚠️ {target_name} 当前金币不足 {stake}，加注后的赌桌已失效。")
                return

            PENDING_DUEL["confirmed"] = True
            PENDING_DUEL["response_action"] = "accept_raised"
            PENDING_DUEL["response_stake"] = stake
            confirm_event = PENDING_DUEL.get("confirm_event")
            if confirm_event:
                confirm_event.set()
            msg = (
                f"🔥【盘口播报】{challenger_name} 一把把筹码推回场中央！\n"
                f"💰 双方确认加注后赌注：{stake} 金币\n"
                f"📢 场子已经彻底热起来了，谁手抖谁就等着被全场笑。"
            )
        else:
            yield event.plain_result("🎲 这桌赌局当前不在确认阶段。")
            return

    yield event.plain_result(msg)


async def handle_raise_duel(event: AstrMessageEvent, bank):
    user_id = event.get_sender_id()
    group_id = _extract_group_id_from_event(event)
    raw_text = event.message_str.replace("/luck", "").strip()
    match = re.search(r"加注\s*(-?\d+)", raw_text)
    if not match:
        yield event.plain_result("⚠️ 加注格式：/luck 加注 金额")
        return

    raise_stake = int(match.group(1))

    async with PENDING_DUEL_LOCK:
        if not PENDING_DUEL.get("active") or (group_id and str(PENDING_DUEL.get("group_id", "")) != group_id):
            yield event.plain_result("🎲 当前没有可加注的对赌局。")
            return

        if PENDING_DUEL.get("source_kind") != "free":
            yield event.plain_result("⚠️ 只有日常公开对赌支持手动加注。")
            return

        if PENDING_DUEL.get("phase") != "await_target":
            yield event.plain_result("⚠️ 这桌赌局当前不能加注。")
            return

        target_uid = PENDING_DUEL.get("target_uid")
        target_name = PENDING_DUEL.get("target_name")
        challenger_uid = PENDING_DUEL.get("challenger_uid")
        challenger_name = PENDING_DUEL.get("challenger_name")
        current_stake = int(PENDING_DUEL.get("stake", 0))
        max_stake = int(PENDING_DUEL.get("max_stake", 0))
        min_stake = int(PENDING_DUEL.get("min_stake", 1))

        if user_id != target_uid:
            yield event.plain_result("⚠️ 只有被挑战者可以在应战阶段抬注。")
            return
        if raise_stake <= current_stake:
            yield event.plain_result(f"⚠️ 加注金额必须大于当前赌注 {current_stake}。")
            return
        if raise_stake < min_stake or raise_stake > max_stake:
            yield event.plain_result(f"⚠️ 赌注必须位于 {min_stake} ~ {max_stake} 金币之间。")
            return
        if not await _has_enough_gold(bank, target_uid, target_name, raise_stake):
            yield event.plain_result(f"⚠️ 你的金币不足 {raise_stake}，别空手抬价。")
            return
        if not await _has_enough_gold(bank, challenger_uid, challenger_name, raise_stake):
            yield event.plain_result(f"⚠️ {challenger_name} 当前金币不足 {raise_stake}，你这口价已经把他抬出桌外了。")
            return

        PENDING_DUEL["stake"] = raise_stake
        PENDING_DUEL["phase"] = "await_challenger_raise_confirm"
        PENDING_DUEL["confirmed"] = True
        PENDING_DUEL["response_action"] = "raise"
        PENDING_DUEL["response_stake"] = raise_stake
        confirm_event = PENDING_DUEL.get("confirm_event")
        if confirm_event:
            confirm_event.set()

    yield event.plain_result(
        f"💥【盘口播报】{target_name} 反手把赌注抬到 {raise_stake} 金币！\n"
        f"📣 场边已经叫起来了——现在轮到 {challenger_name} 发送「/luck 确认」接下这口加注。"
    )


async def handle_pure_duel(event: AstrMessageEvent, bank, config: dict):
    user_id = event.get_sender_id()
    user_name = event.get_sender_name()
    group_id = str((config or {}).get("_group_id", "")).strip()
    today = datetime.now().strftime("%Y-%m-%d")

    duel_cfg = _get_public_duel_settings(config)
    if not duel_cfg["enabled"]:
        yield event.plain_result("🎲 公开对赌模式未开启。")
        return

    user_data = await bank.get_user_data(user_id, user_name)
    daily_limit = duel_cfg["daily_limit"]
    min_stake = duel_cfg["min_stake"]
    max_stake = duel_cfg["max_stake"]

    if user_data.get("pure_dice_date") != today:
        user_data["pure_dice_date"] = today
        user_data["pure_dice_count"] = 0

    if int(user_data.get("pure_dice_count", 0)) >= daily_limit:
        yield event.plain_result(f"⛔ 你今天的公开对赌次数已用尽（{daily_limit}/{daily_limit}）。")
        return

    target_id = None
    for comp in event.get_messages():
        if isinstance(comp, At):
            target_id = str(comp.qq)
            break

    if not target_id:
        yield event.plain_result("⚠️ 公开对赌必须 @ 一名目标。示例：/luck 对赌 @某人 50")
        return

    if target_id == user_id:
        yield event.plain_result("⚠️ 不能和自己对赌。")
        return

    raw_text = event.message_str.replace("/luck", "").strip()
    if not raw_text.startswith("对赌"):
        yield event.plain_result("⚠️ 对赌格式：/luck 对赌@某人 金额")
        return

    stake = _extract_duel_stake(raw_text)
    if stake is None:
        stake = min_stake
    if stake < min_stake or stake > max_stake:
        yield event.plain_result(f"⚠️ 赌注必须位于 {min_stake} ~ {max_stake} 金币之间。")
        return
    if not await _has_enough_gold(bank, user_id, user_name, stake):
        yield event.plain_result(f"⚠️ 你的金币不足 {stake}，没资格拍这桌。")
        return

    all_users = await bank.get_all_users()
    target_name = all_users.get(target_id, {}).get("name", f"群友({target_id})")

    async with PENDING_DUEL_LOCK:
        if PENDING_DUEL.get("active") and str(PENDING_DUEL.get("group_id", "")) == group_id:
            yield event.plain_result("🎰 当前已有对局进行中，请稍候再开盘。")
            return

        confirm_event = asyncio.Event()
        PENDING_DUEL.update({
            "active": True,
            "group_id": group_id,
            "session_id": f"duel:{group_id}:{user_id}:{target_id}:{int(time.time())}",
            "challenger_uid": user_id,
            "challenger_name": user_name,
            "target_uid": target_id,
            "target_name": target_name,
            "card_name": "公开对赌",
            "stake": stake,
            "min_stake": min_stake,
            "max_stake": max_stake,
            "source_kind": "free",
            "phase": "await_target",
            "confirmed": False,
            "response_action": "",
            "response_stake": stake,
            "confirm_event": confirm_event,
            "created_at": int(time.time()),
            "expire_at": int(time.time()) + DUEL_CONFIRM_WINDOW_SEC,
        })

    yield event.plain_result(
        f"🎰【盘口播报】{user_name} 把 {stake} 金币往场中央一甩，点名要和 {target_name} 见真章！\n"
        f"📣 请 {target_name} 在 60 秒内发送「/luck 确认」接战，或发送「/luck 加注 金额」把场面继续抬高。\n"
        f"💰 本桌限额：{min_stake} ~ {max_stake} 金币\n"
        f"👀 这局不代打，得双方亲自点头，围观的人可都等着看呢。"
    )

    try:
        await asyncio.wait_for(confirm_event.wait(), timeout=DUEL_CONFIRM_WINDOW_SEC)
    except asyncio.TimeoutError:
        async with PENDING_DUEL_LOCK:
            if PENDING_DUEL.get("session_id"):
                _reset_pending_duel()
        yield event.plain_result("⌛ 60 秒过去，场边都快喊累了，还是没人接话。这局只能散了。")
        return

    async with PENDING_DUEL_LOCK:
        response_action = PENDING_DUEL.get("response_action")
        current_stake = int(PENDING_DUEL.get("stake", stake))

        if response_action == "raise":
            confirm_event = asyncio.Event()
            PENDING_DUEL["phase"] = "await_challenger_raise_confirm"
            PENDING_DUEL["confirmed"] = False
            PENDING_DUEL["response_action"] = ""
            PENDING_DUEL["confirm_event"] = confirm_event
            PENDING_DUEL["expire_at"] = int(time.time()) + DUEL_CONFIRM_WINDOW_SEC
        elif response_action == "accept":
            session = dict(PENDING_DUEL)
            _reset_pending_duel()
            confirm_event = None
        else:
            session = None
            confirm_event = None

    if response_action == "raise":
        yield event.plain_result(
            f"😈【盘口播报】赌注已经被抬到 {current_stake} 金币！\n"
            f"📣 现在全场都盯着 {user_name} —— 60 秒内发送「/luck 确认」，接不接就这一句。"
        )
        try:
            await asyncio.wait_for(confirm_event.wait(), timeout=DUEL_CONFIRM_WINDOW_SEC)
        except asyncio.TimeoutError:
            async with PENDING_DUEL_LOCK:
                if PENDING_DUEL.get("session_id"):
                    _reset_pending_duel()
            yield event.plain_result("⌛ 发起者迟迟没回话，围观的人先哄起来了。这口加注没人接，本局作废。")
            return

        async with PENDING_DUEL_LOCK:
            session = dict(PENDING_DUEL)
            _reset_pending_duel()

    if not session:
        yield event.plain_result("⚠️ 场子状态有点乱，这局没能顺利立起来。")
        return

    user_data["pure_dice_count"] = int(user_data.get("pure_dice_count", 0)) + 1
    await bank.save_user_data()
    remain = max(0, daily_limit - int(user_data.get("pure_dice_count", 0)))

    duel_result = await _resolve_public_duel_result(bank, session, config)


    challenger_name = session["challenger_name"]
    target_name = session["target_name"]
    stake = duel_result["stake"]

    yield event.plain_result(
        f"🎲【盘口播报】赌局锁死！\n"
        f"{challenger_name} 与 {target_name} 各自按住 {stake} 金币，场边已经开始猜谁会先翻车。"
    )
    await asyncio.sleep(DUEL_STAGE_DELAY_SEC)

    challenger_roll = duel_result["challenger_roll"]
    first_line = f"🎯 第一掷先开——{challenger_name} 抢先出手，骰子转了几圈，最后定在 {challenger_roll['first_total']} 点！"
    if challenger_roll["reroll_triggered"]:
        first_line += f"\n{challenger_roll['reroll_text']}"
    yield event.plain_result(first_line)
    await asyncio.sleep(DUEL_STAGE_DELAY_SEC)

    target_roll = duel_result["target_roll"]
    second_line = f"🎯 第二掷跟上——轮到 {target_name} 接招，骰子一落，直接翻出 {target_roll['first_total']} 点！"
    if target_roll["reroll_triggered"]:
        second_line += f"\n{target_roll['reroll_text']}"
    yield event.plain_result(second_line)
    await asyncio.sleep(DUEL_STAGE_DELAY_SEC)

    final_report = (
        f"💥【盘口终局】\n"
        f"🎲 最终点数：{challenger_name} {challenger_roll['final_total']} vs {target_name} {target_roll['final_total']}\n"
        f"{duel_result['result_line']}\n"
        f"📣 场边已经吵成一片。\n"
        f"🎟️ {challenger_name} 今日公开对赌剩余次数：{remain}"
    )

    await bank.log_battle(session["challenger_uid"], f"发起了与 {target_name} 的公开对赌，赌注 {stake}。结果：{duel_result['result_line']}")
    await bank.log_battle(session["target_uid"], f"应战了 {challenger_name} 的公开对赌，赌注 {stake}。结果：{duel_result['result_line']}")
    yield event.plain_result(final_report)


# ================= 🏆 善恶排行榜逻辑 =================
async def handle_karma_leaderboard(event: AstrMessageEvent, bank, board_length: int = 10):
    all_users = await bank.get_all_users()
    valid_users = {uid: data for uid, data in all_users.items() if data.get("karma_value", 0) != 0}

    if not valid_users:
        yield event.plain_result("⚖️ 【天道善恶榜】\n当前异世界一片祥和，暂无行善或积恶之人上榜。")
        return

    sorted_users = sorted(valid_users.items(), key=lambda x: x[1].get("karma_value", 0), reverse=True)
    lines = ["⚖️ 【天道善恶榜】", "━━━━━━━━━━━━━━"]

    for i, (uid, data) in enumerate(sorted_users[:board_length]):
        name = data.get("name", f"群友({uid})")
        karma = data.get("karma_value", 0)
        tag = "👼 善" if karma > 0 else "💀 恶"
        # 显示善恶称号标记
        title_tag = ""
        titles = data.get("titles", [])
        if "行善之人" in titles:
            title_tag = " [行善之人]"
        elif "邪恶之人" in titles:
            title_tag = " [邪恶之人]"
        lines.append(f"{i+1}. {name}{title_tag} | 业报: {karma} {tag}")

    lines.append("━━━━━━━━━━━━━━")
    lines.append("💡 施放治疗法术积攒善意，发起攻击累积罪恶。")
    lines.append("🏅 善值≥5 获得【行善之人】称号，恶值≤-5 获得【邪恶之人】称号。")
    yield event.plain_result("\n".join(lines))


# ================= 🎴 核心功能卡牌逻辑 =================
async def handle_panel(event: AstrMessageEvent, bank, config: dict, target_id: str | None = None, target_name: str | None = None):
    viewer_id = event.get_sender_id()
    viewer_name = event.get_sender_name()

    user_id = target_id or viewer_id
    user_name = target_name or viewer_name

    user_data = await bank.get_user_data(user_id, user_name)
    rank = await calculate_rank(bank, user_id)

    panel_title = config.get("ui_settings", {}).get("panel_title", "【个人状态观测仪】")

    gold = user_data.get("total_gold", 0)
    karma = user_data.get("karma_value", 0)
    karma_str = f"+{karma} (善)" if karma > 0 else f"{karma} (恶)" if karma < 0 else "0 (中立)"

    lines = [
        f"📊 {panel_title}",
        f"👤 观测对象：{user_name}",
        f"💰 金币总量：{gold} (位阶：第 {rank} 位)",
        f"⚖️ 善恶业报：{karma_str}"
    ]

    titles = user_data.get("titles", [])
    equipped_titles = set(TitleEngine.get_equipped_titles(user_data, config))
    max_titles = TitleEngine.get_max_equipped_titles(config)
    if not titles:
        lines.append("🏅 当前称号：无名之辈")
    else:
        lines.append(f"🏅 【称号】 已佩戴 {len(equipped_titles)}/{max_titles} · 共拥有 {len(titles)}")
        for t in titles:
            t_info = TitleEngine.get_title_info(t, config)
            state = "🟢" if t in equipped_titles else "⚪"
            lines.append(f"  {state} {t_info['name']} - {_format_title_effect_desc(t, config)}")




            

            
    lines.append("━━━━━━━━━━━━━━")
    lines.append("🎭 【异界干涉状态】")
    statuses = user_data.get("statuses", [])
    now = int(time.time())
    valid_statuses = []
    for st in statuses:
        if "expire_time" in st:
            if now < st["expire_time"]:
                rem_sec = st["expire_time"] - now
                h, r = divmod(rem_sec, 3600)
                m, _ = divmod(r, 60)
                desc = f"剩余 {h}小时{m}分自动解封"
                lines.append(f"  ▪️ [{st.get('name')}] - {desc}")
                valid_statuses.append(st)
        else:
            lines.append(f"  ▪️ [{st.get('name', '未知')}] - {st.get('desc', '')}")
            valid_statuses.append(st)
            
            
    if len(valid_statuses) != len(statuses):
        user_data["statuses"] = valid_statuses
        await bank.save_user_data()


    if _sync_expired_defense_cards(user_data, config):
        await bank.save_user_data()

    if not valid_statuses:


        lines.append("  🎐 当前周身清明，无任何异样状态。")
    lines.append("━━━━━━━━━━━━━━")
    lines.append("🎲 【骰局状态】")
    now_ts = int(time.time())
    dice_status_lines = []
    for st in valid_statuses:
        name = str(st.get("name", ""))
        is_dice_state = (
            name in {"天命重投", "职业骰"}
            or any(k in st for k in ["dice_count_mod", "dice_sides_mod", "dice_total_mod", "dice_min_floor_mod", "dice_max_cap_mod"])
        )
        if not is_dice_state:
            continue

        desc_parts = []
        if name == "天命重投":
            desc_parts.append("下次掷到最低点时自动重投1次")
        if st.get("dice_count_mod"):
            desc_parts.append(f"骰子数量{int(st.get('dice_count_mod')):+d}")
        if st.get("dice_sides_mod"):
            desc_parts.append(f"骰子面数{int(st.get('dice_sides_mod')):+d}")
        if st.get("dice_total_mod"):
            desc_parts.append(f"总点修正{int(st.get('dice_total_mod')):+d}")
        if st.get("dice_min_floor_mod"):
            desc_parts.append(f"最小值+{int(st.get('dice_min_floor_mod'))}")
        if st.get("dice_max_cap_mod"):
            desc_parts.append(f"最大值+{int(st.get('dice_max_cap_mod'))}")

        if st.get("expire_time") and int(st.get("expire_time", 0)) > now_ts:
            rem_sec = int(st.get("expire_time", 0)) - now_ts
            h, r = divmod(rem_sec, 3600)
            m, _ = divmod(r, 60)
            desc_parts.append(f"剩余 {h}小时{m}分")

        desc = "，".join(desc_parts) if desc_parts else st.get("desc", "骰子规则生效中")
        dice_status_lines.append(f"  ▪️ [{name}] - {desc}")

    if not dice_status_lines:
        lines.append("  🎲 当前无骰局加成状态。")
    else:
        lines.extend(dice_status_lines)

        lines.append("━━━━━━━━━━━━━━")
    inventory = user_data.get("inventory", [])
    slot_count = len(inventory)
    lines.append(f"🎴 【战术卡槽】 ({slot_count}/3)")
    for i in range(3):
        if i < slot_count:
            card = inventory[i]
            card_name = card.get("card_name", "未知卡牌")

            # 💡 战损系统面板渲染
            if card.get("is_broken", False):
                reason = str(card.get("broken_reason", "") or "").strip()
                status_tag = f" (💔已销毁：{reason})" if reason else " (💔已销毁)"
            else:
                status_tag = " (🛡️已启用)" if card.get("is_active", False) else ""

            lines.append(f"  {i+1}. [{card_name}]{status_tag}")
        else:
            lines.append(f"  {i+1}. [空]")


    lines.append("━━━━━━━━━━━━━━")
    lines.append("📜 【近期恩怨纪事（最近3天）】")
    battle_logs = user_data.get("battle_logs", [])
    if not battle_logs:
        lines.append("  🎐 近期风和日丽，无事发生。")
    else:
        for log in battle_logs:
            lines.append(f"  {log}")

    yield event.plain_result("\n".join(lines))

async def handle_draw_func_card(event: AstrMessageEvent, bank, config: dict):
    user_id = event.get_sender_id()
    user_name = event.get_sender_name()
    today = datetime.now().strftime("%Y-%m-%d")

    user_data = await bank.get_user_data(user_id, user_name)
    TitleEngine.ensure_user_title_fields(user_data)

    blocked_by = find_gate_block(user_data, GATE_DRAW_FUNC_CARD)
    if blocked_by:
        msg = format_gate_block_message(
            blocked_by,
            "⚠️ 你的当前状态禁止抽取功能牌，请稍后再试。"
        )
        yield event.plain_result(msg)
        return
        cards_config = load_func_cards_config(config)
        if not cards_config:
            yield event.plain_result("⚠️ 功能牌卡池为空或配置无效，请检查功能牌池数据。")
            return


    eco_cfg = config.get("func_cards_settings", {}).get("economy_settings", {})
    draw_cost = int(eco_cfg.get("draw_cost", 20) or 20)
    free_daily = int(eco_cfg.get("free_daily_draw", 1) or 1)
    base_prob = int(eco_cfg.get("draw_probability", 5) or 5)
    pity_threshold = int(eco_cfg.get("pity_threshold", 10) or 10)

    title_effects = TitleEngine.calculate_effects(user_data, config)
    free_daily += int(title_effects.get("free_draw_bonus", 0) or 0)
    draw_cost = max(0, draw_cost - int(title_effects.get("draw_cost_discount", 0) or 0))
    pity_threshold = max(1, pity_threshold - int(title_effects.get("pity_threshold_mod", 0) or 0))

    if user_data.get("last_func_draw_date") != today:
        user_data["last_func_draw_date"] = today
        user_data["today_free_draws"] = free_daily
        user_data["today_paid_draws"] = 0

    inventory = user_data.get("inventory", [])
    if len(inventory) >= 3:
        yield event.plain_result("⚠️ 你的战术卡槽已满 (3/3)！请先使用或发送「/luck 丢弃 [卡名]」腾出空间。")
        return

    is_free = False
    if int(user_data.get("today_free_draws", 0) or 0) > 0:
        user_data["today_free_draws"] -= 1
        is_free = True
    else:
        if int(user_data.get("today_paid_draws", 0) or 0) >= 1:
            yield event.plain_result("⚠️ 天道法则限制：每天最多只能进行 1 次额外付费抽取。")
            return
        success = await bank.change_gold(user_id, -draw_cost)
        if not success:
            yield event.plain_result(f"📉 金币不足或已坠入深渊！每次额外抽取需要 {draw_cost} 金币。")
            return
        user_data["today_paid_draws"] = int(user_data.get("today_paid_draws", 0) or 0) + 1

    luck_val = int(user_data.get("today_luck_value", 50) or 50)
    luck_mod = 0
    if 51 <= luck_val <= 70:
        luck_mod = 2
    elif 71 <= luck_val <= 90:
        luck_mod = 5
    elif 91 <= luck_val <= 100:
        luck_mod = 10

    title_mod = TitleEngine.calculate_total_bonus_prob(user_data, config)

    now_ts = int(time.time())
    status_prob_mod = 0
    for st in user_data.get("statuses", []):
        if st.get("expire_time") and st.get("expire_time", 0) <= now_ts:
            continue
        status_prob_mod += int(st.get("func_draw_prob_mod", 0) or 0)

    final_prob = max(0, min(100, base_prob + luck_mod + title_mod + status_prob_mod))
    current_pity = int(user_data.get("func_card_pity_count", 0) or 0)
    roll = random.randint(1, 100)

    is_hit = False
    if current_pity + 1 >= pity_threshold:
        is_hit = True
        hit_reason = "【深渊同情·保底触发】"
    elif roll <= final_prob:
        is_hit = True
        hit_reason = f"【星象共鸣·出金率 {final_prob}% 触发！】"

    if not is_hit:
        user_data["func_card_pity_count"] = current_pity + 1
        await bank.save_user_data()
        cost_str = f"消耗：免费抽取次数（下次 {draw_cost} 金币）" if is_free else f"消耗：{draw_cost} 金币"
        yield event.plain_result(
            f"💨 法阵闪烁了一瞬，随后化为乌有...\n━━━━━━━━\n{cost_str}\n📈 祈愿保底进度：{user_data['func_card_pity_count']}/{pity_threshold}\n💡 当前你的出金率为：{final_prob}% (基础{base_prob}% +运势{luck_mod}% +称号{title_mod}% +状态{status_prob_mod}%)"
        )
        return

    user_data["func_card_pity_count"] = 0
    rarity_map = {1: "⚪ 普通", 2: "🔵 稀有", 3: "🟣 史诗", 4: "🟡 传说", 5: "🔴 神话"}

    card = _pick_func_card(cards_config, config, user_data)
    if not card:
        yield event.plain_result("⚠️ 功能牌卡池为空，无法完成抽取。")
        return

    actual_rarity_str = rarity_map.get(card.get("rarity", 1), "⚪ 普通")
    user_data.setdefault("inventory", []).append({
        "card_name": card["card_name"],
        "is_active": False,
        "is_broken": False,
        "broken_reason": "",
    })


    user_data["total_func_cards_drawn"] = int(user_data.get("total_func_cards_drawn", 0) or 0) + 1

    recent = user_data.setdefault("recent_drawn_cards", [])
    recent.append(card["card_name"])
    if len(recent) > _DEDUP_WINDOW:
        user_data["recent_drawn_cards"] = recent[-_DEDUP_WINDOW:]

    draw_events = TitleEngine.sync_titles(user_data, config)
    await bank.save_user_data()

    cost_str = f"消耗：免费抽取次数（下次 {draw_cost} 金币）" if is_free else f"消耗：{draw_cost} 金币"
    text = card.get("description", "一张神秘的战术卡")
    title_hint = ""
    if draw_events:
        title_hint = "\n" + "\n".join(TitleEngine.format_title_event_lines(draw_events, config))
    res_text = f"✨ {hit_reason}\n你从虚空中凝结出了：\n【{actual_rarity_str}】{card['card_name']}\n━━━━━━━━\n📝 {text}\n{cost_str}\n🎴 当前卡槽：{len(user_data['inventory'])}/3{title_hint}"

    img_filename = str(card.get("filename", "")).strip()
    img_path = ""
    storage_paths = (config or {}).get("_storage_paths", {})
    func_assets_dir = storage_paths.get("func_assets_dir")
    profile_img_path = os.path.join(str(func_assets_dir), img_filename) if func_assets_dir and img_filename else ""
    legacy_img_path = os.path.join(os.path.dirname(__file__), "..", "assets", "func_cards", img_filename) if img_filename else ""

    if profile_img_path and os.path.isfile(profile_img_path):
        img_path = profile_img_path
    elif legacy_img_path and os.path.isfile(legacy_img_path):
        img_path = legacy_img_path

    if img_path:
        yield event.chain_result([Image.fromFileSystem(img_path), Plain("\n" + res_text)])
    else:
        if img_filename:
            res_text += f"\n⚠️ 卡图未找到：{img_filename}（已使用纯文本展示）"
        yield event.plain_result(res_text)



async def handle_discard_card(event: AstrMessageEvent, bank, target_card_name: str):
    user_id = event.get_sender_id()
    user_name = event.get_sender_name()

    if not target_card_name:
        yield event.plain_result("⚠️ 请指定要丢弃的卡牌名。例如：/luck 丢弃 掠夺之手")
        return

    user_data = await bank.get_user_data(user_id, user_name)
    inventory = user_data.get("inventory", [])

    if not inventory:
        yield event.plain_result(f"📭 {user_name}，你的战术卡槽空空如也，无牌可丢。")
        return

        found_index = -1
    for i, card in enumerate(inventory):
        if card.get("card_name") == target_card_name:
            found_index = i
            break

    if found_index != -1:
        discarded_card = inventory.pop(found_index)
        await bank.save_user_data()


        status_note = ""
        if discarded_card.get("is_broken"):

            reason = str(discarded_card.get("broken_reason", "") or "").strip()
            status_note = f" (清理了废铁：{reason})" if reason else " (清理了废铁)"
        elif discarded_card.get("is_active"):
            status_note = " (撤销了护盾阵眼)"

        yield event.plain_result(f"🗑️ 你将 [{target_card_name}] 扔进了虚空裂缝{status_note}。\n🎴 当前卡槽：{len(inventory)}/3")
    else:

        yield event.plain_result(f"❓ 你的卡槽中并未发现名为 [{target_card_name}] 的战术牌。")

async def handle_use_card(event: AstrMessageEvent, bank, cmd_str: str, config: dict = None):
    user_id = event.get_sender_id()
    user_name = event.get_sender_name()
    today = datetime.now().strftime("%Y-%m-%d")

    raw_text = event.message_str.replace("/luck", "").strip()
    match = re.search(r"使用\s*([^\s@]+)", raw_text)
    if not match:
        yield event.plain_result("⚠️ 咒语格式错误。\n👉 举例：/luck 使用绝对零度@某人\n👉 也支持：/luck 使用 绝对零度 @某人\n👉 群攻：/luck 使用南蛮入侵")
        return
    target_card_name = match.group(1).strip()

    user_data = await bank.get_user_data(user_id, user_name)
    TitleEngine.ensure_user_title_fields(user_data)

    blocked_by = find_gate_block(user_data, GATE_USE_CARD)

    if blocked_by:
        msg = format_gate_block_message(
            blocked_by,
            "⚠️ 你的当前状态禁止使用功能牌，请稍后再试。"
        )
        yield event.plain_result(msg)
        return

    inventory = user_data.get("inventory", [])
    found_index = -1
    for i, card in enumerate(inventory):
        if card.get("card_name") == target_card_name:
            found_index = i
            break
            
    if found_index == -1:
        yield event.plain_result(f"❓ 你的卡槽中并未发现 [{target_card_name}]。")
        return
        
    # 💡 战损拦截：破烂的牌无法被使用
    if inventory[found_index].get("is_broken", False):
        yield event.plain_result(f"⚠️ 你的 [{target_card_name}] 已经彻底销毁，只剩一堆废铁，无法催动魔力！请发送「/luck 丢弃 {target_card_name}」清理卡槽。")
        return

    cards_config = load_func_cards_config(config)
    raw_cards_config = load_func_cards_config(config, include_disabled_dice=True)
    card_cfg = next((c for c in cards_config if c.get("card_name") == target_card_name), None)
    if not card_cfg:
        raw_cfg = next((c for c in raw_cards_config if c.get("card_name") == target_card_name), None)
        if raw_cfg and _is_dice_card_by_tags(raw_cfg.get("tags", [])) and not (config or {}).get("func_cards_settings", {}).get("enable_dice_cards", True):
            yield event.plain_result("🎲 当前已关闭骰子玩法，无法使用该骰子功能牌。")
            return
        yield event.plain_result("⚠️ 异界法则缺失，无法解析该卡牌属性。")
        return

    card_type = card_cfg.get("type", "unknown")
    tags = card_cfg.get("tags", [])
    is_aoe = any(t.startswith("aoe_") for t in tags)
    is_dice_duel = any(str(t).startswith("dice_duel:") for t in tags)
    is_reroll_bless = any(str(t) == "dice_reroll_lowest_once" for t in tags)

    if card_type == "defense":
        yield event.plain_result(f"🛡️ [{target_card_name}] 是防御牌，无法直接使用。\n👉 请发送：/luck 启用 {target_card_name}")
        return

    target_id = None
    target_name = None
    is_random = False
    all_users = await bank.get_all_users()
    target_data = None

    if not is_aoe:
        for comp in event.get_messages():
            if isinstance(comp, At):
                target_id = str(comp.qq)
                break
        
        if not target_id and "随机" in raw_text:
            is_random = True

        if is_dice_duel:
            is_random = False

        if card_type == "attack":
            if not target_id and not is_random:
                yield event.plain_result(f"⚠️ 施法中断！使用【{target_card_name}】必须指定目标。\n👉 请 @ 一名群友，或者在指令最后加上“随机”。")
                return
            
            if is_random:
                valid_targets = [uid for uid in all_users.keys() if uid != user_id]
                if not valid_targets:
                    yield event.plain_result("⚠️ 虚空之中空无一人，找不到可以盲打的目标！")
                    return
                target_id = random.choice(valid_targets)
                # 💡 修复：强制真名盲打播报
                target_name = all_users[target_id].get("name", f"群友({target_id})")
                yield event.plain_result(f"🎲 命运的轮盘开始转动... 法术锁定了盲打目标：{target_name}！")

        elif card_type == "heal":
            if not target_id:
                target_id = user_id

        if card_type == "attack" and target_id == user_id:
            yield event.plain_result("⚠️ 异界法则禁止将恶意法术倾泻在自己身上！")
            return

        # 💡 修复：确保无论是不是盲打，获取的都是真名
        if target_id in all_users:
            real_target_name = all_users[target_id].get("name", target_name or f"群友({target_id})")
        else:
            real_target_name = target_name or f"群友({target_id})"

            target_data = await bank.get_user_data(target_id, real_target_name)

    else:
        target_id = "AOE"
        target_data = user_data



    # 🎲 天命重投：主动上状态，不走攻击结算
    if is_reroll_bless:
        _apply_reroll_status(user_data, hours=24)
        inventory.pop(found_index)
        await bank.save_user_data()
        yield event.plain_result(
            f"🍀 {user_name} 启动了 [{target_card_name}]！\n"
            f"接下来 24 小时内，你在掷骰出现最低点时将自动重投 1 次。\n"
            f"🎴 当前卡槽：{len(inventory)}/3"
        )
        return

    # 🎰 对赌卡：进入确认窗口（并发锁）
    if is_dice_duel:
        if not target_id or target_id == user_id:
            yield event.plain_result("⚠️ 对赌必须 @ 一名其他玩家。")
            return

        duel_tag = next((str(t) for t in tags if str(t).startswith("dice_duel:")), "dice_duel:20")
        try:
            stake = max(1, int(duel_tag.split(":")[1]))
        except Exception:
            stake = 20

        async with PENDING_DUEL_LOCK:
            current_group_id = str((config or {}).get("_group_id", "")).strip()
            if PENDING_DUEL.get("active") and str(PENDING_DUEL.get("group_id", "")) == current_group_id:
                yield event.plain_result("🎰 当前已有对局进行中，请稍候再开盘。")
                return

            target_name_duel = target_data.get("name", f"群友({target_id})")
            confirm_event = asyncio.Event()
            PENDING_DUEL.update({
                "active": True,
                "group_id": current_group_id,
                "session_id": f"duel:{current_group_id}:{user_id}:{target_id}:{int(time.time())}",
                "challenger_uid": user_id,
                "challenger_name": user_name,
                "target_uid": target_id,
                "target_name": target_name_duel,
                "card_name": target_card_name,
                "stake": stake,
                "min_stake": stake,
                "max_stake": stake,
                "source_kind": "card",
                "phase": "await_target",
                "confirmed": False,
                "response_action": "",
                "response_stake": stake,
                "confirm_event": confirm_event,
                "created_at": int(time.time()),
                "expire_at": int(time.time()) + DUEL_CONFIRM_WINDOW_SEC,
            })

        yield event.plain_result(
            f"🎰【盘口播报】{user_name} 向 {target_name_duel} 发起了高压对赌！\n"
            f"💰 本局筹码：{stake} 金币\n"
            f"📣 请 {target_name_duel} 在 60 秒内回复「/luck 确认」应战！\n"
            f"👀 围观的人已经让开位置，就等你们开这一局。"
        )

        accepted = False
        try:
            await asyncio.wait_for(confirm_event.wait(), timeout=DUEL_CONFIRM_WINDOW_SEC)
            accepted = True
        except asyncio.TimeoutError:
            accepted = False

        async with PENDING_DUEL_LOCK:
            session = dict(PENDING_DUEL)
            _reset_pending_duel()

                # 对赌牌消耗
        inventory.pop(found_index)

        report_str = await _resolve_duel(bank, session, accepted, config)

        if user_data.get("last_attack_date") != today:

            user_data["last_attack_date"] = today
            user_data["daily_attack_count"] = 1
            karma_report = "\n🩸 【天道法则】今日首次发起攻击，世界线已留下你的气息。"
        else:

            user_data["daily_attack_count"] += 1
            user_data["karma_value"] -= 1
            karma_report = "\n💀 【业报积累】今日连续发动攻击，善恶值 -1！"

        duel_evil_bonus = TitleEngine.calculate_total_attack_gold_bonus(user_data.get("titles", []))
        if duel_evil_bonus > 0:


            user_data["total_gold"] += duel_evil_bonus
            karma_report += f"\n😈 【邪恶之人】攻击奖励触发，额外获得 {duel_evil_bonus} 金币！"
        karma_report += _build_karma_title_report(user_data, config)



        await bank.save_user_data()
        yield event.plain_result(
            f"⚡ {user_name} 打出了 [{target_card_name}]！\n━━━━━━━━\n{report_str}{karma_report}\n🎴 当前卡槽：{len(inventory)}/3"
        )
        return





        evil_bonus = 0
        title_effects = TitleEngine.calculate_effects(user_data, config)

    karma_report = ""
    if card_type == "attack":
        if user_data.get("last_attack_date") != today:
            user_data["last_attack_date"] = today
            user_data["daily_attack_count"] = 1
            karma_report = "\n🩸 【天道法则】今日首次发起攻击，世界线已留下你的气息。"
        else:
            user_data["daily_attack_count"] += 1
            user_data["karma_value"] -= 1
            karma_report = "\n💀 【业报积累】今日连续发动攻击，善恶值 -1！"

        evil_bonus = int(title_effects.get("attack_gold_bonus", 0) or 0)
        if evil_bonus > 0:
            user_data["total_gold"] += evil_bonus
            karma_report += f"\n😈 【称号加成】攻击奖励触发，额外获得 {evil_bonus} 金币！"
    elif card_type == "heal" and (target_id != user_id or is_aoe):
        user_data["karma_value"] += 1
        karma_report = "\n👼 【善意涌动】福泽四方，善恶值 +1！"

    user_data["_title_effects"] = title_effects
    engine = CardEngine()
    battle_reports = await engine.execute_tags(user_data, target_data, tags, all_users, user_id)
    user_data.pop("_title_effects", None)

    user_data["total_func_cards_used"] = int(user_data.get("total_func_cards_used", 0) or 0) + 1
    if card_type == "attack" and battle_reports:
        user_data["total_attack_success"] = int(user_data.get("total_attack_success", 0) or 0) + 1
    elif card_type == "heal" and battle_reports:
        user_data["total_heal_success"] = int(user_data.get("total_heal_success", 0) or 0) + 1
        heal_bonus = int(title_effects.get("heal_gold_bonus", 0) or 0)
        if heal_bonus > 0:
            user_data["total_gold"] += heal_bonus
            karma_report += f"\n💚 【称号加成】治疗奖励触发，额外获得 {heal_bonus} 金币！"
    karma_report += "".join(f"\n{line}" for line in TitleEngine.format_title_event_lines(TitleEngine.sync_titles(user_data, config), config))



        # AOE 施法者使用简报，避免日志过长；被波及者保留精准个人战报
    aoe_chain = None
    if is_aoe:
        aoe_kind = "damage"

        if any(t.startswith("aoe_heal:") for t in tags):
            aoe_kind = "heal"
        elif any(t.startswith("aoe_cleanse:") for t in tags):
            aoe_kind = "cleanse"

        if aoe_kind == "heal":
            aoe_events = sorted(
                engine.last_aoe_events,
                key=lambda e: 0 if str(e.get("target_uid", "")) == str(user_id) else 1,
            )
            affected_count = len(aoe_events)
            total_heal = sum(int(e.get("amount", 0)) for e in aoe_events)
            report_str = f"🌿 范围援助命中 {affected_count} 人（含自己），总恢复 {total_heal} 金币。"
        elif aoe_kind == "cleanse":
            aoe_events = sorted(
                engine.last_aoe_events,
                key=lambda e: 0 if str(e.get("target_uid", "")) == str(user_id) else 1,
            )
            affected_count = len(aoe_events)
            cleaned_count = sum(1 for e in aoe_events if e.get("removed_status"))
            report_str = f"✨ 群体净化影响 {affected_count} 人（含自己），实际解除 {cleaned_count} 个负面状态。"
        else:
            aoe_events = [e for e in engine.last_aoe_events if e.get("target_uid") != user_id]
            affected_count = len(aoe_events)
            blocked_count = sum(1 for e in aoe_events if e.get("blocked"))
            total_damage = sum(int(e.get("amount", 0)) for e in aoe_events)
            report_str = f"🏹 范围攻击命中 {affected_count} 人（免疫 {blocked_count} 人），总造成 {total_damage} 金币伤害。"
        aoe_chain = _format_aoe_chain(user_id, user_name, target_card_name, aoe_events, aoe_kind, karma_report, len(inventory) - 1)

    else:
        report_str = "\n".join(battle_reports) if battle_reports else "💨 法术消散在风中，似乎什么也没发生..."
    
    inventory.pop(found_index)
    await bank.save_user_data()

    if is_aoe:
        final_msg = None
    else:
        final_msg = f"⚡ {user_name} 打出了 [{target_card_name}]！\n━━━━━━━━\n{report_str}{karma_report}\n🎴 当前卡槽：{len(inventory)}/3"
    
    log_msg = f"使用了 [{target_card_name}]"
    await bank.log_battle(user_id, f"{log_msg}。结果：{report_str}")

    if is_aoe:
        for aoe_event in engine.last_aoe_events:
            target_uid_evt = str(aoe_event.get("target_uid", ""))
            if not target_uid_evt or target_uid_evt == user_id:
                continue

            amount = int(aoe_event.get("amount", 0))
            blocked = bool(aoe_event.get("blocked", False))
            if aoe_event.get("type") == "aoe_heal":
                target_report = f"受到 {user_name} 的范围援助 [{target_card_name}]。结果：✨ 恢复 {amount} 金币。"
            else:
                if blocked:
                    target_report = f"遭到 {user_name} 的范围攻击 [{target_card_name}]。结果：🛡️ 你触发了【无懈可击】，成功挡下这次波及！"
                else:
                    target_report = f"遭到 {user_name} 的范围攻击 [{target_card_name}]。结果：💥 你被范围波及，损失 {amount} 金币。"

            await bank.log_battle(target_uid_evt, target_report)
    elif target_id != user_id:
        await bank.log_battle(target_id, f"遭到 {user_name} {log_msg}。结果：{report_str}")

    if is_aoe and aoe_chain:
        yield event.chain_result(aoe_chain)
    else:
        yield event.plain_result(final_msg)

async def handle_active_card(event: AstrMessageEvent, bank, cmd_str: str, is_activate: bool, config: dict = None):
    user_id = event.get_sender_id()
    user_name = event.get_sender_name()
    
    action_str = "启用" if is_activate else "停用"
    raw_text = event.message_str.replace("/luck", "").strip()
    match = re.search(rf"{action_str}\s*([^\s]+)", raw_text)
    
    if not match:
        yield event.plain_result(f"⚠️ 格式错误。正确格式：/luck {action_str}卡牌名（或 /luck {action_str} 卡牌名）")
        return
        
    target_card_name = match.group(1).strip()
    user_data = await bank.get_user_data(user_id, user_name)
    
    blocked_by = find_gate_block(user_data, GATE_TOGGLE_CARD)
    if blocked_by:
        msg = format_gate_block_message(
            blocked_by,
            "⚠️ 你的当前状态禁止启用或停用功能牌，请稍后再试。"
        )
        yield event.plain_result(msg)
        return

    inventory = user_data.get("inventory", [])
    if _sync_expired_defense_cards(user_data, config):
        await bank.save_user_data()

    for card in inventory:

        if card.get("card_name") == target_card_name:
            
            # 💡 战损拦截：破烂的牌不能挂载
            if card.get("is_broken", False):
                yield event.plain_result(f"⚠️ 你的 [{target_card_name}] 已经销毁，无法再作为法阵阵眼！请先丢弃它。")
                return

            if card.get("is_active") == is_activate:
                yield event.plain_result(f"⚠️ [{target_card_name}] 已经处于该状态了。")
                return
                
            cards_config = load_func_cards_config(config)

            card_cfg = next((c for c in cards_config if c.get("card_name") == target_card_name), {})
            
            if card_cfg.get("type") != "defense":
                yield event.plain_result("⚠️ 只有【防御牌】才能被挂载到状态栏。")
                return
            
            engine = CardEngine()
            if is_activate:
                await engine.execute_tags(user_data, user_data, card_cfg.get("tags", []))
                card["is_active"] = True
                msg = f"🛡️ 阵法流转！[{target_card_name}] 已成功挂载至你的状态栏，时刻警戒四周。"
            else:
                # 根据防御牌词条，卸载对应状态
                remove_names = []
                for tag in card_cfg.get("tags", []):
                    if tag == "add_shield":
                        remove_names.append("无懈可击")
                    elif tag.startswith("thorn_armor:"):
                        remove_names.append("反甲")

                if remove_names:
                    user_data["statuses"] = [
                        st for st in user_data.get("statuses", [])
                        if st.get("name") not in set(remove_names)
                    ]

                card["is_active"] = False
                msg = f"🎐 灵力收回，[{target_card_name}] 已从你的状态栏卸载，重回卡槽休眠。"
                
            await bank.save_user_data()
            yield event.plain_result(msg)
            return

    yield event.plain_result(f"❓ 你的卡槽中并未发现 [{target_card_name}]。")