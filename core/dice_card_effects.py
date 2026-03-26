from typing import Any, Dict, List, Callable


# ================= 🎲 骰子结果 -> 功能牌业务结算映射 =================
# 这里专门处理“骰子命中结果”如何转成卡牌效果。
# 目的是把“骰子规则定义”与“卡牌业务执行”再拆一层，便于后续扩展更多 op。
#
# 当前支持 payload.op:
# - sac_steal
#   参数:
#   - cost: 消耗施法者金币
#   - steal: 掠夺目标金币
#   - reserve: 施法后施法者至少保留金币（防自爆）


def apply_dice_payload(
    payload: Dict[str, Any],
    source_data: Dict[str, Any],
    target_data: Dict[str, Any],
    target_name: str,
    on_damage_reflect: Callable[[Dict[str, Any], Dict[str, Any], int], int] | None = None,
) -> List[str]:
    reports: List[str] = []

    op = (payload or {}).get("op")
    if not op:
        return reports

    if op == "sac_steal":
        cost = int(payload.get("cost", 0))
        steal_val = int(payload.get("steal", 0))
        reserve = max(0, int(payload.get("reserve", 1)))

        if source_data.get("total_gold", 0) - cost < reserve:
            reports.append(f"🩸 强夺术式失败：金币不足（需施法后至少保留 {reserve} 金币）。")
            return reports

        source_data["total_gold"] -= cost
        actual_steal = min(steal_val, max(0, target_data.get("total_gold", 0)))
        target_data["total_gold"] -= actual_steal
        source_data["total_gold"] += actual_steal

        net = actual_steal - cost
        reports.append(f"🔥 你消耗 {cost} 金币，强夺 {target_name} {actual_steal} 金币（净收益 {net:+d}）。")

        if on_damage_reflect:
            reflected = int(on_damage_reflect(source_data, target_data, actual_steal) or 0)
            if reflected > 0:
                reports.append(f"🪞 目标反甲触发！你被反震 {reflected} 金币。")

        return reports

    reports.append(f"⚠️ 未支持的骰子业务操作：{op}")
    return reports
