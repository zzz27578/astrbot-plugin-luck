from __future__ import annotations

import json
import random
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

from aiohttp import ClientSession, ClientTimeout

from .plugin_storage import CONFIG_DIR

_TIMEOUT = ClientTimeout(total=15)
_ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_FUNC_TYPES = ("attack", "heal", "defense")

# =============================================================================
# 工具函数
# =============================================================================
def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default

def _tokenize(value: str) -> list[str]:
    text = str(value or "").lower()
    parts = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text)
    return [p for p in parts if p]

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

def _extract_suyan_quote(payload) -> str:
    if isinstance(payload, dict):
        text = payload.get("text", "")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""

def _extract_hitokoto(payload) -> str:
    if isinstance(payload, dict):
        text = payload.get("hitokoto", "")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""

def _extract_image_url(payload) -> str:
    if isinstance(payload, dict):
        direct = payload.get("url")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        results = payload.get("results")
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    candidate = item.get("url")
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate.strip()
    return ""

# =============================================================================
# 核心拉取逻辑
# =============================================================================
async def fetch_pure_quote() -> str:
    """优先素颜API，失败尝试一言（去除作者名）"""
    async with ClientSession(timeout=_TIMEOUT) as session:
        try:
            payload = await _fetch_json_url(session, "https://api.suyanw.cn/api/meiju")
            text = _extract_suyan_quote(payload)
            if text:
                return text
        except Exception:
            pass

        try:
            payload = await _fetch_json_url(session, "https://v1.hitokoto.cn")
            text = _extract_hitokoto(payload)
            if text:
                return text
        except Exception:
            pass

    return "命运的车轮，在此刻开始转动。"

async def fetch_random_waifu_image(target_dir: Path, prefix: str) -> str:
    target_dir.mkdir(parents=True, exist_ok=True)
    async with ClientSession(timeout=_TIMEOUT) as session:
        image_url = ""
        for source_url in ("https://api.waifu.pics/sfw/waifu", "https://nekos.best/api/v2/neko"):
            try:
                payload = await _fetch_json_url(session, source_url)
                image_url = _extract_image_url(payload)
                if image_url:
                    break
            except Exception:
                continue
        if not image_url:
            raise RuntimeError("无法获取可用的图片地址")

        async with session.get(image_url, headers={"User-Agent": "luck_rank_lazy/1.0"}) as resp:
            if resp.status != 200:
                raise RuntimeError(f"图片下载失败: HTTP {resp.status}")
            content = await resp.read()
            if len(content) < 32:
                raise RuntimeError("图片内容太小，疑似无效")
            suffix = _pick_image_suffix(image_url, resp.headers.get("Content-Type", ""))
            filename = f"{prefix}_{uuid.uuid4().hex[:12]}{suffix}"
            (target_dir / filename).write_bytes(content)
            return filename

def _choose_local_image(target_dir: Path, seeds: list[str]) -> str:
    if not target_dir.exists():
        return ""
    files = [f for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in _ALLOWED_IMAGE_EXTS]
    if not files:
        return ""

    seed_tokens = set()
    for seed in seeds:
        seed_tokens.update(_tokenize(seed))

    if seed_tokens:
        ranked = []
        for f in files:
            name_tokens = set(_tokenize(f.stem))
            score = len(seed_tokens & name_tokens)
            if score > 0:
                ranked.append((score, f.name))
        if ranked:
            ranked.sort(key=lambda item: (-item[0], item[1]))
            top_score = ranked[0][0]
            top_names = [name for score, name in ranked if score == top_score]
            return random.choice(top_names)

    return random.choice([f.name for f in files])

# =============================================================================
# 编辑器草稿生成逻辑
# =============================================================================
async def build_fate_draft(
    fate_dir: Path, 
    gold_min: int, 
    gold_max: int, 
    gen_pic: bool, 
    gen_text: bool, 
    prefer_local: bool, 
    allow_remote: bool
) -> dict:
    gold = random.randint(min(gold_min, gold_max), max(gold_min, gold_max))
    
    text = ""
    name = "未命名命运牌"
    if gen_text:
        raw_quote = await fetch_pure_quote()
        name = f"命运·{raw_quote[:8]}" if raw_quote else "未命名命运牌"
        prefix = f"金币加{gold}\n" if gold >= 0 else f"金币减{abs(gold)}\n"
        text = f"{prefix}{raw_quote}"

    filename = ""
    if gen_pic:
        if prefer_local:
            filename = _choose_local_image(fate_dir, [name, text])
        if not filename and allow_remote:
            try:
                filename = await fetch_random_waifu_image(fate_dir, "fate")
            except Exception:
                pass
        if not filename and not prefer_local:
            filename = _choose_local_image(fate_dir, [name, text])

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


def _calculate_effect_value(tags: list[str]) -> int:
    """计算这张牌的效果金币影响值（粗略评估）"""
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
    func_dir: Path,
    allowed_types: list[str],
    max_rarity: int,
    max_tags: int,
    max_effect_val: int,
    gen_pic: bool,
    gen_text: bool,
    prefer_local: bool,
    allow_remote: bool
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
        raise RuntimeError("没有满足条件的功能牌模板可供生成")

    base_card = random.choice(valid_pool)
    name = base_card.get("card_name", "未命名")
    desc = base_card.get("description", "")

    if gen_text and not desc:
        desc = "(系统根据模板自动生成的卡牌)"
    elif not gen_text:
        desc = ""

    filename = ""
    if gen_pic:
        if prefer_local:
            filename = _choose_local_image(func_dir, [name, desc])
        if not filename and allow_remote:
            try:
                filename = await fetch_random_waifu_image(func_dir, "func")
            except Exception:
                pass
        if not filename and not prefer_local:
            filename = _choose_local_image(func_dir, [name, desc])

    return {
        "card_name": name,
        "type": base_card.get("type", "attack"),
        "rarity": base_card.get("rarity", 1),
        "description": desc,
        "filename": filename,
        "tags": base_card.get("tags", []),
    }
