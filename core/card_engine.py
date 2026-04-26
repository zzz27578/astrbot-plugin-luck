# ==============================================================================
# 🔮 异世界·纯净版功能词库引擎 (Pure Keyword Engine) 🔮
# ==============================================================================
# 💡 【词库总览与配置说明】
# 🗡️ 攻击/掠夺类：
# - steal:X                 -> 盗取目标 X 金币化为己用。(例: steal:15)
# - steal_fate              -> 窃取目标当前命运牌加成（last_drawn_gold），并清空目标该加成。
# - freeze:X                -> 冻结目标 X 小时，附加逻辑门阻断（抽牌/施法/启停功能牌）。(例: freeze:24)
# - silence:X               -> 沉默目标 X 小时，期间无法使用功能牌。(例: silence:24)
# - seal_draw_all:X         -> 封印目标 X 小时，期间无法抽命运牌和功能牌。(例: seal_draw_all:24)
# - luck_drain:X:Y          -> 抽取目标爆率 Y%，持续 X 小时；目标降低 Y%，施法者提升 Y%。(例: luck_drain:24:8)
# - sac_steal:X:Y           -> 自损 X 金币后，强夺目标 Y 金币（防自爆：施法后至少保留 1 金币）。(例: sac_steal:20:35)
# - dice_rule:KEY           -> 触发骰子规则 KEY（规则在 core/dice_engine.py 中配置，可扩展到拼点/决斗等）。
# - borrow_blade:X:Y        -> 借来第三方之名发动暗算，对目标造成 X~Y 金币伤害，并在播报中点出“借刀者”。(例: borrow_blade:10:20)
# - bounty_mark:X:Y         -> 给目标挂上【悬赏印记】X 小时；期间其每次受到金币类攻击时会额外损失 Y 金币，攻击者额外获得 Y 金币。(例: bounty_mark:24:5)
# - strip_buff_gain:X:Y     -> 移除目标 1 个正面状态，并为施法者附加 X% 功能牌爆率增益，持续 Y 小时。(例: strip_buff_gain:8:24)
# 
# 👼 辅助/治疗类：
# - cleanse                 -> 净化目标 1 个负面状态。(忽略增益状态如无懈可击)
# - luck_bless:X:Y          -> 为自身附加好运状态 X 小时，功能牌爆率提升 Y%。(例: luck_bless:24:10)
# - fate_roulette           -> 触发命运转盘，从 5 种结果中随机结算；默认 4 个结果偏向施法者，1 个结果会反噬施法者。
# 
# 🛡️ 状态/防御类：
# - add_shield              -> 挂载【无懈可击】，抵挡 1 次带有伤害/偷取/控制性质的法术。
# - thorn_armor:X:Y         -> 挂载反甲 X 小时，受到金币伤害时反弹 Y% 给施法者。(例: thorn_armor:8:40)
# =======================================================
# 💥 新增 AOE (群体) 功能词库说明 💥
# =======================================================
#🏷️ aoe_damage:最小伤害:最大伤害:最大波及人数
#  - 作用：群体随机攻击。在全群(排除施法者自己)中随机抽取目标，造成浮动金币伤害。
#  - 机制：会被【无懈可击】护盾完美格挡（破盾但免伤）。
#  - 举例：["aoe_damage:10:20:8"] 
# - 解释：随机抽取最多 8 名群友，每个人单独随机扣除 10 到 20 点金币。
#
#🏷️ aoe_heal:最小治疗:最大治疗:最大波及人数
#   - 作用：群体随机增益。为包含【施法者自己】在内的群体随机增加金币。
#   - 机制：必定包含自己，剩下的名额在全群中随机抽取。
#   - 举例：["aoe_heal:10:30:8"]
#   - 解释：对自己以及随机抽取的最多 7 名群友（合计最多 8 人），每个人单独随机增加 10 到 30 点
#
# ==============================================================================
# ==============================================================================
# 🔮 异世界·纯净版功能词库引擎 (Pure Keyword Engine) 🔮
# ==============================================================================
import time
import random
from .dice_engine import DiceEngine
from .dice_card_effects import apply_dice_payload
from .logic_gate import (
    GATE_DRAW_FATE_CARD,
    GATE_DRAW_FUNC_CARD,
    GATE_USE_CARD,
    GATE_TOGGLE_CARD,
)


