import random
import json
import os
from datetime import datetime, timedelta
from astrbot.api.event import AstrMessageEvent
from ..core.title_engine import TitleEngine

# ================= 🔮 原汁原味的异世界观配置区 🔮 =================
GOOD_THINGS = [
    "擦拭法杖", "冥想", "练习火球术", "探索地下城", "给史莱姆喂食",
    "得到救世魔杖", "整理背包", "购买回复药水", "专心附魔", "擦亮盔甲",
    "向神像祈祷", "研读古籍", "在酒馆打听情报","攻破迷宫","得到古代魔导具","在野外捡到古代魔导具","过越冬节","学习神圣魔法","学习飞龙变","得到天星石戒指","与海豚凯撒战斗","锻炼体能","穿上野兽之袍","滑冰","打乒乓球","去炼狱の汤游玩","喝酒"
]

BAD_THINGS = [
    "遇到帝位魔兽", "单独行动", "喝陌生的药水", "直视深渊", "相信地精的鬼话",
    "在这个时间点强化装备", "在酒馆酗酒", "偷看禁书", "被哈根·雷格法尔根追债",
    "与魔炎龙战斗","遇到独眼巨人", "首饰被卖", "被卖给马戏团", "被村民埋进土里", "被哈根商会抓走","异端审判", "被村民围攻", "被关进监狱", "与魔毒龙战斗",
]
# =======================================================

async def calculate_rank(bank, user_id):
    """计算当前玩家排名"""
    all_users = await bank.get_all_users()
    sorted_users = sorted(all_users.items(), key=lambda x: x[1].get("total_gold", 0), reverse=True)
    for rank, (uid, _) in enumerate(sorted_users):
        if uid == user_id: return rank + 1
    return 999

