import json
import os
import asyncio
import re
from datetime import datetime, timedelta

class LuckBank:
    def __init__(self, data_path: str):
        """
        异世界中央资产管家
        :param data_path: luck_data.json 的绝对或相对路径
        """
        self.data_path = data_path
        # 核心防爆盾：异步互斥锁，防止高并发导致的 JSON 坏档
        self.lock = asyncio.Lock()
        # 内存驻留字典：所有的数据结算都在极速内存中完成
        self._data = {}
        
        # 启动时自动执行数据挂载与静默热更新
        self._load_and_migrate_sync()

    def _parse_battle_log_time(self, log_entry: str, now: datetime) -> datetime | None:
        """解析形如 [MM-DD HH:MM] 的战报时间，自动处理跨年边界。"""
        match = re.match(r"^\[(\d{2})-(\d{2})\s+(\d{2}):(\d{2})\]", log_entry)
        if not match:
            return None

        month, day, hour, minute = map(int, match.groups())
        try:
            dt = datetime(now.year, month, day, hour, minute)
        except ValueError:
            return None

        # 跨年兜底：若解析后“晚于当前时间太多”，视为上一年日志
        if dt > now + timedelta(days=1):
            try:
                dt = dt.replace(year=dt.year - 1)
            except ValueError:
                return None

        return dt

    def _prune_battle_logs(self, user_info: dict, days: int = 3, now: datetime | None = None) -> bool:
        """仅保留最近 N 天战报。返回是否发生变更。"""
        if now is None:
            now = datetime.now()

        logs = user_info.get("battle_logs", [])
        if not logs:
            return False

        cutoff = now - timedelta(days=days)
        new_logs = []
        for entry in logs:
            log_time = self._parse_battle_log_time(entry, now)
            # 无法识别时间格式的旧日志也一并清理，避免永久残留
            if log_time and log_time >= cutoff:
                new_logs.append(entry)

        if len(new_logs) != len(logs):
            user_info["battle_logs"] = new_logs
            return True
        return False

    def _load_and_migrate_sync(self):
        """同步加载数据并执行老版本向下兼容的静默升级"""
        if os.path.exists(self.data_path):
            try:
                # 死焊 utf-8 编码，防止 Linux 容器环境乱码
                with open(self.data_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception as e:
                print(f"[LuckBank] ⚠️ 档案读取异常，可能文件损坏，已初始化为空: {e}")
                self._data = {}
        else:
            self._data = {}

        # 核心：静默热更新老用户档案
        migrated = False
        for uid, info in self._data.items():
            # 旧字段迁移：total_score -> total_gold
            if "total_gold" not in info:
                info["total_gold"] = info.pop("total_score", 0)
                migrated = True
            elif "total_score" in info:
                info.pop("total_score", None)
                migrated = True

            # 旧字段迁移：last_drawn_value -> last_drawn_gold
            if "last_drawn_gold" not in info:
                info["last_drawn_gold"] = info.pop("last_drawn_value", 0)
                migrated = True
            elif "last_drawn_value" in info:
                info.pop("last_drawn_value", None)
                migrated = True

            # 为老用户自动补齐缺失的新纪元字段
            if "inventory" not in info:
                info["inventory"] = []
                migrated = True
            if "statuses" not in info:
                info["statuses"] = []
                migrated = True
            if "karma_value" not in info:
                info["karma_value"] = 0  # 单轴善恶值：正善负恶
                migrated = True
            if "func_card_pity_count" not in info:
                info["func_card_pity_count"] = 0 # 10次保底进度
                migrated = True
            if "battle_logs" not in info:
                info["battle_logs"] = [] # 战报总库
                migrated = True
            if "recent_drawn_cards" not in info:
                info["recent_drawn_cards"] = []  # 近期出牌记录（去重用）
                migrated = True
            
            # 战报保鲜：只保留最近 3 天
            if self._prune_battle_logs(info, days=3):
                migrated = True
                
        # 如果发现了老用户并打了补丁，立刻落盘保存
        if migrated:
            self._save_data_sync()

    def _save_data_sync(self):
        """底层写入方法，调用前必须确保已上锁"""
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=4)

    # ================= 🏦 外部调用 API 接口 =================

    async def get_user_data(self, user_id: str, user_name: str) -> dict:
        """
        获取用户档案。如果是新入群玩家，自动初始化完整结构。
        """
        async with self.lock:
            if user_id not in self._data:
                self._data[user_id] = {
                    "name": user_name,
                    "total_gold": 0,
                    "last_date": "",
                    "last_card_date": "",
                    "last_card_draw_count": 0,
                    "last_drawn_gold": 0,
                    "inventory": [],
                    "statuses": [],
                    "karma_value": 0,
                    "func_card_pity_count": 0,
                    "battle_logs": [],
                    "recent_drawn_cards": []
                }
                self._save_data_sync()
            else:
                # 兜底迁移：防止历史脏数据在运行期进入
                if "total_gold" not in self._data[user_id]:
                    self._data[user_id]["total_gold"] = self._data[user_id].pop("total_score", 0)
                else:
                    self._data[user_id].pop("total_score", None)

                if "last_drawn_gold" not in self._data[user_id]:
                    self._data[user_id]["last_drawn_gold"] = self._data[user_id].pop("last_drawn_value", 0)
                else:
                    self._data[user_id].pop("last_drawn_value", None)

                # 动态更新可能更改的群名片
                self._data[user_id]["name"] = user_name

                # 战报保鲜：只保留最近 3 天
                if self._prune_battle_logs(self._data[user_id], days=3):
                    self._save_data_sync()
            return self._data[user_id]

    async def save_user_data(self):
        """
        手动触发保存（供外部模块修改 inventory 等复杂对象后调用）
        """
        async with self.lock:
            self._save_data_sync()

    async def change_gold(self, user_id: str, amount: int) -> bool:
        """
        安全结算金币。
        :return: bool 是否扣款成功（如果是扣钱且余额不足，返回 False 拦截防贷款）
        """
        async with self.lock:
            if user_id not in self._data:
                return False  # 未注册用户拒绝结算

            current_gold = self._data[user_id].get("total_gold", 0)

            # 防贷款校验：如果是扣除金币，且扣除后小于0，拒绝执行
            if amount < 0 and current_gold < abs(amount):
                return False

            self._data[user_id]["total_gold"] += amount
            self._save_data_sync()
            return True

    # 兼容旧代码调用（后续可移除）
    async def change_score(self, user_id: str, amount: int) -> bool:
        return await self.change_gold(user_id, amount)

    async def add_karma(self, user_id: str, amount: int):
        """增减善恶值（正为善，负为恶）"""
        async with self.lock:
            if user_id in self._data:
                self._data[user_id]["karma_value"] += amount
                self._save_data_sync()

    async def log_battle(self, user_id: str, message: str):
        """
        记录战报，并自动清理 3 天前的旧日志
        """
        async with self.lock:
            if user_id in self._data:
                now_dt = datetime.now()
                time_str = now_dt.strftime("%m-%d %H:%M")
                log_entry = f"[{time_str}] {message}"
                
                self._data[user_id]["battle_logs"].append(log_entry)

                # 只保留最近 3 天战报
                self._prune_battle_logs(self._data[user_id], days=3, now=now_dt)
                
                self._save_data_sync()

    async def get_all_users(self) -> dict:
        """获取全量排名数据（供排行榜只读调用）"""
        async with self.lock:
            # 返回一个浅拷贝，防止外部直接污染内存数据
            return self._data.copy()