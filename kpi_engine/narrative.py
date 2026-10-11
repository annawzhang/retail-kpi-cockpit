"""把诊断结果翻译成管理者可以直接转发的文字结论。"""

from collections import Counter


def pct(v: float | None) -> str:
    return "—" if v is None else f"{v:.0%}"


def region_summary(region: dict, cities: list[dict], alerts: list[dict], project: dict) -> list[str]:
    progress = project["as_of_day"] / project["days_in_month"]
    gap = round(region["target_to_date"] - region["locks"])
    month = int(project["month"][-2:])
    lines = [
        f"截至 {month} 月 {project['as_of_day']} 日，{project['region']} MTD 锁单 {region['locks']:,} 台，"
        f"月目标 {region['month_target']:,} 台；时间进度 {pct(progress)}，进度达成率 {pct(region['achievement'])}"
        + (f"，落后时间进度 {gap} 台。" if gap > 0 else "，已跑赢时间进度。")
    ]

    ranked = sorted(cities, key=lambda c: c["achievement"] or 0, reverse=True)
    best, worst = ranked[0], ranked[-1]
    lines.append(
        f"城市维度：{best['city']} 领跑（达成 {pct(best['achievement'])}），"
        f"{worst['city']} 垫底（达成 {pct(worst['achievement'])}，试驾→锁单 {pct(worst['lock_rate'])}）。"
    )

    by_priority = Counter(a["priority"] for a in alerts)
    by_cause = Counter(a["cause"] for a in alerts)
    cause_text = "、".join(f"{c} {n}" for c, n in by_cause.most_common())
    lines.append(
        f"共 {len(alerts)} 个预警单元：P1 {by_priority['P1']} / P2 {by_priority['P2']} / P3 {by_priority['P3']}；"
        f"病因分布 {cause_text}。"
    )
    return lines


def alert_sentence(alert: dict, metric_names: dict[str, str]) -> str:
    unit = alert["unit"]
    head = f"{alert['store_name']} · {alert['model']}（{alert['tier']}门店，达成 {pct(alert['achievement'])}）"
    metric = alert["metric"]
    if alert["cause"] == "数据类":
        evidence = f"数据异常：{unit['data_issues'][0]}"
    elif metric:
        evidence = (f"{metric_names[metric]} {pct(unit[metric])}，"
                    f"同层均值 {pct(unit['tier_mean'][metric])}")
    else:
        weakest = min(unit["z"], key=unit["z"].get)
        evidence = (f"多环节偏弱，最弱为{metric_names[weakest]} {pct(unit[weakest])}"
                    f"（同层均值 {pct(unit['tier_mean'][weakest])}）")
    return f"{head}：{evidence} → {alert['owner']}：{alert['action']}"
