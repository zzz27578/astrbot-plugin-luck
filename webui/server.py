# ==============================================================================
# 🌐 luck_rank WebUI 管理后端
# ==============================================================================
import os
import json
import asyncio
import tempfile
import shutil
import random
import re
import secrets
import uuid
import hashlib
import time
import sys
import platform
import stat
import tarfile
import subprocess
from urllib.parse import urlparse
from pathlib import Path
from aiohttp import web, ClientSession, ClientTimeout

from ..core.title_engine import TitleEngine
from ..core.json_cache import load_json_cached, invalidate_json_cache
from ..core.lazy_engine import (
    build_func_draft,
    _choose_local_image,
)
from ..core.plugin_storage import (
    DEFAULT_PROFILE_NAME,
    PLUGIN_NAME,

    ensure_default_profile,
    ensure_profile_dirs,
    get_base_storage_paths,
    get_group_profile_map,
    get_profile_storage_paths,
    migrate_legacy_storage,
    save_group_profile_map,
)

# 路径配置
ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
BASE_PATHS = get_base_storage_paths(PLUGIN_NAME)
STORAGE_PATHS = get_profile_storage_paths(DEFAULT_PROFILE_NAME, PLUGIN_NAME)
migrate_legacy_storage(PLUGIN_NAME)
ASSETS_DIR = STORAGE_PATHS["func_assets_dir"]
GROUP_DATA_DIR = BASE_PATHS["group_data_dir"]
GROUP_PROFILE_MAP_FILE = BASE_PATHS["group_profile_map_file"]
PROFILE_META_FILENAME = "profile_meta.json"
GROUP_ACCESS_FILE = BASE_PATHS["plugin_data_dir"] / "group_access_control.json"
FUNC_CARDS_FILE = STORAGE_PATHS["func_cards_file"]
FATE_CARDS_FILE = STORAGE_PATHS["fate_cards_file"]
SIGN_IN_TEXTS_FILE = STORAGE_PATHS["sign_in_texts_file"]
RUNTIME_CONFIG_FILE = STORAGE_PATHS["runtime_config_file"]
FATE_ASSETS_DIR = STORAGE_PATHS["fate_assets_dir"]
WEBUI_DIR = Path(__file__).parent
STATIC_DIR = WEBUI_DIR / "static"
DEFAULT_FUNC_CARDS_FILE = CONFIG_DIR / "func_cards.json"
DEFAULT_FATE_CARDS_FILE = CONFIG_DIR / "cards_config.json"
DEFAULT_RUNTIME_CONFIG_FILE = CONFIG_DIR / "webui_runtime_config.json"
DEFAULT_TITLES_CONFIG_FILE = CONFIG_DIR / "titles_config.json"
BUILTIN_DEFAULT_COPY_FROM = "__builtin_default__"

BLANK_COPY_FROM = "__blank__"
WEBUI_DEFAULT_ACCESS_PASSWORD = "12345678"
WEBUI_SESSION_COOKIE = "luck_webui_session"
WEBUI_ACCESS_CONFIG_FILE = BASE_PATHS["plugin_data_dir"] / "webui_access_config.json"
VISITOR_DATA_DIR = BASE_PATHS["plugin_data_dir"] / "visitor_collab"
VISITOR_ROLES_FILE = VISITOR_DATA_DIR / "roles.json"
VISITOR_KEYS_FILE = VISITOR_DATA_DIR / "keys.json"
VISITOR_DRAFTS_FILE = VISITOR_DATA_DIR / "drafts.json"
VISITOR_AUDIT_FILE = VISITOR_DATA_DIR / "audit_logs.json"
VISITOR_TUNNEL_FILE = VISITOR_DATA_DIR / "tunnel_config.json"
VISITOR_INSTALL_STATE_FILE = VISITOR_DATA_DIR / "cloudflared_install_state.json"
_WEBUI_ACCESS_PASSWORD = WEBUI_DEFAULT_ACCESS_PASSWORD
_AUTH_SESSIONS: dict[str, dict] = {}
_CLOUDFLARED_PROCESS = None
_CLOUDFLARED_PUBLIC_URL = ""
_CLOUDFLARED_INSTALL_TASKS: dict[str, dict] = {}
_CLOUDFLARED_DOWNLOAD_SOURCES = [
    {
        "id": "official",
        "name": "官方 GitHub Release",
        "description": "Cloudflare 官方发布资产。",
    },
    {
        "id": "custom",
        "name": "自定义镜像/模板",
        "description": "使用带 {url} 或 {asset} 的自定义 URL 模板。",
    },
]

# 默认签到文案（fallback）
DEFAULT_SIGN_IN_TEXTS = {
    "good_things": [
        "擦拭法杖", "冥想", "练习火球术", "探索地下城", "给史莱姆喂食",
        "得到救世魔杖", "整理背包", "购买回复药水", "专心附魔", "擦亮盔甲",
        "向神像祈祷", "研读古籍", "在酒馆打听情报", "攻破迷宫", "得到古代魔导具"
    ],
    "bad_things": [
        "遇到帝位魔兽", "单独行动", "喝陌生的药水", "直视深渊", "相信地精的鬼话",
        "在这个时间点强化装备", "在酒馆酗酒", "偷看禁书", "与魔炎龙战斗", "遇到独眼巨人"
    ],
    "luck_comments": {
        "91_100": ["天命之子！鸿运当头，此时不抽更待何时！", "星轨共鸣，今日诸事大吉！"],
        "71_90": ["大吉。如有神助，爆率飙升。", "今日气运高涨，宜乘势而为。"],
        "51_70": ["小吉。灵力涌动，爆率提升。", "稳中有进，今日不宜冒进。"],
        "1_50": ["平平无奇。宜蛰伏蓄锐，莫生事端。", "天道轮回，蛰伏等待时机。"]
    },
    "luck_ranges": [
        {"label": "平运", "min": 1, "max": 50, "gold_delta": 0, "comments": ["平平无奇。宜蛰伏蓄锐，莫生事端。", "天道轮回，蛰伏等待时机。"]},
        {"label": "小吉", "min": 51, "max": 70, "gold_delta": 0, "comments": ["小吉。灵力涌动，爆率提升。", "稳中有进，今日不宜冒进。"]},
        {"label": "大吉", "min": 71, "max": 90, "gold_delta": 0, "comments": ["大吉。如有神助，爆率飙升。", "今日气运高涨，宜乘势而为。"]},
                {"label": "天命", "min": 91, "max": 100, "gold_delta": 0, "comments": ["天命之子！鸿运当头，此时不抽更待何时！", "星轨共鸣，今日诸事大吉！"]}
    ],
    "enable_quote": True,
    "enable_draw_prob": True,
    "use_custom_quote": False,
    "custom_quotes": [
        "这虽然是游戏，但可不是闹着玩的。",
        "风向转变的时候，有人筑墙，有人造风车。",
        "真正的敏捷不是看你能跑多快，而是看你能多快改变方向。"
    ]
}


