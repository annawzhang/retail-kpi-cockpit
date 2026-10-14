"""把诊断结果渲染成单文件 HTML 驾驶舱（内联 SVG 图表，无外部依赖，可直接托管到 GitHub Pages）。"""

from html import escape

from .narrative import alert_sentence, pct

PRIORITY_COLOR = {"P1": "#dc2626", "P2": "#ea580c", "P3": "#ca8a04"}

CSS = """
:root { --text:#0f172a; --muted:#64748b; --border:#e2e8f0; --accent:#2563eb; --bg:#f8fafc; }
* { box-sizing:border-box; }
body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
       background:var(--bg); color:var(--text); }
.wrap { max-width:1180px; margin:0 auto; padding:32px 24px 48px; }
header h1 { margin:0 0 6px; font-size:1.6rem; }
.meta { color:var(--muted); font-size:0.88rem; }
.badge { display:inline-block; margin-left:8px; padding:2px 8px; border-radius:999px;
         background:#fef3c7; color:#92400e; font-size:0.75rem; }
h2 { font-size:1.05rem; margin:32px 0 12px; }
.grid { display:grid; gap:16px; }
.g4 { grid-template-columns:repeat(4,1fr); }
.g2 { grid-template-columns:repeat(2,1fr); }
.g3 { grid-template-columns:repeat(3,1fr); }
@media (max-width:860px) { .g4,.g3,.g2 { grid-template-columns:1fr; } }
.card { background:#fff; border:1px solid var(--border); border-radius:12px; padding:18px; }
.kpi .label { color:var(--muted); font-size:0.8rem; }
.kpi .value { font-size:1.7rem; font-weight:700; margin-top:6px; }
.kpi .sub { color:var(--muted); font-size:0.78rem; margin-top:4px; }
.summary li { line-height:1.8; font-size:0.9rem; }
.actions li { line-height:1.7; font-size:0.86rem; margin-bottom:6px; }
table { width:100%; border-collapse:collapse; font-size:0.82rem; }
th, td { text-align:left; padding:7px 8px; border-bottom:1px solid var(--border); }
th { color:var(--muted); font-weight:600; }
.tag { display:inline-block; padding:1px 7px; border-radius:6px; color:#fff; font-size:0.74rem; }
.heat td { text-align:center; padding:5px; font-size:0.76rem; }
.heat td.name { text-align:left; }
.scroll { max-height:520px; overflow:auto; }
footer { margin-top:40px; color:var(--muted); font-size:0.78rem; }
"""


def heat_color(score: float) -> str:
    # 0 分红、50 分白、100 分绿
    if score < 50:
        t = score / 50
        r, g, b = 220, round(38 + (255 - 38) * t), round(38 + (255 - 38) * t)
    else:
        t = (score - 50) / 50
        r, g, b = round(255 - (255 - 22) * t), round(255 - (255 - 163) * t), round(255 - (255 - 74) * t)
    return f"rgb({r},{g},{b})"


