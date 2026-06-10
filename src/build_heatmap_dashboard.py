import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "bain_aquiline_blackstone_workflow_analysis.json"
OUTPUT = ROOT / "outputs" / "kit_heatmap_dashboard.html"


def build_dashboard_data() -> dict:
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    companies = payload["company_level_records"]
    funds = sorted({fund for company in companies for fund in company["associated_funds"]})
    kits = [
        row["kit_category"]
        for row in sorted(
            payload["kit_level_aggregation_records"],
            key=lambda row: row["reusable_kit_priority_score"],
            reverse=True,
        )
    ]

    cells = []
    for fund in funds:
        for kit in kits:
            matching = [
                company
                for company in companies
                if fund in company["associated_funds"] and kit in company["reusable_kit_categories"]
            ]
            if matching:
                count = len(matching)
                avg_opp = sum(company["opportunity_score"] or 0 for company in matching) / count
                avg_ready = sum(company["deployment_readiness_score"] for company in matching) / count
                avg_potential = sum(company["kit_potential_score"] for company in matching) / count
                avg_conf = sum({"high": 1.0, "medium": 0.7, "low": 0.4}[company["confidence"]] for company in matching) / count
                priority = count * avg_ready * avg_potential * avg_conf
            else:
                count = 0
                avg_opp = avg_ready = avg_potential = avg_conf = priority = 0
            cells.append(
                {
                    "fund": fund,
                    "kit": kit,
                    "count": count,
                    "avgOpportunity": round(avg_opp, 2),
                    "avgReadiness": round(avg_ready, 2),
                    "avgPotential": round(avg_potential, 2),
                    "avgConfidence": round(avg_conf, 2),
                    "priority": round(priority, 2),
                }
            )

    fund_summaries = []
    for fund in funds:
        fund_companies = [company for company in companies if fund in company["associated_funds"]]
        top_cells = sorted(
            [cell for cell in cells if cell["fund"] == fund],
            key=lambda cell: cell["priority"],
            reverse=True,
        )[:5]
        fund_summaries.append(
            {
                "fund": fund,
                "companyCount": len(fund_companies),
                "topKits": top_cells,
            }
        )

    kit_rankings = []
    for kit in kits:
        kit_cells = [cell for cell in cells if cell["kit"] == kit]
        kit_rankings.append(
            {
                "kit": kit,
                "count": sum(cell["count"] for cell in kit_cells),
                "priority": round(sum(cell["priority"] for cell in kit_cells), 2),
                "funds": sum(1 for cell in kit_cells if cell["count"] > 0),
            }
        )

    slim_companies = []
    for company in companies:
        slim_companies.append(
            {
                "company": company["company_name"],
                "funds": company["associated_funds"],
                "vertical": company["vertical"],
                "industry": company["industry"],
                "opportunity": company["opportunity_score"],
                "readiness": company["deployment_readiness_score"],
                "potential": company["kit_potential_score"],
                "owner": company["likely_workflow_owner"],
                "risk": company["risk_level"],
                "hil": company["human_in_loop_need"],
                "confidence": company["confidence"],
                "kits": company["reusable_kit_categories"],
                "hypotheses": company["top_workflow_automation_hypotheses"],
                "summary": company["business_model_summary"],
            }
        )

    return {
        "funds": funds,
        "kits": kits,
        "cells": cells,
        "fundSummaries": fund_summaries,
        "kitRankings": sorted(kit_rankings, key=lambda row: row["priority"], reverse=True),
        "companies": slim_companies,
    }


