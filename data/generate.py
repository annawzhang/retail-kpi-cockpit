"""生成虚构的「门店 × 车型」日度漏斗数据。

所有门店、城市分布、转化率与目标均由固定随机种子生成，不含任何真实业务数据。
"""

import csv
import random
from pathlib import Path

SEED = 42
MONTH = "2026-09"
DAYS = 30
BASE_TRAFFIC = 90

CITIES = {"杭州": 7, "宁波": 6, "苏州": 6, "南京": 6, "无锡": 5, "温州": 4}
MODELS = {"旗舰SUV": 0.30, "家庭SUV": 0.35, "纯电轿车": 0.20, "MPV": 0.15}
BASE_RATE = {"lead": 0.45, "td": 0.38, "lock": 0.26}

# 注入的经营问题：问题类型 -> (受影响的转化环节, 转化率乘数)
ISSUES = {"渠道": ("lead", 0.65), "跟进": ("td", 0.60), "效率": ("lock", 0.55)}
ISSUE_PROB = 0.2


def binom(rng: random.Random, n: int, p: float) -> int:
    return sum(rng.random() < p for _ in range(n))


def build_stores(rng: random.Random) -> list[dict]:
    stores = []
    for city, count in CITIES.items():
        for i in range(1, count + 1):
            store = {
                "store_id": f"S{len(stores) + 1:03d}",
                "store_name": f"{city}{i}号店",
                "city": city,
                "size": rng.uniform(0.4, 1.6),
                "rate_mult": {k: rng.uniform(0.88, 1.12) for k in BASE_RATE},
                "issue": None,
                "issue_models": [],
            }
            if rng.random() < ISSUE_PROB:
                store["issue"] = rng.choice(list(ISSUES))
                store["issue_models"] = rng.sample(list(MODELS), k=rng.choice([1, 2, 4]))
            stores.append(store)
    return stores


def main(out_dir: Path) -> None:
    rng = random.Random(SEED)
    stores = build_stores(rng)
    out_dir.mkdir(parents=True, exist_ok=True)

    daily_rows, target_rows = [], []
    for s in stores:
        for model, share in MODELS.items():
            rates = {k: BASE_RATE[k] * s["rate_mult"][k] for k in BASE_RATE}
            expected = BASE_TRAFFIC * s["size"] * share * rates["lead"] * rates["td"] * rates["lock"] * DAYS
            target_rows.append({
                "store_id": s["store_id"],
                "model": model,
                "month_target": max(1, round(expected * rng.uniform(0.95, 1.1))),
            })

            if s["issue"] and model in s["issue_models"]:
                stage, mult = ISSUES[s["issue"]]
                rates[stage] *= mult

            for day in range(1, DAYS + 1):
                traffic = max(0, round(BASE_TRAFFIC * s["size"] * share * rng.gauss(1, 0.15)))
                leads = binom(rng, traffic, rates["lead"])
                test_drives = binom(rng, leads, rates["td"])
                locks = binom(rng, test_drives, rates["lock"])
                daily_rows.append({
                    "date": f"{MONTH}-{day:02d}",
                    "city": s["city"],
                    "store_id": s["store_id"],
                    "store_name": s["store_name"],
                    "model": model,
                    "traffic": traffic,
                    "leads": leads,
                    "test_drives": test_drives,
                    "locks": locks,
                })

    # 模拟一次重复导入：锁单数大于试驾数，用于验证数据质量校验
    glitch = next(r for r in daily_rows if r["store_id"] == "S011" and r["model"] == "家庭SUV" and r["date"].endswith("-12"))
    glitch["locks"] = glitch["test_drives"] + 40

    with open(out_dir / "daily_funnel.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(daily_rows[0]))
        writer.writeheader()
        writer.writerows(daily_rows)
    with open(out_dir / "targets.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(target_rows[0]))
        writer.writeheader()
        writer.writerows(target_rows)

    print(f"生成 {len(stores)} 家门店 · {len(daily_rows)} 行日度数据 → {out_dir}")


if __name__ == "__main__":
    main(Path(__file__).parent)
