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

# 路径配置
ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
ASSETS_DIR = ROOT_DIR / "assets" / "func_cards"
DATA_FILE = ROOT_DIR / "data" / "luck_data.json"
FUNC_CARDS_FILE = CONFIG_DIR / "func_cards.json"
FATE_CARDS_FILE = CONFIG_DIR / "cards_config.json"
SIGN_IN_TEXTS_FILE = CONFIG_DIR / "sign_in_texts.json"
RUNTIME_CONFIG_FILE = CONFIG_DIR / "webui_runtime_config.json"
FATE_ASSETS_DIR = ROOT_DIR / "assets" / "cards"
WEBUI_DIR = Path(__file__).parent
STATIC_DIR = WEBUI_DIR / "static"

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
    current = _read_json(RUNTIME_CONFIG_FILE, {})
    merged = _deep_merge_dict(_default_runtime_config(), current)
    return web.json_response({"ok": True, "config": merged})


async def api_save_runtime_config(request):
    try:
        body = await request.json()
        cfg = body.get("config", {})
        if not isinstance(cfg, dict):
            return web.json_response({"ok": False, "error": "config must be object"}, status=400)
        merged = _deep_merge_dict(_default_runtime_config(), cfg)
        _atomic_write(RUNTIME_CONFIG_FILE, merged)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_get_fate_cards(request):
    cards = _read_json(FATE_CARDS_FILE, [])
    return web.json_response({"ok": True, "cards": cards})


async def api_save_fate_cards(request):
    try:
        body = await request.json()
        cards = body.get("cards", [])
        _atomic_write(FATE_CARDS_FILE, cards)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_upload_fate_image(request):
    """上传命运牌图片到 assets/cards/"""
    try:
        FATE_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        reader = await request.multipart()
        uploaded = []
        async for field in reader:
            if field.name == "files":
                filename = field.filename
                if not filename:
                    continue
                safe_name = Path(filename).name
                dest = FATE_ASSETS_DIR / safe_name
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
    if not FATE_ASSETS_DIR.exists():
        return web.json_response({"ok": True, "images": []})
    exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    images = [f.name for f in FATE_ASSETS_DIR.iterdir() if f.suffix.lower() in exts]
    return web.json_response({"ok": True, "images": sorted(images)})


async def api_get_func_cards(request):
    cards = _read_json(FUNC_CARDS_FILE, [])
    return web.json_response({"ok": True, "cards": cards})


async def api_save_func_cards(request):
    try:
        body = await request.json()
        cards = body.get("cards", [])
        _atomic_write(FUNC_CARDS_FILE, cards)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_get_sign_in_texts(request):
    texts = _read_json(SIGN_IN_TEXTS_FILE, DEFAULT_SIGN_IN_TEXTS)
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


async def api_save_sign_in_texts(request):
    try:
        body = await request.json()
        texts = body.get("texts", {})
        _atomic_write(SIGN_IN_TEXTS_FILE, texts)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_get_user_stats(request):
    """只读用户数据，供概率分析和持牌检测用"""
    data = _read_json(DATA_FILE, {})
    stats = {
        "total_users": len(data),
        "card_holders": {}  # card_name -> count
    }
    for uid, info in data.items():
        for card in info.get("inventory", []):
            name = card.get("card_name", "")
            if name:
                stats["card_holders"][name] = stats["card_holders"].get(name, 0) + 1
    return web.json_response({"ok": True, "stats": stats})


async def api_upload_image(request):
    """上传卡图到 assets/func_cards/"""
    try:
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        reader = await request.multipart()
        uploaded = []
        async for field in reader:
            if field.name == "files":
                filename = field.filename
                if not filename:
                    continue
                safe_name = Path(filename).name
                dest = ASSETS_DIR / safe_name
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
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    exts = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    files = [f.name for f in ASSETS_DIR.iterdir() if f.suffix.lower() in exts]
    files.sort()
    return web.json_response({"ok": True, "files": files})


async def api_delete_image(request):
    filename = request.match_info.get("filename", "")
    if not filename:
        return web.json_response({"ok": False, "error": "no filename"}, status=400)
    target = ASSETS_DIR / Path(filename).name
    if target.exists():
        target.unlink()
    return web.json_response({"ok": True})


async def api_check_missing_images(request):
    """检查所有卡牌中引用了但实际不存在的图片"""
    cards = _read_json(FUNC_CARDS_FILE, [])
    missing = []
    for card in cards:
        fn = str(card.get("filename", "")).strip()
        if fn and not (ASSETS_DIR / fn).exists():
            missing.append({"card_name": card.get("card_name"), "filename": fn})
    return web.json_response({"ok": True, "missing": missing})


async def serve_image(request):
    """提供图片文件访问"""
    filename = request.match_info.get("filename", "")
    target = ASSETS_DIR / Path(filename).name
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

    app = web.Application()

    # API 路由
    app.router.add_get("/api/runtime_config", api_get_runtime_config)
    app.router.add_post("/api/runtime_config", api_save_runtime_config)
    app.router.add_get("/api/fate_cards", api_get_fate_cards)
    app.router.add_post("/api/fate_cards", api_save_fate_cards)
    app.router.add_post("/api/upload_fate_image", api_upload_fate_image)
    app.router.add_get("/api/fate_images", api_list_fate_images)
    app.router.add_static("/fate_assets", FATE_ASSETS_DIR, show_index=False)
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