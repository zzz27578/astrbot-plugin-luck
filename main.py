import os
import re
import json
import asyncio
import time
from pathlib import Path
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import *
from .modules.m_sign_in import handle_sign_in

# ================= 🔌 核心底座与模块导入 =================
from .core.luck_bank import LuckBank
from .core.json_cache import load_json_cached
from .core.plugin_storage import PLUGIN_NAME, get_base_storage_paths, get_runtime_context, migrate_legacy_storage
from .modules import m_sign_in, m_fate_cards, m_func_cards
from .webui.server import (
    start_webui,
    verify_webui_admin_password,
    visitor_create_key_from_role,
    visitor_ensure_public_url,
    visitor_get_drafts_summary,
    visitor_get_roles_summary,
    visitor_public_url,
    visitor_review_draft_by_id,
)


migrate_legacy_storage(PLUGIN_NAME)


def _deep_merge_dict(base: dict, override: dict) -> dict:
    result = dict(base or {})
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge_dict(result[k], v)
        else:
            result[k] = v
    return result


def _load_runtime_override(runtime_config_file: str) -> dict:
    if not os.path.exists(runtime_config_file):
        return {}
    try:
        data = load_json_cached(runtime_config_file, default={})
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_webui_access_password(password: str, plugin_name: str = PLUGIN_NAME) -> Path:
    base_paths = get_base_storage_paths(plugin_name)
    password_file = base_paths["plugin_data_dir"] / "webui_access_config.json"
    password_file.parent.mkdir(parents=True, exist_ok=True)
    with open(password_file, "w", encoding="utf-8") as f:
        json.dump({"access_password": str(password or "").strip() or "12345678"}, f, ensure_ascii=False, indent=2)
    return password_file


def _normalize_public_duel_runtime(config: dict) -> dict:
    merged = dict(config or {})
    func_cfg = dict(merged.get("func_cards_settings", {}) or {})
    duel_cfg = m_func_cards._get_public_duel_settings(merged)
    func_cfg["enable_public_duel_mode"] = duel_cfg["enabled"]
    func_cfg["public_duel_daily_limit"] = duel_cfg["daily_limit"]
    func_cfg["public_duel_min_stake"] = duel_cfg["min_stake"]
    func_cfg["public_duel_max_stake"] = duel_cfg["max_stake"]
    merged["func_cards_settings"] = func_cfg
    return merged


def _extract_group_id(event: AstrMessageEvent) -> str | None:
    """尽可能兼容不同 AstrBot 版本/适配器的群号提取。"""
    candidates = []

    for attr in ("get_group_id", "get_chat_id"):
        getter = getattr(event, attr, None)
        if callable(getter):
            try:
                value = getter()
                if value:
                    candidates.append(value)
            except Exception:
                pass

    for attr in ("group_id", "chat_id"):
        value = getattr(event, attr, None)
        if value:
            candidates.append(value)

    message_obj = getattr(event, "message_obj", None)
    if message_obj is not None:
        for attr in ("group_id", "group_openid", "peer_id"):
            value = getattr(message_obj, attr, None)
            if value:
                candidates.append(value)
        for nested in ("group", "sender", "scene"):
            obj = getattr(message_obj, nested, None)
            if obj is None:
                continue
            for attr in ("id", "group_id"):
                value = getattr(obj, attr, None)
                if value:
                    candidates.append(value)

    session = getattr(event, "session", None)
    if session is not None:
        for attr in ("group_id",):
            value = getattr(session, attr, None)
            if value:
                candidates.append(value)

    for value in candidates:
        text = str(value).strip()
        if not text:
            continue
        if text.isdigit():
            return text
        match = re.search(r"(\d{5,})", text)
        if match:
            return match.group(1)

    return None


def _normalize_luck_command(raw_text: str) -> str | None:
    """仅兼容前后空白与全角空格，不放宽到普通聊天可误触的程度。"""
    text = str(raw_text or "").replace("\u3000", " ").strip()
    if not text:
        return ""
    match = re.match(r"^/luck(?:\s+(.*))?$", text, flags=re.IGNORECASE)
    if not match:
        return None
    cmd = (match.group(1) or "").replace("\u3000", " ")
    cmd = re.sub(r"\s+", " ", cmd).strip()
    return cmd


def _extract_at_target(event: AstrMessageEvent) -> tuple[str | None, str | None]:
    for comp in event.get_messages():
        if isinstance(comp, At):
            qq = getattr(comp, "qq", None)
            if qq:
                qq_str = str(qq).strip()
                if qq_str.lower() in {"all", "notify_all", "all_members", "0"}:
                    continue
                if qq_str:
                    return qq_str, f"群友({qq_str})"
    return None, None


def _has_at_all_target(event: AstrMessageEvent) -> bool:
    for comp in event.get_messages():
        if isinstance(comp, At):
            qq = str(getattr(comp, "qq", "") or "").strip().lower()
            if qq in {"all", "notify_all", "all_members", "0"}:
                return True
    raw_text = str(getattr(event, "message_str", "") or "")
    return bool(re.search(r"@(?:全体成员|全体|全员)", raw_text))



    


