import time
from typing import Any, Dict, Iterable, Optional

# ================= 统一逻辑门定义 =================
GATE_DRAW_FATE_CARD = "draw_fate_card"
GATE_DRAW_FUNC_CARD = "draw_func_card"
GATE_USE_CARD = "use_card"
GATE_TOGGLE_CARD = "toggle_card"


GATE_LABELS = {
    GATE_DRAW_FATE_CARD: "抽取命运牌",
    GATE_DRAW_FUNC_CARD: "抽取功能牌",
    GATE_USE_CARD: "使用功能牌",
    GATE_TOGGLE_CARD: "启用/停用功能牌",
}


def _is_status_active(status: Dict[str, Any], now: int) -> bool:
    expire_time = status.get("expire_time")
    if expire_time is None:
        return True
    return now < int(expire_time)


def find_gate_block(user_data: Dict[str, Any], gate_name: str, now: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """检查某个逻辑门是否被阻断。命中时返回对应状态对象。"""
    if now is None:
        now = int(time.time())

    statuses: Iterable[Dict[str, Any]] = user_data.get("statuses", [])
    for status in statuses:
        if not _is_status_active(status, now):
            continue

        blocked = set(status.get("block_actions", []))
        if gate_name in blocked:
            return status

    return None


def format_gate_block_message(status: Dict[str, Any], default_msg: str) -> str:
    """优先使用状态自定义阻断文案；无则返回默认文案。"""
    return status.get("block_msg") or default_msg