def render_html(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False)
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ciridae Workflow Kit Heatmap</title>
  <style>
    :root {{
      --bg: #f7f7f4;
      --panel: #ffffff;
      --ink: #1d2426;
      --muted: #647174;
      --line: #d9dedb;
      --accent: #1f7a6b;
      --accent-2: #b4552a;
      --soft: #eef3ef;
      --warn: #f1d9c9;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
    }}
    .shell {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
    }}
    header {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 24px;
      padding: 8px 0 18px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{
      margin: 0;
      font-size: 28px;
      line-height: 1.1;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 16px;
      letter-spacing: 0;
    }}
    p {{
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
    }}
    .controls {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    label {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
    }}
    select, input {{
      height: 36px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      padding: 0 10px;
      border-radius: 6px;
      font: inherit;
      font-size: 14px;
    }}
    main {{
      display: grid;
      grid-template-columns: minmax(780px, 1fr) 360px;
      gap: 18px;
      margin-top: 18px;
      align-items: start;
    }}
    section, aside {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }}
    .stat {{
      background: var(--soft);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
    }}
    .stat strong {{
      display: block;
      font-size: 22px;
      line-height: 1;
    }}
    .stat span {{
      color: var(--muted);
      font-size: 12px;
    }}
    .heatmap-wrap {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    .heatmap {{
      min-width: 980px;
      display: grid;
      grid-template-columns: 210px repeat(var(--fund-count), minmax(142px, 1fr));
    }}
    .hm-cell, .hm-head, .hm-kit {{
      min-height: 52px;
      border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
      padding: 9px 10px;
      display: flex;
      align-items: center;
    }}
    .hm-head {{
      position: sticky;
      top: 0;
      z-index: 2;
      background: #eff2ef;
      font-weight: 750;
      justify-content: center;
      text-align: center;
    }}
    .hm-kit {{
      position: sticky;
      left: 0;
      z-index: 1;
      background: #fafaf8;
      font-size: 12px;
      font-weight: 700;
      line-height: 1.25;
    }}
    .hm-cell {{
      cursor: pointer;
      justify-content: space-between;
      gap: 8px;
      transition: transform .08s ease, box-shadow .08s ease;
    }}
    .hm-cell:hover, .hm-cell.selected {{
      outline: 2px solid var(--ink);
      outline-offset: -2px;
      box-shadow: inset 0 0 0 999px rgba(255,255,255,.12);
    }}
    .hm-value {{
      font-size: 18px;
      font-weight: 800;
    }}
    .hm-sub {{
      font-size: 11px;
      color: rgba(29,36,38,.78);
      text-align: right;
      line-height: 1.2;
    }}
    .side-stack {{
      display: grid;
      gap: 18px;
    }}
    .bars {{
      display: grid;
      gap: 8px;
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: 1fr 64px;
      gap: 8px;
      align-items: center;
      font-size: 12px;
    }}
    .bar-track {{
      height: 10px;
      background: var(--soft);
      border-radius: 999px;
      overflow: hidden;
      border: 1px solid var(--line);
    }}
    .bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }}
    .detail {{
      margin-top: 18px;
    }}
    .detail-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
    }}
    .table-wrap {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      max-height: 520px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 1020px;
      font-size: 12px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 10px;
      vertical-align: top;
      text-align: left;
    }}
    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: #eff2ef;
      color: #394548;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    td.company {{
      font-weight: 750;
      min-width: 180px;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 2px 7px;
      border-radius: 999px;
      background: var(--soft);
      border: 1px solid var(--line);
      margin: 0 4px 4px 0;
      white-space: nowrap;
    }}
    .hypothesis {{
      max-width: 360px;
      line-height: 1.35;
    }}
    .empty {{
      color: var(--muted);
      padding: 18px;
    }}
    @media (max-width: 1100px) {{
      main {{ grid-template-columns: 1fr; }}
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      header {{ align-items: flex-start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>Ciridae Workflow Kit Heatmap</h1>
        <p>Interactive fund-by-kit view across Bain, Aquiline, and Blackstone portfolio scans.</p>
      </div>
      <div class="controls">
        <label for="metric">Metric</label>
        <select id="metric">
          <option value="priority">Priority score</option>
          <option value="count">Company count</option>
          <option value="avgOpportunity">Avg opportunity</option>
          <option value="avgReadiness">Avg readiness</option>
          <option value="avgPotential">Avg kit potential</option>
        </select>
        <label for="search">Search</label>
        <input id="search" type="search" placeholder="Company, kit, vertical">
      </div>
    </header>

    <main>
      <section>
        <div class="stats" id="stats"></div>
        <h2>Fund x Kit Heatmap</h2>
        <div class="heatmap-wrap">
          <div id="heatmap" class="heatmap"></div>
        </div>
        <section class="detail">
          <div class="detail-head">
            <div>
              <h2 id="detailTitle">Companies</h2>
              <p id="detailSubtitle">Click a heatmap cell to focus the table.</p>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Fund</th>
                  <th>Vertical</th>
                  <th>Opp.</th>
                  <th>Ready</th>
                  <th>Kits</th>
                  <th>Owner</th>
                  <th>Risk</th>
                  <th>Hypotheses</th>
                </tr>
              </thead>
              <tbody id="companyRows"></tbody>
            </table>
          </div>
        </section>
      </section>

      <aside class="side-stack">
        <section>
          <h2>Kit Priority Ranking</h2>
          <div id="kitBars" class="bars"></div>
        </section>
        <section>
          <h2>Fund Profiles</h2>
          <div id="fundProfiles" class="bars"></div>
        </section>
      </aside>
    </main>
  </div>

  <script>
    const data = __DASHBOARD_DATA__;
    const state = {{ metric: "priority", selected: null, search: "" }};
    const metricLabels = {{
      priority: "Priority",
      count: "Companies",
      avgOpportunity: "Avg opp.",
      avgReadiness: "Avg ready",
      avgPotential: "Avg potential"
    }};

    const fmt = value => {{
      if (value === 0) return "0";
      if (Number.isInteger(value)) return String(value);
      return Number(value).toFixed(value >= 100 ? 0 : 2).replace(/\\.00$/, "");
    }};

    function colorFor(value, max) {{
      if (!value || !max) return "#f6f6f2";
      const t = Math.max(0, Math.min(1, value / max));
      const light = 94 - t * 46;
      const sat = 18 + t * 34;
      return `hsl(164 ${sat}% ${light}%)`;
    }}

    function rankedKits() {{
      const metric = state.metric;
      return data.kits.map(kit => {{
        const cells = data.cells.filter(cell => cell.kit === kit);
        const count = cells.reduce((sum, cell) => sum + cell.count, 0);
        let value;
        if (metric === "priority" || metric === "count") {{
          value = cells.reduce((sum, cell) => sum + cell[metric], 0);
        }} else {{
          value = count
            ? cells.reduce((sum, cell) => sum + (cell[metric] * cell.count), 0) / count
            : 0;
        }}
        return {{ kit, value, count }};
      }}).sort((a, b) => b.value - a.value);
    }}

    function renderStats() {{
      const companies = data.companies.length;
      const fundCount = data.funds.length;
      const kitCount = data.kits.length;
      const top = rankedKits()[0];
      document.getElementById("stats").innerHTML = [
        ["Companies", companies],
        ["Funds", fundCount],
        ["Kit categories", kitCount],
        ["Top kit", top.kit]
      ].map(([label, value]) => `
        <div class="stat"><strong>${value}</strong><span>${label}</span></div>
      `).join("");
    }}

    function renderHeatmap() {{
      const metric = state.metric;
      const max = Math.max(...data.cells.map(cell => cell[metric]));
      const el = document.getElementById("heatmap");
      el.style.setProperty("--fund-count", data.funds.length);
      const header = [`<div class="hm-head">Kit category</div>`, ...data.funds.map(fund => `<div class="hm-head">${fund}</div>`)].join("");
      const rows = rankedKits().map(row => row.kit).map(kit => {{
        const cells = data.funds.map(fund => {{
          const cell = data.cells.find(row => row.fund === fund && row.kit === kit);
          const selected = state.selected && state.selected.fund === fund && state.selected.kit === kit ? " selected" : "";
          return `
            <div class="hm-cell${selected}" data-fund="${fund}" data-kit="${kit}" style="background:${colorFor(cell[metric], max)}">
              <div class="hm-value">${fmt(cell[metric])}</div>
              <div class="hm-sub">${cell.count} companies<br>${fmt(cell.avgOpportunity)} opp.</div>
            </div>
          `;
        }}).join("");
        return `<div class="hm-kit">${kit}</div>${cells}`;
      }}).join("");
      el.innerHTML = header + rows;
      el.querySelectorAll(".hm-cell").forEach(cell => {{
        cell.addEventListener("click", () => {{
          state.selected = {{ fund: cell.dataset.fund, kit: cell.dataset.kit }};
          render();
        }});
      }});
    }}

    function filteredCompanies() {{
      const q = state.search.trim().toLowerCase();
      return data.companies.filter(company => {{
        const selectedMatch = !state.selected || (
          company.funds.includes(state.selected.fund) && company.kits.includes(state.selected.kit)
        );
        const text = [
          company.company,
          company.funds.join(" "),
          company.vertical,
          company.industry,
          company.kits.join(" "),
          company.owner,
          company.hypotheses.join(" ")
        ].join(" ").toLowerCase();
        return selectedMatch && (!q || text.includes(q));
      }}).sort((a, b) => (b.opportunity || 0) - (a.opportunity || 0));
    }}

    function renderCompanyRows() {{
      const rows = filteredCompanies();
      const title = state.selected ? `${state.selected.fund} - ${state.selected.kit}` : "Companies";
      document.getElementById("detailTitle").textContent = title;
      document.getElementById("detailSubtitle").textContent = `${rows.length} matching companies`;
      const body = document.getElementById("companyRows");
      if (!rows.length) {{
        body.innerHTML = `<tr><td colspan="9" class="empty">No matching companies.</td></tr>`;
        return;
      }}
      body.innerHTML = rows.map(company => `
        <tr>
          <td class="company">${company.company}</td>
          <td>${company.funds.map(fund => `<span class="pill">${fund}</span>`).join("")}</td>
          <td>${company.vertical}</td>
          <td>${fmt(company.opportunity || 0)}</td>
          <td>${company.readiness}</td>
          <td>${company.kits.map(kit => `<span class="pill">${kit}</span>`).join("")}</td>
          <td>${company.owner}</td>
          <td>${company.risk}<br>${company.hil} HIL</td>
          <td class="hypothesis">${company.hypotheses.slice(0, 2).join("<br><br>")}</td>
        </tr>
      `).join("");
    }}

    function renderBars() {{
      const rows = rankedKits();
      const maxValue = Math.max(...rows.map(row => row.value));
      document.querySelector(".side-stack section h2").textContent = `Kit Ranking - ${metricLabels[state.metric]}`;
      document.getElementById("kitBars").innerHTML = rows.map(row => `
        <div class="bar-row">
          <div>
            <div>${row.kit}</div>
            <div class="bar-track"><div class="bar-fill" style="width:${maxValue ? (row.value / maxValue) * 100 : 0}%"></div></div>
          </div>
          <strong>${fmt(row.value)}</strong>
        </div>
      `).join("");

      document.getElementById("fundProfiles").innerHTML = data.fundSummaries.map(fund => `
        <div class="bar-row" style="grid-template-columns:1fr;">
          <div>
            <strong>${fund.fund}</strong>
            <p>${fund.companyCount} companies. Top: ${fund.topKits.slice(0, 3).map(row => row.kit).join(", ")}</p>
          </div>
        </div>
      `).join("");
    }}

    function render() {{
      renderStats();
      renderHeatmap();
      renderCompanyRows();
      renderBars();
    }}

    document.getElementById("metric").addEventListener("change", event => {{
      state.metric = event.target.value;
      render();
    }});
    document.getElementById("search").addEventListener("input", event => {{
      state.search = event.target.value;
      renderCompanyRows();
    }});

    render();
  </script>
</body>
</html>
"""
    html = html.replace("{{", "{").replace("}}", "}")
    return html.replace("__DASHBOARD_DATA__", data_json)


def main() -> None:
    data = build_dashboard_data()
    OUTPUT.write_text(render_html(data), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
