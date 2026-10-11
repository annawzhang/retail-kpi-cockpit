"""读取日度漏斗数据，按「门店 × 车型」汇总月初至今（MTD）原子指标，并做数据质量校验。"""

import csv
from pathlib import Path

ATOMIC = ("traffic", "leads", "test_drives", "locks")
# 漏斗上下游关系：下游数量不应超过上游
FUNNEL_CHECKS = (("leads", "traffic"), ("test_drives", "leads"), ("locks", "test_drives"))


def load_units(daily_path: Path, targets_path: Path, as_of_day: int, days_in_month: int) -> list[dict]:
    targets = {}
    with open(targets_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            targets[(r["store_id"], r["model"])] = int(r["month_target"])

    units: dict[tuple, dict] = {}
    with open(daily_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            day = int(r["date"][-2:])
            if day > as_of_day:
                continue
            key = (r["store_id"], r["model"])
            unit = units.get(key)
            if unit is None:
                unit = units[key] = {
                    "store_id": r["store_id"],
                    "store_name": r["store_name"],
                    "city": r["city"],
                    "model": r["model"],
                    "data_issues": [],
                    **{k: 0 for k in ATOMIC},
                }
            values = {k: int(r[k]) for k in ATOMIC}
            for down, up in FUNNEL_CHECKS:
                if values[down] > values[up]:
                    unit["data_issues"].append(f"{r['date']} {down}({values[down]}) > {up}({values[up]})")
            for k in ATOMIC:
                unit[k] += values[k]

    progress = as_of_day / days_in_month
    for key, unit in units.items():
        unit["month_target"] = targets.get(key, 0)
        unit["target_to_date"] = unit["month_target"] * progress
    return list(units.values())


def rollup(units: list[dict], by: str) -> list[dict]:
    """把「门店 × 车型」单元汇总到门店或城市层级。"""
    groups: dict[str, dict] = {}
    for u in units:
        g = groups.get(u[by])
        if g is None:
            g = groups[u[by]] = {by: u[by], "city": u["city"], "data_issues": [],
                                 **{k: 0 for k in (*ATOMIC, "month_target", "target_to_date")}}
            if by == "store_id":
                g["store_name"] = u["store_name"]
        for k in (*ATOMIC, "month_target", "target_to_date"):
            g[k] += u[k]
        g["data_issues"] += u["data_issues"]
    return list(groups.values())