def _load_group_access_config(plugin_name: str = PLUGIN_NAME) -> dict:
    default_cfg = {"mode": "off", "blacklist": [], "whitelist": []}
    try:
        base_paths = get_base_storage_paths(plugin_name)
        group_access_file = base_paths["plugin_data_dir"] / "group_access_control.json"
        if not group_access_file.exists():
            return default_cfg
        data = load_json_cached(group_access_file, default=default_cfg)
        if not isinstance(data, dict):
            return default_cfg
        mode = str(data.get("mode", "off")).strip().lower()
        return {
            "mode": mode if mode in {"off", "blacklist", "whitelist"} else "off",
            "blacklist": [str(x).strip() for x in data.get("blacklist", []) if str(x).strip()],
            "whitelist": [str(x).strip() for x in data.get("whitelist", []) if str(x).strip()],
        }
    except Exception:
        return default_cfg




def _is_group_access_allowed(group_id: str, plugin_name: str = PLUGIN_NAME) -> bool:
    cfg = _load_group_access_config(plugin_name)
    mode = cfg.get("mode", "off")
    group_key = str(group_id).strip()
    if mode == "blacklist":
        return group_key not in set(cfg.get("blacklist", []))
    if mode == "whitelist":
        return group_key in set(cfg.get("whitelist", []))
    return True


PLUGIN_NAME = "luck_rank"
AUTHOR = "YourName" # 可修改为你自己的名字
VERSION = "5.4.0-Pro"

