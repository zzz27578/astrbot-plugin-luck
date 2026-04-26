from __future__ import annotations

import json
from pathlib import Path

from .plugin_storage import CONFIG_DIR
from .json_cache import load_json_cached


class TitleEngine:
    DEFAULT_TITLES_FILE = CONFIG_DIR / "titles_config.json"
    DEFAULT_MAX_EQUIPPED = 3
    CONDITION_LABELS = {
        "sign_in_consecutive": "连续签到",
        "sign_in_total": "累计签到",
        "karma_good": "善值达到",
        "karma_evil": "恶值达到",
        "fate_card_gold": "命运牌单次金币",
        "fate_card_drawn": "命运牌累计抽取",
        "func_card_drawn": "功能牌累计抽取",
        "func_card_used": "功能牌累计使用",
        "attack_success": "攻击成功次数",
        "heal_success": "治疗成功次数",
        "defense_success": "防御成功次数",
        "duel_win": "决斗胜利次数",
        "duel_count": "参与决斗次数",
        "gold_total": "金币总量",
        "luck_value": "今日运势",
        "title_count": "拥有称号数量",
        }
    EFFECT_LABELS = {

        "func_draw_prob": "功能牌爆率",
        "attack_gold_bonus": "攻击额外金币",
        "heal_gold_bonus": "治疗额外金币",
        "defense_gold_bonus": "防御额外金币",
        "sign_in_gold_bonus": "签到金币加成",
        "fate_draw_bonus": "命运牌次数",
        "free_draw_bonus": "免费抽卡次数",
        "draw_cost_discount": "抽卡费用减免",
        "pity_threshold_mod": "保底阈值修正",
        "steal_bonus": "偷取收益加成",
        "aoe_range_bonus": "群体波及人数增加",
        "duel_stake_bonus": "决斗胜利金币加成",
    }


    @classmethod
    def ensure_user_title_fields(cls, user_data: dict) -> dict:
        user_data.setdefault("titles", [])
        user_data.setdefault("equipped_titles", [])
        user_data.setdefault("manual_titles", [])
        user_data.setdefault("title_events", [])
        return user_data

    @classmethod
    def load_titles_config(cls, config: dict | None = None) -> list[dict]:
        path = (config or {}).get("_storage_paths", {}).get("titles_config_file")
        target = path if isinstance(path, Path) else cls.DEFAULT_TITLES_FILE
        return load_json_cached(target, default=[], normalize=cls.normalize_titles)

    @classmethod
    def normalize_titles(cls, raw_titles) -> list[dict]:
        normalized = []
        for item in raw_titles if isinstance(raw_titles, list) else []:
            if not isinstance(item, dict):
                continue
            title_id = str(item.get("id", "") or "").strip()
            name = str(item.get("name", title_id) or title_id).strip()
            if not title_id or not name:
                continue
            conditions = []
            for cond in item.get("conditions", []) if isinstance(item.get("conditions", []), list) else []:
                if not isinstance(cond, dict):
                    continue
                cond_type = str(cond.get("type", "") or "").strip()
                if not cond_type:
                    continue
                conditions.append({
                    "type": cond_type,
                    "operator": str(cond.get("operator", ">=") or ">=").strip(),
                    "value": cond.get("value", 0),
                })
            effects = []
            for eff in item.get("effects", []) if isinstance(item.get("effects", []), list) else []:
                if not isinstance(eff, dict):
                    continue
                eff_type = str(eff.get("type", "") or "").strip()
                if not eff_type:
                    continue
                effects.append({
                    "type": eff_type,
                    "value": eff.get("value", 0),
                })
            normalized.append({
                "id": title_id,
                "name": name,
                "category": str(item.get("category", "未分类") or "未分类").strip() or "未分类",
                "desc": str(item.get("desc", "") or "").strip(),
                "allow_loss": bool(item.get("allow_loss", False)),
                "conditions": conditions,
                "effects": effects,
            })
        return normalized

    @classmethod
    def get_title_catalog(cls) -> dict:
        return {
            "conditions": [
                {"key": "sign_in_consecutive", "name": "连续签到天数", "param": "阈值"},
                {"key": "sign_in_total", "name": "累计签到天数", "param": "阈值"},
                {"key": "karma_good", "name": "善值达到", "param": "阈值"},
                {"key": "karma_evil", "name": "恶值达到", "param": "阈值"},
                {"key": "fate_card_gold", "name": "命运牌单次金币", "param": "阈值"},
                {"key": "fate_card_drawn", "name": "命运牌累计抽取", "param": "阈值"},
                {"key": "func_card_drawn", "name": "功能牌累计抽取", "param": "阈值"},
                {"key": "func_card_used", "name": "功能牌累计使用", "param": "阈值"},
                {"key": "attack_success", "name": "攻击成功次数", "param": "阈值"},
                {"key": "heal_success", "name": "治疗成功次数", "param": "阈值"},
                {"key": "defense_success", "name": "防御成功次数", "param": "阈值"},
                {"key": "duel_win", "name": "决斗胜利次数", "param": "阈值"},
                {"key": "duel_count", "name": "参与决斗次数", "param": "阈值"},
                {"key": "gold_total", "name": "金币总量", "param": "阈值"},
                {"key": "luck_value", "name": "今日运势", "param": "阈值"},
                {"key": "title_count", "name": "拥有称号数量", "param": "阈值"},
            ],
            "effects": [
                {"key": "func_draw_prob", "name": "功能牌爆率加成", "param": "百分比"},
                {"key": "attack_gold_bonus", "name": "攻击额外金币", "param": "数值"},
                {"key": "heal_gold_bonus", "name": "治疗额外金币", "param": "数值"},
                {"key": "defense_gold_bonus", "name": "防御额外金币", "param": "数值"},
                {"key": "sign_in_gold_bonus", "name": "签到金币加成", "param": "百分比"},
                {"key": "fate_draw_bonus", "name": "命运牌每日次数加成", "param": "数值"},
                {"key": "free_draw_bonus", "name": "功能牌每日免费次数加成", "param": "数值"},
                {"key": "draw_cost_discount", "name": "功能牌抽卡费用减免", "param": "数值"},
                {"key": "pity_threshold_mod", "name": "保底阈值修正", "param": "数值"},
                                {"key": "steal_bonus", "name": "偷取收益加成", "param": "百分比"},
                {"key": "aoe_range_bonus", "name": "群体波及人数增加", "param": "人数"},
                {"key": "duel_stake_bonus", "name": "决斗胜利金币加成", "param": "百分比"},

            ],
        }

    @classmethod
    def _compare(cls, current, operator: str, expected) -> bool:
        try:
            current_val = float(current)
            expected_val = float(expected)
        except Exception:
            current_val = current
            expected_val = expected
        if operator == "<=":
            return current_val <= expected_val
        if operator == "==":
            return current_val == expected_val
        if operator == "<":
            return current_val < expected_val
        if operator == ">":
            return current_val > expected_val
        return current_val >= expected_val

    @classmethod
    def _condition_value(cls, user_data: dict, condition_type: str):
        mapping = {
            "sign_in_consecutive": int(user_data.get("consecutive_sign_ins", 0) or 0),
            "sign_in_total": int(user_data.get("total_sign_in_days", 0) or 0),
            "karma_good": int(user_data.get("karma_value", 0) or 0),
            "karma_evil": int(user_data.get("karma_value", 0) or 0),
            "fate_card_gold": int(user_data.get("max_fate_card_gold", 0) or 0),
            "fate_card_drawn": int(user_data.get("total_fate_card_draws", 0) or 0),
            "func_card_drawn": int(user_data.get("total_func_cards_drawn", 0) or 0),
            "func_card_used": int(user_data.get("total_func_cards_used", 0) or 0),
            "attack_success": int(user_data.get("total_attack_success", 0) or 0),
            "heal_success": int(user_data.get("total_heal_success", 0) or 0),
            "defense_success": int(user_data.get("total_defense_success", 0) or 0),
            "duel_win": int(user_data.get("total_duel_wins", 0) or 0),
            "duel_count": int(user_data.get("total_duel_count", 0) or 0),
            "gold_total": int(user_data.get("total_gold", 0) or 0),
            "luck_value": int(user_data.get("today_luck_value", 0) or 0),
            "title_count": len(user_data.get("titles", [])),
        }
        return mapping.get(condition_type, 0)

    @classmethod
    def check_title_conditions(cls, user_data: dict, title_cfg: dict) -> bool:
        conditions = title_cfg.get("conditions", [])
        if not conditions:
            return False
        for cond in conditions:
            current = cls._condition_value(user_data, cond.get("type", ""))
            if not cls._compare(current, str(cond.get("operator", ">=")), cond.get("value", 0)):
                return False
        return True

    @classmethod
    def sync_titles(cls, user_data: dict, config: dict | None = None) -> list[tuple[str, str]]:
        cls.ensure_user_title_fields(user_data)
        title_cfgs = cls.load_titles_config(config)
        title_map = {item["name"]: item for item in title_cfgs}
        owned = user_data.setdefault("titles", [])
        equipped = user_data.setdefault("equipped_titles", [])
        manual_titles_raw = user_data.setdefault("manual_titles", [])
        manual_titles = set(manual_titles_raw)
        events: list[tuple[str, str]] = []

        for title_name in list(owned):
            cfg = title_map.get(title_name)
            if not cfg:
                owned.remove(title_name)
                if title_name in equipped:
                    equipped.remove(title_name)
                manual_titles.discard(title_name)
                events.append(("lost", title_name))
                continue
            if title_name in manual_titles:
                continue
            if cfg.get("allow_loss", False) and not cls.check_title_conditions(user_data, cfg):
                owned.remove(title_name)
                if title_name in equipped:
                    equipped.remove(title_name)
                events.append(("lost", title_name))

        user_data["manual_titles"] = [title_name for title_name in manual_titles_raw if title_name in title_map and title_name in owned]
        user_data["equipped_titles"] = [title_name for title_name in equipped if title_name in owned]

        for cfg in title_cfgs:
            title_name = cfg["name"]
            if title_name in owned:
                continue
            if cls.check_title_conditions(user_data, cfg):
                owned.append(title_name)
                events.append(("gained", title_name))

        return events

    @classmethod
    def get_title_info(cls, title_name: str, config: dict | None = None) -> dict:
        for item in cls.load_titles_config(config):
            if item.get("name") == title_name:
                return item
        return {
            "id": title_name,
            "name": title_name,
            "category": "未分类",
            "desc": "未知的神秘称号",
            "allow_loss": False,
            "conditions": [],
            "effects": [],
        }

    @classmethod
    def get_max_equipped_titles(cls, config: dict | None = None) -> int:
        runtime_cfg = (config or {}).get("func_cards_settings", {})
        return max(1, int(runtime_cfg.get("max_equipped_titles", cls.DEFAULT_MAX_EQUIPPED) or cls.DEFAULT_MAX_EQUIPPED))

    @classmethod
    def get_equipped_titles(cls, user_data: dict, config: dict | None = None) -> list[str]:
        cls.ensure_user_title_fields(user_data)
        owned = set(user_data.get("titles", []))
        max_count = cls.get_max_equipped_titles(config)
        equipped = [name for name in user_data.get("equipped_titles", []) if name in owned]
        if len(equipped) > max_count:
            equipped = equipped[:max_count]
            user_data["equipped_titles"] = equipped
        return equipped

    @classmethod
    def calculate_effects(cls, user_data: dict, config: dict | None = None) -> dict:
        effects: dict[str, int] = {}
        for title_name in cls.get_equipped_titles(user_data, config):
            info = cls.get_title_info(title_name, config)
            for effect in info.get("effects", []):
                effect_type = str(effect.get("type", "") or "").strip()
                if not effect_type:
                    continue
                effects[effect_type] = effects.get(effect_type, 0) + int(effect.get("value", 0) or 0)
        return effects

    @classmethod
    def calculate_total_bonus_prob(cls, user_data: dict | list, config: dict | None = None) -> int:
        if isinstance(user_data, list):
            total = 0
            for title_name in user_data:
                info = cls.get_title_info(title_name, config)
                for effect in info.get("effects", []):
                    if effect.get("type") == "func_draw_prob":
                        total += int(effect.get("value", 0) or 0)
            return total
        return cls.calculate_effects(user_data, config).get("func_draw_prob", 0)

    @classmethod
    def calculate_total_attack_gold_bonus(cls, user_data: dict | list, config: dict | None = None) -> int:
        if isinstance(user_data, list):
            total = 0
            for title_name in user_data:
                info = cls.get_title_info(title_name, config)
                for effect in info.get("effects", []):
                    if effect.get("type") == "attack_gold_bonus":
                        total += int(effect.get("value", 0) or 0)
            return total
        return cls.calculate_effects(user_data, config).get("attack_gold_bonus", 0)

    @classmethod
    def format_title_event_lines(cls, events: list[tuple[str, str]], config: dict | None = None) -> list[str]:
        lines = []
        for action, title_name in events:
            info = cls.get_title_info(title_name, config)
            if action == "gained":
                lines.append(f"🏅 达成伟业！获得称号：【{title_name}】")
            else:
                lines.append(f"🥀 条件不再满足，称号【{title_name}】已撤销。")
            if info.get("desc"):
                lines.append(f"   └ {info['desc']}")
        return lines

    @classmethod
    def describe_effects(cls, effects: list[dict]) -> list[str]:
        lines = []
        for eff in effects if isinstance(effects, list) else []:
            eff_type = str(eff.get("type", "") or "").strip()
            value = int(eff.get("value", 0) or 0)
            if eff_type == "func_draw_prob":
                lines.append(f"功能牌爆率 +{value}%")
            elif eff_type == "attack_gold_bonus":
                lines.append(f"攻击成功额外 +{value} 金币")
            elif eff_type == "heal_gold_bonus":
                lines.append(f"治疗成功额外 +{value} 金币")
            elif eff_type == "defense_gold_bonus":
                lines.append(f"防御成功额外 +{value} 金币")
            elif eff_type == "sign_in_gold_bonus":
                lines.append(f"签到金币 +{value}%")
            elif eff_type == "fate_draw_bonus":
                lines.append(f"命运牌每日次数 +{value}")
            elif eff_type == "free_draw_bonus":
                lines.append(f"功能牌每日免费次数 +{value}")
            elif eff_type == "draw_cost_discount":
                lines.append(f"功能牌抽卡费用 -{value}")
            elif eff_type == "pity_threshold_mod":
                lines.append(f"保底阈值修正 {value:+d}")
            elif eff_type == "steal_bonus":
                lines.append(f"偷取收益 +{value}%")
            elif eff_type == "aoe_range_bonus":
                lines.append(f"群体波及人数 +{value}")
            elif eff_type == "duel_stake_bonus":
                lines.append(f"决斗胜利金币 +{value}%")


        return lines
