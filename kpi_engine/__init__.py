"""kpi_engine：零售门店经营诊断引擎。"""

import tomllib
from pathlib import Path

from .alerts import build_alerts
from .data import load_units, rollup
from .diagnosis import assign_tiers, score_health
from .metrics import derive
from .narrative import region_summary


def load_config(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def run(config: dict, data_dir: Path) -> dict:
    project = config["project"]
    units = load_units(data_dir / "daily_funnel.csv", data_dir / "targets.csv",
                       project["as_of_day"], project["days_in_month"])
    metric_defs = config["metrics"]
    health = config["health"]

    stores = derive(rollup(units, "store_id"), metric_defs)
    cities = derive(rollup(units, "city"), metric_defs)
    region = derive([_total(units)], metric_defs)[0]
    derive(units, metric_defs)

    tiers = assign_tiers(stores, health["tier_by"], health["tiers"])
    for u in units:
        u["tier"] = tiers[u["store_id"]]
    score_health(stores, health["weights"], health["center"], health["scale"])
    score_health(units, health["weights"], health["center"], health["scale"])

    alerts = build_alerts(units, config["alerts"])
    models = list(dict.fromkeys(u["model"] for u in units))
    return {
        "config": config,
        "project": project,
        "units": units,
        "stores": stores,
        "cities": cities,
        "region": region,
        "alerts": alerts,
        "models": models,
        "summary": region_summary(region, cities, alerts, project),
    }


def _total(units: list[dict]) -> dict:
    keys = ("traffic", "leads", "test_drives", "locks", "month_target", "target_to_date")
    return {k: sum(u[k] for u in units) for k in keys}
