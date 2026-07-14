
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


EXPECTED_FILES = {
    "source_registry": Path("data/source_registry.json"),
    "ingestion_report": Path("outputs/ingestion_report.json"),
    "normalization_report": Path("outputs/normalization_report.json"),
    "chunking_report": Path("outputs/chunking_report.json"),
    "chunk_quality_report": Path("outputs/chunk_quality_report.json"),
    "approved_evidence": Path("data/evidence/approved_evidence.json"),
    "relationships": Path("data/relationships/relationships.json"),
    "intelligence": Path("data/intelligence/intelligence_objects.json"),
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_all_data(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    missing_files: list[str] = []

    for key, relative_path in EXPECTED_FILES.items():
        absolute_path = root / relative_path

        if not absolute_path.exists():
            missing_files.append(str(relative_path))

        result[key] = _load_json(absolute_path)

    result["missing_files"] = missing_files
    return result


def _registry_sources(registry: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("sources", "source_registry", "items"):
        value = registry.get(key)
        if isinstance(value, list):
            return value
    return []


def metric_summary(data: dict[str, Any]) -> dict[str, int]:
    registry_sources = _registry_sources(data.get("source_registry", {}))

    ingestion = data.get("ingestion_report", {})
    normalization = data.get("normalization_report", {})
    chunking = data.get("chunking_report", {})
    quality = data.get("chunk_quality_report", {})
    evidence = data.get("approved_evidence", {})
    relationships = data.get("relationships", {})
    intelligence = data.get("intelligence", {})

    return {
        "registered_sources": len(registry_sources)
        or int(data.get("source_registry", {}).get("total_sources", 0) or 0),
        "ingested_documents": int(
            ingestion.get("success", 0)
            or ingestion.get("successful", 0)
            or ingestion.get("total_success", 0)
            or 0
        ),
        "normalized_documents": int(
            normalization.get("normalized", 0)
            or normalization.get("normalized_documents", 0)
            or normalization.get("total_docs", 0)
            or 0
        ),
        "generated_chunks": int(
            chunking.get("total_chunks", 0) or 0
        ),
        "evidence_ready_chunks": int(
            quality.get("kept_chunks", 0)
            or quality.get("evidence_ready_chunks", 0)
            or 0
        ),
        "approved_evidence": int(
            evidence.get("approved_evidence_count", 0)
            or len(evidence.get("evidence", []))
        ),
        "relationships": int(
            relationships.get("relationship_count", 0)
            or len(relationships.get("relationships", []))
        ),
        "intelligence_objects": int(
            intelligence.get("intelligence_object_count", 0)
            or len(intelligence.get("intelligence_objects", []))
        ),
    }


def evidence_dataframe(data: dict[str, Any]) -> pd.DataFrame:
    items = data.get("approved_evidence", {}).get("evidence", [])
    return pd.DataFrame(items)


def relationship_dataframe(data: dict[str, Any]) -> pd.DataFrame:
    items = data.get("relationships", {}).get("relationships", [])
    return pd.DataFrame(items)


def intelligence_dataframe(data: dict[str, Any]) -> pd.DataFrame:
    items = data.get("intelligence", {}).get("intelligence_objects", [])
    return pd.DataFrame(items)
