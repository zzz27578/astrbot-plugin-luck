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
import uuid
from urllib.parse import urlparse
from pathlib import Path
from aiohttp import web, ClientSession, ClientTimeout

from ..core.title_engine import TitleEngine
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
    except Exception:
        if tmp and tmp.exists():
            tmp.unlink()
        raise


def _read_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


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

        for item in data.get("luck_ranges", []) if isinstance(data.get("luck_ranges", []), list) else []:
            if not isinstance(item, dict):
                continue
        min_val = _safe_int(item.get("min", 1), 1)
        max_val = _safe_int(item.get("max", 100), 100)
        if min_val > max_val:
            min_val, max_val = max_val, min_val
        result["luck_ranges"].append({
            "label": str(item.get("label", "") or "新区间").strip() or "新区间",
                    "min": min_val,
                    "max": max_val,
                    "gold_delta": _safe_int(item.get("gold_delta", 0), 0),
                    "comments": [str(x).strip() for x in item.get("comments", []) if str(x).strip()] if isinstance(item.get("comments", []), list) else [],
                })

    result["enable_quote"] = bool(data.get("enable_quote", True))
    result["enable_draw_prob"] = bool(data.get("enable_draw_prob", True))
    result["use_custom_quote"] = bool(data.get("use_custom_quote", False))
    result["custom_quotes"] = [str(x).strip() for x in data.get("custom_quotes", []) if str(x).strip()]
    if not result["custom_quotes"]:
                result["custom_quotes"] = DEFAULT_SIGN_IN_TEXTS.get("custom_quotes", ["这虽然是游戏，但可不是闹着玩的。"])

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
            "rarity_mode": "default",
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
                "paid_daily_draw": 10,
                "draw_cost": 20,
                "pity_threshold": 10,
            },
            "max_equipped_titles": 3,
        },

    }


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
    merged = _deep_merge_dict(_default_runtime_config(), current if isinstance(current, dict) else {})
    return paths, merged


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
    available = [text for text in _LAZY_QUOTE_FALLBACKS if text not in used_texts]
    if available:
        text = random.choice(available)
        used_texts.add(text)
        return text
    text = f"命运的幕布再次拉开·第 {len(used_texts) + 1} 幕"
    used_texts.add(text)
    return text


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
    if image_mode == "remote":
        try:
            return await _fetch_unique_lazy_image(session, remote_dir, prefix, used_remote_urls)
        except Exception:
            filename = _choose_local_image_with_repeat(local_dir, used_images, allow_repeat=True)
            if filename:
                used_images.add(filename)
            return filename
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
        paths, _ = _get_request_runtime_config(request)

        count = max(1, min(10, _safe_int(body.get("count", 1))))
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
        paths, _ = _get_request_runtime_config(request)

        count = max(1, min(10, _safe_int(body.get("count", 1))))
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
        merged = _deep_merge_dict(_default_runtime_config(), current)
        return web.json_response({"ok": True, "config": merged})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "config": _default_runtime_config()}, status=500)


async def api_save_runtime_config(request):
    try:
        body = await request.json()
        cfg = body.get("config", {})
        if not isinstance(cfg, dict):
            return web.json_response({"ok": False, "error": "config must be object"}, status=400)
        merged = _deep_merge_dict(_default_runtime_config(), cfg)
        paths = _get_request_profile_paths(request)
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
        _atomic_write(paths["fate_cards_file"], cards)
        return web.json_response({"ok": True, "cards": cards})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_upload_fate_image(request):
    """上传命运牌图片到 assets/cards/"""
    try:
        paths = _get_request_profile_paths(request)
        fate_assets_dir = paths["fate_assets_dir"]
        fate_assets_dir.mkdir(parents=True, exist_ok=True)
        reader = await request.multipart()
        uploaded = []
        async for field in reader:
            if field.name == "files":
                filename = field.filename
                if not filename:
                    continue
                safe_name = Path(filename).name
                dest = fate_assets_dir / safe_name
                with open(dest, "wb") as f:
                    while True:
                        chunk = await field.read_chunk(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                uploaded.append(safe_name)
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
        _atomic_write(paths["sign_in_texts_file"], texts)
        return web.json_response({"ok": True, "texts": texts})
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
        _atomic_write(paths["titles_config_file"], titles)
        return web.json_response({"ok": True, "titles": titles})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)



async def api_get_user_stats(request):
    """按方案汇总只读用户数据，供概率分析和持牌检测用"""
    try:
        profile_id = _get_request_profile_id(request)
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
            
            for uid, info in data.items():
                gold = _safe_int(info.get("gold", 0), 0)
                sign_ins = _safe_int(info.get("sign_in_count", 0), 0)
                inventory = info.get("inventory", [])
                cards_count = len(inventory) if isinstance(inventory, list) else 0
                
                stats["total_gold"] += gold
                stats["total_cards_issued"] += cards_count
                stats["total_sign_ins"] += sign_ins
                group_gold += gold
                group_cards += cards_count
                group_sign_ins += sign_ins
                
                if sign_ins > 0:
                    stats["active_users"] += 1

                for card in inventory:
                    if isinstance(card, dict):
                        cname = str(card.get("card_name", "")).strip()
                        if cname:
                            stats["card_holders"][cname] = stats["card_holders"].get(cname, 0) + 1

                        r = str(card.get("rarity", 1))
                        if r in stats["rarity_distribution"]:
                            stats["rarity_distribution"][r] += 1
                        else:
                            stats["rarity_distribution"]["1"] += 1
                            
                titles = info.get("titles", [])
                if isinstance(titles, list):
                    for t in titles:
                        tname = str(t.get("name", t) if isinstance(t, dict) else t).strip()
                        if tname:
                            stats["title_holders"][tname] = stats["title_holders"].get(tname, 0) + 1

                stats["wealth_leaderboard"].append({
                    "uid": str(uid),
                    "gold": gold,
                    "cards": cards_count
                })
                
            stats["groups"].append({
                "group_id": group_dir.name, 
                "user_count": len(data),
                "group_gold": group_gold,
                "group_sign_ins": group_sign_ins
            })
            stats["total_users"] += len(data)
            
        # 财富排行榜排序并截取 Top 50
        stats["wealth_leaderboard"].sort(key=lambda x: x["gold"], reverse=True)
        stats["wealth_leaderboard"] = stats["wealth_leaderboard"][:50]
        
        # 群组排行榜按总金币或活跃度排序
        stats["groups"].sort(key=lambda x: x["group_gold"], reverse=True)
        
        return web.json_response({"ok": True, "stats": stats})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "stats": {"total_groups": 0, "total_users": 0, "total_gold": 0, "total_cards_issued": 0, "wealth_leaderboard": [], "groups": [], "profile_id": DEFAULT_PROFILE_NAME}}, status=500)


async def api_upload_image(request):
    """上传卡图到 assets/func_cards/"""
    try:
        paths = _get_request_profile_paths(request)
        assets_dir = paths["func_assets_dir"]
        assets_dir.mkdir(parents=True, exist_ok=True)
        reader = await request.multipart()
        uploaded = []
        async for field in reader:
            if field.name == "files":
                filename = field.filename
                if not filename:
                    continue
                safe_name = Path(filename).name
                dest = assets_dir / safe_name
                with open(dest, "wb") as f:
                    while True:
                        chunk = await field.read_chunk(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                uploaded.append(safe_name)
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


def run_server_process(port: int):
    """给 multiprocessing.Process 调用的同步入口"""
    import asyncio

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
    app = web.Application()

        # API 路由
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
