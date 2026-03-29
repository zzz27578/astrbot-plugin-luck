# ==============================================================================
# 🏅 异世界·称号系统引擎 (Title Engine) 
# ==============================================================================
# 💡 【配置说明】
# name: 称号名字
# desc: 称号的具体说明（将在面板中单独分行展示）
# bonus_prob: 该称号能为“抽取功能牌”额外增加的爆率百分比
# ==============================================================================

class TitleEngine:
    TITLES_CONFIG = {
        "勤勉之人": {
            "name": "勤勉之人",
            "desc": "连续签到7天以上获得。天道酬勤，抽取功能牌爆率永久 +5%",
            "bonus_prob": 5,
            "attack_gold_bonus": 0
        },
        "行善之人": {
            "name": "行善之人",
            "desc": "善值达到 5 点以上获得。心存善念，抽取功能牌爆率永久 +5%",
            "bonus_prob": 5,
            "attack_gold_bonus": 0
        },
        "邪恶之人": {
            "name": "邪恶之人",
            "desc": "恶值达到 5 点以上获得。每次使用功能牌发动攻击时，额外获得 10 金币。",
            "bonus_prob": 0,
            "attack_gold_bonus": 10
        }
    }

    # 善恶称号阈值
    KARMA_GOOD_THRESHOLD = 5
    KARMA_EVIL_THRESHOLD = -5

    @classmethod
    def get_title_info(cls, title_name: str) -> dict:
        """获取称号的详细配置信息"""
        return cls.TITLES_CONFIG.get(title_name, {
            "name": title_name,
            "desc": "未知的神秘称号",
            "bonus_prob": 0
        })

    @classmethod
    def calculate_total_bonus_prob(cls, user_titles: list) -> int:
        """遍历玩家拥有的所有称号，把它们加成的爆率全部加和起来"""
        total_bonus = 0
        for t in user_titles:
            info = cls.get_title_info(t)
            total_bonus += info.get("bonus_prob", 0)
        return total_bonus

    @classmethod
    def calculate_total_attack_gold_bonus(cls, user_titles: list) -> int:
        """遍历玩家拥有的所有称号，合计攻击额外金币收益"""
        total = 0
        for t in user_titles:
            info = cls.get_title_info(t)
            total += info.get("attack_gold_bonus", 0)
        return total

    @classmethod
    def sync_karma_titles(cls, user_data: dict) -> list:
        """
        根据当前善恶值自动授予或撤销善恶称号。
        返回发生变化的事件列表，每项为 (action, title_name)，
        action 为 'gained' 或 'lost'。
        """
        karma = int(user_data.get("karma_value", 0))
        titles = user_data.setdefault("titles", [])
        events = []

        # 行善之人：善值 >= 5 授予，跌回 < 5 撤销
        if karma >= cls.KARMA_GOOD_THRESHOLD:
            if "行善之人" not in titles:
                titles.append("行善之人")
                events.append(("gained", "行善之人"))
        else:
            if "行善之人" in titles:
                titles.remove("行善之人")
                events.append(("lost", "行善之人"))

        # 邪恶之人：恶值 <= -5 授予，回升到 > -5 撤销
        if karma <= cls.KARMA_EVIL_THRESHOLD:
            if "邪恶之人" not in titles:
                titles.append("邪恶之人")
                events.append(("gained", "邪恶之人"))
        else:
            if "邪恶之人" in titles:
                titles.remove("邪恶之人")
                events.append(("lost", "邪恶之人"))

        return events