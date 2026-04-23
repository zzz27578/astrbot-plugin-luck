import sys

with open('webui/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

start_str = "async def api_lazy_quote(request):"
end_str = "# ============================================================================== \n# API 路由处理"

start_idx = content.find(start_str)
end_idx = content.find(end_str)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + """\
async def api_lazy_match(request):
    try:
        body = await request.json() if request.can_read_body else {}
        if not isinstance(body, dict):
            body = {}
        paths, _ = _get_request_runtime_config(request)
        
        kind = str(body.get("kind", "")).strip()
        if kind not in ("fate", "func"):
            return web.json_response({"ok": False, "error": "invalid kind"}, status=400)

        card = body.get("card", {})
        gen_pic = bool(body.get("gen_pic", True))
        gen_text = bool(body.get("gen_text", True))
        prefer_local = bool(body.get("prefer_local", True))
        allow_remote = bool(body.get("allow_remote", True))

        if kind == "fate":
            target_dir = paths["fate_assets_dir"]
            name = card.get("name", "")
            text = card.get("text", "")
            filename = card.get("filename", "")
            if gen_text and not text:
                text = await fetch_pure_quote()
                card["text"] = text
                if not name:
                    card["name"] = f"命运·{text[:8]}"
            if gen_pic and not filename:
                if prefer_local:
                    filename = _choose_local_image(target_dir, [name, text])
                if not filename and allow_remote:
                    try:
                        filename = await fetch_random_waifu_image(target_dir, "fate")
                    except Exception:
                        pass
                if not filename and not prefer_local:
                    filename = _choose_local_image(target_dir, [name, text])
                card["filename"] = filename
        else:
            target_dir = paths["func_assets_dir"]
            name = card.get("card_name", "")
            desc = card.get("description", "")
            filename = card.get("filename", "")
            if gen_pic and not filename:
                if prefer_local:
                    filename = _choose_local_image(target_dir, [name, desc])
                if not filename and allow_remote:
                    try:
                        filename = await fetch_random_waifu_image(target_dir, "func")
                    except Exception:
                        pass
                if not filename and not prefer_local:
                    filename = _choose_local_image(target_dir, [name, desc])
                card["filename"] = filename
        
        return web.json_response({"ok": True, "card": card})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def api_lazy_batch_fate(request):
    try:
        body = await request.json() if request.can_read_body else {}
        if not isinstance(body, dict):
            body = {}
        paths, runtime_cfg = _get_request_runtime_config(request)
        if not runtime_cfg.get("fate_cards_settings", {}).get("enable", True):
            return web.json_response({"ok": False, "error": "命运牌模块未开启。"}, status=403)

        count = max(1, min(10, _safe_int(body.get("count", 1))))
        gold_min = _safe_int(body.get("gold_min", -20), -20)
        gold_max = _safe_int(body.get("gold_max", 100), 100)
        gen_pic = bool(body.get("gen_pic", True))
        gen_text = bool(body.get("gen_text", True))
        prefer_local = bool(body.get("prefer_local", True))
        allow_remote = bool(body.get("allow_remote", True))

        results = []
        for _ in range(count):
            draft = await build_fate_draft(
                paths["fate_assets_dir"],
                gold_min, gold_max, gen_pic, gen_text, prefer_local, allow_remote
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
        paths, runtime_cfg = _get_request_runtime_config(request)
        if not runtime_cfg.get("func_cards_settings", {}).get("enable", True):
            return web.json_response({"ok": False, "error": "功能牌模块未开启。"}, status=403)

        count = max(1, min(10, _safe_int(body.get("count", 1))))
        allowed_types = body.get("allowed_types")
        if not isinstance(allowed_types, list):
            allowed_types = ["attack", "heal", "defense"]
        max_rarity = max(1, min(5, _safe_int(body.get("max_rarity", 5), 5)))
        max_tags = max(1, _safe_int(body.get("max_tags", 2), 2))
        max_effect_val = _safe_int(body.get("max_effect_val", 50), 50)
        
        gen_pic = bool(body.get("gen_pic", True))
        gen_text = bool(body.get("gen_text", True))
        prefer_local = bool(body.get("prefer_local", True))
        allow_remote = bool(body.get("allow_remote", True))

        results = []
        for _ in range(count):
            draft = await build_func_draft(
                paths["func_assets_dir"],
                allowed_types, max_rarity, max_tags, max_effect_val,
                gen_pic, gen_text, prefer_local, allow_remote
            )
            results.append(draft)

        return web.json_response({"ok": True, "cards": results})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


""" + content[end_idx:]

    with open('webui/server.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("API replaced successfully.")
else:
    print("Could not find markers.", start_idx, end_idx)