def _load_sign_in_texts(config: dict | None = None):
    sign_in_file = str((config or {}).get("_storage_paths", {}).get("sign_in_texts_file", ""))
    try:
        if sign_in_file and os.path.exists(sign_in_file):
            with open(sign_in_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _pick_luck_range_rule(luck_val: int, config: dict | None = None):
    texts = _load_sign_in_texts(config)
    ranges = texts.get("luck_ranges", [])
    valid = [r for r in ranges if isinstance(r, dict) and isinstance(r.get("min"), int) and isinstance(r.get("max"), int)]
    for rule in valid:
        if int(rule.get("min", 0)) <= luck_val <= int(rule.get("max", 0)):
            return rule
    return None


async def handle_sign_in(event: AstrMessageEvent, bank, config: dict):
    """处理 /luck 运势 逻辑 (彻底同步精准爆率)"""
    user_id = event.get_sender_id()
    user_name = event.get_sender_name()

    today_dt = datetime.now()
    today = today_dt.strftime("%Y-%m-%d")
    yesterday = (today_dt - timedelta(days=1)).strftime("%Y-%m-%d")

    user_data = await bank.get_user_data(user_id, user_name)
    TitleEngine.ensure_user_title_fields(user_data)
    func_cards_enabled = config.get("func_cards_settings", {}).get("enable", True)

    if user_data.get("last_date") == today:
        rank = await calculate_rank(bank, user_id)
        yield event.plain_result(f"⚖️ {user_name}，今日已占卜。\n当前排名：第 {rank} 位")
        return

    titles = user_data.setdefault("titles", [])
    equipped_titles = user_data.setdefault("equipped_titles", [])

    if user_data.get("last_date") == yesterday:
        user_data["consecutive_sign_ins"] = user_data.get("consecutive_sign_ins", 0) + 1
    else:
        user_data["consecutive_sign_ins"] = 1

    consec_days = user_data["consecutive_sign_ins"]
    luck_val = random.randint(1, 100)
    user_data["today_luck_value"] = luck_val
    user_data["last_date"] = today
    user_data["total_sign_in_days"] = int(user_data.get("total_sign_in_days", 0) or 0) + 1

    base_reward = (luck_val - 1) // 10 + 1
    total_reward = base_reward

    rule = _pick_luck_range_rule(luck_val, config)
    rule_label = str(rule.get("label", "")).strip() if rule else ""
    rule_gold_delta = int(rule.get("gold_delta", 0)) if rule else 0
    total_reward += rule_gold_delta
    if total_reward < 0:
        total_reward = 0

    streak_bonus_str = ""
    if consec_days > 3:
        total_reward += 5
        streak_bonus_str = " (含连签+5)"

    sync_events = TitleEngine.sync_titles(user_data, config)
    if not equipped_titles and titles:
        max_slots = TitleEngine.get_max_equipped_titles(config)
        user_data["equipped_titles"] = titles[:max_slots]

    title_effects = TitleEngine.calculate_effects(user_data, config)
    sign_bonus = int(title_effects.get("sign_in_gold_bonus", 0) or 0)
    if sign_bonus:
        total_reward += max(0, (total_reward * sign_bonus) // 100)

    title_str = ""
    for line in TitleEngine.format_title_event_lines(sync_events, config):
        title_str += f"\n{line}"

    user_data["total_gold"] += total_reward
    await bank.save_user_data()

    eco_cfg = config.get("func_cards_settings", {}).get("economy_settings", {})
    base_prob = eco_cfg.get("draw_probability", 5)

    luck_mod = 0
    if 51 <= luck_val <= 70:
        luck_mod = 2
    elif 71 <= luck_val <= 90:
        luck_mod = 5
    elif 91 <= luck_val <= 100:
        luck_mod = 10

    title_mod = TitleEngine.calculate_total_bonus_prob(user_data, config)
    total_prob = base_prob + luck_mod + title_mod

    current_rank = await calculate_rank(bank, user_id)
    texts_cfg = _load_sign_in_texts(config)
    good_pool = [x for x in texts_cfg.get("good_things", GOOD_THINGS) if isinstance(x, str) and x.strip()]
    bad_pool = [x for x in texts_cfg.get("bad_things", BAD_THINGS) if isinstance(x, str) and x.strip()]
    good_thing = random.choice(good_pool or GOOD_THINGS)
    bad_thing = random.choice(bad_pool or BAD_THINGS)

    comment = ""
    if rule and isinstance(rule.get("comments"), list):
        pool = [x for x in rule.get("comments", []) if isinstance(x, str) and x.strip()]
        if pool:
            comment = random.choice(pool)
    if not comment:
        if luck_val >= 91:
            comment = "天命之子！鸿运当头，此时不抽更待何时！" if func_cards_enabled else "天命之子！鸿运当头，今日诸事皆宜。"
        elif luck_val >= 71:
            comment = "大吉。如有神助，爆率飙升。" if func_cards_enabled else "大吉。如有神助，宜乘势而为。"
        elif luck_val >= 51:
            comment = "小吉。灵力涌动，爆率提升。" if func_cards_enabled else "小吉。灵力涌动，稳中有进。"
        else:
            comment = "平平无奇。宜蛰伏蓄锐，莫生事端。"

    extra_line = ""
    if func_cards_enabled:
        extra_line = f"\n📈 今日精准出金率：{total_prob}% (基础{base_prob}% +运势{luck_mod}% +称号{title_mod}%)"
    if sign_bonus:
        extra_line += f"\n🏅 签到称号加成：+{sign_bonus}%"

    msg = (
        f"🔮 【{user_name} 的命运星象】\n"
        f"🎲 运势：{luck_val}/100{' · ' + rule_label if rule_label else ''} (+{total_reward}{streak_bonus_str})\n"
        f"💰 总金币：{user_data['total_gold']} (第 {current_rank} 位)\n"
        f"📅 连续签到：{consec_days} 天{title_str}\n"
        f"✅ 宜：{good_thing}\n"
        f"❌ 忌：{bad_thing}\n"
        f"🗣️ 启示：{comment}\n"
        f"━━━━━━━━━━━━━━"
        f"{extra_line}"
    )
    yield event.plain_result(msg)


# (排行榜逻辑保持不变，统一修改 name)
def _normalize_rank_titles(values, defaults: list[str]) -> list[str]:
    source = values if isinstance(values, list) else []
    items = []
    for idx in range(3):
        fallback = defaults[idx]
        value = str(source[idx] if idx < len(source) else fallback).strip() or fallback
        items.append(value)
    return items


def get_leaderboard_settings(config: dict | None = None, kind: str = "wealth") -> dict:
    ui_cfg = (config or {}).get("ui_settings", {})
    legacy_length = ui_cfg.get("board_length", 10)
    raw = ui_cfg.get("wealth_leaderboard" if kind == "wealth" else "karma_leaderboard", {})
    if kind == "wealth" and not isinstance(raw, dict):
        raw = ui_cfg.get("leaderboard", {})
    if not isinstance(raw, dict):
        raw = {}
    try:
        board_length = max(1, int(raw.get("board_length", legacy_length) or legacy_length))
    except (TypeError, ValueError):
        board_length = 10

    if kind == "karma":
        return {
            "enabled": bool(raw.get("enabled", True)),
            "show_positive": bool(raw.get("show_positive", True)),
            "show_negative": bool(raw.get("show_negative", True)),
            "show_nearby": bool(raw.get("show_nearby", True)),
            "board_length": board_length,
            "title": str(raw.get("title", "⚖️ 【天道善恶榜】") or "⚖️ 【天道善恶榜】").strip() or "⚖️ 【天道善恶榜】",
            "positive_header": str(raw.get("positive_header", "😇 【善业榜】") or "😇 【善业榜】").strip() or "😇 【善业榜】",
            "negative_header": str(raw.get("negative_header", "😈 【恶业榜】") or "😈 【恶业榜】").strip() or "😈 【恶业榜】",
            "nearby_header": str(raw.get("nearby_header", "🧭 【你的附近位】") or "🧭 【你的附近位】").strip() or "🧭 【你的附近位】",
            "positive_titles": _normalize_rank_titles(raw.get("positive_titles", []), ["😇 首善", "🍀 积福者", "🤝 仁心客"]),
            "negative_titles": _normalize_rank_titles(raw.get("negative_titles", []), ["😈 首恶", "🔥 业火者", "🌩️ 灾厄客"]),
        }

    return {
        "enabled": bool(raw.get("enabled", True)),
        "show_top": bool(raw.get("show_top", True)),
        "show_bottom": bool(raw.get("show_bottom", True)),
        "show_nearby": bool(raw.get("show_nearby", True)),
        "board_length": board_length,
        "title": str(raw.get("title", "💰 ✦异世界·金币双榜✦ 💰") or "💰 ✦异世界·金币双榜✦ 💰").strip() or "💰 ✦异世界·金币双榜✦ 💰",
        "top_header": str(raw.get("top_header", "🏆 【金币·封神榜】") or "🏆 【金币·封神榜】").strip() or "🏆 【金币·封神榜】",
        "bottom_header": str(raw.get("bottom_header", "🃃 【倒霉·深渊榜】") or "🃃 【倒霉·深渊榜】").strip() or "🃃 【倒霉·深渊榜】",
        "nearby_header": str(raw.get("nearby_header", "🧭 【你的附近位】") or "🧭 【你的附近位】").strip() or "🧭 【你的附近位】",
        "top_titles": _normalize_rank_titles(raw.get("top_titles", []), ["👑 金冠", "🥈 银序", "🥉 铜席"]),
        "bottom_titles": _normalize_rank_titles(raw.get("bottom_titles", []), ["💀 穷途", "🪙 漏财", "🕳️ 深渊"]),
    }


async def handle_leaderboard(event: AstrMessageEvent, bank, config: dict | None = None):
    user_id = event.get_sender_id()
    all_users = await bank.get_all_users()
    if not all_users:
        yield event.plain_result("榜单暂无数据。")
        return

    settings = get_leaderboard_settings(config, "wealth")
    if not settings["enabled"]:
        yield event.plain_result("⚠️ 当前方案已关闭财富排行榜。")
        return
    if not settings["show_top"] and not settings["show_bottom"] and not settings["show_nearby"]:
        yield event.plain_result("⚠️ 当前排行榜的全部展示区块都已关闭。")
        return

    board_length = settings["board_length"]
    full_list = sorted(all_users.items(), key=lambda x: x[1].get("total_gold", 0), reverse=True)
    top_n = full_list[:board_length]
    bottom_n = sorted(all_users.items(), key=lambda x: x[1].get("total_gold", 0), reverse=False)[:board_length]

    result = ["📜 ✦ 异世界·金币双榜 ✦ 📜", "", "🏆 【金币·封神榜】"]
    visible_users = set()

    for index, (uid, info) in enumerate(top_n):
        visible_users.add(uid)
        rank = index + 1
        icon = "👑" if rank == 1 else "⚜️" if rank == 2 else "✨" if rank == 3 else f"{rank}."
        # 💡 修复：读取真名 "name"
        result.append(f"{icon} {info.get('name', f'群友({uid})')} : {info['total_gold']}")
    
    result.append("")
    result.append("💀 【倒霉·深渊榜】")
    
    for index, (uid, info) in enumerate(bottom_n):
        visible_users.add(uid)
        icon = "☠️" if index == 0 else "🕸️" if index == 1 else "🥀" if index == 2 else f"{index+1}."
        result.append(f"{icon} {info.get('name', f'群友({uid})')} : {info['total_gold']}")

    if user_id in all_users and user_id not in visible_users:
        my_index = next((i for i, (uid, _) in enumerate(full_list) if uid == user_id), -1)
        if my_index != -1:
            start = max(0, my_index - 3)
            end = min(len(full_list), my_index + 4)
            result.append("")
            result.append("🔭 【你的位阶·观测圈】")
            for i in range(start, end):
                u_id, info = full_list[i]
                real_rank = i + 1
                prefix = "👉" if u_id == user_id else f"No.{real_rank}"
                result.append(f"{prefix} {info.get('name', f'群友({u_id})')} : {info['total_gold']}")

    yield event.plain_result("\n".join(result))


async def handle_leaderboard_v2(event: AstrMessageEvent, bank, config: dict | None = None):
    user_id = event.get_sender_id()
    all_users = await bank.get_all_users()
    if not all_users:
        yield event.plain_result("榜单暂无数据。")
        return

    settings = get_leaderboard_settings(config)
    if not settings["enabled"]:
        yield event.plain_result("⚠️ 当前方案已关闭财富排行榜。")
        return
    if not settings["show_top"] and not settings["show_bottom"] and not settings["show_nearby"]:
        yield event.plain_result("⚠️ 当前排行榜的全部展示区块都已关闭。")
        return

    board_length = settings["board_length"]
    full_list = sorted(all_users.items(), key=lambda x: x[1].get("total_gold", 0), reverse=True)
    top_n = full_list[:board_length]
    bottom_n = sorted(all_users.items(), key=lambda x: x[1].get("total_gold", 0))[:board_length]

    result = [settings["title"]]
    visible_users = set()

    if settings["show_top"]:
        result.extend(["", settings["top_header"]])
        for index, (uid, info) in enumerate(top_n):
            visible_users.add(uid)
            rank = index + 1
            icon = "👑" if rank == 1 else "⚜️" if rank == 2 else "✨" if rank == 3 else f"{rank}."
            title_tag = f" [{settings['top_titles'][index]}]" if index < 3 else ""
            icon = f"{rank}."
            result.append(f"{icon}{title_tag} {info.get('name', f'群友({uid})')} : {info.get('total_gold', 0)}")

    if settings["show_bottom"]:
        result.extend(["", settings["bottom_header"]])
        for index, (uid, info) in enumerate(bottom_n):
            visible_users.add(uid)
            icon = "☠️" if index == 0 else "🪩️" if index == 1 else "🚅" if index == 2 else f"{index + 1}."
            title_tag = f" [{settings['bottom_titles'][index]}]" if index < 3 else ""
            icon = f"{index + 1}."
            result.append(f"{icon}{title_tag} {info.get('name', f'群友({uid})')} : {info.get('total_gold', 0)}")

    if settings["show_nearby"] and user_id in all_users and user_id not in visible_users:
        my_index = next((i for i, (uid, _) in enumerate(full_list) if uid == user_id), -1)
        if my_index != -1:
            start = max(0, my_index - 3)
            end = min(len(full_list), my_index + 4)
            result.extend(["", settings["nearby_header"]])
            for i in range(start, end):
                u_id, info = full_list[i]
                real_rank = i + 1
                prefix = "👉" if u_id == user_id else f"No.{real_rank}"
                result.append(f"{prefix} {info.get('name', f'群友({u_id})')} : {info.get('total_gold', 0)}")

    yield event.plain_result("\n".join(result))