def _is_group_participant(user_info: dict) -> bool:
    if not isinstance(user_info, dict):
        return False
    return any([
        int(user_info.get("total_sign_in_days", user_info.get("sign_in_count", 0)) or 0) > 0,
        bool(str(user_info.get("last_date", "")).strip()),
        int(user_info.get("total_gold", user_info.get("gold", 0)) or 0) != 0,
        bool(user_info.get("inventory")),
        bool(user_info.get("titles")),
        int(user_info.get("total_func_cards_drawn", 0) or 0) > 0,
        int(user_info.get("total_fate_card_draws", 0) or 0) > 0,
    ])


def _filter_participant_uids(all_users: dict, exclude: set | None = None) -> list[str]:
    excluded = {str(uid) for uid in (exclude or set())}
    result = []
    for uid, data in (all_users or {}).items():
        uid_text = str(uid)
        if uid_text in excluded:
            continue
        if _is_group_participant(data):
            result.append(uid_text)
    return result


def _parse_aoe_range_tag(tag: str, expected_key: str) -> tuple[int, int, int] | None:
    parts = str(tag or "").split(":")
    if len(parts) != 4 or parts[0] != expected_key:
        return None
    try:
        min_val = int(str(parts[1]).strip())
        max_val = int(str(parts[2]).strip())
        count = int(str(parts[3]).strip())
    except (TypeError, ValueError):
        return None
    min_val = max(0, min_val)
    max_val = max(min_val, max_val)
    count = max(1, count)
    return min_val, max_val, count


def _parse_aoe_count_tag(tag: str, expected_key: str) -> int | None:
    parts = str(tag or "").split(":")
    if len(parts) != 2 or parts[0] != expected_key:
        return None
    try:
        count = int(str(parts[1]).strip())
    except (TypeError, ValueError):
        return None
    return max(1, count)


