import random
import time
import os
import json
from typing import Any, Dict, List, Optional


# ================= 🎲 可扩展骰子规则池（纯掷骰，不做业务结算） =================
# 规则来源：config/dice_rules.json
# 规则说明：
# - dice: 掷骰基础配置
#   - count: 骰子个数
#   - sides: 每个骰子的面数
#   - keep: 计分模式（sum/highest/lowest）
# - outcomes: 点数区间结果
#   - min/max: 命中区间
#   - outcome_id: 业务层可识别的结果 ID（骰子模块不解释）
#   - title: 结果文案
#   - payload: 透传给业务层的数据（骰子模块不执行）

_FALLBACK_DICE_RULES: Dict[str, Dict[str, Any]] = {
    "all_in_raid_v1": {
        "name": "孤注一掷",
        "dice": {"count": 1, "sides": 6, "keep": "sum"},
        "outcomes": [
            {
                "min": 1,
                "max": 2,
                "outcome_id": "bad",
                "title": "【下下签】手抖了，强袭失准！",
                "payload": {"op": "sac_steal", "cost": 12, "steal": 16, "reserve": 1},
            },
            {
                "min": 3,
                "max": 4,
                "outcome_id": "mid",
                "title": "【中签】赌对一半，强夺得手。",
                "payload": {"op": "sac_steal", "cost": 20, "steal": 32, "reserve": 1},
            },
            {
                "min": 5,
                "max": 5,
                "outcome_id": "good",
                "title": "【上签】时机完美，爆发劫掠！",
                "payload": {"op": "sac_steal", "cost": 28, "steal": 50, "reserve": 1},
            },
            {
                "min": 6,
                "max": 6,
                "outcome_id": "crit",
                "title": "【天命暴击】命运眷顾，梭哈成功！",
                "payload": {"op": "sac_steal", "cost": 36, "steal": 72, "reserve": 1},
            },
        ],
    }
}


def _load_dice_rules_config() -> Dict[str, Dict[str, Any]]:
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "dice_rules.json")
    if not os.path.exists(config_path):
        return _FALLBACK_DICE_RULES

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and data:
                return data
    except Exception:
        pass

    return _FALLBACK_DICE_RULES


DICE_RULES: Dict[str, Dict[str, Any]] = _load_dice_rules_config()


class DiceEngine:
    """纯骰子引擎：只负责掷骰和返回结果，不参与金币/状态业务结算。"""

    def get_status_modifiers(self, statuses: List[Dict[str, Any]]) -> Dict[str, int]:
        """从状态中提取掷骰修正，供外部按需调用。"""
        now_ts = int(time.time())
        mods = {"count": 0, "sides": 0, "total": 0}

        for st in statuses or []:
            expire_time = st.get("expire_time")
            if expire_time is not None and int(expire_time) <= now_ts:
                continue

            mods["count"] += int(st.get("dice_count_mod", 0) or 0)
            mods["sides"] += int(st.get("dice_sides_mod", 0) or 0)
            mods["total"] += int(st.get("dice_total_mod", 0) or 0)

        return mods

    def roll(self, count: int = 1, sides: int = 6, keep: str = "sum", total_mod: int = 0) -> Dict[str, Any]:
        """执行一次纯掷骰。"""
        count = max(1, int(count))
        sides = max(2, int(sides))

        rolls = [random.randint(1, sides) for _ in range(count)]
        if keep == "highest":
            used = [max(rolls)]
            base_total = used[0]
        elif keep == "lowest":
            used = [min(rolls)]
            base_total = used[0]
        else:
            used = rolls[:]
            base_total = sum(used)

        final_total = base_total + int(total_mod)
        return {
            "rolls": rolls,
            "used": used,
            "base_total": base_total,
            "total_mod": int(total_mod),
            "final_total": final_total,
        }

    def roll_rule(self, rule_key: str, statuses: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """按规则键执行掷骰并返回命中 outcome（仅透传 payload）。"""
        rule = DICE_RULES.get(rule_key)
        if not rule:
            return {
                "ok": False,
                "reports": [f"⚠️ 骰子规则不存在：{rule_key}"],
                "rule_key": rule_key,
                "outcome_id": None,
                "payload": None,
            }

        dice_cfg = rule.get("dice", {})
        mods = self.get_status_modifiers(statuses or [])

        count = max(1, int(dice_cfg.get("count", 1)) + mods["count"])
        sides = max(2, int(dice_cfg.get("sides", 6)) + mods["sides"])
        keep = str(dice_cfg.get("keep", "sum"))

        roll_ret = self.roll(count=count, sides=sides, keep=keep, total_mod=mods["total"])
        final_total = int(roll_ret["final_total"])

        reports = [
            f"🎲 掷骰结果：{roll_ret['rolls']}（计分 {roll_ret['used']}，修正 {mods['total']:+d}）=> 总点数 {final_total}"
        ]

        chosen = None
        for outcome in rule.get("outcomes", []):
            if int(outcome.get("min", -10**9)) <= final_total <= int(outcome.get("max", 10**9)):
                chosen = outcome
                break

        if not chosen:
            reports.append("💨 骰面坍缩，未命中任何结算区间。")
            return {
                "ok": True,
                "reports": reports,
                "rule_key": rule_key,
                "roll": roll_ret,
                "outcome_id": None,
                "payload": None,
            }

        title = chosen.get("title")
        if title:
            reports.append(f"✨ {title}")

        return {
            "ok": True,
            "reports": reports,
            "rule_key": rule_key,
            "roll": roll_ret,
            "outcome_id": chosen.get("outcome_id"),
            "payload": chosen.get("payload"),
        }
