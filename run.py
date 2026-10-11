"""生成驾驶舱：python run.py [--as-of 20]"""

import argparse
import csv
from pathlib import Path

from kpi_engine import load_config, run
from kpi_engine.render import render

ROOT = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser(description="生成门店经营驾驶舱")
    parser.add_argument("--as-of", type=int, help="数据截至当月第几天，默认读配置")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "index.html")
    args = parser.parse_args()

    config = load_config(ROOT / "config" / "metrics.toml")
    if args.as_of:
        config["project"]["as_of_day"] = args.as_of
    ctx = run(config, ROOT / "data")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(ctx), encoding="utf-8")

    alerts_path = args.out.parent / "alerts.csv"
    with open(alerts_path, "w", newline="", encoding="utf-8") as f:
        fields = ["priority", "cause", "city", "store_name", "model", "tier", "achievement", "owner", "action"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for a in ctx["alerts"]:
            writer.writerow({**a, "achievement": f"{a['achievement']:.3f}" if a["achievement"] is not None else ""})

    print("\n".join(ctx["summary"]))
    print(f"\n驾驶舱 → {args.out}\n预警清单 → {alerts_path}")


if __name__ == "__main__":
    main()
