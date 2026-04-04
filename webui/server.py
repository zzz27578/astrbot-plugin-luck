# ==============================================================================
# 🌐 luck_rank WebUI 管理后端
# ==============================================================================
import os
import json
import asyncio
import tempfile
import shutil
from pathlib import Path
from aiohttp import web

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
    ]
}


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


def _load_json_template(path: Path, default):
    data = _read_json(path, default)
    if isinstance(default, list):
        return data if isinstance(data, list) else list(default)
    if isinstance(default, dict):
        return data if isinstance(data, dict) else dict(default)
    return data


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


def _ensure_private_dirs():
    """确保官方隔离数据目录存在，避免 WebUI 因目录缺失读取异常。"""
    for directory in (BASE_PATHS["plugin_data_dir"], BASE_PATHS["profiles_dir"], GROUP_DATA_DIR, FATE_ASSETS_DIR, ASSETS_DIR):
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
        "fate_cards_settings": {
            "enable": True,
            "daily_draw_limit": 3,
        },
        "func_cards_settings": {
            "enable": True,
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
                "draw_cost": 20,
                "pity_threshold": 10,
            },
        },
    }


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
        cards = _read_json(paths["fate_cards_file"], [])
        return web.json_response({"ok": True, "cards": cards if isinstance(cards, list) else []})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "cards": []}, status=500)


async def api_save_fate_cards(request):
    try:
        body = await request.json()
        cards = body.get("cards", [])
        paths = _get_request_profile_paths(request)
        _atomic_write(paths["fate_cards_file"], cards)
        return web.json_response({"ok": True})
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
        if not fate_assets_dir.exists():
            return web.json_response({"ok": True, "images": []})
        exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        images = [f.name for f in fate_assets_dir.iterdir() if f.suffix.lower() in exts]
        return web.json_response({"ok": True, "images": sorted(images)})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "images": []}, status=500)


async def api_get_func_cards(request):
    try:
        paths = _get_request_profile_paths(request)
        cards = _read_json(paths["func_cards_file"], [])
        return web.json_response({"ok": True, "cards": cards if isinstance(cards, list) else []})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "cards": []}, status=500)


async def api_save_func_cards(request):
    try:
        body = await request.json()
        cards = body.get("cards", [])
        paths = _get_request_profile_paths(request)
        _atomic_write(paths["func_cards_file"], cards)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_get_sign_in_texts(request):
    try:
        paths = _get_request_profile_paths(request)
        texts = _read_json(paths["sign_in_texts_file"], DEFAULT_SIGN_IN_TEXTS)
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
        texts = body.get("texts", {})
        paths = _get_request_profile_paths(request)
        _atomic_write(paths["sign_in_texts_file"], texts)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_get_user_stats(request):
    """按方案汇总只读用户数据，供概率分析和持牌检测用"""
    try:
        profile_id = _get_request_profile_id(request)
        stats = {
            "total_groups": 0,
            "total_users": 0,
            "card_holders": {},
            "groups": [],
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
            stats["groups"].append({"group_id": group_dir.name, "user_count": len(data)})
            stats["total_users"] += len(data)
            for _, info in data.items():
                for card in info.get("inventory", []):
                    name = card.get("card_name", "")
                    if name:
                        stats["card_holders"][name] = stats["card_holders"].get(name, 0) + 1
        return web.json_response({"ok": True, "stats": stats})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "stats": {"total_groups": 0, "total_users": 0, "card_holders": {}, "groups": [], "profile_id": DEFAULT_PROFILE_NAME}}, status=500)


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
        exts = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        files = [f.name for f in assets_dir.iterdir() if f.suffix.lower() in exts]
        files.sort()
        return web.json_response({"ok": True, "files": files})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e), "files": []}, status=500)


