import os
import json
import random
from datetime import datetime
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Plain, Image
from ..core.logic_gate import find_gate_block, format_gate_block_message, GATE_DRAW_FATE_CARD

def load_cards_config():
    """读取你原有的静态命运牌配置"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "cards_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

async def handle_fate_card_draw(event: AstrMessageEvent, bank, max_limit: int = 3):
    """处理 /luck 抽卡 (命运牌) 逻辑"""
    user_id = event.get_sender_id()
    user_name = event.get_sender_name()
    today = datetime.now().strftime("%Y-%m-%d")

    cards_config = load_cards_config()
    if not cards_config:
        yield event.plain_result("⚠️ 异世界的卡池空空如也，请联系天道配置 config/cards_config.json！")
        return

    # 获取用户档案
    user_data = await bank.get_user_data(user_id, user_name)

    # ==========================================
    # 🚧 逻辑门拦截：抽取命运牌
    # ==========================================
    blocked_by = find_gate_block(user_data, GATE_DRAW_FATE_CARD)
    if blocked_by:
        msg = format_gate_block_message(
            blocked_by,
            "⚠️ 你的当前状态禁止抽取命运牌，请稍后再试。"
        )
        yield event.plain_result(msg)
        return

    # 日期变更重置抽卡次数
    if user_data.get("last_card_date") != today:
        user_data["last_card_draw_count"] = 0
        user_data["last_drawn_gold"] = 0
        user_data["last_card_date"] = today

    # 检查每日次数上限 (配置默认3次)
    if user_data["last_card_draw_count"] >= max_limit:
        yield event.plain_result(f"⏳ {user_name}，今日的命运牌抽换机会已用尽，期待明天的命运指引吧。")
        return

    # 核心博弈回滚逻辑：如果是换牌，先扣掉旧牌的分数
    user_data["total_gold"] -= user_data.get("last_drawn_gold", 0)

    # 抽取命运牌
    card = random.choice(cards_config)
    img_filename = card.get("filename", "")
    text = card.get("text", "一张神秘的卡牌")
    value = card.get("value", 0)

    # 匹配原有的图库路径
    img_path = os.path.join(os.path.dirname(__file__), "..", "assets", "cards", img_filename)
    
    if not os.path.exists(img_path):
        # 图片丢失时的失败回滚保护
        user_data["total_gold"] += user_data.get("last_drawn_gold", 0)
        yield event.plain_result(f"⚠️ 抽到了卡牌，但异界裂缝吞噬了卡面图片：{img_filename}")
        return

    # 写入新卡数据并落盘
    user_data["total_gold"] += value
    user_data["last_drawn_gold"] = value
    user_data["last_card_draw_count"] += 1
    await bank.save_user_data()

    val_str = f"+{value}" if value > 0 else str(value)
    remaining_chances = max_limit - user_data["last_card_draw_count"]
    chance_hint = f"今日还能换牌的次数：{remaining_chances}" if remaining_chances > 0 else "今日换牌机会已用完"

    # 原汁原味的图文混排输出
    chain = [
        Image.fromFileSystem(img_path),
        Plain(f"\n\n{text}\n━━━━━━━━\n💰 金币波动：{val_str}\n💰 当前总金币：{user_data['total_gold']}\n💡 {chance_hint}")
    ]
    yield event.chain_result(chain)