_LAZY_HTTP_TIMEOUT = ClientTimeout(total=15)
_LAZY_ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_API_IMAGE_PREFIXES = ("api_fate_", "api_func_", "rfate_", "rfunc_", "auto_fate_", "auto_func_")
_FAST_PORTRAIT_APIS = [
    "https://jrys-api.gh0.pw/api/v1/get/image",
    "https://api.yimian.xyz/img?type=moe&size=1080x1920",
    "https://t.alcy.cc/mp",
    "https://api.btstu.cn/sjbz/api.php?method=mobile&lx=dongman",
]
_FALLBACK_IMAGE_URLS = [
    "https://i0.hdslb.com/bfs/article/546ab5af12b986c2d1070028b2a23c678ee6078e.png",
    "https://i0.hdslb.com/bfs/article/288ba1731d3f66ebc5974f6385a59ee6aec25d0a.png",
    "https://i0.hdslb.com/bfs/article/948c5350f766c5179c3f1194a1bdb8b3f86a41e5.png",
    "https://i0.hdslb.com/bfs/article/2e53b99f39e5385ee49b0c8fdbfca22d6a5e5e78.jpg",
    "https://i0.hdslb.com/bfs/article/28ab6b0958a346dc91dec6d2685beee4392cd55f.jpg",
    "https://i0.hdslb.com/bfs/article/2bfc59df642a9847e97eaa6d9e3bca9029b6cf1.png",
    "https://i0.hdslb.com/bfs/article/db54b81d0bce136a442a703820843132a966de.jpg",
    "https://i0.hdslb.com/bfs/article/26fee679ab039aaa5b35cbc3d3a4b8aa391c177.png",
]
_LAZY_QUOTE_FALLBACKS = [
    "命运的车轮已经开始转动。",
    "今晚的风，会替你翻开下一页。",
    "别急，答案正在来的路上。",
    "你以为是偶然，其实是伏笔。",
    "此刻的犹豫，也会成为转机。",
    "有些奖励，会在坚持之后出现。",
    "命运不会催你，但会在拐角等你。",
    "云层之后的光，正在替你蓄力。",
    "下一次抉择，也许就是转运的入口。",
]
_LAZY_QUOTE_OPENERS = ["今夜", "此刻", "转角处", "云层之后", "命运的轨道上", "风停之前", "黎明抵达前"]
_LAZY_QUOTE_SUBJECTS = ["答案", "好运", "回响", "转机", "伏笔", "光", "信号", "机会"]
_LAZY_QUOTE_VERBS = ["正在靠近", "已经启程", "会悄悄出现", "正等你伸手", "藏在下一步里", "比想象更早抵达"]
_LAZY_QUOTE_ENDINGS = ["别急。", "抬头就能看见。", "你会接住它。", "这次别错过。", "只差一步。", "很快就轮到你。"]
_BUILTIN_FALLBACK_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb1\x00\x00\x00\x00IEND\xaeB`\x82"
)

_DEFAULT_PANEL_SECTIONS = [
    {"id": "basic_profile", "enabled": True, "label": "观测对象", "emoji": "📊", "required": True},
    {"id": "titles", "enabled": True, "label": "称号", "emoji": "🏅", "required": False},
    {"id": "statuses", "enabled": True, "label": "异界干涉状态", "emoji": "🎭", "required": False},
    {"id": "dice_status", "enabled": True, "label": "骰局状态", "emoji": "🎲", "required": False},
    {"id": "card_slots", "enabled": True, "label": "战术卡槽", "emoji": "🎴", "required": False},
    {"id": "battle_logs", "enabled": True, "label": "近期恩怨纪事", "emoji": "📜", "required": False},
]


def _default_panel_sections() -> list[dict]:
    return [{k: v for k, v in item.items() if k != "required"} for item in _DEFAULT_PANEL_SECTIONS]


def _sanitize_rank_titles(raw_titles, defaults: list[str]) -> list[str]:
    source = raw_titles if isinstance(raw_titles, list) else []
    values: list[str] = []
    for idx in range(3):
        fallback = defaults[idx]
        value = str(source[idx] if idx < len(source) else fallback).strip() or fallback
        values.append(value)
    return values


def _default_leaderboard_settings(kind: str = "wealth") -> dict:
    if kind == "karma":
        return {
            "enabled": True,
            "show_positive": True,
            "show_negative": True,
            "show_nearby": True,
            "board_length": 10,
            "title": "⚖️ 【天道善恶榜】",
            "positive_header": "😇 【善业榜】",
            "negative_header": "😈 【恶业榜】",
            "nearby_header": "🧭 【你的附近位】",
            "positive_titles": ["😇 首善", "🍀 积福者", "🤝 仁心客"],
            "negative_titles": ["😈 首恶", "🔥 业火者", "🌩️ 灾厄客"],
        }
    return {
        "enabled": True,
        "show_top": True,
        "show_bottom": True,
        "show_nearby": True,
        "board_length": 10,
        "title": "💰 ✦异世界·金币双榜✦ 💰",
        "top_header": "🏆 【金币·封神榜】",
        "bottom_header": "🃃 【倒霉·深渊榜】",
        "nearby_header": "🧭 【你的附近位】",
        "top_titles": ["👑 金冠", "🥈 银序", "🥉 铜席"],
        "bottom_titles": ["💀 穷途", "🪙 漏财", "🕳️ 深渊"],
    }


def _sanitize_leaderboard_settings(raw_settings, fallback_length: int = 10, *, kind: str = "wealth") -> dict:
    merged = _default_leaderboard_settings(kind)
    if isinstance(raw_settings, dict):
        merged.update(raw_settings)
    merged["enabled"] = bool(merged.get("enabled", True))
    merged["board_length"] = _clamp_int(
        merged.get("board_length", fallback_length),
        fallback_length,
        minimum=1,
        maximum=50,
    )
    if kind == "karma":
        merged["show_positive"] = bool(merged.get("show_positive", True))
        merged["show_negative"] = bool(merged.get("show_negative", True))
        merged["show_nearby"] = bool(merged.get("show_nearby", True))
        merged["title"] = str(merged.get("title", _default_leaderboard_settings("karma")["title"]) or _default_leaderboard_settings("karma")["title"]).strip() or _default_leaderboard_settings("karma")["title"]
        merged["positive_header"] = str(merged.get("positive_header", _default_leaderboard_settings("karma")["positive_header"]) or _default_leaderboard_settings("karma")["positive_header"]).strip() or _default_leaderboard_settings("karma")["positive_header"]
        merged["negative_header"] = str(merged.get("negative_header", _default_leaderboard_settings("karma")["negative_header"]) or _default_leaderboard_settings("karma")["negative_header"]).strip() or _default_leaderboard_settings("karma")["negative_header"]
        merged["nearby_header"] = str(merged.get("nearby_header", _default_leaderboard_settings("karma")["nearby_header"]) or _default_leaderboard_settings("karma")["nearby_header"]).strip() or _default_leaderboard_settings("karma")["nearby_header"]
        merged["positive_titles"] = _sanitize_rank_titles(merged.get("positive_titles", []), _default_leaderboard_settings("karma")["positive_titles"])
        merged["negative_titles"] = _sanitize_rank_titles(merged.get("negative_titles", []), _default_leaderboard_settings("karma")["negative_titles"])
    else:
        merged["show_top"] = bool(merged.get("show_top", True))
        merged["show_bottom"] = bool(merged.get("show_bottom", True))
        merged["show_nearby"] = bool(merged.get("show_nearby", True))
        merged["title"] = str(merged.get("title", _default_leaderboard_settings()["title"]) or _default_leaderboard_settings()["title"]).strip() or _default_leaderboard_settings()["title"]
        merged["top_header"] = str(merged.get("top_header", _default_leaderboard_settings()["top_header"]) or _default_leaderboard_settings()["top_header"]).strip() or _default_leaderboard_settings()["top_header"]
        merged["bottom_header"] = str(merged.get("bottom_header", _default_leaderboard_settings()["bottom_header"]) or _default_leaderboard_settings()["bottom_header"]).strip() or _default_leaderboard_settings()["bottom_header"]
        merged["nearby_header"] = str(merged.get("nearby_header", _default_leaderboard_settings()["nearby_header"]) or _default_leaderboard_settings()["nearby_header"]).strip() or _default_leaderboard_settings()["nearby_header"]
        merged["top_titles"] = _sanitize_rank_titles(merged.get("top_titles", []), _default_leaderboard_settings()["top_titles"])
        merged["bottom_titles"] = _sanitize_rank_titles(merged.get("bottom_titles", []), _default_leaderboard_settings()["bottom_titles"])
    return merged


def _default_panel_section_settings() -> dict:
    return {
        "basic_profile": {
            "show_rank": True,
            "show_karma": True,
        },
        "titles": {
            "display_limit": 6,
        },
        "statuses": {
            "display_limit": 5,
        },
        "dice_status": {
            "display_limit": 4,
        },
        "battle_logs": {
            "display_limit": 6,
            "recent_days": 3,
        },
    }


def _sanitize_panel_section_settings(raw_settings) -> dict:
    defaults = _default_panel_section_settings()
    merged = _deep_merge_dict(defaults, raw_settings if isinstance(raw_settings, dict) else {})

    basic = merged.setdefault("basic_profile", {})
    basic["show_rank"] = bool(basic.get("show_rank", True))
    basic["show_karma"] = bool(basic.get("show_karma", True))

    for section_id, default_limit in {
        "titles": 6,
        "statuses": 5,
        "dice_status": 4,
        "battle_logs": 6,
    }.items():
        section_cfg = merged.setdefault(section_id, {})
        section_cfg["display_limit"] = _clamp_int(
            section_cfg.get("display_limit", defaults.get(section_id, {}).get("display_limit", default_limit)),
            default_limit,
            minimum=1,
            maximum=50,
        )
    battle_cfg = merged.setdefault("battle_logs", {})
    battle_cfg["recent_days"] = _clamp_int(
        battle_cfg.get("recent_days", defaults.get("battle_logs", {}).get("recent_days", 3)),
        3,
        minimum=1,
        maximum=30,
    )

    return merged


def _sanitize_panel_sections(raw_sections) -> list[dict]:
    default_map = {item["id"]: item for item in _DEFAULT_PANEL_SECTIONS}
    normalized: list[dict] = []
    seen: set[str] = set()

    for item in raw_sections if isinstance(raw_sections, list) else []:
        if not isinstance(item, dict):
            continue
        section_id = str(item.get("id", "") or "").strip()
        if section_id not in default_map or section_id in seen:
            continue
        default = default_map[section_id]
        enabled = bool(item.get("enabled", default["enabled"]))
        if default.get("required", False):
            enabled = True
        label = str(item.get("label", default["label"]) or default["label"]).strip() or default["label"]
        emoji = str(item.get("emoji", default["emoji"]) or default["emoji"]).strip() or default["emoji"]
        normalized.append({
            "id": section_id,
            "enabled": enabled,
            "label": label,
            "emoji": emoji,
        })
        seen.add(section_id)

    for default in _DEFAULT_PANEL_SECTIONS:
        if default["id"] in seen:
            continue
        normalized.append({
            "id": default["id"],
            "enabled": bool(default["enabled"]),
            "label": default["label"],
            "emoji": default["emoji"],
        })

    basic_index = next((idx for idx, section in enumerate(normalized) if section.get("id") == "basic_profile"), -1)
    if basic_index > 0:
        normalized.insert(0, normalized.pop(basic_index))
    elif basic_index < 0:
        normalized.insert(0, {
            "id": "basic_profile",
            "enabled": True,
            "label": default_map["basic_profile"]["label"],
            "emoji": default_map["basic_profile"]["emoji"],
        })

    normalized[0]["enabled"] = True
    return normalized


def _atomic_write(path: Path, data):
    """原子写入：先写临时文件再替换，防止写到一半损坏"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        tmp = Path(tmp_path)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        shutil.move(str(tmp), str(path))
        invalidate_json_cache(path)
    except Exception:
        if tmp and tmp.exists():
            tmp.unlink()
        raise


def _read_json(path: Path, default=None):
    return load_json_cached(path, default={} if default is None else default)


def _deep_merge_dict(base: dict, override: dict) -> dict:
    result = dict(base or {})
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge_dict(result[k], v)
        else:
            result[k] = v
    return result


def _list_image_files(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    return sorted(f.name for f in directory.iterdir() if f.is_file() and f.suffix.lower() in exts)


def _is_api_generated_image(filename: str) -> bool:
    return str(filename or "").strip().lower().startswith(_API_IMAGE_PREFIXES)


def _build_procedural_lazy_quote(used_texts: set[str]) -> str:
    for _ in range(24):
        text = f"{random.choice(_LAZY_QUOTE_OPENERS)}，{random.choice(_LAZY_QUOTE_SUBJECTS)} {random.choice(_LAZY_QUOTE_VERBS)}，{random.choice(_LAZY_QUOTE_ENDINGS)}"
        if text not in used_texts:
            used_texts.add(text)
            return text
    text = f"命运回响第 {len(used_texts) + 1} 章已经翻开。"
    used_texts.add(text)
    return text


def _choose_any_image(target_dir: Path, used_images: set[str], allow_repeat: bool = True) -> str:
    if not target_dir.exists():
        return ""
    files = [f.name for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in _LAZY_ALLOWED_IMAGE_EXTS]
    if not files:
        return ""
    if allow_repeat:
        return random.choice(files)
    available = [f for f in files if f not in used_images]
    return random.choice(available) if available else ""


def _create_builtin_fallback_image(target_dir: Path, prefix: str) -> str:
    target_dir.mkdir(parents=True, exist_ok=True)
    logo_path = ROOT_DIR / "logo.png"
    filename = f"{prefix}_{uuid.uuid4().hex[:12]}.png"
    dest = target_dir / filename
    if logo_path.exists():
        shutil.copy2(logo_path, dest)
        return filename
    dest.write_bytes(_BUILTIN_FALLBACK_PNG)
    return filename


def _load_json_template(path: Path, default):
    data = _read_json(path, default)
    if isinstance(default, list):
        return data if isinstance(data, list) else list(default)
    if isinstance(default, dict):
        return data if isinstance(data, dict) else dict(default)
    return data


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _normalize_fate_cards(cards) -> list:
    normalized = []
    for card in cards if isinstance(cards, list) else []:
        if not isinstance(card, dict):
            continue
        normalized.append({
            "name": str(card.get("name", "") or "").strip() or "未命名命运牌",
            "text": str(card.get("text", "") or "一张神秘的卡牌").strip() or "一张神秘的卡牌",
            "gold": _safe_int(card.get("gold", card.get("value", 0)), 0),
            "filename": Path(str(card.get("filename", "") or "")).name,
        })
    return normalized


def _normalize_func_cards(cards) -> list:
    normalized = []
    for card in cards if isinstance(cards, list) else []:
        if not isinstance(card, dict):
            continue
        card_name = str(card.get("card_name", "") or "").strip()
        if not card_name:
            continue
        raw_tags = card.get("tags", [])
        tags = [str(t).strip() for t in raw_tags if str(t).strip()] if isinstance(raw_tags, list) else []
        rarity = max(1, min(5, _safe_int(card.get("rarity", 1), 1)))
        normalized.append({
            "card_name": card_name,
            "type": str(card.get("type", "attack") or "attack").strip() or "attack",
            "description": str(card.get("description", "") or "一张神秘的战术卡").strip() or "一张神秘的战术卡",
            "filename": Path(str(card.get("filename", "") or "")).name,
            "tags": tags,
            "rarity": rarity,
        })
    return normalized


def _normalize_sign_in_texts(texts) -> dict:
    data = texts if isinstance(texts, dict) else {}
    result = {
        "good_things": [str(x).strip() for x in data.get("good_things", []) if str(x).strip()],
        "bad_things": [str(x).strip() for x in data.get("bad_things", []) if str(x).strip()],
        "luck_ranges": [],
    }

    legacy_comments = data.get("luck_comments")
    if isinstance(legacy_comments, dict):
        result["luck_comments"] = legacy_comments

    raw_ranges = data.get("luck_ranges", [])
    if isinstance(raw_ranges, list):
        for item in raw_ranges:
            if not isinstance(item, dict):
                continue
            min_val = _safe_int(item.get("min", 1), 1)
            max_val = _safe_int(item.get("max", 100), 100)
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            comments = item.get("comments", [])
            result["luck_ranges"].append({
                "label": str(item.get("label", "") or "\u65b0\u533a\u95f4").strip() or "\u65b0\u533a\u95f4",
                "min": min_val,
                "max": max_val,
                "gold_delta": _safe_int(item.get("gold_delta", 0), 0),
                "comments": [str(x).strip() for x in comments if str(x).strip()] if isinstance(comments, list) else [],
            })

    result["enable_quote"] = bool(data.get("enable_quote", True))
    result["enable_draw_prob"] = bool(data.get("enable_draw_prob", True))
    result["use_custom_quote"] = bool(data.get("use_custom_quote", False))
    result["custom_quotes"] = [str(x).strip() for x in data.get("custom_quotes", []) if str(x).strip()]
    if not result["custom_quotes"]:
        result["custom_quotes"] = DEFAULT_SIGN_IN_TEXTS.get("custom_quotes", [])

    return result

def _normalize_titles_config(titles) -> list:
    return TitleEngine.normalize_titles(titles)



def _ensure_profile_seed_data(profile_id: str):
    paths = get_profile_storage_paths(profile_id, PLUGIN_NAME)
    ensure_profile_dirs(profile_id, PLUGIN_NAME)

    if not paths["func_cards_file"].exists() or not isinstance(_read_json(paths["func_cards_file"], []), list) or not _read_json(paths["func_cards_file"], []):
        _atomic_write(paths["func_cards_file"], _load_json_template(DEFAULT_FUNC_CARDS_FILE, []))

    if not paths["fate_cards_file"].exists() or not isinstance(_read_json(paths["fate_cards_file"], []), list) or not _read_json(paths["fate_cards_file"], []):
        _atomic_write(paths["fate_cards_file"], _load_json_template(DEFAULT_FATE_CARDS_FILE, []))

    if not paths["runtime_config_file"].exists() or not isinstance(_read_json(paths["runtime_config_file"], {}), dict) or not _read_json(paths["runtime_config_file"], {}):
        runtime_seed = _load_json_template(DEFAULT_RUNTIME_CONFIG_FILE, {})
        merged_runtime = _deep_merge_dict(_default_runtime_config(), runtime_seed if isinstance(runtime_seed, dict) else {})
        _atomic_write(paths["runtime_config_file"], merged_runtime)

    if not paths["sign_in_texts_file"].exists() or not isinstance(_read_json(paths["sign_in_texts_file"], {}), dict) or not _read_json(paths["sign_in_texts_file"], {}):
        _atomic_write(paths["sign_in_texts_file"], DEFAULT_SIGN_IN_TEXTS)

    if not paths["titles_config_file"].exists() or not isinstance(_read_json(paths["titles_config_file"], []), list):
        _atomic_write(paths["titles_config_file"], _load_json_template(DEFAULT_TITLES_CONFIG_FILE, []))





def _ensure_private_dirs():
    """确保官方隔离数据目录存在，避免 WebUI 因目录缺失读取异常。"""
    lazy_fate_dir = BASE_PATHS["plugin_data_dir"] / "lazy_images" / "fate"
    lazy_func_dir = BASE_PATHS["plugin_data_dir"] / "lazy_images" / "func"
    for directory in (
        BASE_PATHS["plugin_data_dir"],
        BASE_PATHS["profiles_dir"],
        GROUP_DATA_DIR,
        FATE_ASSETS_DIR,
        ASSETS_DIR,
        lazy_fate_dir,
        lazy_func_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def _default_group_access_config() -> dict:
    return {
        "mode": "off",
        "blacklist": [],
        "whitelist": [],
    }


def _sanitize_profile_id(profile_id: str) -> str:
    raw = str(profile_id or "").strip()
    if not raw:
        return DEFAULT_PROFILE_NAME
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in raw)
    return cleaned[:64] or DEFAULT_PROFILE_NAME


def _profile_meta_path(profile_id: str) -> Path:
    return get_profile_storage_paths(profile_id, PLUGIN_NAME)["profile_dir"] / PROFILE_META_FILENAME


def _default_profile_meta(profile_id: str) -> dict:
    return {
        "profile_id": profile_id,
        "display_name": "默认配置" if profile_id == DEFAULT_PROFILE_NAME else profile_id,
        "cover_image": "",
        "created_at": "",
    }


def _get_profile_meta(profile_id: str) -> dict:
    meta = _read_json(_profile_meta_path(profile_id), _default_profile_meta(profile_id))
    if not isinstance(meta, dict):
        meta = _default_profile_meta(profile_id)
    meta.setdefault("profile_id", profile_id)
    meta.setdefault("display_name", "默认配置" if profile_id == DEFAULT_PROFILE_NAME else profile_id)
    meta.setdefault("cover_image", "")
    meta.setdefault("created_at", "")
    return meta


def _save_profile_meta(profile_id: str, meta: dict):
    base = _default_profile_meta(profile_id)
    base.update(meta or {})
    _atomic_write(_profile_meta_path(profile_id), base)


def _get_request_profile_id(request) -> str:
    profile_id = _sanitize_profile_id(request.query.get("profile") or request.headers.get("X-Luck-Profile") or DEFAULT_PROFILE_NAME)
    _ensure_profile_seed_data(profile_id)
    return profile_id


def _get_request_profile_paths(request) -> dict:
    profile_id = _get_request_profile_id(request)
    return get_profile_storage_paths(profile_id, PLUGIN_NAME)


def _list_profile_ids() -> list[str]:
    ensure_default_profile(PLUGIN_NAME)
    _ensure_profile_seed_data(DEFAULT_PROFILE_NAME)
    profiles_dir = BASE_PATHS["profiles_dir"]
    result = []
    for item in profiles_dir.iterdir():
        if item.is_dir():
            result.append(item.name)
    if DEFAULT_PROFILE_NAME not in result:
        result.insert(0, DEFAULT_PROFILE_NAME)
    return sorted(set(result), key=lambda x: (x != DEFAULT_PROFILE_NAME, x.lower()))


def _collect_profile_stats(profile_id: str) -> dict:
    _ensure_profile_seed_data(profile_id)
    paths = get_profile_storage_paths(profile_id, PLUGIN_NAME)
    meta = _get_profile_meta(profile_id)
    func_cards = _read_json(paths["func_cards_file"], [])
    fate_cards = _read_json(paths["fate_cards_file"], [])
    mapping = get_group_profile_map(PLUGIN_NAME)
    groups = sorted([gid for gid, pid in mapping.items() if pid == profile_id])
    total_users = 0
    for gid in groups:
        group_file = GROUP_DATA_DIR / str(gid) / "luck_data.json"
        group_data = _read_json(group_file, {})
        if isinstance(group_data, dict):
            total_users += len(group_data)
    return {
        "profile_id": profile_id,
        "display_name": meta.get("display_name") or profile_id,
        "cover_image": meta.get("cover_image", ""),
        "desc": meta.get("desc", ""),
        "tags": meta.get("tags", []),

        "groups": groups,
        "group_count": len(groups),
        "user_count": total_users,
        "func_card_count": len(func_cards) if isinstance(func_cards, list) else 0,
        "fate_card_count": len(fate_cards) if isinstance(fate_cards, list) else 0,
        "is_default": profile_id == DEFAULT_PROFILE_NAME,
    }


def _default_runtime_config() -> dict:
    return {
        "webui_settings": {
            "enable": True,
            "port": 4399,
        },
        "ui_settings": {
            "panel_title": "【个人状态观测仪】",
            "wealth_leaderboard": _default_leaderboard_settings("wealth"),
            "karma_leaderboard": _default_leaderboard_settings("karma"),
            "panel_sections": _default_panel_sections(),
            "panel_section_settings": _default_panel_section_settings(),
        },
        "sign_in_settings": {
            "enable": True,
        },
                "fate_cards_settings": {
            "enable": True,
            "daily_draw_limit": 3,
            "enable_lazy_match": False,
            "enable_super_lazy": False,
            "super_lazy_gold_min": 0,
            "super_lazy_gold_max": 50,
        },
                "func_cards_settings": {
                    "enable": True,
                    "enable_lazy_match": False,
                    "enable_super_lazy": False,
                    "enable_dice_cards": True,
            "enable_public_duel_mode": False,
            "public_duel_daily_limit": 3,
            "public_duel_min_stake": 10,
            "public_duel_max_stake": 200,
            "enable_rarity_dedup": True,
            "custom_rarity_weights": {
                "rarity_1": 30,
                "rarity_2": 30,
                "rarity_3": 28,
                "rarity_4": 11,
                "rarity_5": 1,
            },
                        "economy_settings": {
                "draw_probability": 5,
                "free_daily_draw": 1,
                "paid_daily_draw": 1,
                "draw_cost": 20,
                "pity_threshold": 10,
            },
            "max_equipped_titles": 3,
            "max_inventory_slots": 3,
        },

    }


def _normalize_access_password(value) -> str:
    text = str(value or "").strip()
    return text or WEBUI_DEFAULT_ACCESS_PASSWORD


def _load_current_access_password() -> str:
    data = _read_json(WEBUI_ACCESS_CONFIG_FILE, {})
    if isinstance(data, dict):
        return _normalize_access_password(data.get("access_password", _WEBUI_ACCESS_PASSWORD))
    return _normalize_access_password(_WEBUI_ACCESS_PASSWORD)


def verify_webui_admin_password(password: str) -> bool:
    return secrets.compare_digest(str(password or ""), _load_current_access_password())


def _get_session_token(request: web.Request) -> str:
    return str(request.cookies.get(WEBUI_SESSION_COOKIE, "") or "").strip()


def _get_session_identity(request: web.Request) -> dict:
    token = _get_session_token(request)
    if not token:
        return {}
    return _AUTH_SESSIONS.get(token, {})


def _is_authenticated_request(request: web.Request) -> bool:
    return bool(_get_session_identity(request))


def _is_admin_request(request: web.Request) -> bool:
    return _get_session_identity(request).get("type") == "admin"


def _is_visitor_request(request: web.Request) -> bool:
    return _get_session_identity(request).get("type") == "visitor"


def _default_permissions(**overrides) -> dict:
    data = {
        "can_view": True,
        "can_create_func_card": False,
        "can_edit_func_card": False,
        "can_delete_func_card": False,
        "can_create_fate_card": False,
        "can_edit_fate_card": False,
        "can_delete_fate_card": False,
        "can_upload_image": False,
        "can_delete_image": False,
        "can_edit_titles": False,
        "can_edit_signin": False,
        "can_edit_runtime": False,
        "can_use_lazy_batch_cards": False,
        "can_use_lazy_batch_images": False,
        "requires_review": True,
        "max_cards_per_submit": 1,
        "max_images_per_submit": 2,
        "max_pending_drafts": 3,
        "max_image_size_mb": 5,
    }
    data.update(overrides)
    return data


def _default_visitor_roles() -> list[dict]:
    return [
        {
            "id": "readonly",
            "name": "只读访客",
            "description": "只能查看配置，不能提交任何改动。",
            "permissions": _default_permissions(requires_review=True, max_pending_drafts=0),
            "builtin": True,
        },
        {
            "id": "func_submitter",
            "name": "功能牌投稿员",
            "description": "只能新增少量功能牌和上传少量图片，提交后进入审核。",
            "permissions": _default_permissions(
                can_create_func_card=True,
                can_upload_image=True,
                requires_review=True,
                max_cards_per_submit=1,
                max_images_per_submit=2,
                max_pending_drafts=3,
            ),
            "builtin": True,
        },
        {
            "id": "func_collaborator",
            "name": "功能牌协作者",
            "description": "可以新增和修改功能牌，不能删除，默认需要审核。",
            "permissions": _default_permissions(
                can_create_func_card=True,
                can_edit_func_card=True,
                can_upload_image=True,
                requires_review=True,
                max_cards_per_submit=5,
                max_images_per_submit=5,
                max_pending_drafts=8,
            ),
            "builtin": True,
        },
        {
            "id": "trusted_collaborator",
            "name": "受信协作者",
            "description": "可新增、修改和上传图片，改动可直接生效，但不能删除核心数据。",
            "permissions": _default_permissions(
                can_create_func_card=True,
                can_edit_func_card=True,
                can_create_fate_card=True,
                can_edit_fate_card=True,
                can_upload_image=True,
                can_use_lazy_batch_cards=True,
                requires_review=False,
                max_cards_per_submit=10,
                max_images_per_submit=8,
                max_pending_drafts=20,
            ),
            "builtin": True,
        },
    ]


def _ensure_visitor_files():
    BASE_PATHS["plugin_data_dir"].mkdir(parents=True, exist_ok=True)
    VISITOR_DATA_DIR.mkdir(parents=True, exist_ok=True)
    legacy_map = {
        BASE_PATHS["plugin_data_dir"] / "visitor_roles.json": VISITOR_ROLES_FILE,
        BASE_PATHS["plugin_data_dir"] / "visitor_keys.json": VISITOR_KEYS_FILE,
        BASE_PATHS["plugin_data_dir"] / "visitor_drafts.json": VISITOR_DRAFTS_FILE,
        BASE_PATHS["plugin_data_dir"] / "visitor_audit_logs.json": VISITOR_AUDIT_FILE,
        BASE_PATHS["plugin_data_dir"] / "visitor_tunnel_config.json": VISITOR_TUNNEL_FILE,
    }
    for old_path, new_path in legacy_map.items():
        if old_path.exists() and not new_path.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_path, new_path)
    if not VISITOR_ROLES_FILE.exists():
        _atomic_write(VISITOR_ROLES_FILE, _default_visitor_roles())
    if not VISITOR_KEYS_FILE.exists():
        _atomic_write(VISITOR_KEYS_FILE, [])
    if not VISITOR_DRAFTS_FILE.exists():
        _atomic_write(VISITOR_DRAFTS_FILE, [])
    if not VISITOR_AUDIT_FILE.exists():
        _atomic_write(VISITOR_AUDIT_FILE, [])
    if not VISITOR_TUNNEL_FILE.exists():
        _atomic_write(VISITOR_TUNNEL_FILE, {
            "mode": "manual",
            "cloudflared_path": "",
            "custom_public_url": "",
            "cloudflared_download_source": "official",
            "cloudflared_download_url_template": "",
            "allow_plugin_start_tunnel": False,
            "allow_install_script": False,
        })
    else:
        cfg = _read_dict_file(VISITOR_TUNNEL_FILE)
        changed = False
        for key, value in {
            "cloudflared_download_source": "official",
            "cloudflared_download_url_template": "",
        }.items():
            if key not in cfg:
                cfg[key] = value
                changed = True
        if changed:
            _atomic_write(VISITOR_TUNNEL_FILE, cfg)
    if not VISITOR_INSTALL_STATE_FILE.exists():
        _atomic_write(VISITOR_INSTALL_STATE_FILE, {})


def _read_list_file(path: Path) -> list:
    data = _read_json(path, [])
    return data if isinstance(data, list) else []


def _read_dict_file(path: Path) -> dict:
    data = _read_json(path, {})
    return data if isinstance(data, dict) else {}


def _load_visitor_roles() -> list[dict]:
    _ensure_visitor_files()
    roles = _read_list_file(VISITOR_ROLES_FILE)
    existing = {str(r.get("id", "")): r for r in roles if isinstance(r, dict)}
    changed = False
    for default in _default_visitor_roles():
        if default["id"] not in existing:
            roles.append(default)
            changed = True
    if changed:
        _atomic_write(VISITOR_ROLES_FILE, roles)
    return roles


def _role_map() -> dict[str, dict]:
    return {str(role.get("id", "")): role for role in _load_visitor_roles() if isinstance(role, dict)}


def _normalize_role_id(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_\-]+", "_", text)
    return text.strip("_") or f"role_{uuid.uuid4().hex[:8]}"


def _find_role_by_name_or_id(value: str) -> dict | None:
    needle = str(value or "").strip()
    if not needle:
        return None
    roles = _load_visitor_roles()
    for role in roles:
        if needle == str(role.get("id", "")) or needle == str(role.get("name", "")):
            return role
    lower = needle.lower()
    for role in roles:
        if lower == str(role.get("id", "")).lower() or lower == str(role.get("name", "")).lower():
            return role
    return None


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(str(secret or "").encode("utf-8")).hexdigest()


def _make_visitor_key() -> str:
    raw = secrets.token_urlsafe(18).replace("_", "").replace("-", "").upper()
    chunks = [raw[i:i + 4] for i in range(0, min(len(raw), 16), 4)]
    return "LR-" + "-".join(chunks)


def _public_role(role: dict) -> dict:
    return {
        "id": role.get("id", ""),
        "name": role.get("name", ""),
        "description": role.get("description", ""),
        "permissions": role.get("permissions", {}),
        "builtin": bool(role.get("builtin", False)),
    }


def _public_key_record(item: dict) -> dict:
    return {
        "id": item.get("id", ""),
        "key_prefix": item.get("key_prefix", ""),
        "role_id": item.get("role_id", ""),
        "role_name": item.get("role_name", ""),
        "remark": item.get("remark", ""),
        "status": item.get("status", "active"),
        "created_at": item.get("created_at", 0),
        "last_used_at": item.get("last_used_at", 0),
        "uses": item.get("uses", 0),
        "submissions": item.get("submissions", 0),
    }


def _permission(request: web.Request, key: str, default=False):
    identity = _get_session_identity(request)
    if identity.get("type") == "admin":
        return True
    perms = identity.get("permissions", {})
    return perms.get(key, default)


def _session_role_permissions(request: web.Request) -> dict:
    identity = _get_session_identity(request)
    if identity.get("type") == "admin":
        return _default_permissions(
            can_create_func_card=True,
            can_edit_func_card=True,
            can_delete_func_card=True,
            can_create_fate_card=True,
            can_edit_fate_card=True,
            can_delete_fate_card=True,
            can_upload_image=True,
            can_delete_image=True,
            can_edit_titles=True,
            can_edit_signin=True,
            can_edit_runtime=True,
            can_use_lazy_batch_cards=True,
            can_use_lazy_batch_images=True,
            requires_review=False,
            max_cards_per_submit=100,
            max_images_per_submit=100,
            max_pending_drafts=999,
        )
    return dict(identity.get("permissions", {}) or {})


def _visitor_error(message: str, status: int = 403):
    return web.json_response({"ok": False, "error": message, "code": "permission_denied"}, status=status)


def _load_drafts() -> list[dict]:
    _ensure_visitor_files()
    return _read_list_file(VISITOR_DRAFTS_FILE)


def _save_drafts(drafts: list[dict]):
    _atomic_write(VISITOR_DRAFTS_FILE, drafts)


def _append_audit(event: str, detail: dict):
    _ensure_visitor_files()
    logs = _read_list_file(VISITOR_AUDIT_FILE)
    logs.append({"id": f"audit_{uuid.uuid4().hex[:12]}", "event": event, "at": int(time.time()), "detail": detail})
    _atomic_write(VISITOR_AUDIT_FILE, logs[-500:])


def _count_pending_for_identity(identity: dict) -> int:
    if not identity or identity.get("type") != "visitor":
        return 0
    invite_id = identity.get("invite_id", "")
    return sum(1 for draft in _load_drafts() if draft.get("invite_id") == invite_id and draft.get("status") == "pending")


def _create_review_draft(request: web.Request, resource_type: str, action: str, before, after, summary: str) -> dict:
    identity = _get_session_identity(request)
    profile_id = _get_request_profile_id(request)
    draft = {
        "id": f"draft_{uuid.uuid4().hex[:12]}",
        "status": "pending",
        "resource_type": resource_type,
        "action": action,
        "summary": summary,
        "profile_id": profile_id,
        "before": before,
        "after": after,
        "invite_id": identity.get("invite_id", ""),
        "key_prefix": identity.get("key_prefix", ""),
        "role_id": identity.get("role_id", ""),
        "role_name": identity.get("role_name", ""),
        "created_at": int(time.time()),
        "reviewed_at": 0,
        "reviewer": "",
    }
    drafts = [d for d in _load_drafts() if d.get("status") == "pending"]
    drafts.append(draft)
    _save_drafts(drafts)
    _increment_key_counter(identity.get("invite_id", ""), "submissions")
    _append_audit("draft_created", {"draft_id": draft["id"], "resource_type": resource_type, "summary": summary})
    return draft


def _resource_label(resource_type: str) -> str:
    return {
        "func_cards": "功能牌",
        "fate_cards": "命运牌",
        "titles": "称号",
        "signin": "签到配置",
        "runtime": "运行配置",
    }.get(str(resource_type or ""), str(resource_type or "配置"))


def _draft_changed_keys(before, after) -> list[str]:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return []
    hidden = {"access_password", "password", "secret", "secret_hash", "token", "key"}
    keys = sorted(set(before.keys()) | set(after.keys()))
    return [str(key) for key in keys if key not in hidden and before.get(key) != after.get(key)]


def _draft_brief(draft: dict) -> dict:
    before = draft.get("before")
    after = draft.get("after")
    resource_type = str(draft.get("resource_type") or "")
    details: list[str] = []
    if isinstance(before, list) and isinstance(after, list):
        details.append(f"{_resource_label(resource_type)}：{len(before)} -> {len(after)} 项")
    elif isinstance(before, dict) and isinstance(after, dict):
        changed = _draft_changed_keys(before, after)
        details.append("改动字段：" + ("、".join(changed[:8]) if changed else "无明显字段变化"))
    return {
        "id": draft.get("id", ""),
        "status": draft.get("status", "pending"),
        "resource_type": resource_type,
        "resource_label": _resource_label(resource_type),
        "action": draft.get("action", ""),
        "summary": draft.get("summary") or _resource_label(resource_type),
        "profile_id": draft.get("profile_id", DEFAULT_PROFILE_NAME),
        "role_id": draft.get("role_id", ""),
        "role_name": draft.get("role_name", ""),
        "key_prefix": draft.get("key_prefix", ""),
        "created_at": int(draft.get("created_at", 0) or 0),
        "reviewed_at": int(draft.get("reviewed_at", 0) or 0),
        "reviewer": draft.get("reviewer", ""),
        "details": details,
    }


def _increment_key_counter(key_id: str, field: str):
    if not key_id:
        return
    keys = _read_list_file(VISITOR_KEYS_FILE)
    for item in keys:
        if item.get("id") == key_id:
            item[field] = int(item.get(field, 0) or 0) + 1
            item["last_used_at"] = int(time.time())
            break
    _atomic_write(VISITOR_KEYS_FILE, keys)


def _diff_named_records(kind: str, before: list, after: list) -> dict:
    key_name = "card_name" if kind == "func" else "name"
    if kind == "title":
        key_name = "name"
    before_map = {str(item.get(key_name, "")).strip(): item for item in before if isinstance(item, dict) and str(item.get(key_name, "")).strip()}
    after_map = {str(item.get(key_name, "")).strip(): item for item in after if isinstance(item, dict) and str(item.get(key_name, "")).strip()}
    created = [name for name in after_map if name not in before_map]
    deleted = [name for name in before_map if name not in after_map]
    updated = [name for name in after_map if name in before_map and after_map[name] != before_map[name]]
    return {"created": created, "updated": updated, "deleted": deleted}


def _enforce_card_permissions(request: web.Request, kind: str, before: list, after: list) -> tuple[bool, str, dict]:
    if _is_admin_request(request):
        return True, "", _diff_named_records(kind, before, after)
    diff = _diff_named_records(kind, before, after)
    perms = _session_role_permissions(request)
    prefix = "func" if kind == "func" else "fate"
    if diff["created"] and not perms.get(f"can_create_{prefix}_card", False):
        return False, "当前访客身份不允许新增此类卡片。", diff
    if diff["updated"] and not perms.get(f"can_edit_{prefix}_card", False):
        return False, "当前访客身份不允许修改已有卡片。", diff
    if diff["deleted"] and not perms.get(f"can_delete_{prefix}_card", False):
        return False, "当前访客身份不允许删除卡片。", diff
    changed_count = len(diff["created"]) + len(diff["updated"]) + len(diff["deleted"])
    if changed_count <= 0:
        return True, "", diff
    max_cards = max(0, _safe_int(perms.get("max_cards_per_submit", 1), 1))
    if changed_count > max_cards:
        return False, f"本次改动 {changed_count} 项，超过当前身份允许的 {max_cards} 项上限。", diff
    max_pending = max(0, _safe_int(perms.get("max_pending_drafts", 3), 3))
    if perms.get("requires_review", True) and _count_pending_for_identity(_get_session_identity(request)) >= max_pending:
        return False, f"当前密钥待审核数量已达到 {max_pending} 项上限。", diff
    return True, "", diff


def _change_summary(kind: str, diff: dict) -> str:
    label = {"func": "功能牌", "fate": "命运牌", "title": "称号"}.get(kind, kind)
    parts = []
    if diff.get("created"):
        parts.append(f"新增 {len(diff['created'])} 个{label}: " + "、".join(diff["created"][:5]))
    if diff.get("updated"):
        parts.append(f"修改 {len(diff['updated'])} 个{label}: " + "、".join(diff["updated"][:5]))
    if diff.get("deleted"):
        parts.append(f"删除 {len(diff['deleted'])} 个{label}: " + "、".join(diff["deleted"][:5]))
    return "；".join(parts) or f"{label}配置无实质变化"


def _visitor_pending_response(draft: dict):
    return web.json_response({"ok": True, "pending_review": True, "draft": draft, "message": "改动已提交到待审核区，管理员批准后才会写入正式配置。"})


def _public_session_identity(identity: dict) -> dict:
    if not identity:
        return {"type": "anonymous", "permissions": {}}
    return {
        "type": identity.get("type", "anonymous"),
        "role_id": identity.get("role_id", ""),
        "role_name": identity.get("role_name", "管理员" if identity.get("type") == "admin" else ""),
        "key_prefix": identity.get("key_prefix", ""),
        "permissions": identity.get("permissions", {}),
    }


def _admin_identity() -> dict:
    return {
        "type": "admin",
        "role_id": "admin",
        "role_name": "管理员",
        "permissions": _default_permissions(
            can_create_func_card=True,
            can_edit_func_card=True,
            can_delete_func_card=True,
            can_create_fate_card=True,
            can_edit_fate_card=True,
            can_delete_fate_card=True,
            can_upload_image=True,
            can_delete_image=True,
            can_edit_titles=True,
            can_edit_signin=True,
            can_edit_runtime=True,
            can_use_lazy_batch_cards=True,
            can_use_lazy_batch_images=True,
            requires_review=False,
            max_cards_per_submit=100,
            max_images_per_submit=100,
            max_pending_drafts=999,
        ),
    }


def _verify_visitor_key(secret: str) -> dict | None:
    _ensure_visitor_files()
    secret_hash = _hash_secret(secret)
    roles = _role_map()
    keys = _read_list_file(VISITOR_KEYS_FILE)
    now = int(time.time())
    matched = None
    for item in keys:
        if item.get("status", "active") != "active":
            continue
        if secrets.compare_digest(str(item.get("secret_hash", "")), secret_hash):
            matched = item
            break
    if not matched:
        return None
    role = roles.get(str(matched.get("role_id", "")))
    if not role:
        return None
    matched["uses"] = int(matched.get("uses", 0) or 0) + 1
    matched["last_used_at"] = now
    _atomic_write(VISITOR_KEYS_FILE, keys)
    return {
        "type": "visitor",
        "invite_id": matched.get("id", ""),
        "key_prefix": matched.get("key_prefix", ""),
        "role_id": role.get("id", ""),
        "role_name": role.get("name", ""),
        "permissions": role.get("permissions", {}),
    }


def _is_public_request_path(path: str) -> bool:
    if path in {"/", "/api/access/status", "/api/access/verify", "/api/access/logout", "/favicon.ico"}:
        return True
    return path.startswith("/static/")


@web.middleware
async def auth_middleware(request: web.Request, handler):
    path = request.path
    if _is_public_request_path(path) or _is_authenticated_request(request):
        if _is_visitor_request(request) and path.startswith("/api/") and not _is_visitor_api_path_allowed(request):
            return _visitor_error("当前访客身份不能访问该管理接口。")
        return await handler(request)
    if path.startswith("/api/"):
        return web.json_response(
            {"ok": False, "error": "请先完成访问口令验证。", "code": "auth_required"},
            status=401,
        )
    raise web.HTTPFound("/")


def _is_visitor_api_path_allowed(request: web.Request) -> bool:
    path = request.path
    method = request.method.upper()
    if path.startswith("/api/access/") or path.startswith("/api/visitor/drafts") or path == "/api/visitor/state":
        return True
    read_paths = {
        "/api/runtime_config",
        "/api/fate_cards",
        "/api/fate_images",
        "/api/func_cards",
        "/api/images",
        "/api/sign_in_texts",
        "/api/titles",
        "/api/check_missing_images",
    }
    write_paths = {
        "/api/runtime_config",
        "/api/fate_cards",
        "/api/func_cards",
        "/api/sign_in_texts",
        "/api/titles",
        "/api/upload_fate_image",
        "/api/upload_image",
        "/api/lazy/batch_fate",
        "/api/lazy/batch_func",
        "/api/lazy/auto_bind",
    }
    if method == "GET" and path in read_paths:
        return bool(_permission(request, "can_view", True))
    if method in {"POST", "PUT", "PATCH"} and path in write_paths:
        return True
    if method == "DELETE" and (path.startswith("/api/images/") or path.startswith("/api/fate_images/")):
        return True
    return False


def _seed_profile_from_builtin_defaults(paths: dict):
    runtime_seed = _load_json_template(DEFAULT_RUNTIME_CONFIG_FILE, {})
    merged_runtime = _deep_merge_dict(_default_runtime_config(), runtime_seed if isinstance(runtime_seed, dict) else {})
    _atomic_write(paths["func_cards_file"], _load_json_template(DEFAULT_FUNC_CARDS_FILE, []))
    _atomic_write(paths["fate_cards_file"], _load_json_template(DEFAULT_FATE_CARDS_FILE, []))
    _atomic_write(paths["sign_in_texts_file"], DEFAULT_SIGN_IN_TEXTS)
    _atomic_write(paths["titles_config_file"], _load_json_template(DEFAULT_TITLES_CONFIG_FILE, []))
    _atomic_write(paths["runtime_config_file"], merged_runtime)


def _seed_blank_profile(paths: dict):
    runtime_seed = _load_json_template(DEFAULT_RUNTIME_CONFIG_FILE, {})
    merged_runtime = _deep_merge_dict(_default_runtime_config(), runtime_seed if isinstance(runtime_seed, dict) else {})
    _atomic_write(paths["func_cards_file"], [])
    _atomic_write(paths["fate_cards_file"], [])
    _atomic_write(paths["sign_in_texts_file"], DEFAULT_SIGN_IN_TEXTS)
    _atomic_write(paths["titles_config_file"], _load_json_template(DEFAULT_TITLES_CONFIG_FILE, []))
    _atomic_write(paths["runtime_config_file"], merged_runtime)


def _get_request_runtime_config(request) -> tuple[dict, dict]:
    paths = _get_request_profile_paths(request)
    current = _read_json(paths["runtime_config_file"], {})
    merged = _sanitize_runtime_config(current if isinstance(current, dict) else {})
    return paths, merged


def _clamp_int(value, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except Exception:
        number = int(default)
    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _sanitize_runtime_config(cfg: dict | None) -> dict:
    merged = _deep_merge_dict(_default_runtime_config(), cfg if isinstance(cfg, dict) else {})
    ui_cfg = merged.setdefault("ui_settings", {})
    ui_cfg["panel_title"] = str(ui_cfg.get("panel_title", "【个人状态观测仪】") or "【个人状态观测仪】").strip() or "【个人状态观测仪】"
    legacy_board_length = _clamp_int(ui_cfg.get("board_length", 10), 10, minimum=1, maximum=50)
    wealth_seed = ui_cfg.get("wealth_leaderboard")
    if not isinstance(wealth_seed, dict):
        wealth_seed = ui_cfg.get("leaderboard", {})
    ui_cfg["wealth_leaderboard"] = _sanitize_leaderboard_settings(wealth_seed, legacy_board_length, kind="wealth")
    ui_cfg["karma_leaderboard"] = _sanitize_leaderboard_settings(ui_cfg.get("karma_leaderboard", {}), legacy_board_length, kind="karma")
    ui_cfg["panel_sections"] = _sanitize_panel_sections(ui_cfg.get("panel_sections", _default_panel_sections()))
    ui_cfg["panel_section_settings"] = _sanitize_panel_section_settings(ui_cfg.get("panel_section_settings", {}))

    fate_cfg = merged.setdefault("fate_cards_settings", {})
    fate_cfg["enable"] = bool(fate_cfg.get("enable", True))
    fate_cfg["daily_draw_limit"] = _clamp_int(
        fate_cfg.get("daily_draw_limit", 3),
        3,
        minimum=1,
        maximum=100,
    )

    func_cfg = merged.setdefault("func_cards_settings", {})
    func_cfg["enable"] = bool(func_cfg.get("enable", True))
    func_cfg["enable_dice_cards"] = bool(func_cfg.get("enable_dice_cards", True))
    func_cfg["enable_public_duel_mode"] = bool(func_cfg.get("enable_public_duel_mode", False))
    func_cfg["enable_rarity_dedup"] = bool(func_cfg.get("enable_rarity_dedup", True))
    func_cfg["max_equipped_titles"] = _clamp_int(
        func_cfg.get("max_equipped_titles", 3),
        3,
        minimum=1,
        maximum=12,
    )
    func_cfg["max_inventory_slots"] = _clamp_int(
        func_cfg.get("max_inventory_slots", 3),
        3,
        minimum=1,
        maximum=12,
    )
    func_cfg["public_duel_daily_limit"] = _clamp_int(
        func_cfg.get("public_duel_daily_limit", 3),
        3,
        minimum=1,
        maximum=50,
    )
    duel_min = _clamp_int(
        func_cfg.get("public_duel_min_stake", 10),
        10,
        minimum=1,
        maximum=1_000_000,
    )
    duel_max = _clamp_int(
        func_cfg.get("public_duel_max_stake", 200),
        200,
        minimum=1,
        maximum=1_000_000,
    )
    func_cfg["public_duel_min_stake"] = duel_min
    func_cfg["public_duel_max_stake"] = max(duel_min, duel_max)

    weights_cfg = func_cfg.setdefault("custom_rarity_weights", {})
    for rarity_key, default_value in {
        "rarity_1": 30,
        "rarity_2": 30,
        "rarity_3": 28,
        "rarity_4": 11,
        "rarity_5": 1,
    }.items():
        weights_cfg[rarity_key] = _clamp_int(
            weights_cfg.get(rarity_key, default_value),
            default_value,
            minimum=0,
            maximum=100000,
        )

    eco_cfg = func_cfg.setdefault("economy_settings", {})
    eco_cfg["draw_probability"] = _clamp_int(
        eco_cfg.get("draw_probability", 5),
        5,
        minimum=0,
        maximum=100,
    )
    eco_cfg["free_daily_draw"] = _clamp_int(
        eco_cfg.get("free_daily_draw", 1),
        1,
        minimum=0,
        maximum=100,
    )
    eco_cfg["paid_daily_draw"] = _clamp_int(
        eco_cfg.get("paid_daily_draw", 1),
        1,
        minimum=0,
        maximum=100,
    )
    eco_cfg["draw_cost"] = _clamp_int(
        eco_cfg.get("draw_cost", 20),
        20,
        minimum=0,
        maximum=1_000_000,
    )
    eco_cfg["pity_threshold"] = _clamp_int(
        eco_cfg.get("pity_threshold", 10),
        10,
        minimum=1,
        maximum=1000,
    )
    return merged


def _lazy_title_from_text(text: str, prefix: str, fallback: str, max_len: int = 12) -> str:
    raw = re.split(r"[。！？!?\n，,：:；;、|/\\-]", str(text or "").strip())[0].strip()
    raw = re.sub(r"\s+", "", raw)
    raw = raw[:max_len] if raw else ""
    return f"{prefix}{raw}" if raw else fallback


def _pick_image_suffix(url: str, content_type: str = "") -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in _LAZY_ALLOWED_IMAGE_EXTS:
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
    bust = uuid.uuid4().hex
    joiner = "&" if "?" in url else "?"
    final_url = f"{url}{joiner}_t={bust}"
    headers = {
        "User-Agent": "luck_rank_webui/1.0",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    async with session.get(final_url, headers=headers) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        return await resp.json(content_type=None)


def _extract_quote_text(payload) -> str:
    if isinstance(payload, dict):
        for key in ("hitokoto", "data", "text", "msg", "content", "sentence"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in payload.values():
            if isinstance(value, (dict, list)):
                nested = _extract_quote_text(value)
                if nested:
                    return nested
    elif isinstance(payload, list):
        for item in payload:
            nested = _extract_quote_text(item)
            if nested:
                return nested
    elif isinstance(payload, str) and payload.strip():
        return payload.strip()
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
        for value in payload.values():
            if isinstance(value, (dict, list)):
                nested = _extract_image_url(value)
                if nested:
                    return nested
    elif isinstance(payload, list):
        for item in payload:
            nested = _extract_image_url(item)
            if nested:
                return nested
    return ""


async def _fetch_lazy_quote(session: ClientSession) -> dict:
    sources = [
        ("hitokoto", "https://v1.hitokoto.cn"),
        ("hitokoto_alt", "https://international.v1.hitokoto.cn"),
        ("suyanw", "https://api.suyanw.cn/api/meiju"),
        ("xxapi_hitokoto", "https://v2.xxapi.cn/api/yiyan?type=hitokoto"),
        ("mir6_yulu", "https://api.mir6.com/api/yulu?txt=4&type=json"),
        ("jinrishici", "https://v1.jinrishici.com/all.json"),
    ]
    errors = []
    for source, url in random.sample(sources, len(sources)):
        try:
            payload = await _fetch_json_url(session, url)
            text = _extract_quote_text(payload)
            if text:
                return {"text": text, "source": source, "source_url": url}
            errors.append(f"{source}: empty")
        except Exception as exc:
            errors.append(f"{source}: {exc}")
    raise RuntimeError("; ".join(errors) or "quote source unavailable")



async def _fetch_lazy_image_url(session: ClientSession) -> dict:
    sources = [
        *[(f"portrait_api_{idx}", url) for idx, url in enumerate(_FAST_PORTRAIT_APIS, start=1)],
        ("waifu.pics", "https://api.waifu.pics/sfw/waifu"),
        ("nekos.best", "https://nekos.best/api/v2/neko"),
    ]
    random.shuffle(sources)
    errors = []
    tasks = [asyncio.create_task(_fetch_image_from_source(session, source, url)) for source, url in sources]
    try:
        for future in asyncio.as_completed(tasks):
            try:
                result = await future
                for task in tasks:
                    if not task.done():
                        task.cancel()
                return {"url": result["image_url"], "source": result["source"], "content": result.get("content"), "content_type": result.get("content_type", "")}
            except Exception as exc:
                errors.append(str(exc))
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
    if _FALLBACK_IMAGE_URLS:
        fallback_url = random.choice(_FALLBACK_IMAGE_URLS)
        return {"url": fallback_url, "source": "fallback_url", "content": None, "content_type": ""}
    raise RuntimeError("; ".join(errors) or "image source unavailable")


async def _download_lazy_image(session: ClientSession, image_url: str, target_dir: Path, prefix: str) -> str:
    return await _save_lazy_image_content(session, image_url, None, "", target_dir, prefix)


async def _save_lazy_image_content(
    session: ClientSession,
    image_url: str,
    content: bytes | None,
    content_type: str,
    target_dir: Path,
    prefix: str,
) -> str:
    target_dir.mkdir(parents=True, exist_ok=True)
    if content is None:
        bust = uuid.uuid4().hex
        joiner = "&" if "?" in image_url else "?"
        final_url = f"{image_url}{joiner}_t={bust}"
        headers = {
            "User-Agent": "luck_rank_webui/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        async with session.get(final_url, headers=headers) as resp:
            if resp.status != 200:
                raise RuntimeError(f"image download failed: HTTP {resp.status}")
            content = await resp.read()
            if len(content) < 32:
                raise RuntimeError("image content too small")
            content_type = resp.headers.get("Content-Type", "")
    suffix = _pick_image_suffix(image_url, content_type)
    filename = f"{prefix}_{uuid.uuid4().hex[:12]}{suffix}"
    (target_dir / filename).write_bytes(content)
    return filename


def _choose_local_image_with_repeat(target_dir: Path, used_images: set[str], allow_repeat: bool = False) -> str:
    if not target_dir.exists():
        return ""
    files = [
        f.name
        for f in target_dir.iterdir()
        if f.is_file() and f.suffix.lower() in _LAZY_ALLOWED_IMAGE_EXTS and not _is_api_generated_image(f.name)
    ]
    if not allow_repeat:
        available = [f for f in files if f not in used_images]
        return random.choice(available) if available else ""
    return random.choice(files) if files else ""


def _fallback_lazy_quote(used_texts: set[str]) -> str:
    pool = [text for text in _LAZY_QUOTE_FALLBACKS if text not in used_texts]
    if pool and random.random() < 0.35:
        text = random.choice(pool)
        used_texts.add(text)
        return text
    return _build_procedural_lazy_quote(used_texts)


async def _fetch_unique_lazy_quote(session: ClientSession, used_texts: set[str]) -> str:
    last_text = ""
    for _ in range(8):
        try:
            result = await _fetch_lazy_quote(session)
            text = str(result.get("text", "")).strip()
            if not text:
                continue
            last_text = text
            if text not in used_texts:
                used_texts.add(text)
                return text
        except Exception:
            continue
    if last_text and last_text not in used_texts:
        used_texts.add(last_text)
        return last_text
    return _fallback_lazy_quote(used_texts)


async def _fetch_unique_lazy_image(
    session: ClientSession,
    target_dir: Path,
    prefix: str,
    used_remote_urls: set[str],
) -> str:
    last_seen_url = ""
    last_seen_content = None
    last_seen_content_type = ""
    for _ in range(8):
        image_result = await _fetch_lazy_image_url(session)
        image_url = str(image_result.get("url", "")).strip()
        if not image_url:
            continue
        last_seen_url = image_url
        last_seen_content = image_result.get("content")
        last_seen_content_type = str(image_result.get("content_type", "") or "")
        if image_url in used_remote_urls:
            continue
        filename = await _save_lazy_image_content(session, image_url, last_seen_content, last_seen_content_type, target_dir, prefix)
        used_remote_urls.add(image_url)
        return filename
    if last_seen_url:
        return await _save_lazy_image_content(session, last_seen_url, last_seen_content, last_seen_content_type, target_dir, prefix)
    raise RuntimeError("image source unavailable")


async def _select_lazy_image(
    session: ClientSession,
    *,
    image_mode: str,
    remote_dir: Path,
    local_dir: Path,
    prefix: str,
    used_images: set[str],
    used_remote_urls: set[str],
    allow_repeat: bool = False,
) -> str:
    if image_mode == "local":
        filename = _choose_local_image_with_repeat(local_dir, used_images, allow_repeat=allow_repeat)
        if filename:
            used_images.add(filename)
            return filename
        filename = _choose_any_image(local_dir, used_images, allow_repeat=True)
        if filename:
            used_images.add(filename)
            return filename
        return _create_builtin_fallback_image(local_dir, prefix)
    if image_mode == "remote":
        try:
            filename = await _fetch_unique_lazy_image(session, remote_dir, prefix, used_remote_urls)
            if filename:
                return filename
        except Exception:
            pass
        filename = _choose_any_image(local_dir, used_images, allow_repeat=True)
        if filename:
            used_images.add(filename)
            return filename
        return _create_builtin_fallback_image(local_dir, prefix)
    return ""


async def _fetch_image_from_source(session: ClientSession, source: str, url: str) -> dict:
    headers = {
        "User-Agent": "luck_rank_webui/1.0",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    bust = uuid.uuid4().hex
    joiner = "&" if "?" in url else "?"
    final_url = f"{url}{joiner}_t={bust}"
    async with session.get(final_url, headers=headers, allow_redirects=True) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        content_type = (resp.headers.get("Content-Type") or "").lower()
        if any(token in content_type for token in ("image/", "application/octet-stream")):
            content = await resp.read()
            if len(content) < 32:
                raise RuntimeError("image content too small")
            final_image_url = str(resp.url)
            return {
                "source": source,
                "image_url": final_image_url,
                "content": content,
                "content_type": content_type,
            }
        if "json" in content_type or "text" in content_type:
            payload = await resp.json(content_type=None)
            image_url = _extract_image_url(payload)
            if image_url:
                return {"source": source, "image_url": image_url, "content": None, "content_type": ""}
        raise RuntimeError("unsupported payload")


async def _build_lazy_fate_draft(
    session: ClientSession,
    *,
    remote_dir: Path,
    local_dir: Path,
    gold_min: int,
    gold_max: int,
    image_mode: str,
    gen_text: bool,
    used_texts: set[str],
    used_images: set[str],
    used_remote_urls: set[str],
) -> dict:
    gold = random.randint(min(gold_min, gold_max), max(gold_min, gold_max))
    text = ""
    name = "未命名命运牌"
    if gen_text:
        raw_quote = await _fetch_unique_lazy_quote(session, used_texts)
        name = _lazy_title_from_text(raw_quote, "命运·", "未命名命运牌", max_len=8)
        prefix = f"金币+{gold}\n" if gold >= 0 else f"金币-{abs(gold)}\n"
        text = f"{prefix}{raw_quote}"
    filename = await _select_lazy_image(
        session,
        image_mode=image_mode,
        remote_dir=local_dir,
        local_dir=local_dir,
        prefix="api_fate",
        used_images=used_images,
        used_remote_urls=used_remote_urls,
    )
    return {
        "name": name,
        "text": text,
        "gold": gold,
        "filename": filename,
    }


async def _build_lazy_func_draft(
    session: ClientSession,
    *,
    remote_dir: Path,
    local_dir: Path,
    allowed_types: list,
    max_rarity: int,
    max_tags: int,
    max_effect_val: int,
    image_mode: str,
    gen_text: bool,
    used_images: set[str],
    used_remote_urls: set[str],
) -> dict:
    draft = await build_func_draft(
        remote_dir,
        local_dir,
        allowed_types,
        max_rarity,
        max_tags,
        max_effect_val,
        "none",
        gen_text,
        set(),
    )
    draft["filename"] = await _select_lazy_image(
        session,
        image_mode=image_mode,
        remote_dir=local_dir,
        local_dir=local_dir,
        prefix="api_func",
        used_images=used_images,
        used_remote_urls=used_remote_urls,
    )
    return draft


async def api_lazy_batch_fate(request):
    try:
        body = await request.json() if request.can_read_body else {}
        if not isinstance(body, dict):
            body = {}
        if _is_visitor_request(request) and not _permission(request, "can_use_lazy_batch_cards"):
            return _visitor_error("当前访客身份不允许使用懒狗批量生成。")
        paths, _ = _get_request_runtime_config(request)

        count = max(1, min(100, _safe_int(body.get("count", 1))))
        if _is_visitor_request(request):
            count = min(count, max(1, _safe_int(_permission(request, "max_cards_per_submit", 1), 1)))
        gold_min = _safe_int(body.get("gold_min", -20), -20)
        gold_max = _safe_int(body.get("gold_max", 100), 100)
        image_mode = str(body.get("image_mode", "none")).strip()
        gen_text = bool(body.get("gen_text", True))

        remote_dir = paths["plugin_data_dir"] / "lazy_images" / "fate"
        local_dir = paths["fate_assets_dir"]

        results = []
        used_texts = set()
        used_images = set()
        used_remote_urls = set()
        async with ClientSession(timeout=_LAZY_HTTP_TIMEOUT) as session:
            for _ in range(count):
                draft = await _build_lazy_fate_draft(
                    session,
                    remote_dir=remote_dir,
                    local_dir=local_dir,
                    gold_min=gold_min,
                    gold_max=gold_max,
                    image_mode=image_mode,
                    gen_text=gen_text,
                    used_texts=used_texts,
                    used_images=used_images,
                    used_remote_urls=used_remote_urls,
                )
                results.append(draft)
        
        return web.json_response({"ok": True, "cards": results})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_lazy_batch_func(request):
    try:
        body = await request.json() if request.can_read_body else {}
        if not isinstance(body, dict):
            body = {}
        if _is_visitor_request(request) and not _permission(request, "can_use_lazy_batch_cards"):
            return _visitor_error("当前访客身份不允许使用懒狗批量生成。")
        paths, _ = _get_request_runtime_config(request)

        count = max(1, min(100, _safe_int(body.get("count", 1))))
        if _is_visitor_request(request):
            count = min(count, max(1, _safe_int(_permission(request, "max_cards_per_submit", 1), 1)))
        allowed_types = body.get("allowed_types")
        if not isinstance(allowed_types, list):
            allowed_types = ["attack", "heal", "defense"]
        max_rarity = max(1, min(5, _safe_int(body.get("max_rarity", 5), 5)))
        max_tags = max(1, _safe_int(body.get("max_tags", 2), 2))
        max_effect_val = _safe_int(body.get("max_effect_val", 50), 50)
        
        image_mode = str(body.get("image_mode", "none")).strip()
        gen_text = bool(body.get("gen_text", True))

        remote_dir = paths["plugin_data_dir"] / "lazy_images" / "func"
        local_dir = paths["func_assets_dir"]

        results = []
        used_images = set()
        used_remote_urls = set()
        async with ClientSession(timeout=_LAZY_HTTP_TIMEOUT) as session:
            for _ in range(count):
                draft = await _build_lazy_func_draft(
                    session,
                    remote_dir=remote_dir,
                    local_dir=local_dir,
                    allowed_types=allowed_types,
                    max_rarity=max_rarity,
                    max_tags=max_tags,
                    max_effect_val=max_effect_val,
                    image_mode=image_mode,
                    gen_text=gen_text,
                    used_images=used_images,
                    used_remote_urls=used_remote_urls,
                )
                results.append(draft)

        return web.json_response({"ok": True, "cards": results})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_lazy_auto_bind(request):
    try:
        body = await request.json() if request.can_read_body else {}
        if not isinstance(body, dict):
            body = {}
        if _is_visitor_request(request) and not _permission(request, "can_use_lazy_batch_images"):
            return _visitor_error("当前访客身份不允许批量绑定或生成图片。")
        paths, _ = _get_request_runtime_config(request)
        kind = str(body.get("kind", "fate")).strip()
        
        if kind == "fate":
            cards_file = paths["fate_cards_file"]
            local_dir = paths["fate_assets_dir"]
            remote_dir = paths["fate_assets_dir"]
            cards = _normalize_fate_cards(_read_json(cards_file, []))
        else:
            cards_file = paths["func_cards_file"]
            local_dir = paths["func_assets_dir"]
            remote_dir = paths["func_assets_dir"]
            cards = _normalize_func_cards(_read_json(cards_file, []))

        image_mode = str(body.get("image_mode", "local")).strip()
        allow_repeat = bool(body.get("allow_repeat", False))
        used_images = {str(c.get("filename", "")) for c in cards if c.get("filename")}
        used_remote_urls = set()
        changed = 0
        async with ClientSession(timeout=_LAZY_HTTP_TIMEOUT) as session:
            for c in cards:
                if not str(c.get("filename", "")).strip():
                    new_file = await _select_lazy_image(
                        session,
                        image_mode=image_mode,
                        remote_dir=remote_dir,
                        local_dir=local_dir,
                        prefix=f"api_{kind}",
                        used_images=used_images,
                        used_remote_urls=used_remote_urls,
                        allow_repeat=allow_repeat,
                    )
                    if new_file:
                        c["filename"] = new_file
                        used_images.add(new_file)
                        changed += 1

        if changed > 0:
            _atomic_write(cards_file, cards)
            
        return web.json_response({"ok": True, "changed": changed, "cards": cards})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)

# ============================================================================== 
# API 路由处理
# ==============================================================================


async def api_get_runtime_config(request):
    try:
        paths = _get_request_profile_paths(request)
        current = _read_json(paths["runtime_config_file"], {})
        merged = _sanitize_runtime_config(current)
        return web.json_response({"ok": True, "config": merged})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "config": _default_runtime_config()}, status=500)


async def api_save_runtime_config(request):
    try:
        body = await request.json()
        cfg = body.get("config", {})
        if not isinstance(cfg, dict):
            return web.json_response({"ok": False, "error": "config must be object"}, status=400)
        merged = _sanitize_runtime_config(cfg)
        paths = _get_request_profile_paths(request)
        if _is_visitor_request(request):
            if not _permission(request, "can_edit_runtime"):
                return _visitor_error("当前访客身份不允许修改运行配置。")
            if _permission(request, "requires_review", True):
                current = _sanitize_runtime_config(_read_json(paths["runtime_config_file"], {}))
                draft = _create_review_draft(request, "runtime", "replace", current, merged, "修改运行配置")
                return _visitor_pending_response(draft)
        _atomic_write(paths["runtime_config_file"], merged)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_get_fate_cards(request):
    try:
        paths = _get_request_profile_paths(request)
        cards = _normalize_fate_cards(_read_json(paths["fate_cards_file"], []))
        return web.json_response({"ok": True, "cards": cards})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "cards": []}, status=500)


async def api_save_fate_cards(request):
    try:
        body = await request.json()
        cards = _normalize_fate_cards(body.get("cards", []))
        paths = _get_request_profile_paths(request)
        current = _normalize_fate_cards(_read_json(paths["fate_cards_file"], []))
        ok, error, diff = _enforce_card_permissions(request, "fate", current, cards)
        if not ok:
            return _visitor_error(error)
        if _is_visitor_request(request) and _permission(request, "requires_review", True):
            draft = _create_review_draft(request, "fate_cards", "replace", current, cards, _change_summary("fate", diff))
            return _visitor_pending_response(draft)
        _atomic_write(paths["fate_cards_file"], cards)
        return web.json_response({"ok": True, "cards": cards})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_upload_fate_image(request):
    """上传命运牌图片到 assets/cards/"""
    try:
        if _is_visitor_request(request) and not _permission(request, "can_upload_image"):
            return _visitor_error("当前访客身份不允许上传图片。")
        paths = _get_request_profile_paths(request)
        fate_assets_dir = paths["fate_assets_dir"]
        fate_assets_dir.mkdir(parents=True, exist_ok=True)
        reader = await request.multipart()
        uploaded = []
        max_images = max(1, _safe_int(_permission(request, "max_images_per_submit", 20), 20))
        max_bytes = max(1, _safe_int(_permission(request, "max_image_size_mb", 20), 20)) * 1024 * 1024
        async for field in reader:
            if field.name == "files":
                if _is_visitor_request(request) and len(uploaded) >= max_images:
                    break
                filename = field.filename
                if not filename:
                    continue
                safe_name = Path(filename).name
                dest = fate_assets_dir / safe_name
                total = 0
                with open(dest, "wb") as f:
                    while True:
                        chunk = await field.read_chunk(8192)
                        if not chunk:
                            break
                        total += len(chunk)
                        if _is_visitor_request(request) and total > max_bytes:
                            raise ValueError("图片超过当前访客身份允许的大小上限。")
                        f.write(chunk)
                uploaded.append(safe_name)
        if _is_visitor_request(request) and _permission(request, "requires_review", True) and uploaded:
            _create_review_draft(request, "upload_fate_image", "upload", [], uploaded, f"上传 {len(uploaded)} 张命运牌图片")
        return web.json_response({"ok": True, "uploaded": uploaded})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_list_fate_images(request):
    """列出 assets/cards/ 下所有图片"""
    try:
        paths = _get_request_profile_paths(request)
        fate_assets_dir = paths["fate_assets_dir"]
        lazy_dir = paths["plugin_data_dir"] / "lazy_images" / "fate"
        local_files = _list_image_files(fate_assets_dir)
        legacy_lazy_files = [name for name in _list_image_files(lazy_dir) if name not in local_files]
        return web.json_response({"ok": True, "images": sorted(local_files + legacy_lazy_files), "lazy_images": legacy_lazy_files})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "images": [], "lazy_images": []}, status=500)


async def api_get_func_cards(request):
    try:
        paths = _get_request_profile_paths(request)
        cards = _normalize_func_cards(_read_json(paths["func_cards_file"], []))
        return web.json_response({"ok": True, "cards": cards})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "cards": []}, status=500)


async def api_save_func_cards(request):
    try:
        body = await request.json()
        cards = _normalize_func_cards(body.get("cards", []))
        paths = _get_request_profile_paths(request)
        current = _normalize_func_cards(_read_json(paths["func_cards_file"], []))
        ok, error, diff = _enforce_card_permissions(request, "func", current, cards)
        if not ok:
            return _visitor_error(error)
        if _is_visitor_request(request) and _permission(request, "requires_review", True):
            draft = _create_review_draft(request, "func_cards", "replace", current, cards, _change_summary("func", diff))
            return _visitor_pending_response(draft)
        _atomic_write(paths["func_cards_file"], cards)
        return web.json_response({"ok": True, "cards": cards})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_get_sign_in_texts(request):
    try:
        paths = _get_request_profile_paths(request)
        texts = _normalize_sign_in_texts(_read_json(paths["sign_in_texts_file"], DEFAULT_SIGN_IN_TEXTS))
        for key in DEFAULT_SIGN_IN_TEXTS:
            if key not in texts:
                texts[key] = DEFAULT_SIGN_IN_TEXTS[key]
        if not texts.get("luck_ranges"):
            legacy = texts.get("luck_comments", {})
            texts["luck_ranges"] = [
                {"label": "平运", "min": 1, "max": 50, "gold_delta": 0, "comments": legacy.get("1_50", DEFAULT_SIGN_IN_TEXTS["luck_comments"]["1_50"])},
                {"label": "小吉", "min": 51, "max": 70, "gold_delta": 0, "comments": legacy.get("51_70", DEFAULT_SIGN_IN_TEXTS["luck_comments"]["51_70"])},
                {"label": "大吉", "min": 71, "max": 90, "gold_delta": 0, "comments": legacy.get("71_90", DEFAULT_SIGN_IN_TEXTS["luck_comments"]["71_90"])},
                {"label": "天命", "min": 91, "max": 100, "gold_delta": 0, "comments": legacy.get("91_100", DEFAULT_SIGN_IN_TEXTS["luck_comments"]["91_100"])},
            ]
        return web.json_response({"ok": True, "texts": texts})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "texts": DEFAULT_SIGN_IN_TEXTS}, status=500)


async def api_save_sign_in_texts(request):
    try:
        body = await request.json()
        texts = _normalize_sign_in_texts(body.get("texts", {}))
        paths = _get_request_profile_paths(request)
        if _is_visitor_request(request):
            if not _permission(request, "can_edit_signin"):
                return _visitor_error("当前访客身份不允许修改签到配置。")
            if _permission(request, "requires_review", True):
                current = _normalize_sign_in_texts(_read_json(paths["sign_in_texts_file"], DEFAULT_SIGN_IN_TEXTS))
                draft = _create_review_draft(request, "signin", "replace", current, texts, "修改签到配置")
                return _visitor_pending_response(draft)
        _atomic_write(paths["sign_in_texts_file"], texts)
        return web.json_response({"ok": True, "texts": texts, "saved_range_count": len(texts.get("luck_ranges", []))})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_get_titles(request):
    try:
        paths = _get_request_profile_paths(request)
        titles = _normalize_titles_config(_read_json(paths["titles_config_file"], []))
        return web.json_response({"ok": True, "titles": titles, "catalog": TitleEngine.get_title_catalog()})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "titles": [], "catalog": TitleEngine.get_title_catalog()}, status=500)


async def api_save_titles(request):
    try:
        body = await request.json()
        titles = _normalize_titles_config(body.get("titles", []))
        paths = _get_request_profile_paths(request)
        if _is_visitor_request(request):
            if not _permission(request, "can_edit_titles"):
                return _visitor_error("当前访客身份不允许修改称号配置。")
            current = _normalize_titles_config(_read_json(paths["titles_config_file"], []))
            diff = _diff_named_records("title", current, titles)
            if _permission(request, "requires_review", True):
                draft = _create_review_draft(request, "titles", "replace", current, titles, _change_summary("title", diff))
                return _visitor_pending_response(draft)
        _atomic_write(paths["titles_config_file"], titles)
        return web.json_response({"ok": True, "titles": titles})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)



async def api_get_user_stats(request):
    """按方案汇总只读用户数据，供概率分析和持牌检测用"""
    try:
        profile_id = _get_request_profile_id(request)
        profile_paths = get_profile_storage_paths(profile_id, PLUGIN_NAME)
        func_cards = _normalize_func_cards(_read_json(profile_paths["func_cards_file"], []))
        rarity_by_name = {
            str(card.get("card_name", "")).strip(): max(1, min(5, _safe_int(card.get("rarity", 1), 1)))
            for card in func_cards
            if isinstance(card, dict) and str(card.get("card_name", "")).strip()
        }
        stats = {
            "total_groups": 0,
            "total_users": 0,
            "active_users": 0,
            "total_gold": 0,
            "total_cards_issued": 0,
            "total_sign_ins": 0,
            "rarity_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
            "wealth_leaderboard": [],
            "groups": [],
            "card_holders": {},
            "title_holders": {},
            "profile_id": profile_id,
        }
        if not GROUP_DATA_DIR.exists():
            return web.json_response({"ok": True, "stats": stats})

        mapping = get_group_profile_map(PLUGIN_NAME)
        for group_dir in GROUP_DATA_DIR.iterdir():
            if not group_dir.is_dir():
                continue
            if mapping.get(group_dir.name, DEFAULT_PROFILE_NAME) != profile_id:
                continue
            data = _read_json(group_dir / "luck_data.json", {})
            if not isinstance(data, dict):
                continue
            
            stats["total_groups"] += 1
            group_gold = 0
            group_cards = 0
            group_sign_ins = 0
            group_active_users = 0
            group_user_count = 0
            
            for uid, info in data.items():
                gold = _safe_int(info.get("total_gold", info.get("gold", 0)), 0)
                sign_ins = _safe_int(info.get("total_sign_in_days", info.get("sign_in_count", 0)), 0)
                inventory = info.get("inventory", [])
                cards_count = len(inventory) if isinstance(inventory, list) else 0
                last_date = str(info.get("last_date", "") or "").strip()
                titles = info.get("titles", [])
                display_name = str(info.get("name", "") or "").strip() or f"群友({uid})"
                is_active_user = any([
                    sign_ins > 0,
                    bool(last_date),
                    gold != 0,
                    cards_count > 0,
                    bool(titles),
                ])
                
                stats["total_gold"] += gold
                stats["total_cards_issued"] += cards_count
                stats["total_sign_ins"] += sign_ins
                group_gold += gold
                group_cards += cards_count
                group_sign_ins += sign_ins
                
                if is_active_user:
                    stats["active_users"] += 1
                    group_active_users += 1
                    group_user_count += 1

                for card in inventory:
                    if isinstance(card, dict):
                        cname = str(card.get("card_name", "")).strip()
                        if cname:
                            stats["card_holders"][cname] = stats["card_holders"].get(cname, 0) + 1

                        rarity = rarity_by_name.get(cname, max(1, min(5, _safe_int(card.get("rarity", 1), 1))))
                        rarity_key = str(rarity)
                        if rarity_key in stats["rarity_distribution"]:
                            stats["rarity_distribution"][rarity_key] += 1
                        else:
                            stats["rarity_distribution"]["1"] += 1
                            
                if isinstance(titles, list):
                    for t in titles:
                        tname = str(t.get("name", t) if isinstance(t, dict) else t).strip()
                        if tname:
                            stats["title_holders"][tname] = stats["title_holders"].get(tname, 0) + 1

                if is_active_user:
                    stats["wealth_leaderboard"].append({
                        "uid": str(uid),
                        "name": display_name,
                        "gold": gold,
                        "cards": cards_count,
                        "sign_ins": sign_ins,
                    })
                
            stats["groups"].append({
                "group_id": group_dir.name, 
                "user_count": group_user_count,
                "group_gold": group_gold,
                "group_cards": group_cards,
                "group_sign_ins": group_sign_ins,
                "active_users": group_active_users,
            })
            stats["total_users"] += group_user_count
            
        # 财富排行榜排序并截取 Top 50
        stats["wealth_leaderboard"].sort(key=lambda x: (x["gold"], x["cards"], x["sign_ins"]), reverse=True)
        stats["wealth_leaderboard"] = stats["wealth_leaderboard"][:50]
        
        # 群组排行榜按总金币或活跃度排序
        stats["groups"].sort(key=lambda x: (x["group_sign_ins"], x["group_gold"], x["active_users"]), reverse=True)
        
        return web.json_response({"ok": True, "stats": stats})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "stats": {"total_groups": 0, "total_users": 0, "total_gold": 0, "total_cards_issued": 0, "wealth_leaderboard": [], "groups": [], "profile_id": DEFAULT_PROFILE_NAME}}, status=500)


async def api_upload_image(request):
    """上传卡图到 assets/func_cards/"""
    try:
        if _is_visitor_request(request) and not _permission(request, "can_upload_image"):
            return _visitor_error("当前访客身份不允许上传图片。")
        paths = _get_request_profile_paths(request)
        assets_dir = paths["func_assets_dir"]
        assets_dir.mkdir(parents=True, exist_ok=True)
        reader = await request.multipart()
        uploaded = []
        max_images = max(1, _safe_int(_permission(request, "max_images_per_submit", 20), 20))
        max_bytes = max(1, _safe_int(_permission(request, "max_image_size_mb", 20), 20)) * 1024 * 1024
        async for field in reader:
            if field.name == "files":
                if _is_visitor_request(request) and len(uploaded) >= max_images:
                    break
                filename = field.filename
                if not filename:
                    continue
                safe_name = Path(filename).name
                dest = assets_dir / safe_name
                total = 0
                with open(dest, "wb") as f:
                    while True:
                        chunk = await field.read_chunk(8192)
                        if not chunk:
                            break
                        total += len(chunk)
                        if _is_visitor_request(request) and total > max_bytes:
                            raise ValueError("图片超过当前访客身份允许的大小上限。")
                        f.write(chunk)
                uploaded.append(safe_name)
        if _is_visitor_request(request) and _permission(request, "requires_review", True) and uploaded:
            _create_review_draft(request, "upload_func_image", "upload", [], uploaded, f"上传 {len(uploaded)} 张功能牌图片")
        return web.json_response({"ok": True, "uploaded": uploaded})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_list_images(request):
    """列出 assets/func_cards/ 下所有图片文件"""
    try:
        paths = _get_request_profile_paths(request)
        assets_dir = paths["func_assets_dir"]
        assets_dir.mkdir(parents=True, exist_ok=True)
        lazy_dir = paths["plugin_data_dir"] / "lazy_images" / "func"
        local_files = _list_image_files(assets_dir)
        legacy_lazy_files = [name for name in _list_image_files(lazy_dir) if name not in local_files]
        return web.json_response({"ok": True, "files": sorted(local_files + legacy_lazy_files), "lazy_files": legacy_lazy_files})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "files": [], "lazy_files": []}, status=500)


async def api_delete_image(request):
    if _is_visitor_request(request) and not _permission(request, "can_delete_image"):
        return _visitor_error("当前访客身份不允许删除图片。")
    filename = request.match_info.get("filename", "")
    if not filename:
        return web.json_response({"ok": False, "error": "no filename"}, status=400)
    paths = _get_request_profile_paths(request)
    safe_name = Path(filename).name
    deleted = False
    for target in (
        paths["func_assets_dir"] / safe_name,
        paths["plugin_data_dir"] / "lazy_images" / "func" / safe_name,
    ):
        if target.exists():
            target.unlink()
            deleted = True
    return web.json_response({"ok": True, "deleted": deleted})


async def api_delete_fate_image(request):
    if _is_visitor_request(request) and not _permission(request, "can_delete_image"):
        return _visitor_error("当前访客身份不允许删除图片。")
    filename = request.match_info.get("filename", "")
    if not filename:
        return web.json_response({"ok": False, "error": "no filename"}, status=400)
    paths = _get_request_profile_paths(request)
    safe_name = Path(filename).name
    deleted = False
    for target in (
        paths["fate_assets_dir"] / safe_name,
        paths["plugin_data_dir"] / "lazy_images" / "fate" / safe_name,
    ):
        if target.exists():
            target.unlink()
            deleted = True
    return web.json_response({"ok": True, "deleted": deleted})


async def api_check_missing_images(request):
    """检查所有卡牌中引用了但实际不存在的图片"""
    try:
        paths = _get_request_profile_paths(request)
        cards = _read_json(paths["func_cards_file"], [])
        missing = []
        for card in cards:
            fn = str(card.get("filename", "")).strip()
            if fn and not (paths["func_assets_dir"] / fn).exists():
                missing.append({"card_name": card.get("card_name"), "filename": fn})
        return web.json_response({"ok": True, "missing": missing})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "missing": []}, status=500)


async def api_access_status(request):
    identity = _get_session_identity(request)
    return web.json_response({"ok": True, "verified": bool(identity), "identity": _public_session_identity(identity)})


async def api_access_verify(request):
    try:
        body = await request.json() if request.can_read_body else {}
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    password = str(body.get("password", "") or "")
    expected_password = _load_current_access_password()
    if not password.strip():
        return web.json_response({"ok": False, "error": "请输入访问口令。"}, status=400)
    if not secrets.compare_digest(password, expected_password):
        return web.json_response({"ok": False, "error": "访问口令错误。", "code": "invalid_password"}, status=401)
    token = secrets.token_urlsafe(32)
    _AUTH_SESSIONS.add(token)
    response = web.json_response({"ok": True, "verified": True})
    response.set_cookie(
        WEBUI_SESSION_COOKIE,
        token,
        httponly=True,
        samesite="Lax",
        secure=False,
        path="/",
        max_age=86400,
    )
    return response


async def api_access_logout(request):
    token = _get_session_token(request)
    if token:
        _AUTH_SESSIONS.discard(token)
    response = web.json_response({"ok": True, "verified": False})
    response.del_cookie(WEBUI_SESSION_COOKIE, path="/")
    return response


async def api_access_status(request):
    identity = _get_session_identity(request)
    return web.json_response({"ok": True, "verified": bool(identity), "identity": _public_session_identity(identity)})


async def api_access_verify(request):
    try:
        body = await request.json() if request.can_read_body else {}
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    password = str(body.get("password", "") or "")
    if not password.strip():
        return web.json_response({"ok": False, "error": "请输入访问口令。"}, status=400)
    identity = _admin_identity() if verify_webui_admin_password(password) else _verify_visitor_key(password)
    if not identity:
        return web.json_response({"ok": False, "error": "访问口令错误。", "code": "invalid_password"}, status=401)
    token = secrets.token_urlsafe(32)
    _AUTH_SESSIONS[token] = identity
    response = web.json_response({"ok": True, "verified": True, "identity": _public_session_identity(identity)})
    response.set_cookie(
        WEBUI_SESSION_COOKIE,
        token,
        httponly=True,
        samesite="Lax",
        secure=False,
        path="/",
        max_age=86400,
    )
    return response


async def api_access_logout(request):
    token = _get_session_token(request)
    if token:
        _AUTH_SESSIONS.pop(token, None)
    response = web.json_response({"ok": True, "verified": False})
    response.del_cookie(WEBUI_SESSION_COOKIE, path="/")
    return response


def visitor_get_roles_summary() -> str:
    lines = []
    for role in _load_visitor_roles():
        perms = role.get("permissions", {})
        bits = []
        if perms.get("can_view"):
            bits.append("可查看")
        if perms.get("can_create_func_card"):
            bits.append("可新增功能牌")
        if perms.get("can_edit_func_card"):
            bits.append("可修改功能牌")
        if perms.get("can_upload_image"):
            bits.append("可上传图片")
        if perms.get("can_use_lazy_batch_cards"):
            bits.append("可使用懒狗批量")
        bits.append("需审核" if perms.get("requires_review", True) else "免审核")
        lines.append(f"{role.get('name')} ({role.get('id')}): " + "、".join(bits))
    return "\n".join(lines)


def visitor_public_url() -> str:
    cfg = _read_dict_file(VISITOR_TUNNEL_FILE)
    return str(_CLOUDFLARED_PUBLIC_URL or cfg.get("custom_public_url") or cfg.get("last_public_url") or "").strip()


def _cloudflared_filename() -> str:
    return "cloudflared.exe" if sys.platform.startswith("win") else "cloudflared"


def _cloudflared_bin_dir() -> Path:
    return BASE_PATHS["plugin_data_dir"] / "bin"


def _cloudflared_managed_path() -> Path:
    return _cloudflared_bin_dir() / _cloudflared_filename()


def _cloudflared_partial_path() -> Path:
    asset, _ = _cloudflared_download_asset()
    return _cloudflared_bin_dir() / asset


def _install_task_public(task: dict | None = None) -> dict:
    if task is None:
        state = _read_dict_file(VISITOR_INSTALL_STATE_FILE)
        task = state if state else None
    if not task:
        return {}
    safe = dict(task)
    safe.setdefault("logs", [])
    safe["logs"] = safe["logs"][-80:]
    return safe


def _save_install_task(task_id: str, **updates):
    task = _CLOUDFLARED_INSTALL_TASKS.setdefault(task_id, {"task_id": task_id, "logs": []})
    task.update(updates)
    task["updated_at"] = int(time.time())
    _atomic_write(VISITOR_INSTALL_STATE_FILE, _install_task_public(task))


def _append_install_log(task_id: str | None, message: str):
    if not task_id:
        return
    task = _CLOUDFLARED_INSTALL_TASKS.setdefault(task_id, {"task_id": task_id, "logs": []})
    logs = task.setdefault("logs", [])
    logs.append(f"[{time.strftime('%H:%M:%S')}] {message}")
    task["logs"] = logs[-120:]
    task["updated_at"] = int(time.time())
    _atomic_write(VISITOR_INSTALL_STATE_FILE, _install_task_public(task))


def _cloudflared_download_asset() -> tuple[str, str]:
    machine = platform.machine().lower()
    arch = "arm64" if "arm64" in machine or "aarch64" in machine else "386" if machine in {"x86", "i386", "i686"} else "amd64"
    if sys.platform.startswith("win"):
        return f"cloudflared-windows-{arch}.exe", "exe"
    if sys.platform == "darwin":
        return f"cloudflared-darwin-{arch}.tgz", "tgz"
    return f"cloudflared-linux-{arch}", "bin"


def _cloudflared_official_download_url(asset: str | None = None) -> str:
    if not asset:
        asset, _ = _cloudflared_download_asset()
    return f"https://github.com/cloudflare/cloudflared/releases/latest/download/{asset}"


def _cloudflared_download_url() -> str:
    asset, _ = _cloudflared_download_asset()
    official_url = _cloudflared_official_download_url(asset)
    cfg = _read_dict_file(VISITOR_TUNNEL_FILE)
    source = str(cfg.get("cloudflared_download_source") or "official").strip()
    template = str(cfg.get("cloudflared_download_url_template") or "").strip()
    if source != "custom" or not template:
        return official_url
    try:
        if "{url}" in template or "{asset}" in template:
            return template.format(url=official_url, asset=asset)
        if template.endswith("/"):
            return template + asset
        return template
    except Exception:
        return official_url


def _cloudflared_download_source_name() -> str:
    cfg = _read_dict_file(VISITOR_TUNNEL_FILE)
    source = str(cfg.get("cloudflared_download_source") or "official").strip()
    if source == "custom":
        return "custom"
    return "official"


def _cloudflared_error_hint(error: Exception | str) -> str:
    text = str(error)
    lower = text.lower()
    if "cannot connect to host" in lower or "connect call failed" in lower or "connection refused" in lower:
        return "当前运行 AstrBot 的环境连不上下载源的 HTTPS 端口；请切换可用镜像源、检查服务器网络/DNS，或手动下载后填写 cloudflared 路径。"
    if "timed out" in lower or "timeout" in lower:
        return "下载源响应超时；建议重新下载、切换镜像源，或手动放置 cloudflared。"
    if "ssl" in lower or "certificate" in lower:
        return "SSL/TLS 校验或握手失败；多半是网络代理、证书环境或镜像源异常。"
    if "http 404" in lower:
        return "下载地址返回 404；请检查镜像模板是否保留了 {asset} 或 {url} 占位符。"
    if "http 403" in lower or "http 429" in lower:
        return "下载源拒绝或限流；请稍后重试或切换镜像源。"
    return "自动安装失败；可以重新下载、切换下载源，或手动下载 cloudflared 后填写路径。"


def _valid_cloudflared_path(path: str | Path | None) -> str:
    if not path:
        return ""
    candidate = Path(str(path)).expanduser()
    if candidate.exists() and candidate.is_file() and _cloudflared_version(candidate).get("ok"):
        return str(candidate)
    return ""


def _cloudflared_version(path: str | Path | None) -> dict:
    if not path:
        return {"ok": False, "error": "path is empty", "version": ""}
    candidate = Path(str(path)).expanduser()
    if not candidate.exists() or not candidate.is_file():
        return {"ok": False, "error": "file not found", "version": ""}
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
        result = subprocess.run(
            [str(candidate), "--version"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=creationflags,
        )
        output = (result.stdout or result.stderr or "").strip()
        return {"ok": result.returncode == 0, "error": "" if result.returncode == 0 else output, "version": output}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "version": ""}


def _detect_cloudflared_path() -> str:
    cfg = _read_dict_file(VISITOR_TUNNEL_FILE)
    for candidate in (
        cfg.get("cloudflared_path", ""),
        _cloudflared_managed_path(),
        shutil.which("cloudflared"),
    ):
        found = _valid_cloudflared_path(candidate)
        if found:
            return found
    return ""


async def _download_cloudflared_binary(task_id: str | None = None, force: bool = False) -> dict:
    url = _cloudflared_download_url()
    asset, kind = _cloudflared_download_asset()
    bin_dir = _cloudflared_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)
    download_path = bin_dir / asset
    final_path = _cloudflared_managed_path()
    existing = _cloudflared_version(final_path)
    if existing.get("ok") and not force:
        _append_install_log(task_id, f"Found usable cloudflared: {existing.get('version')}")
        return {"path": str(final_path), "url": url, "version": existing.get("version", "")}
    if force:
        _append_install_log(task_id, "Forced re-download requested; replacing managed binary and partial files.")
    if final_path.exists():
        _append_install_log(task_id, "Existing managed binary is not usable; replacing it.")
        try:
            final_path.unlink()
        except Exception:
            pass
    if download_path.exists():
        _append_install_log(task_id, f"Found partial download {download_path.name}; replacing it.")
        try:
            download_path.unlink()
        except Exception:
            pass
    if task_id:
        _save_install_task(
            task_id,
            status="downloading",
            downloaded=0,
            total=0,
            percent=0,
            url=url,
            source=_cloudflared_download_source_name(),
        )
        _append_install_log(task_id, f"Download source: {_cloudflared_download_source_name()}")
        _append_install_log(task_id, f"Downloading {url}")
    async with ClientSession(timeout=ClientTimeout(total=300, connect=30, sock_connect=30, sock_read=60)) as session:
        async with session.get(url, allow_redirects=True) as resp:
            if resp.status != 200:
                raise RuntimeError(f"download failed: HTTP {resp.status}")
            total_size = int(resp.headers.get("Content-Length") or 0)
            if task_id:
                _save_install_task(task_id, total=total_size)
                if total_size:
                    _append_install_log(task_id, f"Remote file size: {round(total_size / 1024 / 1024, 1)} MB")
                else:
                    _append_install_log(task_id, "Remote file size is unknown; showing downloaded bytes instead of a reliable percent.")
            downloaded = 0
            last_logged = 0
            with open(download_path, "wb") as f:
                while True:
                    chunk = await resp.content.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if task_id:
                        _save_install_task(
                            task_id,
                            downloaded=downloaded,
                            percent=round((downloaded / total_size) * 100, 1) if total_size else 0,
                        )
                        if downloaded - last_logged >= 2 * 1024 * 1024:
                            last_logged = downloaded
                            _append_install_log(task_id, f"Downloaded {round(downloaded / 1024 / 1024, 1)} MB")
    if task_id:
        _save_install_task(task_id, status="installing", percent=98)
        _append_install_log(task_id, "Download finished; installing binary.")
    if kind == "tgz":
        with tarfile.open(download_path, "r:gz") as tar:
            member = next((m for m in tar.getmembers() if Path(m.name).name == "cloudflared" and m.isfile()), None)
            if not member:
                raise RuntimeError("cloudflared not found in archive")
            extracted = tar.extractfile(member)
            if extracted is None:
                raise RuntimeError("failed to extract cloudflared")
            with open(final_path, "wb") as f:
                shutil.copyfileobj(extracted, f)
        download_path.unlink(missing_ok=True)
    elif download_path != final_path:
        shutil.move(str(download_path), str(final_path))
    if not sys.platform.startswith("win"):
        final_path.chmod(final_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    version = _cloudflared_version(final_path)
    if not version.get("ok"):
        raise RuntimeError(f"cloudflared downloaded but cannot run: {version.get('error')}")
    _append_install_log(task_id, f"Verified cloudflared: {version.get('version')}")
    cfg = _read_dict_file(VISITOR_TUNNEL_FILE)
    cfg["cloudflared_path"] = str(final_path)
    _atomic_write(VISITOR_TUNNEL_FILE, cfg)
    return {"path": str(final_path), "url": url, "version": version.get("version", "")}


async def _start_cloudflared_quick_tunnel(local_url: str) -> dict:
    global _CLOUDFLARED_PROCESS, _CLOUDFLARED_PUBLIC_URL
    if _CLOUDFLARED_PROCESS and _CLOUDFLARED_PROCESS.returncode is None and _CLOUDFLARED_PUBLIC_URL:
        return {"public_url": _CLOUDFLARED_PUBLIC_URL, "running": True}
    path = _detect_cloudflared_path()
    if not path:
        raise RuntimeError("cloudflared is not installed")
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
    _CLOUDFLARED_PROCESS = await asyncio.create_subprocess_exec(
        path,
        "tunnel",
        "--url",
        local_url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        creationflags=creationflags,
    )
    pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
    deadline = time.time() + 25
    while time.time() < deadline:
        if _CLOUDFLARED_PROCESS.stdout is None:
            break
        try:
            line = await asyncio.wait_for(_CLOUDFLARED_PROCESS.stdout.readline(), timeout=2)
        except asyncio.TimeoutError:
            continue
        if not line:
            if _CLOUDFLARED_PROCESS.returncode is not None:
                break
            continue
        text = line.decode("utf-8", errors="ignore")
        match = pattern.search(text)
        if match:
            _CLOUDFLARED_PUBLIC_URL = match.group(0)
            cfg = _read_dict_file(VISITOR_TUNNEL_FILE)
            cfg["last_public_url"] = _CLOUDFLARED_PUBLIC_URL
            cfg["cloudflared_path"] = path
            _atomic_write(VISITOR_TUNNEL_FILE, cfg)
            return {"public_url": _CLOUDFLARED_PUBLIC_URL, "running": True}
    raise RuntimeError("cloudflared started but no trycloudflare URL was detected")


def visitor_create_key_from_role(role_name_or_id: str, remark: str = "") -> dict:
    role = _find_role_by_name_or_id(role_name_or_id)
    if not role:
        return {"ok": False, "error": "未找到该访客身份。"}
    _ensure_visitor_files()
    secret = _make_visitor_key()
    item = {
        "id": f"key_{uuid.uuid4().hex[:12]}",
        "secret_hash": _hash_secret(secret),
        "key_prefix": secret[:10],
        "role_id": role.get("id", ""),
        "role_name": role.get("name", ""),
        "remark": str(remark or "").strip(),
        "status": "active",
        "created_at": int(time.time()),
        "last_used_at": 0,
        "uses": 0,
        "submissions": 0,
    }
    keys = _read_list_file(VISITOR_KEYS_FILE)
    keys.append(item)
    _atomic_write(VISITOR_KEYS_FILE, keys)
    _append_audit("key_created", {"key_id": item["id"], "role_id": item["role_id"], "remark": item["remark"]})
    return {"ok": True, "key": secret, "record": _public_key_record(item), "role": _public_role(role), "public_url": visitor_public_url()}


def visitor_get_drafts_summary(limit: int = 8) -> str:
    drafts = [d for d in _load_drafts() if d.get("status") == "pending"]
    if not drafts:
        return "当前没有待审核草稿。"
    lines = []
    for draft in drafts[:limit]:
        lines.append(f"{draft.get('id')}: {draft.get('summary') or draft.get('resource_type')} [{draft.get('role_name')}]")
    if len(drafts) > limit:
        lines.append(f"还有 {len(drafts) - limit} 条，请到 WebUI 查看。")
    return "\n".join(lines)


def _apply_draft(draft: dict):
    profile_id = _sanitize_profile_id(draft.get("profile_id") or DEFAULT_PROFILE_NAME)
    paths = get_profile_storage_paths(profile_id, PLUGIN_NAME)
    resource = draft.get("resource_type")
    after = draft.get("after")
    if resource == "func_cards":
        _atomic_write(paths["func_cards_file"], _normalize_func_cards(after if isinstance(after, list) else []))
    elif resource == "fate_cards":
        _atomic_write(paths["fate_cards_file"], _normalize_fate_cards(after if isinstance(after, list) else []))
    elif resource == "titles":
        _atomic_write(paths["titles_config_file"], _normalize_titles_config(after if isinstance(after, list) else []))
    elif resource == "signin":
        _atomic_write(paths["sign_in_texts_file"], _normalize_sign_in_texts(after if isinstance(after, dict) else {}))
    elif resource == "runtime":
        _atomic_write(paths["runtime_config_file"], _sanitize_runtime_config(after if isinstance(after, dict) else {}))


def visitor_review_draft_by_id(draft_id: str, approve: bool, reviewer: str = "qq") -> dict:
    drafts = [d for d in _load_drafts() if d.get("status") == "pending"]
    target = None
    target_index = -1
    for index, draft in enumerate(drafts):
        if draft.get("id") == draft_id:
            target = draft
            target_index = index
            break
    if not target:
        return {"ok": False, "error": "未找到草稿。"}
    if target.get("status") != "pending":
        return {"ok": False, "error": "该草稿已经处理过。"}
    if approve:
        _apply_draft(target)
        target["status"] = "approved"
        event_name = "draft_approved"
    else:
        target["status"] = "rejected"
        event_name = "draft_rejected"
    target["reviewed_at"] = int(time.time())
    target["reviewer"] = reviewer
    public_target = _draft_brief(target)
    if target_index >= 0:
        drafts.pop(target_index)
    _save_drafts(drafts)
    _append_audit(event_name, {
        "draft_id": draft_id,
        "reviewer": reviewer,
        "summary": target.get("summary", ""),
        "resource_type": target.get("resource_type", ""),
        "profile_id": target.get("profile_id", ""),
        "role_name": target.get("role_name", ""),
    })
    return {"ok": True, "draft": public_target}


async def api_visitor_state(request):
    identity = _get_session_identity(request)
    roles = [_public_role(role) for role in _load_visitor_roles()]
    return web.json_response({
        "ok": True,
        "identity": _public_session_identity(identity),
        "roles": roles if _is_admin_request(request) else [],
        "public_url": visitor_public_url(),
    })


async def api_visitor_roles(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以管理访客身份。")
    if request.method == "GET":
        return web.json_response({"ok": True, "roles": [_public_role(role) for role in _load_visitor_roles()]})
    body = await request.json()
    roles = _load_visitor_roles()
    role_id = _normalize_role_id(body.get("id") or body.get("name"))
    item = {
        "id": role_id,
        "name": str(body.get("name") or role_id).strip(),
        "description": str(body.get("description") or "").strip(),
        "permissions": _deep_merge_dict(_default_permissions(), body.get("permissions") if isinstance(body.get("permissions"), dict) else {}),
        "builtin": False,
    }
    roles = [r for r in roles if r.get("id") != role_id]
    roles.append(item)
    _atomic_write(VISITOR_ROLES_FILE, roles)
    return web.json_response({"ok": True, "role": _public_role(item), "roles": [_public_role(role) for role in roles]})


async def api_visitor_delete_role(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以删除访客身份。")
    role_id = request.match_info.get("role_id", "")
    roles = _load_visitor_roles()
    target = next((r for r in roles if r.get("id") == role_id), None)
    if not target:
        return web.json_response({"ok": False, "error": "身份不存在。"}, status=404)
    if target.get("builtin"):
        return web.json_response({"ok": False, "error": "内置身份不能删除，可以新建自定义身份替代。"}, status=400)
    roles = [r for r in roles if r.get("id") != role_id]
    _atomic_write(VISITOR_ROLES_FILE, roles)
    return web.json_response({"ok": True, "roles": [_public_role(role) for role in roles]})


async def api_visitor_keys(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以管理临时密钥。")
    if request.method == "GET":
        keys = [_public_key_record(item) for item in _read_list_file(VISITOR_KEYS_FILE)]
        return web.json_response({"ok": True, "keys": keys})
    body = await request.json()
    result = visitor_create_key_from_role(body.get("role_id") or body.get("role_name"), body.get("remark", ""))
    status = 200 if result.get("ok") else 400
    return web.json_response(result, status=status)


async def api_visitor_revoke_key(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以撤销密钥。")
    key_id = request.match_info.get("key_id", "")
    keys = _read_list_file(VISITOR_KEYS_FILE)
    changed = False
    for item in keys:
        if item.get("id") == key_id:
            item["status"] = "revoked"
            changed = True
            break
    if changed:
        _atomic_write(VISITOR_KEYS_FILE, keys)
        _append_audit("key_revoked", {"key_id": key_id})
    return web.json_response({"ok": True, "changed": changed})


async def api_visitor_drafts(request):
    if not _is_authenticated_request(request):
        return _visitor_error("请先登录。", status=401)
    drafts = [d for d in _load_drafts() if d.get("status") == "pending"]
    if not _is_admin_request(request):
        invite_id = _get_session_identity(request).get("invite_id", "")
        drafts = [d for d in drafts if d.get("invite_id") == invite_id]
    return web.json_response({"ok": True, "drafts": [_draft_brief(draft) for draft in drafts]})


async def api_visitor_review_draft(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以审核草稿。")
    draft_id = request.match_info.get("draft_id", "")
    action = request.match_info.get("action", "")
    result = visitor_review_draft_by_id(draft_id, action == "approve", "webui")
    return web.json_response(result, status=200 if result.get("ok") else 400)


async def api_visitor_tunnel_status(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以查看协作通道。")
    cfg = _read_dict_file(VISITOR_TUNNEL_FILE)
    detected = _detect_cloudflared_path()
    version_info = _cloudflared_version(detected) if detected else {"ok": False, "version": "", "error": ""}
    port = request.app.get("webui_port", 4399)
    local_url = f"http://127.0.0.1:{port}"
    system = sys.platform
    if system.startswith("win"):
        install_hint = "winget install --id Cloudflare.cloudflared"
    elif system == "darwin":
        install_hint = "brew install cloudflared"
    else:
        install_hint = "按 Cloudflare 官方文档安装 cloudflared，或下载对应架构二进制。"
    return web.json_response({
        "ok": True,
        "config": cfg,
        "detected_path": detected or "",
        "detected": bool(detected),
        "version": version_info.get("version", ""),
        "version_ok": bool(version_info.get("ok")),
        "version_error": version_info.get("error", ""),
        "running": bool(_CLOUDFLARED_PROCESS and _CLOUDFLARED_PROCESS.returncode is None),
        "public_url": visitor_public_url(),
        "managed_path": str(_cloudflared_managed_path()),
        "download_url": _cloudflared_download_url(),
        "official_download_url": _cloudflared_official_download_url(),
        "download_sources": _CLOUDFLARED_DOWNLOAD_SOURCES,
        "download_asset": _cloudflared_download_asset()[0],
        "local_url": local_url,
        "quick_tunnel_command": f"cloudflared tunnel --url {local_url}",
        "install_hint": install_hint,
        "install_task": _install_task_public(),
        "docs": [
            "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/",
            "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/",
        ],
    })


async def api_visitor_tunnel_config(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以配置协作通道。")
    body = await request.json()
    cfg = _read_dict_file(VISITOR_TUNNEL_FILE)
    for key in (
        "mode",
        "cloudflared_path",
        "custom_public_url",
        "last_public_url",
        "cloudflared_download_source",
        "cloudflared_download_url_template",
    ):
        if key in body:
            cfg[key] = str(body.get(key) or "").strip()
    if cfg.get("cloudflared_download_source") not in {"official", "custom"}:
        cfg["cloudflared_download_source"] = "official"
    for key in ("allow_plugin_start_tunnel", "allow_install_script"):
        if key in body:
            cfg[key] = bool(body.get(key))
    _atomic_write(VISITOR_TUNNEL_FILE, cfg)
    return web.json_response({"ok": True, "config": cfg})


async def api_visitor_cloudflared_install(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以安装 cloudflared。")
    try:
        result = await _download_cloudflared_binary(force=True)
        return web.json_response({"ok": True, **result})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "error_hint": _cloudflared_error_hint(e), "download_url": _cloudflared_download_url()}, status=500)


async def _run_cloudflared_install_task(task_id: str):
    try:
        _append_install_log(task_id, "Install task started.")
        task = _CLOUDFLARED_INSTALL_TASKS.get(task_id) or _read_dict_file(VISITOR_INSTALL_STATE_FILE)
        result = await _download_cloudflared_binary(task_id, force=bool(task.get("force")))
        _save_install_task(
            task_id,
            ok=True,
            status="done",
            percent=100,
            path=result.get("path", ""),
            version=result.get("version", ""),
        )
        _append_install_log(task_id, "Install task completed.")
    except Exception as exc:
        _save_install_task(task_id, ok=False, status="error", error=str(exc), error_hint=_cloudflared_error_hint(exc))
        _append_install_log(task_id, f"Install task failed: {exc}")
        _append_install_log(task_id, _cloudflared_error_hint(exc))


async def api_visitor_cloudflared_install_start(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以安装 cloudflared。")
    try:
        body = await request.json()
    except Exception:
        body = {}
    cfg_changed = False
    cfg = _read_dict_file(VISITOR_TUNNEL_FILE)
    for key in ("cloudflared_download_source", "cloudflared_download_url_template"):
        if key in body:
            cfg[key] = str(body.get(key) or "").strip()
            cfg_changed = True
    if cfg.get("cloudflared_download_source") not in {"official", "custom"}:
        cfg["cloudflared_download_source"] = "official"
        cfg_changed = True
    if cfg.get("cloudflared_download_source") == "custom" and not cfg.get("cloudflared_download_url_template"):
        return web.json_response({"ok": False, "error": "自定义下载源需要填写 URL 模板。"}, status=400)
    if cfg_changed:
        _atomic_write(VISITOR_TUNNEL_FILE, cfg)
    force = bool(body.get("force"))
    detected = _detect_cloudflared_path()
    if detected and not force:
        version = _cloudflared_version(detected)
        task_id = f"cf_{uuid.uuid4().hex[:12]}"
        _save_install_task(
            task_id,
            ok=True,
            status="done",
            percent=100,
            downloaded=0,
            total=0,
            error="",
            url=_cloudflared_download_url(),
            source=_cloudflared_download_source_name(),
            path=detected,
            version=version.get("version", ""),
            logs=[f"[{time.strftime('%H:%M:%S')}] Existing cloudflared is usable: {version.get('version', '')}"],
            created_at=int(time.time()),
        )
        return web.json_response({"ok": True, "task_id": task_id, "already_installed": True})
    for existing_id, task in _CLOUDFLARED_INSTALL_TASKS.items():
        if task.get("status") in {"queued", "downloading", "installing"}:
            return web.json_response({"ok": True, "task_id": existing_id, "already_running": True})
    state = _read_dict_file(VISITOR_INSTALL_STATE_FILE)
    if state.get("status") in {"queued", "downloading", "installing"} and state.get("task_id"):
        if state["task_id"] in _CLOUDFLARED_INSTALL_TASKS:
            return web.json_response({"ok": True, "task_id": state["task_id"], "already_running": True})
        state["ok"] = False
        state["status"] = "error"
        state["error"] = "install task was interrupted"
        state["error_hint"] = "上一次安装任务已经不在运行，可能是 WebUI/AstrBot 重启导致；可以点击重新下载。"
        state.setdefault("logs", []).append(f"[{time.strftime('%H:%M:%S')}] Install task was interrupted; ready for retry.")
        _atomic_write(VISITOR_INSTALL_STATE_FILE, _install_task_public(state))
    task_id = f"cf_{uuid.uuid4().hex[:12]}"
    _save_install_task(
        task_id,
        ok=True,
        status="queued",
        downloaded=0,
        total=0,
        percent=0,
        error="",
        url=_cloudflared_download_url(),
        source=_cloudflared_download_source_name(),
        force=force,
        logs=[],
        created_at=int(time.time()),
    )
    asyncio.create_task(_run_cloudflared_install_task(task_id))
    return web.json_response({"ok": True, "task_id": task_id})


async def api_visitor_cloudflared_install_progress(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以查看安装进度。")
    task_id = request.query.get("task_id", "")
    if not task_id:
        task = _read_dict_file(VISITOR_INSTALL_STATE_FILE)
        task_id = task.get("task_id", "")
    task = _CLOUDFLARED_INSTALL_TASKS.get(task_id) or _read_dict_file(VISITOR_INSTALL_STATE_FILE)
    if not task:
        return web.json_response({"ok": False, "error": "install task not found"}, status=404)
    if task.get("status") in {"queued", "downloading", "installing"} and task.get("task_id") not in _CLOUDFLARED_INSTALL_TASKS:
        task["ok"] = False
        task["status"] = "error"
        task["error"] = "install task was interrupted"
        task["error_hint"] = "上一次安装任务已经不在运行，可能是 WebUI/AstrBot 重启导致；可以点击重新下载。"
        task.setdefault("logs", []).append(f"[{time.strftime('%H:%M:%S')}] Install task was interrupted; ready for retry.")
        _atomic_write(VISITOR_INSTALL_STATE_FILE, _install_task_public(task))
    return web.json_response({"ok": True, "task": _install_task_public(task)})


async def api_visitor_tunnel_start(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以启动临时通道。")
    port = request.app.get("webui_port", 4399)
    local_url = f"http://127.0.0.1:{port}"
    try:
        result = await _start_cloudflared_quick_tunnel(local_url)
        return web.json_response({"ok": True, **result})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_visitor_tunnel_stop(request):
    if not _is_admin_request(request):
        return _visitor_error("只有管理员可以停止临时通道。")
    global _CLOUDFLARED_PROCESS, _CLOUDFLARED_PUBLIC_URL
    if _CLOUDFLARED_PROCESS and _CLOUDFLARED_PROCESS.returncode is None:
        _CLOUDFLARED_PROCESS.terminate()
        try:
            await asyncio.wait_for(_CLOUDFLARED_PROCESS.wait(), timeout=5)
        except asyncio.TimeoutError:
            _CLOUDFLARED_PROCESS.kill()
    _CLOUDFLARED_PROCESS = None
    _CLOUDFLARED_PUBLIC_URL = ""
    return web.json_response({"ok": True, "running": False})


async def api_profile_overview(request):
    try:
        profiles = [_collect_profile_stats(pid) for pid in _list_profile_ids()]
        return web.json_response({"ok": True, "profiles": profiles, "default_profile": DEFAULT_PROFILE_NAME})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "profiles": [], "default_profile": DEFAULT_PROFILE_NAME}, status=500)


async def api_create_profile(request):
    try:
        body = await request.json()
        name = str(body.get("name", "")).strip()
        raw_copy_from = str(body.get("copy_from") or DEFAULT_PROFILE_NAME).strip()
        copy_from = _sanitize_profile_id(raw_copy_from or DEFAULT_PROFILE_NAME)
        if not name:
            return web.json_response({"ok": False, "error": "name required"}, status=400)
        profile_id = _sanitize_profile_id(body.get("profile_id") or name.lower())
        if profile_id == DEFAULT_PROFILE_NAME and name != "默认配置":
            return web.json_response({"ok": False, "error": "default profile id reserved"}, status=400)
        paths = get_profile_storage_paths(profile_id, PLUGIN_NAME)
        if paths["profile_dir"].exists() and any(paths["profile_dir"].iterdir()):
            return web.json_response({"ok": False, "error": "profile already exists"}, status=400)

        ensure_profile_dirs(profile_id, PLUGIN_NAME)

        if raw_copy_from == BUILTIN_DEFAULT_COPY_FROM:

            _seed_profile_from_builtin_defaults(paths)
        elif raw_copy_from == BLANK_COPY_FROM:
            _seed_blank_profile(paths)
        else:
            source_paths = get_profile_storage_paths(copy_from, PLUGIN_NAME)
            ensure_profile_dirs(copy_from, PLUGIN_NAME)
            _ensure_profile_seed_data(copy_from)
            for key in ("func_cards_file", "fate_cards_file", "sign_in_texts_file", "runtime_config_file", "titles_config_file"):
                data = _read_json(source_paths[key], [] if "cards" in key or "titles" in key else {})
                _atomic_write(paths[key], data)

            for src_key, dst_key in (("func_assets_dir", "func_assets_dir"), ("fate_assets_dir", "fate_assets_dir")):

                src_dir = source_paths[src_key]
                dst_dir = paths[dst_key]
                dst_dir.mkdir(parents=True, exist_ok=True)
                if src_dir.exists():
                    for item in src_dir.iterdir():
                        if item.is_file():
                            shutil.copy2(item, dst_dir / item.name)

                desc = str(body.get("desc", "")).strip()
        tags = body.get("tags", [])
        if not isinstance(tags, list): tags = []
        tags = [str(t).strip() for t in tags if str(t).strip()]
        _save_profile_meta(profile_id, {"display_name": name, "cover_image": "", "desc": desc, "tags": tags})
        return web.json_response({"ok": True, "profile": _collect_profile_stats(profile_id)})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_update_profile_meta(request):
    try:
        body = await request.json()
        profile_id = _sanitize_profile_id(body.get("profile_id") or DEFAULT_PROFILE_NAME)
        action = str(body.get("action", "")).strip().lower()
        if action == "delete":
            ok, error = _delete_profile_storage(profile_id)
            if not ok:
                status = 404 if error == "profile not found" else 400 if error == "default profile cannot be deleted" else 500
                return web.json_response({"ok": False, "error": error}, status=status)
            return web.json_response({"ok": True, "deleted_profile": profile_id, "fallback_profile": DEFAULT_PROFILE_NAME})

        name = str(body.get("display_name", "")).strip()
        cover_image = str(body.get("cover_image", "")).strip()
        desc = str(body.get("desc", "")).strip()
        tags = body.get("tags", [])
        if not isinstance(tags, list): tags = []
        tags = [str(t).strip() for t in tags if str(t).strip()]
        if not name:
            return web.json_response({"ok": False, "error": "display_name required"}, status=400)
        meta = _get_profile_meta(profile_id)
        meta["display_name"] = name
        meta["cover_image"] = cover_image
        meta["desc"] = desc
        meta["tags"] = tags
        _save_profile_meta(profile_id, meta)
        return web.json_response({"ok": True, "profile": _collect_profile_stats(profile_id)})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_bind_group_profile(request):
    try:
        body = await request.json()
        profile_id = _sanitize_profile_id(body.get("profile_id") or DEFAULT_PROFILE_NAME)
        group_id = str(body.get("group_id", "")).strip()
        if not group_id.isdigit():
            return web.json_response({"ok": False, "error": "group_id invalid"}, status=400)
        ensure_profile_dirs(profile_id, PLUGIN_NAME)
        mapping = get_group_profile_map(PLUGIN_NAME)
        mapping[group_id] = profile_id
        save_group_profile_map(mapping, PLUGIN_NAME)
        return web.json_response({"ok": True, "profile": _collect_profile_stats(profile_id)})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_unbind_group_profile(request):
    try:
        body = await request.json()
        profile_id = _sanitize_profile_id(body.get("profile_id") or DEFAULT_PROFILE_NAME)
        group_id = str(body.get("group_id", "")).strip()
        mapping = get_group_profile_map(PLUGIN_NAME)
        if mapping.get(group_id) == profile_id:
            mapping.pop(group_id, None)
            save_group_profile_map(mapping, PLUGIN_NAME)
        return web.json_response({"ok": True, "profile": _collect_profile_stats(profile_id)})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


def _resolve_delete_profile_id(request, body: dict | None = None) -> str:
    if request.match_info.get("profile_id"):
        return _sanitize_profile_id(request.match_info.get("profile_id"))
    if isinstance(body, dict) and body.get("profile_id"):
        return _sanitize_profile_id(body.get("profile_id"))
    return _sanitize_profile_id(
        request.query.get("profile_id")
        or request.headers.get("X-Delete-Profile")
        or DEFAULT_PROFILE_NAME
    )


def _delete_profile_storage(profile_id: str) -> tuple[bool, str]:
    if profile_id == DEFAULT_PROFILE_NAME:
        return False, "default profile cannot be deleted"

    paths = get_profile_storage_paths(profile_id, PLUGIN_NAME)
    profile_dir = paths["profile_dir"]
    if not profile_dir.exists():
        return False, "profile not found"

    mapping = get_group_profile_map(PLUGIN_NAME)
    changed = False
    for gid, pid in list(mapping.items()):
        if pid == profile_id:
            mapping[gid] = DEFAULT_PROFILE_NAME
            changed = True
    if changed:
        save_group_profile_map(mapping, PLUGIN_NAME)

    shutil.rmtree(profile_dir)
    if profile_dir.exists():
        return False, "profile delete failed"
    return True, ""


async def api_remove_profile(request):
    try:
        body = await request.json()
        profile_id = _resolve_delete_profile_id(request, body if isinstance(body, dict) else None)
        ok, error = _delete_profile_storage(profile_id)
        if not ok:
            status = 404 if error == "profile not found" else 400 if error == "default profile cannot be deleted" else 500
            return web.json_response({"ok": False, "error": error}, status=status)
        return web.json_response({"ok": True, "deleted_profile": profile_id, "fallback_profile": DEFAULT_PROFILE_NAME})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_delete_profile(request):
    try:
        body = None
        if request.can_read_body:
            try:
                body = await request.json()
            except Exception:
                body = None
        profile_id = _resolve_delete_profile_id(request, body)
        ok, error = _delete_profile_storage(profile_id)
        if not ok:
            status = 404 if error == "profile not found" else 400 if error == "default profile cannot be deleted" else 500
            return web.json_response({"ok": False, "error": error}, status=status)
        return web.json_response({"ok": True, "deleted_profile": profile_id, "fallback_profile": DEFAULT_PROFILE_NAME})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_profile_delete_post(request):
    return await api_delete_profile(request)


async def api_profile_delete_get(request):
    return await api_delete_profile(request)


async def api_delete_profile_by_path(request):
    return await api_delete_profile(request)


async def api_get_group_access(request):
    try:
        cfg = _read_json(GROUP_ACCESS_FILE, _default_group_access_config())
        if not isinstance(cfg, dict):
            cfg = _default_group_access_config()
        cfg.setdefault("mode", "off")
        cfg.setdefault("blacklist", [])
        cfg.setdefault("whitelist", [])
        return web.json_response({"ok": True, "config": cfg})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "config": _default_group_access_config()}, status=500)


async def api_save_group_access(request):
    try:
        body = await request.json()
        cfg = body.get("config", {})
        if not isinstance(cfg, dict):
            return web.json_response({"ok": False, "error": "config must be object"}, status=400)
        mode = str(cfg.get("mode", "off")).strip().lower()
        if mode not in {"off", "blacklist", "whitelist"}:
            return web.json_response({"ok": False, "error": "invalid mode"}, status=400)
        data = {
            "mode": mode,
            "blacklist": [str(x).strip() for x in cfg.get("blacklist", []) if str(x).strip()],
            "whitelist": [str(x).strip() for x in cfg.get("whitelist", []) if str(x).strip()],
        }
        _atomic_write(GROUP_ACCESS_FILE, data)
        return web.json_response({"ok": True, "config": data})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def serve_fate_image(request):
    filename = request.match_info.get("filename", "")
    profile_id = _sanitize_profile_id(request.query.get("profile") or DEFAULT_PROFILE_NAME)
    safe_name = Path(filename).name
    paths = get_profile_storage_paths(profile_id, PLUGIN_NAME)
    for target in (
        paths["fate_assets_dir"] / safe_name,
        paths["plugin_data_dir"] / "lazy_images" / "fate" / safe_name,
    ):
        if target.exists():
            return web.FileResponse(target)
    raise web.HTTPNotFound()


async def serve_image(request):
    """提供图片文件访问"""
    filename = request.match_info.get("filename", "")
    profile_id = _sanitize_profile_id(request.query.get("profile") or DEFAULT_PROFILE_NAME)
    safe_name = Path(filename).name
    paths = get_profile_storage_paths(profile_id, PLUGIN_NAME)
    for target in (
        paths["func_assets_dir"] / safe_name,
        paths["plugin_data_dir"] / "lazy_images" / "func" / safe_name,
    ):
        if target.exists():
            return web.FileResponse(target)
    raise web.HTTPNotFound()


async def serve_index(request):
    for entry in (STATIC_DIR / "app.html", STATIC_DIR / "index.html"):
        if entry.exists():
            return web.FileResponse(entry)
    return web.Response(text="WebUI not found", status=404)


# ==============================================================================
# 服务器启动/停止
# ==============================================================================

_runner = None
_site = None


def run_server_process(port: int, access_password: str = WEBUI_DEFAULT_ACCESS_PASSWORD):
    """给 multiprocessing.Process 调用的同步入口"""
    import asyncio
    global _WEBUI_ACCESS_PASSWORD
    _WEBUI_ACCESS_PASSWORD = _normalize_access_password(access_password)

    async def _serve():
        await start_webui(host="0.0.0.0", port=port)
        # 永久阻塞，保持进程存活
        await asyncio.Event().wait()

    try:
        asyncio.run(_serve())
    except Exception as exc:
        print(f"[WebUI] WebUI startup failed: {exc}")
        raise


async def start_webui(host: str = "0.0.0.0", port: int = 4399):
    global _runner, _site

    _ensure_private_dirs()
    migrate_legacy_storage(PLUGIN_NAME)
    _ensure_profile_seed_data(DEFAULT_PROFILE_NAME)
    _ensure_visitor_files()
    if not WEBUI_ACCESS_CONFIG_FILE.exists():
        _atomic_write(WEBUI_ACCESS_CONFIG_FILE, {"access_password": _normalize_access_password(_WEBUI_ACCESS_PASSWORD)})
    app = web.Application(middlewares=[auth_middleware])
    app["webui_port"] = port

        # API 路由
    app.router.add_get("/api/access/status", api_access_status)
    app.router.add_post("/api/access/verify", api_access_verify)
    app.router.add_post("/api/access/logout", api_access_logout)
    app.router.add_get("/api/visitor/state", api_visitor_state)
    app.router.add_get("/api/visitor/roles", api_visitor_roles)
    app.router.add_post("/api/visitor/roles", api_visitor_roles)
    app.router.add_delete("/api/visitor/roles/{role_id}", api_visitor_delete_role)
    app.router.add_get("/api/visitor/keys", api_visitor_keys)
    app.router.add_post("/api/visitor/keys", api_visitor_keys)
    app.router.add_post("/api/visitor/keys/{key_id}/revoke", api_visitor_revoke_key)
    app.router.add_get("/api/visitor/drafts", api_visitor_drafts)
    app.router.add_post("/api/visitor/drafts/{draft_id}/{action:approve|reject}", api_visitor_review_draft)
    app.router.add_get("/api/visitor/tunnel", api_visitor_tunnel_status)
    app.router.add_post("/api/visitor/tunnel", api_visitor_tunnel_config)
    app.router.add_post("/api/visitor/cloudflared/install", api_visitor_cloudflared_install)
    app.router.add_post("/api/visitor/cloudflared/install/start", api_visitor_cloudflared_install_start)
    app.router.add_get("/api/visitor/cloudflared/install/progress", api_visitor_cloudflared_install_progress)
    app.router.add_post("/api/visitor/tunnel/start", api_visitor_tunnel_start)
    app.router.add_post("/api/visitor/tunnel/stop", api_visitor_tunnel_stop)
    app.router.add_get("/api/profile_overview", api_profile_overview)
    app.router.add_post("/api/profiles", api_create_profile)
    app.router.add_post("/api/profile_meta", api_update_profile_meta)
    app.router.add_post("/api/profile_bind_group", api_bind_group_profile)
    app.router.add_post("/api/profile_unbind_group", api_unbind_group_profile)
    app.router.add_post("/api/profile_remove", api_remove_profile)
    app.router.add_post("/api/profile_delete", api_profile_delete_post)
    app.router.add_get("/api/profile_delete", api_profile_delete_get)
    app.router.add_delete("/api/profiles/{profile_id}", api_delete_profile_by_path)
    app.router.add_delete("/api/profiles", api_delete_profile)
    app.router.add_get("/api/group_access", api_get_group_access)
    app.router.add_post("/api/group_access", api_save_group_access)
    app.router.add_get("/api/runtime_config", api_get_runtime_config)
    app.router.add_post("/api/runtime_config", api_save_runtime_config)
    app.router.add_post("/api/lazy/batch_fate", api_lazy_batch_fate)
    app.router.add_post("/api/lazy/batch_func", api_lazy_batch_func)
    app.router.add_post("/api/lazy/auto_bind", api_lazy_auto_bind)

    # 专门挂载隔离的外网图片目录
    app.router.add_static("/lazy_assets/fate", BASE_PATHS["plugin_data_dir"] / "lazy_images" / "fate")
    app.router.add_static("/lazy_assets/func", BASE_PATHS["plugin_data_dir"] / "lazy_images" / "func")

    app.router.add_get("/api/fate_cards", api_get_fate_cards)
    app.router.add_post("/api/fate_cards", api_save_fate_cards)
    app.router.add_post("/api/upload_fate_image", api_upload_fate_image)
    app.router.add_get("/api/fate_images", api_list_fate_images)
    app.router.add_delete("/api/fate_images/{filename}", api_delete_fate_image)
    app.router.add_get("/fate_assets/{filename}", serve_fate_image)
    app.router.add_get("/api/func_cards", api_get_func_cards)
    app.router.add_post("/api/func_cards", api_save_func_cards)
    app.router.add_get("/api/sign_in_texts", api_get_sign_in_texts)
    app.router.add_post("/api/sign_in_texts", api_save_sign_in_texts)
    app.router.add_get("/api/titles", api_get_titles)
    app.router.add_post("/api/titles", api_save_titles)
    app.router.add_get("/api/user_stats", api_get_user_stats)
    app.router.add_post("/api/upload_image", api_upload_image)
    app.router.add_get("/api/images", api_list_images)
    app.router.add_delete("/api/images/{filename}", api_delete_image)
    app.router.add_get("/api/check_missing_images", api_check_missing_images)



    # 图片访问
    app.router.add_get("/assets/{filename}", serve_image)

    # 静态文件
    if STATIC_DIR.exists():
        app.router.add_static("/static", STATIC_DIR)

    # 前端入口（所有未匹配路由都返回 index.html）
    app.router.add_get("/", serve_index)
    app.router.add_get("/{tail:.*}", serve_index)

    _runner = web.AppRunner(app)
    await _runner.setup()
    _site = web.TCPSite(_runner, host, port)
    await _site.start()
    print(f"[WebUI] 管理界面已启动：http://{host}:{port}")


async def stop_webui():
    global _runner, _site
    if _runner:
        await _runner.cleanup()
        _runner = None
        _site = None
        print("[WebUI] 管理界面已关闭")


def is_running() -> bool:
    return _runner is not None
