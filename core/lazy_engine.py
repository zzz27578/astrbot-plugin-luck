from __future__ import annotations

import json
import random
import re
import uuid
import time
from pathlib import Path
from urllib.parse import urlparse

from aiohttp import ClientSession, ClientTimeout

from .plugin_storage import CONFIG_DIR

_TIMEOUT = ClientTimeout(total=15)
_ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_FUNC_TYPES = ("attack", "heal", "defense")

def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default

def _pick_image_suffix(url: str, content_type: str = "") -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in _ALLOWED_IMAGE_EXTS:
        return suffix
    content_type = (content_type or "").lower()
    if "png" in content_type:
        return ".png"
    if "gif" in content_type:
        return ".gif"
    if "webp" in content_type:
        return ".webp"
    return ".jpg"

async def _fetch_json_url(session: ClientSession, url: str) -> dict | list:
    async with session.get(url, headers={"User-Agent": "luck_rank_lazy/1.0"}) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        return await resp.json(content_type=None)

def _extract_quote(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""
    # 先尝试素颜API字段
    text = payload.get("text", "")
    if text and isinstance(text, str) and text.strip():
        return text.strip()
    # 尝试 hitokoto 字段
    text = payload.get("hitokoto", "")
    if text and isinstance(text, str) and text.strip():
        return text.strip()
    return ""

def _extract_image_url(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""
    url = payload.get("url")
    if url and isinstance(url, str) and url.strip():
        return url.strip()
    results = payload.get("results")
    if isinstance(results, list) and results:
        item = results[0]
        if isinstance(item, dict):
            return item.get("url", "").strip()
    return ""

async def fetch_pure_quote(used_texts: set[str]) -> str:
    """获取独立的一句话，不重复"""
    async with ClientSession(timeout=_TIMEOUT) as session:
        for _ in range(3):
            try:
                # 强缓存打破
                url = f"https://api.suyanw.cn/api/meiju?_t={random.random()}{time.time()}"
                payload = await _fetch_json_url(session, url)
                text = _extract_quote(payload)
                if text and text not in used_texts:
                    return text
            except Exception:
                pass

            try:
                url = f"https://v1.hitokoto.cn?_t={random.random()}{time.time()}"
                payload = await _fetch_json_url(session, url)
                text = _extract_quote(payload)
                if text and text not in used_texts:
                    return text
            except Exception:
                pass

    return "命运的车轮，在此刻开始转动。"

async def fetch_random_waifu_image(target_dir: Path, prefix: str) -> str:
    """强制外部下载二次元图片并返回新文件名"""
    target_dir.mkdir(parents=True, exist_ok=True)
    async with ClientSession(timeout=_TIMEOUT) as session:
        image_url = ""
        for base_url in ("https://api.waifu.pics/sfw/waifu", "https://nekos.best/api/v2/neko"):
            try:
                source_url = f"{base_url}?_t={random.random()}{time.time()}"
                payload = await _fetch_json_url(session, source_url)
                image_url = _extract_image_url(payload)
                if image_url:
                    break
            except Exception:
                continue
        
        if not image_url:
            raise RuntimeError("无法获取可用的外部图片地址")

        async with session.get(image_url, headers={"User-Agent": "luck_rank_lazy/1.0"}) as resp:
            if resp.status != 200:
                raise RuntimeError(f"图片下载失败: HTTP {resp.status}")
            content = await resp.read()
            if len(content) < 32:
                raise RuntimeError("图片内容太小")
            suffix = _pick_image_suffix(image_url, resp.headers.get("Content-Type", ""))
            filename = f"{prefix}_{uuid.uuid4().hex[:12]}{suffix}"
            (target_dir / filename).write_bytes(content)
            return filename

def _choose_local_image(target_dir: Path, used_images: set[str]) -> str:
    """纯随机从本地选取一张尚未被使用的图片"""
    if not target_dir.exists():
        return ""
    files = [f.name for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in _ALLOWED_IMAGE_EXTS]
    available = [f for f in files if f not in used_images]
    if not available:
        return ""
    return random.choice(available)


async def build_fate_draft(
    remote_dir: Path,
    local_dir: Path,
    gold_min: int,
    gold_max: int,
    image_mode: str,
    gen_text: bool,
    used_texts: set[str],
    used_images: set[str]
) -> dict:
    gold = random.randint(min(gold_min, gold_max), max(gold_min, gold_max))
    
    text = ""
    name = "未命名命运牌"
    if gen_text:
        raw_quote = await fetch_pure_quote(used_texts)
        used_texts.add(raw_quote)
        name = f"命运·{raw_quote[:8]}" if raw_quote else "未命名命运牌"
        prefix = f"金币加{gold}\n" if gold >= 0 else f"金币减{abs(gold)}\n"
        text = f"{prefix}{raw_quote}"

    filename = ""
    if image_mode == "local":
        filename = _choose_local_image(local_dir, used_images)
        if filename:
            used_images.add(filename)
    elif image_mode == "remote":
        try:
            filename = await fetch_random_waifu_image(remote_dir, "rfate")
        except Exception:
            pass

    return {
        "name": name,
        "text": text,
        "gold": gold,
        "filename": filename,
    }


def _load_builtin_func_cards() -> list[dict]:
    path = CONFIG_DIR / "func_cards.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [c for c in data if isinstance(c, dict) and c.get("card_name")]
    except Exception:
        return []

def _translate_tag_to_human_desc(tag: str) -> str:
    raw = str(tag).strip()
    if not raw:
        return ""
    parts = raw.split(":")
    key = parts[0]
    
    if key == "steal": return f"偷取目标 {parts[1] if len(parts)>1 else 0} 金币"
    if key == "freeze": return f"冻结目标 {parts[1] if len(parts)>1 else 0} 小时，期间禁止抽牌与出牌"
    if key == "silence": return f"沉默目标 {parts[1] if len(parts)>1 else 0} 小时，期间禁止出牌"
    if key == "seal_draw_all": return f"封印目标抽牌 {parts[1] if len(parts)>1 else 0} 小时"
    if key == "luck_drain": return f"吸取目标爆率 {parts[2] if len(parts)>2 else 0}%，持续 {parts[1] if len(parts)>1 else 0} 小时"
    if key == "steal_fate": return "偷取目标上一次抽取的命运牌金币收益"
    if key == "borrow_blade": return f"伪装成路人对目标造成 {parts[1] if len(parts)>1 else 0}~{parts[2] if len(parts)>2 else 0} 金币伤害"
    if key == "bounty_mark": return f"对目标施加悬赏印记 {parts[1] if len(parts)>1 else 0} 小时，期间其受损时额外扣除并转移 {parts[2] if len(parts)>2 else 0} 金币"
    if key == "strip_buff_gain": return f"剥夺目标 1 个增益，自身爆率提升 {parts[1] if len(parts)>1 else 0}% 持续 {parts[2] if len(parts)>2 else 0} 小时"
    if key == "aoe_damage": return f"群攻：固定 {parts[3] if len(parts)>3 else (parts[2] if len(parts)>2 else 0)} 人，不足则按全体结算；每人分别造成 {parts[1] if len(parts)>1 else 0}~{parts[2] if len(parts)>2 else 0} 金币伤害"
    if key == "dice_rule": return f"触发一套旧版随机模板"
    if key == "lucky_roulette": return "触发一次自定义幸运转盘，按命中号码结算不同效果"
    if key == "dice_duel": return f"向目标发起一场最低投入为 {parts[1] if len(parts)>1 else 20} 的骰子决斗"
    if key == "cleanse": return "单体净化 1 个负面状态"
    if key == "aoe_cleanse": return f"群辅：固定 {parts[1] if len(parts)>1 else 0} 人，不足则按全体结算；每人各净化 1 个负面状态"
    if key == "aoe_heal": return f"群辅：固定 {parts[3] if len(parts)>3 else (parts[2] if len(parts)>2 else 0)} 人，不足则按全体结算；每人分别恢复 {parts[1] if len(parts)>1 else 0}~{parts[2] if len(parts)>2 else 0} 金币"
    if key == "luck_bless": return f"为自己附加好运，爆率提升 {parts[2] if len(parts)>2 else 0}% 持续 {parts[1] if len(parts)>1 else 0} 小时"
    if key == "fate_roulette": return "触发一次命运转盘"
    if key == "dice_reroll_lowest_once": return "为自己挂载天命重投，下次骰点最低时自动重投 1 次"
    if key == "add_shield": return "为目标挂载一层无懈可击护盾"
    if key == "thorn_armor": return f"挂载反甲 {parts[1] if len(parts)>1 else 0} 小时，按 {parts[2] if len(parts)>2 else 0}% 反弹金币伤害"
    return ""

def _calculate_effect_value(tags: list[str]) -> int:
    val = 0
    for tag in tags:
        raw = str(tag).strip()
        parts = raw.split(":")
        key = parts[0]
        if key == "steal" and len(parts) > 1:
            val += _safe_int(parts[1], 10)
        elif key == "aoe_damage" and len(parts) > 2:
            val += _safe_int(parts[2], 10) * 3
        elif key == "freeze" or key == "silence" or key == "seal_draw_all":
            val += 25
        elif key == "bounty_mark" and len(parts) > 2:
            val += _safe_int(parts[2], 5) * 4
        elif key == "add_shield":
            val += 20
        else:
            val += 10
    return val

async def build_func_draft(
    remote_dir: Path,
    local_dir: Path,
    allowed_types: list[str],
    max_rarity: int,
    max_tags: int,
    max_effect_val: int,
    image_mode: str,
    gen_text: bool,
    used_images: set[str]
) -> dict:
    pool = _load_builtin_func_cards()
    valid_pool = []
    for c in pool:
        ctype = c.get("type", "attack")
        rarity = max(1, min(5, _safe_int(c.get("rarity", 1))))
        tags = c.get("tags", [])
        if allowed_types and ctype not in allowed_types:
            continue
        if rarity > max_rarity:
            continue
        if len(tags) > max_tags:
            continue
        if _calculate_effect_value(tags) > max_effect_val:
            continue
        valid_pool.append(c)

    if not valid_pool:
        raise RuntimeError("没有满足这些条件的功能牌模板可供生成，请放宽条件，例如金币限制或稀有度上限。")

    base_card = random.choice(valid_pool)
    name = base_card.get("card_name", "未命名")
    desc = base_card.get("description", "")
    tags = base_card.get("tags", [])

    if gen_text:
        human_descs = [_translate_tag_to_human_desc(t) for t in tags]
        human_descs = [d for d in human_descs if d]
        if human_descs:
            desc = "，并".join(human_descs) + "。"
        elif not desc:
            desc = "一张毫无特点的卡牌。"

    filename = ""
    if image_mode == "local":
        filename = _choose_local_image(local_dir, used_images)
        if filename:
            used_images.add(filename)
    elif image_mode == "remote":
        try:
            filename = await fetch_random_waifu_image(remote_dir, "rfunc")
        except Exception:
            pass

    return {
        "card_name": name,
        "type": base_card.get("type", "attack"),
        "rarity": base_card.get("rarity", 1),
        "description": desc,
        "filename": filename,
        "tags": tags,
    }
