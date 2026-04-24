import re

with open('webui/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_api = """\
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
        for _ in range(count):
            draft = await build_fate_draft(
                remote_dir, local_dir,
                gold_min, gold_max, image_mode, gen_text,
                used_texts, used_images
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
        for _ in range(count):
            draft = await build_func_draft(
                remote_dir, local_dir,
                allowed_types, max_rarity, max_tags, max_effect_val,
                image_mode, gen_text, used_images
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
            cards = _normalize_fate_cards(_read_json(cards_file, []))
        else:
            cards_file = paths["func_cards_file"]
            local_dir = paths["func_assets_dir"]
            cards = _normalize_func_cards(_read_json(cards_file, []))

        used_images = {str(c.get("filename", "")) for c in cards if c.get("filename")}
        changed = 0
        for c in cards:
            if not str(c.get("filename", "")).strip():
                new_file = _choose_local_image(local_dir, used_images)
                if new_file:
                    c["filename"] = new_file
                    used_images.add(new_file)
                    changed += 1

        if changed > 0:
            _atomic_write(cards_file, cards)
            
        return web.json_response({"ok": True, "changed": changed, "cards": cards})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)
"""

# 替换掉旧的 batch 接口和 match 接口块（因为签名变化了）
start_marker = "async def api_lazy_match(request):"
end_marker = "# ============================================================================== \n# API 路由处理"

sidx = content.find(start_marker)
eidx = content.find(end_marker)

if sidx != -1 and eidx != -1:
    new_content = content[:sidx] + new_api + "\n" + content[eidx:]
    with open('webui/server.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced batch and auto bind api successfully.")
else:
    print("Cannot find markers in server.py")
