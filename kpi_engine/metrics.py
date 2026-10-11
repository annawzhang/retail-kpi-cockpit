"""按配置计算派生指标：每个指标都是 numerator / denominator。"""


def ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def derive(rows: list[dict], metric_defs: list[dict]) -> list[dict]:
    for row in rows:
        for m in metric_defs:
            row[m["id"]] = ratio(row[m["numerator"]], row[m["denominator"]])
    return rows
