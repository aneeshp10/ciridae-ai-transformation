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
