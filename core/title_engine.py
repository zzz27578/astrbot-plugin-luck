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
            "bonus_prob": 5
        }
    }

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