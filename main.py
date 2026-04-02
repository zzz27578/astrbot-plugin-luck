import os
import re
import json
import asyncio
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import *
from .modules.m_sign_in import handle_sign_in, handle_leaderboard

# ================= 🔌 核心底座与模块导入 =================
from .core.luck_bank import LuckBank
from .core.plugin_storage import PLUGIN_NAME, migrate_legacy_storage
from .modules import m_sign_in, m_fate_cards, m_func_cards
from .webui.server import start_webui


RUNTIME_CONFIG_FILE = str(migrate_legacy_storage(PLUGIN_NAME)["runtime_config_file"])


def _deep_merge_dict(base: dict, override: dict) -> dict:
    result = dict(base or {})
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge_dict(result[k], v)
        else:
            result[k] = v
    return result


def _load_runtime_override() -> dict:
    if not os.path.exists(RUNTIME_CONFIG_FILE):
        return {}
    try:
        with open(RUNTIME_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

PLUGIN_NAME = "luck_rank"
AUTHOR = "YourName" # 可修改为你自己的名字
VERSION = "5.3.0-Pro"

@register(PLUGIN_NAME, AUTHOR, "异世界战术金币系统", VERSION)
class LuckPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.storage_paths = migrate_legacy_storage(self.name or PLUGIN_NAME)
        self._base_config = config or {}
        runtime_override = _load_runtime_override()
        self.config = _deep_merge_dict(self._base_config, runtime_override)

        # 激活金币管家，账本放到 AstrBot 官方隔离数据区
        self.bank = LuckBank(str(self.storage_paths["luck_data_file"]))

        # 启动 WebUI，用独立进程跑，和主程序完全隔离
        self._webui_process = None
        webui_cfg = self.config.get("webui_settings", {})
        if webui_cfg.get("enable", False):
            webui_port = int(webui_cfg.get("port", 4399) or 4399)
            from multiprocessing import Process
            from .webui.server import run_server_process
            self._webui_process = Process(
                target=run_server_process,
                args=(webui_port,),
                daemon=True
            )
            self._webui_process.start()
            print(f"[WebUI] 管理界面已在独立进程启动，端口：{webui_port}")

    def _refresh_runtime_config(self):
        """每次处理指令前重新读取运行时覆盖配置，让大多数业务参数可热更新。"""
        runtime_override = _load_runtime_override()
        self.config = _deep_merge_dict(self._base_config, runtime_override)

    # 🟢 绝对前缀拦截器：只认 /luck，无视后面的空格
    @filter.regex(r"^/luck\s*(.*)$", priority=1000)
    async def luck_gateway(self, event: AstrMessageEvent):
        # 第一时间阻断事件，防止底层聊天 AI 抢答
        event.stop_event()
        self._refresh_runtime_config()
        
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        
        # 提取纯净指令
        match = re.match(r"^/luck\s*(.*)$", event.get_message_str())
        cmd_str = match.group(1).strip() if match else ""
        func_cards_enabled = self.config.get("func_cards_settings", {}).get("enable", True)

        # ================= 🚧 0. 功能牌总开关统一拦截 =================
        if not func_cards_enabled and self._is_func_cards_command(cmd_str):
            yield event.plain_result("⚠️ 战术功能牌系统未开启，请先在配置中开启 func_cards_settings.enable。")
            return

        # ================= 👑 1. 天道管理员特权路由 =================
        if cmd_str.startswith("增加"):
            async for res in self._handle_admin_add(event, user_id, cmd_str):
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

        # ================= 📜 3. 基础运势签到路由 =================
        if re.match(r"^(运势|签到|今日运势|jrrp)$", cmd_str):
            if not self.config.get("sign_in_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 异世界星象观测台今日维护，基础签到暂未开放。")
                return
            async for res in handle_sign_in(event, self.bank, self.config):
                yield res
            return

       # ================= 🏆 4. 风云排行榜路由 =================
        if re.match(r"^(排行榜|金币榜|财富榜|气运榜|运势榜)$", cmd_str):
            board_length = self.config.get("ui_settings", {}).get("board_length", 10)
            async for res in m_sign_in.handle_leaderboard(event, self.bank, board_length):
                yield res
            return

        if cmd_str == "善恶榜":
            if not self.config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            board_length = self.config.get("ui_settings", {}).get("board_length", 10)
            async for res in m_func_cards.handle_karma_leaderboard(event, self.bank, board_length):
                yield res
            return

        # ================= 🎴 5. 命运牌抽换路由 =================
        if re.match(r"^(幸运牌|抽牌|抽卡|命运卡牌|换牌|换一张|换一张牌)$", cmd_str):
            if not self.config.get("fate_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 命运卡牌池已被天道封锁，暂未开放。")
                return
            
            max_limit = self.config.get("fate_cards_settings", {}).get("daily_draw_limit", 3)
            async for res in m_fate_cards.handle_fate_card_draw(event, self.bank, max_limit):
                yield res
            return

        # ================= ⚔️ 6. 战术功能牌路由 =================
        if cmd_str == "面板":
            if not self.config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放，面板无法观测。")
                return
            async for res in m_func_cards.handle_panel(event, self.bank, self.config):
                yield res
            return
            
        if cmd_str == "抽取功能牌":
            if not self.config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            # 替换成调用真实的抽卡引擎
            async for res in m_func_cards.handle_draw_func_card(event, self.bank, self.config):
                yield res
            return

        # ================= 🗑️ 7. 丢弃卡牌路由 =================
        if cmd_str.startswith("丢弃"):
            if not self.config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            target_card = cmd_str.replace("丢弃", "").strip()
            async for res in m_func_cards.handle_discard_card(event, self.bank, target_card):
                yield res
            return

        # ================= ⚔️ 8. 核心干涉引擎 =================
        if cmd_str.startswith("使用"):
            if not self.config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_use_card(event, self.bank, cmd_str, self.config):
                yield res
            return

        if cmd_str.startswith("对赌"):
            if not self.config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_pure_duel(event, self.bank, self.config):
                yield res
            return

        if cmd_str == "确认":
            if not self.config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_confirm_duel(event, self.bank):
                yield res
            return

        if cmd_str.startswith("加注"):
            if not self.config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_raise_duel(event, self.bank):
                yield res
            return

        if cmd_str.startswith("启用"):
            if not self.config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_active_card(event, self.bank, cmd_str, True):
                yield res
            return

        if cmd_str.startswith("停用"):
            if not self.config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术博弈系统暂未开放。")
                return
            async for res in m_func_cards.handle_active_card(event, self.bank, cmd_str, False):
                yield res
            return

        # ================= 🚫 兜底处理 =================
        yield event.plain_result(f"❓ 未知的异界法术：{cmd_str}\n发送「/luck 菜单」查看可用口令。")

    def _is_func_cards_command(self, cmd_str: str) -> bool:
        """判断是否为功能牌相关指令（用于总开关统一拦截）。"""
        if not cmd_str:
            return False

        exact_cmds = {"善恶榜", "面板", "抽取功能牌", "功能牌", "确认"}
        if cmd_str in exact_cmds:
            return True

        if cmd_str.startswith(("丢弃", "使用", "启用", "停用", "对赌", "加注")):
            return True

        return False

   # ---------------- 👑 管理员私有方法 ----------------
    async def _handle_admin_add(self, event: AstrMessageEvent, sender_id: str, cmd_str: str):
        # 1. 权限校验 (动态读取，安全开源版)
        is_admin = False
        
        # 兼容 AstrBot 面板的两种数据保存格式 (嵌套结构 vs 扁平结构)
        admin_cfg = self.config.get("admin_settings", {})
        
        # 灵活提取：优先从嵌套结构取，如果没有，则退化到根节点取
        extra_admins_str = admin_cfg.get("extra_admin_qqs") or self.config.get("extra_admin_qqs", "")
        
        # 安全拆分：支持中英文逗号，自动过滤空格和空字符
        extra_admins_str = str(extra_admins_str).replace("，", ",")
        extra_admins = [qq.strip() for qq in extra_admins_str.split(",") if qq.strip()]
        
        if sender_id in extra_admins:
            is_admin = True
        
        if not is_admin:
            yield event.plain_result("⚡ 狂妄！你未拥有天道权限，无法篡改世界线！")
            return

        # 2. 解析目标: 必须包含 @ 某人
        target_id = None
        target_name = ""
        for comp in event.get_messages():
            if isinstance(comp, At):
                target_id = str(comp.qq)
                target_name = f"群友({target_id})"
                break
                
        if not target_id:
            yield event.plain_result("⚠️ 天道法则施放失败：必须 @ 一个明确的目标玩家。")
            return

        # 3. 解析类型和数量 (支持正负数)
        raw_text = event.message_str.replace("/luck", "").replace("增加", "").strip()
        raw_text = re.sub(r"@\S+", "", raw_text).strip()
        
        match = re.search(r"(命运牌|功能牌|金币|气运|运势)\s*(-?\d+)", raw_text)
        if not match:
            yield event.plain_result("⚠️ 参数解析失败。\n正确格式：\n/luck 增加 @某人 命运牌 3\n/luck 增加 @某人 功能牌 1\n/luck 增加 @某人 金币 50 (或 -50)")
            return
            
        card_type = match.group(1)
        add_count = int(match.group(2))

        # 4. 调取档案并执行“资产篡改”
        user_data = await self.bank.get_user_data(target_id, target_name)
        
        if card_type == "命运牌":
            current_drawn = user_data.get("last_card_draw_count", 0)
            user_data["last_card_draw_count"] = current_drawn - add_count
            await self.bank.save_user_data()
            yield event.plain_result(f"✅ 天道意志降临！\n已为 {target_name} 补充了 {add_count} 次【命运牌】换牌机会！")
            
        elif card_type == "功能牌":
            if not self.config.get("func_cards_settings", {}).get("enable", True):
                yield event.plain_result("⚠️ 战术功能牌系统未开启，无法调整功能牌次数。")
                return
            current_free = user_data.get("today_free_draws", 0)
            user_data["today_free_draws"] = current_free + add_count
            await self.bank.save_user_data()
            yield event.plain_result(f"✅ 天赐机缘！\n已为 {target_name} 额外发放了 {add_count} 次【功能牌】免费抽取机会！")
            
        elif card_type in ["金币", "气运", "运势"]:
            current_gold = user_data.get("total_gold", 0)
            user_data["total_gold"] = current_gold + add_count
            await self.bank.save_user_data()
            
            # 根据正负数动态改变文案
            action_str = "增加" if add_count >= 0 else "剥夺"
            abs_count = abs(add_count)
            yield event.plain_result(f"⚡ 天道裁决！\n已强行 {action_str} {target_name} {abs_count} 枚金币！\n💰 当前金币：{user_data['total_gold']}")

    # ---------------- 📖 纯文本视图方法 ----------------
    async def _show_menu(self, event: AstrMessageEvent):
        sign_enabled = self.config.get("sign_in_settings", {}).get("enable", True)
        fate_enabled = self.config.get("fate_cards_settings", {}).get("enable", True)
        func_enabled = self.config.get("func_cards_settings", {}).get("enable", True)
        dice_cards_enabled = self.config.get("func_cards_settings", {}).get("enable_dice_cards", True)
        duel_cfg = self.config.get("func_cards_settings", {})
        duel_enabled = duel_cfg.get("enable_public_duel_mode", duel_cfg.get("enable_pure_dice_mode", False))
        duel_limit = int(duel_cfg.get("public_duel_daily_limit", duel_cfg.get("pure_dice_daily_limit", 3)) or 3)
        duel_min = int(duel_cfg.get("public_duel_min_stake", 10) or 10)
        duel_max = int(duel_cfg.get("public_duel_max_stake", 200) or 200)

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
            "/luck 善恶榜",
            "/luck 使用卡名@某人",
            "/luck 使用卡名随机",
            "/luck 启用卡名",
            "/luck 停用卡名",
            "/luck 丢弃卡名",
            "",
            "【骰子 / 对赌】",
            f"骰子功能牌：{'✅开启' if dice_cards_enabled else '❌关闭'}",
            f"公开对赌：{'✅开启' if duel_enabled else '❌关闭'}",
            f"赌注范围：{duel_min} ~ {duel_max} 金币",
            f"/luck 对赌@某人 金额  (每日{duel_limit}次)",
            "/luck 确认",
            "/luck 加注 金额",
            "━━━━━━━━━━━━",
            "💡 看详细规则：/luck 帮助",
        ]

        yield event.plain_result("\n".join(lines))

    async def _show_help(self, event: AstrMessageEvent):
        sign_enabled = self.config.get("sign_in_settings", {}).get("enable", True)
        fate_enabled = self.config.get("fate_cards_settings", {}).get("enable", True)
        func_enabled = self.config.get("func_cards_settings", {}).get("enable", True)
        dice_cards_enabled = self.config.get("func_cards_settings", {}).get("enable_dice_cards", True)
        duel_cfg = self.config.get("func_cards_settings", {})
        duel_enabled = duel_cfg.get("enable_public_duel_mode", duel_cfg.get("enable_pure_dice_mode", False))
        duel_limit = int(duel_cfg.get("public_duel_daily_limit", duel_cfg.get("pure_dice_daily_limit", 3)) or 3)
        duel_min = int(duel_cfg.get("public_duel_min_stake", 10) or 10)
        duel_max = int(duel_cfg.get("public_duel_max_stake", 200) or 200)

        lines = [
            "📘 /luck 帮助（QQ版）",
            "━━━━━━━━━━━━",
            "【1. 输入规则】",
            "• 多数指令支持无空格写法",
            "• 例：使用绝对零度@某人",
            "• 对赌接受：/luck 确认",
            "• 对赌抬注：/luck 加注 金额",
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
            "• 使用卡名@目标 -> 出牌",
            "• 启用/停用卡名 -> 防御牌",
            "• 丢弃卡名 -> 清卡槽",
            "",
            "【4. 骰子与对赌】",
            f"• 骰子牌：{'开启' if dice_cards_enabled else '关闭'}",
            f"• 公开对赌：{'开启' if duel_enabled else '关闭'}",
            f"• 每日发起上限：{duel_limit}",
            f"• 赌注范围：{duel_min} ~ {duel_max} 金币",
            "• 发起指令：/luck 对赌@某人 金额",
            "• 接受指令：/luck 确认",
            "• 加注指令：/luck 加注 金额",
            "• 免费公开局必须双方明确确认，不会自动代打",
            "• 同时仅允许1场公开局",
            "",
            "【5. 善恶值】",
            "• 主动攻击 -> 善恶值下降",
            "• 治疗他人 -> 善恶值上升",
            "• 查看：/luck 善恶榜",
            "━━━━━━━━━━━━",
            "❓ 常见问题",
            "• 指令失败：先看对应系统是否开启",
            "• 对赌失败：可能已有人在对局，或赌注超出上下限",
            "• 牌用不了：看 /luck 面板状态",
        ]

        yield event.plain_result("\n".join(lines))