"""预警归因：判断每个「门店 × 车型」单元的病因、优先级和责任方。"""

PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2}


def classify(unit: dict, cfg: dict) -> dict | None:
    if unit["data_issues"]:
        cause, priority = "数据类", "P2"
    else:
        achievement = unit["achievement"] or 0.0
        if achievement >= 1.0 or unit["month_target"] < cfg["min_month_target"]:
            return None

        # 试驾样本太少时锁单率波动大，不据此判定效率类问题
        small_sample = unit["test_drives"] < cfg["min_test_drives"]
        causes = [c for c, metric in cfg["causes"].items()
                  if unit["z"][metric] < cfg["z_threshold"] and not (metric == "lock_rate" and small_sample)]

        if len(causes) > 1:
            cause = "综合类"
        elif causes:
            cause = causes[0]
        elif achievement < cfg["p1_achievement"]:
            cause = "综合类"
        else:
            return None

        if achievement < cfg["p1_achievement"]:
            priority = "P1"
        elif achievement < cfg["p2_achievement"]:
            priority = "P2"
        else:
            priority = "P3"

    return {
        "store_id": unit["store_id"],
        "store_name": unit["store_name"],
        "city": unit["city"],
        "model": unit["model"],
        "tier": unit["tier"],
        "cause": cause,
        "priority": priority,
        "owner": cfg["owners"][cause],
        "action": cfg["actions"][cause],
        "achievement": unit["achievement"],
        "metric": cfg["causes"].get(cause),
        "unit": unit,
    }


def build_alerts(units: list[dict], cfg: dict) -> list[dict]:
    alerts = [a for u in units if (a := classify(u, cfg))]
    alerts.sort(key=lambda a: (PRIORITY_ORDER[a["priority"]], a["achievement"] or 0.0))
    return alerts
