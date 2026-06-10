# Ciridae AI Transformation Workflow Analysis

This project parses Ciridae AI Transformation Opportunity Scan PDFs, converts company-level AI profiles into workflow-level automation hypotheses, and aggregates reusable kit categories across PE portfolio companies.

## Key Files

- `src/run_workflow_analysis.py` parses the PDFs and writes company-level and kit-level analysis outputs.
- `src/build_heatmap_dashboard.py` builds a self-contained interactive HTML heatmap dashboard from the combined JSON output.
- `prompts/prompt.txt` contains the analysis prompt/specification.
- `outputs/kit_heatmap_dashboard.html` is the interactive dashboard.
- `docs/index.html` is the GitHub Pages demo entrypoint.

## Live Demo

GitHub Pages URL:

```text
https://aneeshp10.github.io/ciridae-ai-transformation/
```

If Pages has not been enabled yet, configure it in GitHub under **Settings -> Pages** with:

- Source: `Deploy from a branch`
- Branch: `main`
- Folder: `/docs`

## How To Read The Dashboard

The dashboard is a fund-by-workflow-kit view of the portfolio analysis. Rows are reusable Ciridae kit categories, columns are PE funds, and each heatmap cell summarizes how strongly that kit appears within that fund's portfolio.

- **Summary tiles:** show total companies analyzed, number of funds, number of kit categories, and the current top kit under the selected metric.
- **Metric dropdown:** changes the heatmap values and row ordering. `Priority score` is the default build-first score; other options include company count, average opportunity, readiness, and kit potential.
- **Heatmap cells:** the large number is the selected metric for that fund-kit combination. The smaller text shows how many companies are in that cell and their average opportunity score.
- **Cell color:** darker green means a stronger value for the selected metric.
- **Kit ranking:** ranks kit categories by the selected cumulative metric across all funds.
- **Fund profiles:** summarize each fund's company count and top recurring kit patterns.
- **Company table:** click any heatmap cell to see the companies behind that fund-kit signal, including vertical, scores, assigned kits, likely owner, risk, and example workflow hypotheses.

`Priority score` is calculated as:

```text
company count x avg deployment readiness x avg kit potential x avg confidence weight
```

It is intended as a build-first prioritization signal, not a revenue forecast.

## Regenerate Outputs

```bash
.venv/bin/python src/run_workflow_analysis.py
.venv/bin/python src/build_heatmap_dashboard.py
cp outputs/kit_heatmap_dashboard.html docs/index.html
```

Then open:

```bash
open outputs/kit_heatmap_dashboard.html
```

Raw PDFs and extracted text are excluded from git by default.
