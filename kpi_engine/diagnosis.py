"""门店分层与健康分。

大店天然销量高，全区混排会让大店垄断标兵榜、小店找不到对标对象，
因此先按销量把门店切成三层，健康分和排名都只在同层内比较。
"""

from statistics import mean, pstdev


def assign_tiers(stores: list[dict], by: str, tier_names: list[str]) -> dict[str, str]:
    ranked = sorted(stores, key=lambda s: s[by], reverse=True)
    n, k = len(ranked), len(tier_names)
    tiers = {}
    for i, s in enumerate(ranked):
        s["tier"] = tier_names[min(i * k // n, k - 1)]
        tiers[s["store_id"]] = s["tier"]
    return tiers


def score_health(rows: list[dict], weights: dict[str, float], center: float, scale: float) -> None:
    """同层内对各转化率做 Z-score，按权重加总后映射到 0–100，并记录同层均值供结论引用。

    有数据质量问题的行不进入均值和标准差的计算，健康分记为 None，避免脏数据冲上标兵榜。
    """
    by_tier: dict[str, list[dict]] = {}
    for r in rows:
        r["z"], r["tier_mean"] = {}, {}
        by_tier.setdefault(r["tier"], []).append(r)

    for tier_rows in by_tier.values():
        clean = [r for r in tier_rows if not r["data_issues"]]
        for metric in weights:
            present = [r[metric] for r in clean if r[metric] is not None]
            mu = mean(present) if present else None
            sd = pstdev(present) if len(present) > 1 else 0.0
            for r in tier_rows:
                v = r[metric]
                r["tier_mean"][metric] = mu
                r["z"][metric] = (v - mu) / sd if sd and v is not None and not r["data_issues"] else 0.0
        for r in tier_rows:
            if r["data_issues"]:
                r["health"] = None
                continue
            weighted = sum(w * r["z"][m] for m, w in weights.items())
            r["health"] = max(0.0, min(100.0, center + scale * weighted))