@register(PLUGIN_NAME, AUTHOR, "异世界战术金币系统", VERSION)
class LuckPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self._base_config = config or {}
        self._bank_cache: dict[str, LuckBank] = {}
        self._last_runtime_config = self._base_config
        self._private_admin_verified_until: dict[str, float] = {}

        # 启动时先确保默认 profile 与旧数据迁移到位
        migrate_legacy_storage(self.name or PLUGIN_NAME)

        # 启动 WebUI，用独立进程跑，和主程序完全隔离
        self._webui_process = None
        webui_cfg = self._base_config.get("webui_settings", {})
        if webui_cfg.get("enable", False):
            webui_port = int(webui_cfg.get("port", 4399) or 4399)
            webui_access_password = str(webui_cfg.get("access_password", "12345678") or "12345678").strip() or "12345678"
            _write_webui_access_password(webui_access_password, self.name or PLUGIN_NAME)
            from multiprocessing import Process
            from .webui.server import run_server_process
            self._webui_process = Process(
                target=run_server_process,
                args=(webui_port, webui_access_password),
                daemon=True
            )
            self._webui_process.start()
            print(f"[WebUI] 管理界面已在独立进程启动，端口：{webui_port}")

    def _refresh_runtime_config(self, group_id: str) -> tuple[LuckBank, dict]:
        """按群读取运行时配置，确保用户数据与配置方案双重隔离。"""
        runtime_ctx = get_runtime_context(group_id, self.name or PLUGIN_NAME)
        runtime_override = _load_runtime_override(str(runtime_ctx["runtime_config_file"]))
        merged_config = _normalize_public_duel_runtime(_deep_merge_dict(self._base_config, runtime_override))
        merged_config["_storage_paths"] = runtime_ctx
        merged_config["_group_id"] = str(group_id)
        merged_config["_profile_name"] = str(runtime_ctx["active_profile_name"])
        self._last_runtime_config = merged_config

        group_key = str(group_id)
        if group_key not in self._bank_cache:
            self._bank_cache[group_key] = LuckBank(str(runtime_ctx["luck_data_file"]))
        return self._bank_cache[group_key], merged_config

    @filter.regex(r"^\s*/luck(?:\s+.*)?$", priority=1000)
    async def luck_gateway(self, event: AstrMessageEvent):

        # 第一时间阻断事件，防止底层聊天 AI 抢答
        event.stop_event()
        group_id = _extract_group_id(event)
        private_cmd_str = _normalize_luck_command(event.get_message_str())
        private_user_id = event.get_sender_id()
        if not group_id:
            if private_cmd_str is not None:
                if private_cmd_str in {"", "menu", "help", "菜单", "帮助", "规则", "功能菜单"}:
                    if private_cmd_str in {"help", "帮助", "规则"}:
                        async for res in self._show_help(event):
                            yield res
                    else:
                        async for res in self._show_menu(event):
                            yield res
                    return
                handled = False
                async for res in self._handle_private_collab_admin(event, private_user_id, private_cmd_str):
                    handled = True
                    yield res
                if handled:
                    return
                if self._is_extra_admin(str(private_user_id), self._base_config) and self._private_admin_verified_until.get(str(private_user_id), 0) >= time.time():
                    group_id = f"private_{private_user_id}"
                else:
                    yield event.plain_result("私聊测试全部命令前，请先发送：/luck 管理验证 WebUI管理密码\n菜单与帮助可直接私聊使用。")
                    return
            if not group_id:
                yield event.plain_result("⚠️ 当前功能仅支持群聊使用，私聊场景不参与签到与排行映射。")
                return

        if not str(group_id).startswith("private_") and not _is_group_access_allowed(group_id, self.name or PLUGIN_NAME):
            return

        bank, current_config = self._refresh_runtime_config(group_id)

        user_id = event.get_sender_id()
        user_name = event.get_sender_name()

        raw_message = event.get_message_str()
        cmd_str = _normalize_luck_command(raw_message)
        if cmd_str is None:
            return

        func_cards_enabled = current_config.get("func_cards_settings", {}).get("enable", True)


        # ================= 🚧 0. 功能牌总开关统一拦截 =================
        if not func_cards_enabled and self._is_func_cards_command(cmd_str):
            yield event.plain_result("⚠️ 战术功能牌系统未开启，请先在配置中开启 func_cards_settings.enable。")
            return

        # ================= 👑 1. 天道管理员特权路由 =================
        if cmd_str.startswith("增加"):
            async for res in self._handle_admin_add(event, user_id, cmd_str, bank, current_config):
                yield res
            return
        if cmd_str.startswith("授予功能牌") or cmd_str.startswith("授予称号"):
            async for res in self._handle_admin_grant(event, user_id, cmd_str, bank, current_config):
                yield res
            return
        if cmd_str.startswith("丢弃功能牌") or cmd_str.startswith("丢弃称号"):
            async for res in self._handle_admin_discard(event, user_id, cmd_str, bank, current_config):
                yield res
            return

                # ================= 📖 2. 菜单与帮助路由 =================
        if cmd_str in ["", "菜单", "功能菜单", "menu"]:
            async for res in self._show_menu(event):
                yield res
            return
        if cmd_str in ["帮助", "规则", "help"]:
            async for res in self._show_help(event):
                yield res
            return
        if cmd_str in ["管理员菜单", "管理菜单", "admin"]:
            if self._is_extra_admin(str(user_id), current_config):
                yield event.plain_result(self._admin_menu_text())
            else:
                yield event.plain_result("⚠️ 只有插件管理员可以查看管理员菜单。")
            return

        # ================= 📜 3. 基础运势签到路由 =================

        if re.match(r"^(运势|签到|今日运势|jrrp)$", cmd_str):
            if not current_config.get("sign_in_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 异世界星象观测台今日维护，基础签到暂未开放。")
                return
            async for res in handle_sign_in(event, bank, current_config):
                yield res
            return

        # ================= 🏆 4. 风云排行榜路由 =================
        if re.match(r"^(排行榜|金币榜|财富榜|气运榜|运势榜)$", cmd_str):
            async for res in m_sign_in.handle_leaderboard_v2(event, bank, current_config):
                yield res
            return

        if cmd_str == "善恶榜":
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_karma_leaderboard(event, bank, current_config):
                yield res
            return

        if cmd_str.startswith("查询"):
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术功能牌系统暂未开放。")
                return
            card_name = cmd_str.replace("查询", "", 1).strip()
            async for res in m_func_cards.handle_query_func_card(event, current_config, card_name):
                yield res
            return


        if cmd_str == "查看称号":
            async for res in m_func_cards.handle_view_titles(event, bank, current_config):
                yield res
            return

        if cmd_str.startswith("佩戴称号"):
            title_name = cmd_str.replace("佩戴称号", "", 1).strip()
            async for res in m_func_cards.handle_equip_title(event, bank, current_config, title_name):
                yield res
            return

        if cmd_str.startswith("卸下称号"):
            title_name = cmd_str.replace("卸下称号", "", 1).strip()
            async for res in m_func_cards.handle_unequip_title(event, bank, current_config, title_name):
                yield res
            return


        # ================= 🎴 5. 命运牌抽换路由 =================

        if re.match(r"^(幸运牌|抽牌|抽卡|命运卡牌|换牌|换一张|换一张牌)$", cmd_str):
            if not current_config.get("fate_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 命运卡牌池已被天道封锁，暂未开放。")
                return
            
            max_limit = current_config.get("fate_cards_settings", {}).get("daily_draw_limit", 3)
            async for res in m_fate_cards.handle_fate_card_draw(event, bank, current_config, max_limit):
                yield res
            return

                # ================= ⚔️ 6. 战术功能牌路由 =================

        if cmd_str == "面板" or cmd_str.startswith("面板@") or cmd_str.startswith("面板 @"):

            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放，面板无法观测。")
                return
            target_id = None
            target_name = None
            if cmd_str != "面板":
                target_id, target_name = _extract_at_target(event)
                if not target_id:
                    yield event.plain_result("⚠️ 查看他人面板时，请使用 /luck 面板@某人 或 /luck 面板 @某人。")
                    return
            async for res in m_func_cards.handle_panel(event, bank, current_config, target_id=target_id, target_name=target_name):
                yield res
            return

            
        if cmd_str == "抽取功能牌":
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            # 替换成调用真实的抽卡引擎
            async for res in m_func_cards.handle_draw_func_card(event, bank, current_config):
                yield res
            return

        # ================= 🗑️ 7. 丢弃卡牌路由 =================
        if cmd_str.startswith("丢弃"):
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            target_card = cmd_str.replace("丢弃", "").strip()
            async for res in m_func_cards.handle_discard_card(event, bank, target_card, current_config):
                yield res
            return

        # ================= ⚔️ 8. 核心干涉引擎 =================
        if cmd_str.startswith("使用"):
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_use_card(event, bank, cmd_str, current_config):
                yield res
            return

        if cmd_str.startswith(("对赌", "决斗")):
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_pure_duel(event, bank, current_config):
                yield res
            return

        if cmd_str == "确认":
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_confirm_duel(event, bank):
                yield res
            return

        if cmd_str.startswith(("加注", "追加投入")):
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_raise_duel(event, bank):
                yield res
            return

        if cmd_str.startswith("启用"):
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_active_card(event, bank, cmd_str, True, current_config):
                yield res
            return

        if cmd_str.startswith("停用"):
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_active_card(event, bank, cmd_str, False, current_config):
                yield res
            return

                # ================= 🚫 兜底处理 =================
        yield event.plain_result(f"❓ 未知的异界法术：{cmd_str}\n发送「/luck 菜单」查看可用口令。")

    async def _handle_private_collab_admin(self, event: AstrMessageEvent, sender_id: str, cmd_str: str):
        text = str(cmd_str or "").strip()
        visitor_prefixes = ("管理员菜单", "管理菜单", "管理验证", "访客身份", "生成临时密钥", "生成游客密钥", "访客密钥", "待审核", "同意草稿", "拒绝草稿", "通过草稿")
        if not text.startswith(visitor_prefixes):
            return
        if not self._is_extra_admin(str(sender_id), self._base_config):
            yield event.plain_result("⚠️ 只有插件管理员可以在私聊中管理访客协作。")
            return

        if text in {"管理员菜单", "管理菜单"}:
            yield event.plain_result(self._admin_menu_text())
            return

        if text.startswith("管理验证"):
            password = text.replace("管理验证", "", 1).strip()
            if not password:
                yield event.plain_result("请发送：/luck 管理验证 WebUI管理密码")
                return
            if verify_webui_admin_password(password):
                self._private_admin_verified_until[str(sender_id)] = time.time() + 600
                yield event.plain_result("✅ 管理验证通过，10 分钟内可以生成访客密钥和审核草稿。")
            else:
                yield event.plain_result("⚠️ WebUI 管理密码错误。")
            return

        if self._private_admin_verified_until.get(str(sender_id), 0) < time.time():
            yield event.plain_result("请先私聊发送：/luck 管理验证 WebUI管理密码")
            return

        if text in {"访客身份", "访客密钥"}:
            yield event.plain_result("【访客身份列表】\n" + visitor_get_roles_summary())
            return

        if text.startswith(("生成临时密钥", "生成游客密钥")):
            role_name = text
            for prefix in ("生成临时密钥", "生成游客密钥"):
                if role_name.startswith(prefix):
                    role_name = role_name.replace(prefix, "", 1).strip()
                    break
            if not role_name:
                yield event.plain_result("请发送：/luck 生成临时密钥 功能牌投稿员\n可用身份可用 /luck 访客身份 查看。")
                return
            webui_port = 4399
            try:
                webui_port = int((self._base_config.get("webui_settings") or {}).get("port", 4399) or 4399)
            except Exception:
                webui_port = 4399
            tunnel = await visitor_ensure_public_url(webui_port)
            result = visitor_create_key_from_role(role_name, expires_at=int(time.time()) + 24 * 3600)
            if not result.get("ok"):
                yield event.plain_result(f"⚠️ {result.get('error', '生成失败')}")
                return
            url = tunnel.get("public_url") or result.get("public_url") or visitor_public_url() or "未配置公网地址，请先在 WebUI 的访客协作页填写 trycloudflare 地址。"
            role = result.get("role", {})
            tunnel_note = "" if tunnel.get("ok") else f"\n临时地址刷新提示：{tunnel.get('error', '未能自动生成新地址，已使用已保存地址。')}"
            yield event.plain_result(
                "✅ 已生成访客协作密钥\n"
                f"身份：{role.get('name', role_name)}\n"
                f"地址：{url}\n"
                f"密钥：{result.get('key')}\n"
                "请只把访客密钥发给需要协作的人，不要发送 WebUI 管理密码。"
                f"{tunnel_note}"
            )
            return

        if text == "待审核":
            yield event.plain_result("【访客待审核】\n" + visitor_get_drafts_summary())
            return

        if text.startswith(("同意草稿", "通过草稿", "拒绝草稿")):
            approve = not text.startswith("拒绝草稿")
            draft_id = text
            for prefix in ("同意草稿", "通过草稿", "拒绝草稿"):
                draft_id = draft_id.replace(prefix, "", 1).strip()
            if not draft_id:
                yield event.plain_result("请带上草稿 ID，例如：/luck 同意草稿 draft_xxx")
                return
            result = visitor_review_draft_by_id(draft_id, approve, f"qq:{sender_id}")
            if result.get("ok"):
                yield event.plain_result("✅ 草稿已通过并写入正式配置。" if approve else "✅ 草稿已拒绝。")
            else:
                yield event.plain_result(f"⚠️ {result.get('error', '审核失败')}")
            return

    def _admin_menu_text(self) -> str:
        return "\n".join([
            "【/luck 管理员菜单】",
            "/luck 管理验证 WebUI管理密码",
            "/luck 访客身份",
            "/luck 生成临时密钥 身份名称",
            "/luck 待审核",
            "/luck 同意草稿 draft_xxx",
            "/luck 拒绝草稿 draft_xxx",
            "/luck 增加 @某人 数量",
            "/luck 授予功能牌 @某人 牌名",
            "/luck 授予称号 @某人 称号名",
            "/luck 丢弃功能牌 @某人 牌名",
            "/luck 丢弃称号 @某人 称号名",
            "私聊里菜单/帮助/管理员菜单可直接查看；生成密钥和审核前先做管理验证。",
        ])

    def _is_func_cards_command(self, cmd_str: str) -> bool:

        """判断是否为功能牌相关指令（用于总开关统一拦截）。"""
        if not cmd_str:
            return False

        exact_cmds = {"善恶榜", "面板", "抽取功能牌", "功能牌", "确认", "查看称号"}
        if cmd_str in exact_cmds or cmd_str.startswith("面板@") or cmd_str.startswith("面板 @"):
            return True

        if cmd_str.startswith(("丢弃", "使用", "启用", "停用", "对赌", "决斗", "加注", "追加投入", "佩戴称号", "卸下称号")):
            return True

        return False




   # ---------------- 👑 管理员私有方法 ----------------
    def _is_extra_admin(self, sender_id: str, current_config: dict) -> bool:
        admin_cfg = current_config.get("admin_settings", {})
        extra_admins_str = admin_cfg.get("extra_admin_qqs") or current_config.get("extra_admin_qqs", "")
        extra_admins_str = str(extra_admins_str).replace("，", ",")
        extra_admins = [qq.strip() for qq in extra_admins_str.split(",") if qq.strip()]
        return sender_id in extra_admins

    async def _resolve_admin_targets(
        self,
        event: AstrMessageEvent,
        bank: LuckBank,
        sender_id: str,
        sender_name: str,
        raw_text: str,
    ) -> tuple[list[tuple[str, dict]], str, str] | tuple[None, None, str]:
        text = str(raw_text or "").strip()
        if not text:
            return None, None, "⚠️ 请先指定目标。可用目标：自己、@某人、全体成员。"

        target_name = ""
        target_scope = "single"

        for alias in ("自己", "本人", "我自己"):
            if text.startswith(alias):
                target_name = sender_name
                text = text[len(alias):].strip()
                user_data = await bank.get_user_data(sender_id, sender_name)
                return [(sender_id, user_data)], target_name, text

        for alias in ("全体成员", "全体", "全员"):
            if text.startswith(alias) or text.startswith(f"@{alias}"):
                target_scope = "all"
                target_name = "全体成员"
                text = re.sub(rf"^@?{re.escape(alias)}", "", text, count=1).strip()
                break

        if target_scope != "all" and _has_at_all_target(event):
            target_scope = "all"
            target_name = "全体成员"
            text = re.sub(r"^@(?:全体成员|全体|全员)\s*", "", text).strip()

        if target_scope == "all":
            all_users = await bank.get_all_users()
            if not all_users:
                return None, None, "⚠️ 当前尚无可操作的成员档案。"
            target_users = [(uid, await bank.get_user_data(uid, data.get("name", f"群友({uid})"))) for uid, data in all_users.items()]
            return target_users, target_name, text

        target_id, target_name = _extract_at_target(event)
        if not target_id:
            return None, None, "⚠️ 天道法则施放失败：必须指定“自己”、@一名玩家，或使用“全体成员”。"

        cleaned_text = re.sub(r"@\S+", "", text).strip()
        target_user = await bank.get_user_data(target_id, target_name or f"群友({target_id})")
        return [(target_id, target_user)], target_name or f"群友({target_id})", cleaned_text

    async def _handle_admin_add(self, event: AstrMessageEvent, sender_id: str, cmd_str: str, bank: LuckBank, current_config: dict):
        if not self._is_extra_admin(sender_id, current_config):
            yield event.plain_result("⚡ 狂妄！你未拥有天道权限，无法篡改世界线！")
            return

        target_users, target_name, raw_text_or_error = await self._resolve_admin_targets(
            event,
            bank,
            sender_id,
            event.get_sender_name(),
            cmd_str.replace("增加", "", 1).strip(),
        )
        if not target_users:
            yield event.plain_result(raw_text_or_error)
            return
        raw_text = raw_text_or_error
        target_scope = "all" if target_name == "全体成员" else "single"

        # 3. 解析类型和数量 (支持正负数)
        match = re.search(r"(命运牌|功能牌|金币|气运|运势)\s*(-?\d+)", raw_text)
        if not match:
            yield event.plain_result("⚠️ 参数解析失败。\n正确格式：\n/luck 增加 自己 命运牌 3\n/luck 增加 @某人 功能牌 1\n/luck 增加 全体成员 金币 50\n/luck 增加 @某人 金币 -50")
            return
            
        card_type = match.group(1)
        add_count = int(match.group(2))

        affected_count = len(target_users)

        if card_type == "命运牌":
            for _, user_data in target_users:
                current_drawn = user_data.get("last_card_draw_count", 0)
                user_data["last_card_draw_count"] = current_drawn - add_count
            await bank.save_user_data()
            if target_scope == "all":
                yield event.plain_result(f"✅ 天道意志降临！\n已为全体成员统一补充 {add_count} 次【命运牌】换牌机会！\n👥 生效人数：{affected_count}")
            else:
                yield event.plain_result(f"✅ 天道意志降临！\n已为 {target_name} 补充了 {add_count} 次【命运牌】换牌机会！")
            
        elif card_type == "功能牌":
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术功能牌系统未开启，无法调整功能牌次数。")
                return
            for _, user_data in target_users:
                current_free = user_data.get("today_free_draws", 0)
                user_data["today_free_draws"] = current_free + add_count
            await bank.save_user_data()
            if target_scope == "all":
                yield event.plain_result(f"✅ 天赐机缘！\n已为全体成员额外发放 {add_count} 次【功能牌】免费抽取机会！\n👥 生效人数：{affected_count}")
            else:
                yield event.plain_result(f"✅ 天赐机缘！\n已为 {target_name} 额外发放了 {add_count} 次【功能牌】免费抽取机会！")
            
        elif card_type in ["金币", "气运", "运势"]:
            for _, user_data in target_users:
                current_gold = user_data.get("total_gold", 0)
                user_data["total_gold"] = current_gold + add_count
            await bank.save_user_data()
            
            action_str = "增加" if add_count >= 0 else "剥夺"
            abs_count = abs(add_count)
            if target_scope == "all":
                yield event.plain_result(f"⚡ 天道裁决！\n已对全体成员统一{action_str} {abs_count} 枚金币！\n👥 生效人数：{affected_count}")
            else:
                user_data = target_users[0][1]
                yield event.plain_result(f"⚡ 天道裁决！\n已强行 {action_str} {target_name} {abs_count} 枚金币！\n💰 当前金币：{user_data['total_gold']}")

    async def _handle_admin_grant(self, event: AstrMessageEvent, sender_id: str, cmd_str: str, bank: LuckBank, current_config: dict):
        if not self._is_extra_admin(sender_id, current_config):
            yield event.plain_result("⚡ 狂妄！你未拥有天道权限，无法篡改世界线！")
            return

        sender_name = event.get_sender_name()

        if cmd_str.startswith("授予功能牌"):
            if not current_config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术功能牌系统未开启，当前无法授予功能牌。")
                return

            target_users, target_name, raw_text_or_error = await self._resolve_admin_targets(
                event,
                bank,
                sender_id,
                sender_name,
                cmd_str.replace("授予功能牌", "", 1).strip(),
            )
            if not target_users:
                yield event.plain_result(raw_text_or_error)
                return

            card_name = raw_text_or_error.strip()
            if not card_name:
                yield event.plain_result("⚠️ 参数解析失败。\n正确格式：\n/luck 授予功能牌 自己 卡名\n/luck 授予功能牌 @某人 卡名\n/luck 授予功能牌 全体成员 卡名")
                return

            if target_name == "全体成员":
                success_results = []
                failed = []
                for uid, user_data in target_users:
                    result = await m_func_cards.grant_admin_func_card(bank, current_config, uid, user_data.get("name", f"群友({uid})"), card_name)
                    if result.get("ok"):
                        success_results.append((user_data.get("name", f"群友({uid})"), result))
                    else:
                        failed.append((user_data.get("name", f"群友({uid})"), result.get("error", "未知错误")))

                if not success_results:
                    yield event.plain_result(failed[0][1] if failed else "⚠️ 功能牌授予失败。")
                    return

                first_name, first_result = success_results[0]
                real_card_name = first_result["card"]["card_name"]
                preview_names = "、".join(name for name, _ in success_results[:10])
                if len(success_results) > 10:
                    preview_names += "……"
                lines = [
                    "✨ 【天道钦点·额外免费抽取】",
                    f"已为全体成员统一授予功能牌：【{real_card_name}】",
                    f"👥 成功人数：{len(success_results)}",
                    "📦 入库方式：天赐牌形态，可正常使用，但不占战术卡槽。",
                    f"📣 抽中名单：{preview_names}",
                ]
                if failed:
                    lines.append(f"⚠️ 失败人数：{len(failed)}")
                img_path = first_result.get("img_path", "")
                res_text = "\n".join(lines)
                if img_path:
                    yield event.chain_result([Image.fromFileSystem(img_path), Plain("\n" + res_text)])
                else:
                    yield event.plain_result(res_text)
                return

            target_uid, user_data = target_users[0]
            result = await m_func_cards.grant_admin_func_card(bank, current_config, target_uid, user_data.get("name", target_name), card_name)
            if not result.get("ok"):
                yield event.plain_result(result.get("error", "⚠️ 功能牌授予失败。"))
                return

            res_text = m_func_cards.format_admin_func_card_grant_text(target_name, result, current_config)
            img_path = result.get("img_path", "")
            if img_path:
                yield event.chain_result([Image.fromFileSystem(img_path), Plain("\n" + res_text)])
            else:
                yield event.plain_result(res_text)
            return

        target_users, target_name, raw_text_or_error = await self._resolve_admin_targets(
            event,
            bank,
            sender_id,
            sender_name,
            cmd_str.replace("授予称号", "", 1).strip(),
        )
        if not target_users:
            yield event.plain_result(raw_text_or_error)
            return

        title_name = raw_text_or_error.strip()
        if not title_name:
            yield event.plain_result("⚠️ 参数解析失败。\n正确格式：\n/luck 授予称号 自己 称号名\n/luck 授予称号 @某人 称号名\n/luck 授予称号 全体成员 称号名")
            return

        if target_name == "全体成员":
            granted_count = 0
            existed_count = 0
            failed = []
            preview_names = []
            for uid, user_data in target_users:
                result = await m_func_cards.grant_admin_title(bank, current_config, uid, user_data.get("name", f"群友({uid})"), title_name)
                if not result.get("ok"):
                    failed.append((user_data.get("name", f"群友({uid})"), result.get("error", "未知错误")))
                    continue
                preview_names.append(user_data.get("name", f"群友({uid})"))
                if result.get("existed", False):
                    existed_count += 1
                else:
                    granted_count += 1

            if granted_count == 0 and existed_count == 0:
                yield event.plain_result(failed[0][1] if failed else "⚠️ 称号授予失败。")
                return

            preview = "、".join(preview_names[:10])
            if len(preview_names) > 10:
                preview += "……"
            lines = [
                "🏅 【天道敕封】",
                f"已为全体成员处理称号：【{title_name}】",
                f"✅ 新增授予：{granted_count}",
                f"ℹ️ 原本已拥有：{existed_count}",
                "💡 需要生效时，玩家可继续使用：/luck 佩戴称号 称号名",
            ]
            if preview:
                lines.append(f"📣 处理名单：{preview}")
            if failed:
                lines.append(f"⚠️ 失败人数：{len(failed)}")
            yield event.plain_result("\n".join(lines))
            return

        target_uid, user_data = target_users[0]
        result = await m_func_cards.grant_admin_title(bank, current_config, target_uid, user_data.get("name", target_name), title_name)
        if not result.get("ok"):
            yield event.plain_result(result.get("error", "⚠️ 称号授予失败。"))
            return

        title_desc = str(result.get("title_info", {}).get("desc", "") or "").strip()
        action_text = "已拥有，已刷新为手动授予状态" if result.get("existed", False) else "已成功授予"
        lines = [
            "🏅 【天道敕封】",
            f"{action_text}：{target_name} -> 【{title_name}】",
            f"🎽 当前佩戴：{result.get('equipped_count', 0)}/{result.get('max_equipped', 1)}",
            "💡 需要生效时，可继续使用：/luck 佩戴称号 称号名",
        ]
        if title_desc:
            lines.insert(2, f"📝 {title_desc}")
        yield event.plain_result("\n".join(lines))

    async def _handle_admin_discard(self, event: AstrMessageEvent, sender_id: str, cmd_str: str, bank: LuckBank, current_config: dict):
        if not self._is_extra_admin(sender_id, current_config):
            yield event.plain_result("⚡ 狂妄！你未拥有天道权限，无法篡改世界线！")
            return

        sender_name = event.get_sender_name()
        discard_titles = cmd_str.startswith("丢弃称号")
        prefix = "丢弃称号" if discard_titles else "丢弃功能牌"

        target_users, target_name, raw_text_or_error = await self._resolve_admin_targets(
            event,
            bank,
            sender_id,
            sender_name,
            cmd_str.replace(prefix, "", 1).strip(),
        )
        if not target_users:
            yield event.plain_result(raw_text_or_error)
            return

        target_item_name = raw_text_or_error.strip()
        if not target_item_name:
            if discard_titles:
                yield event.plain_result("⚠️ 参数解析失败。\n正确格式：\n/luck 丢弃称号 自己 称号名\n/luck 丢弃称号 @某人 称号名\n/luck 丢弃称号 全体成员 称号名")
            else:
                yield event.plain_result("⚠️ 参数解析失败。\n正确格式：\n/luck 丢弃功能牌 自己 卡名\n/luck 丢弃功能牌 @某人 卡名\n/luck 丢弃功能牌 全体成员 卡名")
            return

        if target_name == "全体成员":
            success_names = []
            failed = []
            for uid, user_data in target_users:
                if discard_titles:
                    result = await m_func_cards.admin_discard_title(bank, current_config, uid, user_data.get("name", f"群友({uid})"), target_item_name)
                else:
                    result = await m_func_cards.admin_discard_func_card(bank, current_config, uid, user_data.get("name", f"群友({uid})"), target_item_name)
                if result.get("ok"):
                    success_names.append(user_data.get("name", f"群友({uid})"))
                else:
                    failed.append((user_data.get("name", f"群友({uid})"), result.get("error", "未知错误")))

            if not success_names:
                yield event.plain_result(failed[0][1] if failed else "⚠️ 没有任何成员处理成功。")
                return

            preview = "、".join(success_names[:10])
            if len(success_names) > 10:
                preview += "……"
            lines = [
                "🗑️ 【天道剥离】",
                f"已为全体成员统一丢弃：{'称号' if discard_titles else '功能牌'}【{target_item_name}】",
                f"👥 成功人数：{len(success_names)}",
                f"📢 处理名单：{preview}",
            ]
            if failed:
                lines.append(f"⚠️ 失败人数：{len(failed)}")
            yield event.plain_result("\n".join(lines))
            return

        target_uid, user_data = target_users[0]
        if discard_titles:
            result = await m_func_cards.admin_discard_title(bank, current_config, target_uid, user_data.get("name", target_name), target_item_name)
        else:
            result = await m_func_cards.admin_discard_func_card(bank, current_config, target_uid, user_data.get("name", target_name), target_item_name)
        if not result.get("ok"):
            yield event.plain_result(result.get("error", "⚠️ 丢弃失败。"))
            return

        if discard_titles:
            lines = [
                "🗑️ 【天道剥离】",
                f"已从 {target_name} 身上移除称号：【{result['title_name']}】",
                f"🎽 当前佩戴：{result.get('equipped_count', 0)}/{result.get('max_equipped', 1)}",
            ]
        else:
            extra_note = ""
            if result.get("removed_status"):
                extra_note = "\n🛡️ 对应的防御状态也已一并卸除。"
            elif result.get("was_active"):
                extra_note = "\n🛡️ 该牌原本处于启用状态，已强制下线。"
            slot_note = "（管理员授予牌，不占卡槽）" if result.get("no_slot") else ""
            lines = [
                "🗑️ 【天道剥离】",
                f"已从 {target_name} 的库存中移除功能牌：【{result['card_name']}】{slot_note}{extra_note}",
                f"🎴 当前卡槽：{result.get('slot_text', '-')}",
            ]
        yield event.plain_result("\n".join(lines))


        # ---------------- 📖 纯文本视图方法 ----------------
    async def _show_menu(self, event: AstrMessageEvent):
        current_config = self._last_runtime_config
        sign_enabled = current_config.get("sign_in_settings", {}).get("enable", True)
        fate_enabled = current_config.get("fate_cards_settings", {}).get("enable", True)
        func_enabled = current_config.get("func_cards_settings", {}).get("enable", True)
        dice_cards_enabled = current_config.get("func_cards_settings", {}).get("enable_dice_cards", True)
        duel_cfg = m_func_cards._get_public_duel_settings(current_config)
        duel_enabled = duel_cfg["enabled"]
        duel_limit = duel_cfg["daily_limit"]
        duel_min = duel_cfg["min_stake"]
        duel_max = duel_cfg["max_stake"]

        lines = [
            "📖 /luck 指令菜单（完整版）",
            "━━━━━━━━━━━━",
            "⚠️ 大部分指令有无空格都能用",
            "例：使用绝对零度@某人",
            "例：使用 绝对零度 @某人",
            "",
            "【基础】",
            f"/luck 运势  {'✅' if sign_enabled else '❌'}",
            f"/luck 抽卡  {'✅' if fate_enabled else '❌'}",
            "/luck 金币榜",
            "/luck 菜单",
            "/luck 帮助",
            "",
            "【功能牌】",
            f"/luck 抽取功能牌  {'✅' if func_enabled else '❌'}",
            "/luck 面板",
            "/luck 面板@某人",
            "/luck 查询 功能牌名",

            "/luck 查看称号",
            "/luck 佩戴称号 名称",
            "/luck 卸下称号 名称",
            "/luck 善恶榜",
            "/luck 使用卡名@某人",
            "/luck 使用卡名随机",
            "/luck 启用卡名",
            "/luck 停用卡名",
            "/luck 丢弃卡名",
            "",
            "【骰子 / 决斗】",
            f"骰子功能牌：{'✅开启' if dice_cards_enabled else '❌关闭'}",
            f"公开决斗：{'✅开启' if duel_enabled else '❌关闭'}",
            f"决斗投入范围：{duel_min} ~ {duel_max} 金币",
            f"/luck 决斗@某人 金额  (每日{duel_limit}次)",
            "/luck 确认",
            "/luck 追加投入 金额",
            "━━━━━━━━━━━━",
            "💡 看详细规则：/luck 帮助",
        ]

        yield event.plain_result("\n".join(lines))

    async def _show_help(self, event: AstrMessageEvent):
        current_config = self._last_runtime_config
        sign_enabled = current_config.get("sign_in_settings", {}).get("enable", True)
        fate_enabled = current_config.get("fate_cards_settings", {}).get("enable", True)
        func_enabled = current_config.get("func_cards_settings", {}).get("enable", True)
        dice_cards_enabled = current_config.get("func_cards_settings", {}).get("enable_dice_cards", True)
        duel_cfg = m_func_cards._get_public_duel_settings(current_config)
        duel_enabled = duel_cfg["enabled"]
        duel_limit = duel_cfg["daily_limit"]
        duel_min = duel_cfg["min_stake"]
        duel_max = duel_cfg["max_stake"]

        lines = [
            "📘 /luck 帮助（QQ版）",
            "━━━━━━━━━━━━",
            "【1. 输入规则】",
            "• 多数指令支持无空格写法",
            "• 例：使用绝对零度@某人",
            "• 决斗确认：/luck 确认",
            "• 追加投入：/luck 追加投入 金额",
            "",
            "【2. 基础玩法】",
            f"• 运势：{'开启' if sign_enabled else '关闭'}",
            f"• 抽卡：{'开启' if fate_enabled else '关闭'}",
            "• 金币榜：查看财富排行",
            "",
            "【3. 功能牌】",
            f"• 系统状态：{'开启' if func_enabled else '关闭'}",
            "• 抽取功能牌 -> 抽牌",
            "• 面板 -> 看卡槽/状态",
            "• 面板@某人 -> 查看对方个人面板",
            "• 查询 功能牌名 -> 查看这张牌的描述与自动效果说明",

            "• 查看称号 -> 看已获称号与佩戴状态",
            "• 佩戴称号 名称 -> 启用称号效果",
            "• 卸下称号 名称 -> 关闭称号效果",
            "• 使用卡名@目标 -> 出牌",
            "• 启用/停用卡名 -> 防御牌",
            "• 丢弃卡名 -> 清卡槽",
            "",
            "【4. 骰子与决斗】",
            f"• 骰子牌：{'开启' if dice_cards_enabled else '关闭'}",
            f"• 公开决斗：{'开启' if duel_enabled else '关闭'}",
            f"• 每日发起上限：{duel_limit}",
            f"• 决斗投入范围：{duel_min} ~ {duel_max} 金币",
            "• 发起指令：/luck 决斗@某人 金额",
            "• 应战确认：/luck 确认",
            "• 追加投入：/luck 追加投入 金额",
            "• 公开决斗必须双方明确确认，不会自动代打",
            "• 同时仅允许 1 场公开决斗",
            "",
            "【5. 善恶值】",
            "• 主动攻击 -> 善恶值下降",
            "• 治疗他人 -> 善恶值上升",
            "• 查看：/luck 善恶榜",
            "━━━━━━━━━━━━",
            "❓ 常见问题",
            "• 指令失败：先看对应系统是否开启",
            "• 决斗失败：可能已有人在对局，或投入超出上下限",
            "• 牌用不了：看 /luck 面板状态",
        ]

        yield event.plain_result("\n".join(lines))