async def api_delete_image(request):
    filename = request.match_info.get("filename", "")
    if not filename:
        return web.json_response({"ok": False, "error": "no filename"}, status=400)
    paths = _get_request_profile_paths(request)
    target = paths["func_assets_dir"] / Path(filename).name
    if target.exists():
        target.unlink()
    return web.json_response({"ok": True})


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
        copy_from = _sanitize_profile_id(body.get("copy_from") or DEFAULT_PROFILE_NAME)
        if not name:
            return web.json_response({"ok": False, "error": "name required"}, status=400)
        profile_id = _sanitize_profile_id(body.get("profile_id") or name.lower())
        if profile_id == DEFAULT_PROFILE_NAME and name != "默认配置":
            return web.json_response({"ok": False, "error": "default profile id reserved"}, status=400)
        paths = get_profile_storage_paths(profile_id, PLUGIN_NAME)
        if paths["profile_dir"].exists() and any(paths["profile_dir"].iterdir()):
            return web.json_response({"ok": False, "error": "profile already exists"}, status=400)
        source_paths = get_profile_storage_paths(copy_from, PLUGIN_NAME)
        ensure_profile_dirs(copy_from, PLUGIN_NAME)
        ensure_profile_dirs(profile_id, PLUGIN_NAME)
        for key in ("func_cards_file", "fate_cards_file", "sign_in_texts_file", "runtime_config_file"):
            data = _read_json(source_paths[key], [] if "cards" in key else {})
            _atomic_write(paths[key], data)
        for src_key, dst_key in (("func_assets_dir", "func_assets_dir"), ("fate_assets_dir", "fate_assets_dir")):
            src_dir = source_paths[src_key]
            dst_dir = paths[dst_key]
            dst_dir.mkdir(parents=True, exist_ok=True)
            if src_dir.exists():
                for item in src_dir.iterdir():
                    if item.is_file():
                        shutil.copy2(item, dst_dir / item.name)
        _save_profile_meta(profile_id, {"display_name": name, "cover_image": ""})
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
        if not name:
            return web.json_response({"ok": False, "error": "display_name required"}, status=400)
        meta = _get_profile_meta(profile_id)
        meta["display_name"] = name
        meta["cover_image"] = cover_image
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
    target = get_profile_storage_paths(profile_id, PLUGIN_NAME)["fate_assets_dir"] / Path(filename).name
    if not target.exists():
        raise web.HTTPNotFound()
    return web.FileResponse(target)


async def serve_image(request):
    """提供图片文件访问"""
    filename = request.match_info.get("filename", "")
    profile_id = _sanitize_profile_id(request.query.get("profile") or DEFAULT_PROFILE_NAME)
    target = get_profile_storage_paths(profile_id, PLUGIN_NAME)["func_assets_dir"] / Path(filename).name
    if not target.exists():
        raise web.HTTPNotFound()
    return web.FileResponse(target)


async def serve_index(request):
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return web.Response(text="WebUI not found", status=404)
    return web.FileResponse(index)


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

    asyncio.run(_serve())


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
    app.router.add_post("/api/profile_delete", api_profile_delete_post)
    app.router.add_get("/api/profile_delete", api_profile_delete_get)
    app.router.add_delete("/api/profiles/{profile_id}", api_delete_profile_by_path)
    app.router.add_delete("/api/profiles", api_delete_profile)
    app.router.add_get("/api/group_access", api_get_group_access)
    app.router.add_post("/api/group_access", api_save_group_access)
    app.router.add_get("/api/runtime_config", api_get_runtime_config)
    app.router.add_post("/api/runtime_config", api_save_runtime_config)
    app.router.add_get("/api/fate_cards", api_get_fate_cards)
    app.router.add_post("/api/fate_cards", api_save_fate_cards)
    app.router.add_post("/api/upload_fate_image", api_upload_fate_image)
    app.router.add_get("/api/fate_images", api_list_fate_images)
    app.router.add_get("/fate_assets/{filename}", serve_fate_image)
    app.router.add_get("/api/func_cards", api_get_func_cards)
    app.router.add_post("/api/func_cards", api_save_func_cards)
    app.router.add_get("/api/sign_in_texts", api_get_sign_in_texts)
    app.router.add_post("/api/sign_in_texts", api_save_sign_in_texts)
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