def funnel_svg(region: dict) -> str:
    stages = [("进店", "traffic"), ("留资", "leads"), ("试驾", "test_drives"), ("锁单", "locks")]
    top = region["traffic"] or 1
    width, bar_h, gap = 520, 34, 18
    parts = [f'<svg viewBox="0 0 {width} {4 * (bar_h + gap)}" width="100%">']
    for i, (label, key) in enumerate(stages):
        w = max(4, (width - 160) * region[key] / top)
        y = i * (bar_h + gap)
        x = (width - 160 - w) / 2 + 60
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="6" fill="#2563eb" opacity="{1 - i * 0.18:.2f}"/>')
        parts.append(f'<text x="0" y="{y + 22}" font-size="13" fill="#0f172a">{label}</text>')
        parts.append(f'<text x="{width - 95}" y="{y + 22}" font-size="13" fill="#0f172a">{region[key]:,}</text>')
        if i:
            prev = region[stages[i - 1][1]]
            parts.append(f'<text x="{width - 40}" y="{y + 22}" font-size="11" fill="#64748b">{pct(region[key] / prev if prev else None)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def city_bar_svg(cities: list[dict]) -> str:
    ranked = sorted(cities, key=lambda c: c["achievement"] or 0, reverse=True)
    width, row_h = 520, 30
    max_v = max(1.2, max((c["achievement"] or 0) for c in ranked))
    plot_w = width - 120
    line_x = 60 + plot_w * 1.0 / max_v
    parts = [f'<svg viewBox="0 0 {width} {len(ranked) * row_h + 20}" width="100%">']
    for i, c in enumerate(ranked):
        v = c["achievement"] or 0
        y = i * row_h
        color = "#16a34a" if v >= 1 else ("#ea580c" if v >= 0.85 else "#dc2626")
        parts.append(f'<text x="0" y="{y + 19}" font-size="13">{escape(c["city"])}</text>')
        parts.append(f'<rect x="60" y="{y + 5}" width="{plot_w * v / max_v:.1f}" height="18" rx="4" fill="{color}"/>')
        parts.append(f'<text x="{66 + plot_w * v / max_v:.1f}" y="{y + 19}" font-size="12" fill="#334155">{pct(v)}</text>')
    h = len(ranked) * row_h
    parts.append(f'<line x1="{line_x:.1f}" y1="0" x2="{line_x:.1f}" y2="{h}" stroke="#0f172a" stroke-dasharray="4 3"/>')
    parts.append(f'<text x="{line_x - 34:.1f}" y="{h + 14}" font-size="11" fill="#64748b">时间进度线</text>')
    parts.append("</svg>")
    return "".join(parts)


def health_cell(row: dict, bold: bool = False) -> str:
    if row["health"] is None:
        return '<td style="background:#e2e8f0;color:#475569">⚠ 待核</td>'
    text = f"<strong>{row['health']:.0f}</strong>" if bold else f"{row['health']:.0f}"
    return f'<td style="background:{heat_color(row["health"])}">{text}</td>'


def heatmap_table(stores: list[dict], units: list[dict], models: list[str], tiers: list[str]) -> str:
    cell = {(u["store_id"], u["model"]): u for u in units}
    order = {t: i for i, t in enumerate(tiers)}
    rows = []
    for s in sorted(stores, key=lambda s: (order[s["tier"]], -(s["health"] if s["health"] is not None else -1))):
        tds = []
        for m in models:
            u = cell.get((s["store_id"], m))
            tds.append(health_cell(u) if u else "<td>—</td>")
        rows.append(f'<tr><td class="name">{escape(s["store_name"])}</td><td>{s["tier"]}</td>'
                    f'{health_cell(s, bold=True)}{"".join(tds)}</tr>')
    head = "".join(f"<th>{escape(m)}</th>" for m in models)
    return (f'<table class="heat"><thead><tr><th>门店</th><th>层级</th><th>门店健康分</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def tier_boards(stores: list[dict], tiers: list[str]) -> str:
    cards = []
    for tier in tiers:
        in_tier = [s for s in stores if s["tier"] == tier]
        members = sorted((s for s in in_tier if s["health"] is not None), key=lambda s: s["health"], reverse=True)
        excluded = [s["store_name"] for s in in_tier if s["health"] is None]
        note = (f'<div class="meta" style="margin-top:8px">数据待核，暂不参与排名：{escape("、".join(excluded))}</div>'
                if excluded else "")
        def rows(items):
            return "".join(f"<tr><td>{escape(s['store_name'])}</td><td>{s['health']:.0f}</td>"
                           f"<td>{pct(s['achievement'])}</td><td>{pct(s['lock_rate'])}</td></tr>" for s in items)
        cards.append(
            f'<div class="card"><strong>{tier}门店</strong>（{len(members)} 家）'
            f'<table><thead><tr><th>标兵</th><th>健康分</th><th>达成</th><th>试驾→锁单</th></tr></thead><tbody>{rows(members[:3])}</tbody></table>'
            f'<table style="margin-top:10px"><thead><tr><th>关注</th><th>健康分</th><th>达成</th><th>试驾→锁单</th></tr></thead><tbody>{rows(members[-3:][::-1])}</tbody></table>{note}</div>'
        )
    return f'<div class="grid g3">{"".join(cards)}</div>'


def alerts_table(alerts: list[dict]) -> str:
    rows = "".join(
        f'<tr><td><span class="tag" style="background:{PRIORITY_COLOR[a["priority"]]}">{a["priority"]}</span></td>'
        f'<td>{escape(a["store_name"])}</td><td>{escape(a["model"])}</td><td>{a["tier"]}</td>'
        f'<td>{a["cause"]}</td><td>{pct(a["achievement"])}</td><td>{escape(a["owner"])}</td></tr>'
        for a in alerts
    )
    return (f'<div class="scroll"><table><thead><tr><th>优先级</th><th>门店</th><th>车型</th><th>层级</th>'
            f'<th>病因</th><th>达成</th><th>责任方</th></tr></thead><tbody>{rows}</tbody></table></div>')


def metric_table(metric_defs: list[dict]) -> str:
    rows = "".join(f"<tr><td>{escape(m['name'])}</td><td><code>{m['id']}</code></td>"
                   f"<td><code>{m['numerator']} / {m['denominator']}</code></td></tr>" for m in metric_defs)
    return f"<table><thead><tr><th>指标</th><th>ID</th><th>口径</th></tr></thead><tbody>{rows}</tbody></table>"


def render(ctx: dict) -> str:
    project, region, cfg = ctx["project"], ctx["region"], ctx["config"]
    metric_names = {m["id"]: m["name"] for m in cfg["metrics"]}
    alerts = ctx["alerts"]
    p1 = sum(a["priority"] == "P1" for a in alerts)
    progress = project["as_of_day"] / project["days_in_month"]

    kpis = [
        ("MTD 锁单", f"{region['locks']:,}", f"月目标 {region['month_target']:,} 台"),
        ("进度达成率", pct(region["achievement"]), f"时间进度 {pct(progress)}"),
        ("试驾→锁单率", pct(region["lock_rate"]), f"留资→试驾 {pct(region['td_rate'])}"),
        ("P1 预警单元", str(p1), f"预警总数 {len(alerts)}"),
    ]
    kpi_html = "".join(f'<div class="card kpi"><div class="label">{l}</div><div class="value">{v}</div>'
                       f'<div class="sub">{s}</div></div>' for l, v, s in kpis)
    summary = "".join(f"<li>{escape(line)}</li>" for line in ctx["summary"])
    actions = "".join(
        f'<li><span class="tag" style="background:{PRIORITY_COLOR[a["priority"]]}">{a["priority"]}</span> '
        f'{escape(alert_sentence(a, metric_names))}</li>' for a in alerts[:6]
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{escape(project['title'])} · {escape(project['region'])}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{escape(project['title'])} · {escape(project['region'])}</h1>
    <div class="meta">{project['month']} · 数据截至第 {project['as_of_day']} 天 · {len(ctx['stores'])} 家门店 × {len(ctx['models'])} 个车型
      <span class="badge">演示数据，全部随机生成</span></div>
  </header>

  <h2>核心指标</h2>
  <div class="grid g4">{kpi_html}</div>

  <h2>今日结论</h2>
  <div class="grid g2">
    <div class="card summary"><ul>{summary}</ul></div>
    <div class="card actions"><strong>优先处理</strong><ul>{actions}</ul></div>
  </div>

  <h2>大区漏斗 · 城市达成</h2>
  <div class="grid g2">
    <div class="card">{funnel_svg(region)}</div>
    <div class="card">{city_bar_svg(ctx['cities'])}</div>
  </div>

  <h2>分层标兵与关注门店（同层内比较）</h2>
  {tier_boards(ctx['stores'], cfg['health']['tiers'])}

  <h2>健康分热力图 · 门店 × 车型</h2>
  <div class="card scroll">{heatmap_table(ctx['stores'], ctx['units'], ctx['models'], cfg['health']['tiers'])}</div>

  <h2>预警清单</h2>
  <div class="card">{alerts_table(alerts)}</div>

  <h2>指标口径</h2>
  <div class="card">{metric_table(cfg['metrics'])}</div>

  <footer>由 kpi_engine 自动生成 · 指标口径与诊断规则见 config/metrics.toml · © 2026 张文婧 (Anna Zhang) · github.com/annawzhang · MIT · 保留署名</footer>
</div>
</body>
</html>
"""
