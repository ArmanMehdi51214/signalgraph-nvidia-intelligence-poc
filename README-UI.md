
# SignalGraph Validation Console

This is a lightweight Streamlit interface for the NVIDIA Competitive
Intelligence POC.

## Expected data

Run the existing pipeline first so these files exist:

- `data/source_registry.json`
- `outputs/ingestion_report.json`
- `outputs/normalization_report.json`
- `outputs/chunking_report.json`
- `outputs/chunk_quality_report.json`
- `data/evidence/approved_evidence.json`
- `data/relationships/relationships.json`
- `data/intelligence/intelligence_objects.json`

## Install

```bash
uv pip install -r requirements-ui.txt
```

## Run

```bash
streamlit run app.py
```

## Views

- Overview
- Evidence Explorer
- Relationship Graph
- Intelligence
- Validation