class CardEngine:
    def __init__(self):
        self.last_aoe_events = []

    def _find_uid_by_data(self, all_users: dict, target_data: dict):
        if not all_users or not target_data:
            return None
        for uid, data in all_users.items():
            if data is target_data or data == target_data:
                return uid
        return None

    def _is_positive_status(self, status: dict) -> bool:
        if not status:
            return False
        name = str(status.get("name", ""))
        if name in {"无懈可击", "反甲", "幸运窃取", "好运加护", "天命重投"}:
            return True
        if int(status.get("func_draw_prob_mod", 0) or 0) > 0:
            return True
        if int(status.get("thorn_ratio", 0) or 0) > 0:
            return True
        return False

    def _apply_bounty_bonus(self, source_data: dict, target_data: dict) -> int:
        if not source_data or not target_data:
            return 0

        now_ts = int(time.time())
        for st in target_data.get("statuses", []):
            if st.get("name") != "悬赏印记":
                continue
            if st.get("expire_time", 0) <= now_ts:
                continue

            bonus = max(0, int(st.get("bounty_bonus", 0) or 0))
            if bonus <= 0:
                return 0

            actual = min(bonus, max(0, target_data.get("total_gold", 0)))
            if actual <= 0:
                return 0

            target_data["total_gold"] -= actual
            source_data["total_gold"] += actual
            return actual

        return 0

    def _upsert_timed_status(self, target_data: dict, status_name: str, expire_time: int, **extra_fields):
        statuses = target_data.setdefault("statuses", [])
        for st in statuses:
            if st.get("name") == status_name:
                st["expire_time"] = expire_time
                st.update(extra_fields)
                return
        new_status = {"name": status_name, "expire_time": expire_time}
        new_status.update(extra_fields)
        statuses.append(new_status)

    def _apply_thorn_reflect(self, source_data: dict, target_data: dict, damage_amount: int) -> int:
        """若目标存在有效反甲，按比例反弹金币。返回反弹值。"""
        if damage_amount <= 0 or not source_data or not target_data:
            return 0

        now_ts = int(time.time())
        for st in target_data.get("statuses", []):
            if st.get("name") != "反甲":
                continue
            if st.get("expire_time", 0) <= now_ts:
                continue

                        
            ratio = int(st.get("thorn_ratio", 0))
            if ratio <= 0:

                return 0

            reflect = max(0, damage_amount * ratio // 100)
            reflect = min(reflect, max(0, source_data.get("total_gold", 0)))
            if reflect > 0:
                source_data["total_gold"] -= reflect
                target_data["total_gold"] += reflect
            return reflect

        return 0



    def _remove_one_negative_status(self, target_data: dict) -> dict | None:
        statuses = target_data.get("statuses", []) if target_data else []
        for i, st in enumerate(list(statuses)):
            if not self._is_positive_status(st):
                return statuses.pop(i)
        return None

    async def execute_tags(self, source_data: dict, target_data: dict, tags: list, all_users: dict = None, source_uid: str = None) -> list:



        reports = []
        self.last_aoe_events = []
        target_data = target_data or source_data



        is_attack_blocked = False

        is_aoe = any(t.startswith("aoe_") for t in tags)
        title_effects = source_data.get("_title_effects", {})




        # ==========================================
        # 🛡️ 单体战术法则：护盾拦截与战损判定
        # ==========================================
        if target_data and not is_aoe:
            for tag in tags:
                if tag.startswith("steal") or tag.startswith("damage") or tag.startswith("freeze") or tag.startswith("sac_steal") or tag.startswith("dice_rule:") or tag.startswith("borrow_blade:") or tag.startswith("bounty_mark:"):
                    for i, st in enumerate(target_data.get("statuses", [])):
                        if st.get("name") == "无懈可击":
                            target_data["statuses"].pop(i)
                            reports.append("🛡️ 铛！【无懈可击】触发，法术被完美抵挡，护盾碎裂！")
                            is_attack_blocked = True
                            
                                                        # 💡 战损联动：去卡槽里把这张盾牌打碎
                            for card in target_data.get("inventory", []):
                                if card.get("card_name") == "无懈可击" and card.get("is_active"):
                                    card["is_active"] = False
                                    card["is_broken"] = True  # 打上破碎标记
                                    card["broken_reason"] = "护盾被击破"
                                    break


                            break
                    break

        if is_attack_blocked:
            return reports

        # ==========================================
        # ⚙️ 核心解析区：挨个执行标签
        # ==========================================
        target_name = target_data.get("name", "目标") if target_data else "目标"
        for tag in tags:
            if tag.startswith("steal:"):
                amount = int(tag.split(":")[1])
                actual_steal = min(amount, max(0, target_data.get("total_gold", 0)))
                target_data["total_gold"] -= actual_steal
                source_data["total_gold"] += actual_steal
                reports.append(f"🗡️ 探入虚空，掠夺了 {target_name} {actual_steal} 金币！")

                bounty_bonus = self._apply_bounty_bonus(source_data, target_data)
                if bounty_bonus > 0:
                    reports.append(f"🎯 悬赏印记发作！{target_name} 额外损失 {bounty_bonus} 金币，并被你一并卷走。")

                reflected = int(self._apply_thorn_reflect(source_data, target_data, actual_steal) or 0)
                if reflected > 0:
                    reports.append(f"🪞 目标反甲触发！你被反震 {reflected} 金币。")

            elif tag == "steal_fate":
                stolen_val = int(target_data.get("last_drawn_gold", 0))
                if stolen_val > 0:
                    steal_amount = min(stolen_val, max(0, target_data.get("total_gold", 0)))
                    target_data["total_gold"] -= steal_amount
                    source_data["total_gold"] += steal_amount
                    target_data["last_drawn_gold"] = 0
                    reports.append(f"🌌 命运逆流！你窃取了 {target_name} 的命运加成 {steal_amount} 金币！")
                else:
                    reports.append(f"🌫️ 你试图窃取 {target_name} 的命运牌，但对方当前没有可窃取加成。")







                        
            elif tag.startswith("sac_steal:"):

                _, cost_s, steal_s = tag.split(":")

                cost = int(cost_s)
                steal_val = int(steal_s)
                steal_bonus_pct = int(title_effects.get("steal_bonus", 0) or 0)
                if steal_bonus_pct > 0:
                    steal_val = int(steal_val * (1 + steal_bonus_pct / 100))

                # 防自爆：至少留 1 金币
                if source_data.get("total_gold", 0) <= cost:

                    reports.append(f"🩸 你想发动【杀敌一千自损八百】掠夺，但金币不足（需要至少 {cost + 1} 金币）！")
                    continue

                source_data["total_gold"] -= cost
                actual_steal = min(steal_val, max(0, target_data.get("total_gold", 0)))
                target_data["total_gold"] -= actual_steal
                source_data["total_gold"] += actual_steal
                net = actual_steal - cost
                reports.append(f"🔥 你燃烧 {cost} 金币发动豪赌，强夺 {target_name} {actual_steal} 金币！（净收益 {net:+d}）")

                bounty_bonus = self._apply_bounty_bonus(source_data, target_data)
                if bounty_bonus > 0:
                    reports.append(f"🎯 悬赏印记发作！{target_name} 又被追加剥走 {bounty_bonus} 金币。")

                reflected = int(self._apply_thorn_reflect(source_data, target_data, actual_steal) or 0)
                if reflected > 0:
                    reports.append(f"🪞 目标反甲触发！你被反震 {reflected} 金币。")

            elif tag.startswith("dice_rule:"):
                rule_key = tag.split(":", 1)[1].strip()
                dice_engine = DiceEngine()
                dice_ret = dice_engine.roll_rule(rule_key, statuses=source_data.get("statuses", []))
                reports.extend(dice_ret.get("reports", []))

                payload = dice_ret.get("payload") or {}
                reports.extend(
                    apply_dice_payload(
                        payload=payload,
                        source_data=source_data,
                        target_data=target_data,
                        target_name=target_name,
                        on_damage_reflect=self._apply_thorn_reflect,
                    )
                )

            elif tag.startswith("freeze:"):
                hours = int(tag.split(":")[1])
                expire_time = int(time.time()) + hours * 3600
                freeze_block_actions = [
                    GATE_DRAW_FATE_CARD,
                    GATE_DRAW_FUNC_CARD,
                    GATE_USE_CARD,
                    GATE_TOGGLE_CARD,
                ]
                freeze_block_msg = "❄️ 极寒刺骨！你处于【冻结】状态，体内魔力停滞，当前无法进行此操作！"

                self._upsert_timed_status(
                    target_data,
                    "冻结",
                    expire_time,
                    block_actions=freeze_block_actions,
                    block_msg=freeze_block_msg,
                )
                reports.append(f"❄️ 极寒领域展开，{target_name} 被【冻结】了 {hours} 小时！")

            elif tag.startswith("silence:"):
                hours = int(tag.split(":")[1])
                expire_time = int(time.time()) + hours * 3600
                self._upsert_timed_status(
                    target_data,
                    "沉默",
                    expire_time,
                    block_actions=[GATE_USE_CARD],
                    block_msg="🔇 你被【沉默】影响，当前无法使用功能牌！",
                )
                reports.append(f"🔇 音律崩塌，{target_name} 被【沉默】{hours} 小时！")

            elif tag.startswith("seal_draw_all:"):
                hours = int(tag.split(":")[1])
                expire_time = int(time.time()) + hours * 3600
                self._upsert_timed_status(
                    target_data,
                    "抽牌封印",
                    expire_time,
                    block_actions=[GATE_DRAW_FATE_CARD, GATE_DRAW_FUNC_CARD],
                    block_msg="🕳️ 你被【抽牌封印】影响，当前无法抽取任何卡牌！",
                )
                reports.append(f"🕳️ 命运书页被锁死，{target_name} 在 {hours} 小时内无法抽牌！")

            elif tag.startswith("luck_drain:"):
                _, hours, percent = tag.split(":")
                hours = int(hours)
                percent = int(percent)
                expire_time = int(time.time()) + hours * 3600

                self._upsert_timed_status(
                    target_data,
                    "幸运流失",
                    expire_time,
                    func_draw_prob_mod=-abs(percent),
                    desc=f"功能牌爆率 {abs(percent)}%",
                )
                self._upsert_timed_status(
                    source_data,
                    "幸运窃取",
                    expire_time,
                    func_draw_prob_mod=abs(percent),
                    desc=f"功能牌爆率 +{abs(percent)}%",
                )
                reports.append(f"🎭 命星偏移！你抽走了 {target_name} 的 {abs(percent)}% 功能牌爆率，持续 {hours} 小时。")

                        
            elif tag == "cleanse":
                removed_st = self._remove_one_negative_status(target_data)
                if removed_st:
                    reports.append(f"✨ 单体净化生效，解除了 {target_name} 的【{removed_st.get('name')}】状态！")
                else:
                    reports.append(f"✨ 单体净化释放完成，但 {target_name} 当前没有可驱散的负面状态。")




            elif tag.startswith("luck_bless:"):
                _, hours, percent = tag.split(":")
                hours = int(hours)
                percent = int(percent)
                expire_time = int(time.time()) + hours * 3600
                self._upsert_timed_status(
                    source_data,
                    "好运加护",
                    expire_time,
                    func_draw_prob_mod=abs(percent),
                    desc=f"功能牌爆率 +{abs(percent)}%",
                )
                reports.append(f"🍀 时运翻涌！你获得【好运加护】，功能牌爆率提升 {abs(percent)}%，持续 {hours} 小时。")

            elif tag == "fate_roulette":
                roll = random.randint(1, 5)
                reports.append(f"🎰 命运转盘开始旋转……结果序号：{roll}/5")
                if roll == 1:
                    gain = 28
                    source_data["total_gold"] += gain
                    reports.append(f"✨ 奖励命中：【金币馈赠】你获得 {gain} 金币。")
                elif roll == 2:
                    _ = int(time.time()) + 24 * 3600
                    has_shield = any(st.get("name") == "无懈可击" for st in source_data.get("statuses", []))
                    if has_shield:
                        reports.append("✨ 奖励命中：【护盾共鸣】你本想再添一层庇护，但护盾已在身，力量只是轻轻荡开。")
                    else:
                        source_data.setdefault("statuses", []).append({"name": "无懈可击", "desc": "抵挡1次恶意法术"})
                        reports.append("✨ 奖励命中：【护盾庇佑】你获得了【无懈可击】。")
                elif roll == 3:
                    expire_time = int(time.time()) + 24 * 3600
                    self._upsert_timed_status(
                        source_data,
                        "好运加护",
                        expire_time,
                        func_draw_prob_mod=8,
                        desc="功能牌爆率 +8%",
                    )
                    reports.append("✨ 奖励命中：【好运加护】功能牌爆率 +8%，持续 24 小时。")
                elif roll == 4:
                    heal = 20
                    source_data["total_gold"] += heal
                    statuses = source_data.get("statuses", [])
                    for i, st in enumerate(list(statuses)):
                        if not self._is_positive_status(st):
                            removed = statuses.pop(i)
                            reports.append(f"✨ 奖励命中：【净化赐福】你获得 {heal} 金币，并解除了自身的【{removed.get('name')}】。")
                            break
                    else:
                        reports.append(f"✨ 奖励命中：【净化赐福】你获得 {heal} 金币。")
                else:
                    loss = min(18, max(0, source_data.get("total_gold", 0)))
                    source_data["total_gold"] -= loss
                    reports.append(f"💥 反噬命中：【命运反咬】你损失 {loss} 金币。")

            elif tag.startswith("borrow_blade:"):
                if not all_users or not source_uid or not target_data:
                    continue
                _, min_val, max_val = tag.split(":")
                min_val, max_val = int(min_val), int(max_val)
                target_uid = self._find_uid_by_data(all_users, target_data)
                valid_helpers = _filter_participant_uids(all_users, {source_uid, target_uid})
                helper_name = "一名路过的群友"
                if valid_helpers:
                    helper_uid = random.choice(valid_helpers)
                    helper_name = all_users.get(helper_uid, {}).get("name", helper_name)
                dmg = random.randint(min_val, max_val)
                actual = min(dmg, max(0, target_data.get("total_gold", 0)))
                target_data["total_gold"] -= actual
                reports.append(f"🗡️ 你借来【{helper_name}】的名头下黑手，成功暗算 {target_name}，造成 {actual} 金币伤害！")

                bounty_bonus = self._apply_bounty_bonus(source_data, target_data)
                if bounty_bonus > 0:
                    reports.append(f"🎯 悬赏印记顺势炸开，{target_name} 额外又掉了 {bounty_bonus} 金币，并被你收走。")

                reflected = int(self._apply_thorn_reflect(source_data, target_data, actual) or 0)
                if reflected > 0:
                    reports.append(f"🪞 目标反甲触发！你被反震 {reflected} 金币。")

            elif tag.startswith("bounty_mark:"):
                _, hours, bonus = tag.split(":")
                hours = int(hours)
                bonus = int(bonus)
                expire_time = int(time.time()) + hours * 3600
                self._upsert_timed_status(
                    target_data,
                    "悬赏印记",
                    expire_time,
                    bounty_bonus=abs(bonus),
                    desc=f"受到金币类攻击时额外损失 {abs(bonus)} 金币，攻击者获得同额收益",
                )
                reports.append(f"📜 悬赏落下！{target_name} 被挂上【悬赏印记】{hours} 小时，之后每次挨打都会额外多掉 {abs(bonus)} 金币。")

            elif tag.startswith("strip_buff_gain:"):
                _, percent, hours = tag.split(":")
                percent = int(percent)
                hours = int(hours)
                statuses = target_data.get("statuses", [])
                removed_name = ""
                for i, st in enumerate(list(statuses)):
                    if self._is_positive_status(st):
                        removed = statuses.pop(i)
                        removed_name = removed.get("name", "未知增益")
                        break

                if removed_name:
                    expire_time = int(time.time()) + hours * 3600
                    self._upsert_timed_status(
                        source_data,
                        "好运加护",
                        expire_time,
                        func_draw_prob_mod=abs(percent),
                        desc=f"功能牌爆率 +{abs(percent)}%",
                    )
                    reports.append(f"🪄 你偷梁换柱，剥走了 {target_name} 的【{removed_name}】，并为自己赢得 {abs(percent)}% 功能牌爆率加成，持续 {hours} 小时！")
                else:
                    reports.append(f"🪄 你试图拆走 {target_name} 的增益，但对方身上没有可被篡改的正面状态。")

            elif tag == "add_shield":
                has_shield = any(st.get("name") == "无懈可击" for st in target_data.get("statuses", []))
                if has_shield:
                    reports.append("🛡️ 目标周身已有同类护盾，法术产生共鸣消散了。")
                else:
                    target_data["statuses"].append({"name": "无懈可击", "desc": "抵挡1次恶意法术"})
                    reports.append("🛡️ 催动法诀，【无懈可击】已成功挂载！")

            elif tag.startswith("thorn_armor:"):
                _, hours, ratio = tag.split(":")
                hours = int(hours)
                ratio = int(ratio)
                expire_time = int(time.time()) + hours * 3600
                self._upsert_timed_status(
                    target_data,
                    "反甲",
                    expire_time,
                    thorn_ratio=ratio,
                    desc=f"受到攻击时反弹 {ratio}% 伤害",
                )
                reports.append(f"🦔 荆棘装甲覆盖全身！反甲生效 {hours} 小时，反弹比例 {ratio}%。")

            # ----------------------------------------
            # 🏷️ 词库：aoe_damage (群体随机伤害)
            # ----------------------------------------
            elif tag.startswith("aoe_damage:"):
                if not all_users or not source_uid: continue
                parsed = _parse_aoe_range_tag(tag, "aoe_damage")
                if not parsed:
                    reports.append("⚠️ 群体攻击配置无效，正确格式应为：aoe_damage:最小值:最大值:人数")
                    continue
                min_val, max_val, count = parsed
                
                valid_targets = _filter_participant_uids(all_users, {source_uid})
                target_count = min(count, len(valid_targets))
                selected = random.sample(valid_targets, target_count)
                
                if not selected:
                    reports.append("💨 虚空之中空无一人，大军迷路了...")
                    continue
                    
                hit_logs = []
                for uid in selected:
                    t_data = all_users[uid]
                    # 💡 修复：强制读取真名 "name"
                    t_name = t_data.get("name", f"群友({uid})")
                    
                    has_shield = False
                    for i, st in enumerate(t_data.get("statuses", [])):
                        if st.get("name") == "无懈可击":
                            t_data["statuses"].pop(i)
                            has_shield = True
                            # 💡 战损联动：打破 AOE 目标的盾牌
                            for card in t_data.get("inventory", []):
                                if card.get("card_name") == "无懈可击" and card.get("is_active"):
                                    card["is_active"] = False
                                    card["is_broken"] = True
                                    card["broken_reason"] = "护盾被击破"
                                    break

                            break
                            
                    if has_shield:
                        hit_logs.append(f"{t_name}(🛡️免疫)")
                        self.last_aoe_events.append({
                            "type": "aoe_damage",
                            "target_uid": uid,
                            "target_name": t_name,
                            "amount": 0,
                            "blocked": True,
                            "reflected": 0,
                        })
                    else:
                        dmg = random.randint(min_val, max_val)
                        actual_dmg = min(dmg, max(0, t_data.get("total_gold", 0)))
                        t_data["total_gold"] -= actual_dmg
                        bounty_bonus = self._apply_bounty_bonus(source_data, t_data)

                        reflected = int(self._apply_thorn_reflect(source_data, t_data, actual_dmg) or 0)
                        shown_dmg = max(0, actual_dmg - reflected) + bounty_bonus
                        hit_logs.append(f"{t_name}(-{shown_dmg})")

                        self.last_aoe_events.append({
                            "type": "aoe_damage",
                            "target_uid": uid,
                                                        "target_name": t_name,
                            "amount": shown_dmg,
                            "blocked": False,
                            "reflected": reflected,
                        })
                        
                reports.append(f"🏹 大军横扫全场！波及目标：{', '.join(hit_logs)}")

            # ----------------------------------------

            # 🏷️ 词库：aoe_heal (群体随机治疗)
            # ----------------------------------------
            elif tag.startswith("aoe_heal:"):
                if not all_users or not source_uid: continue
                parsed = _parse_aoe_range_tag(tag, "aoe_heal")
                if not parsed:
                    reports.append("⚠️ 群体回复配置无效，正确格式应为：aoe_heal:最小值:最大值:人数")
                    continue
                min_val, max_val, count = parsed
                
                valid_targets = _filter_participant_uids(all_users, {source_uid})
                other_count = min(max(0, count - 1), len(valid_targets))
                selected_others = random.sample(valid_targets, other_count)
                selected = [source_uid] + selected_others
                
                hit_logs = []
                for uid in selected:
                    t_data = all_users[uid]
                    # 💡 修复：强制读取真名 "name"
                    t_name = t_data.get("name", f"群友({uid})")
                    heal = random.randint(min_val, max_val)
                    t_data["total_gold"] += heal
                    hit_logs.append(f"{t_name}(+{heal})")
                    self.last_aoe_events.append({
                        "type": "aoe_heal",
                        "target_uid": uid,
                        "target_name": t_name,
                        "amount": heal,
                        "blocked": False,
                    })
                reports.append(f"🌿 盛宴洒向全场！波及目标：{', '.join(hit_logs)}")

            elif tag.startswith("aoe_cleanse:"):
                if not all_users or not source_uid:
                    continue
                count = _parse_aoe_count_tag(tag, "aoe_cleanse")
                if count is None:
                    reports.append("⚠️ 群体净化配置无效，正确格式应为：aoe_cleanse:人数")
                    continue

                valid_targets = _filter_participant_uids(all_users, {source_uid})
                selected_others = random.sample(valid_targets, min(max(0, count - 1), len(valid_targets)))
                selected = [source_uid] + selected_others

                hit_logs = []

                for uid in selected:
                    t_data = all_users[uid]
                    t_name = t_data.get("name", f"群友({uid})")
                    removed = self._remove_one_negative_status(t_data)
                    removed_name = removed.get("name", "") if removed else ""
                    if removed_name:
                        hit_logs.append(f"{t_name}(已净化 {removed_name})")
                        self.last_aoe_events.append({
                            "type": "aoe_cleanse",
                            "target_uid": uid,
                            "target_name": t_name,
                            "amount": 1,
                            "blocked": False,
                            "removed_status": removed_name,
                        })
                    else:
                        hit_logs.append(f"{t_name}(无负面)")
                        self.last_aoe_events.append({
                            "type": "aoe_cleanse",
                            "target_uid": uid,
                            "target_name": t_name,
                            "amount": 0,
                            "blocked": False,
                            "removed_status": "",
                        })

                reports.append(f"✨ 群体净化扩散完成！影响目标：{', '.join(hit_logs)}")

        return reports
