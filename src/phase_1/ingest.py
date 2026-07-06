import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from source_registry import load_registry, get_active_sources


RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "CustomIntelligencePOC/0.1 contact: research@example.com",
    "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")[:80]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def fetch_url(url: str) -> Dict[str, Any]:
    parsed = urlparse(url)

    if parsed.scheme == "file":
        return {
            "status": "manual_required",
            "raw_text": "",
            "raw_html": "",
            "content_type": "local_file",
            "error": "Local/manual source. Not fetched by HTTP."
        }

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        content_type = response.headers.get("Content-Type", "")

        if response.status_code != 200:
            return {
                "status": "failed",
                "raw_text": "",
                "raw_html": "",
                "content_type": content_type,
                "error": f"HTTP {response.status_code}"
            }

        if "application/json" in content_type or url.endswith(".json"):
            raw_text = json.dumps(response.json(), indent=2)
            return {
                "status": "success",
                "raw_text": raw_text,
                "raw_html": "",
                "content_type": content_type,
                "error": ""
            }

        if "pdf" in content_type or url.lower().endswith(".pdf"):
            return {
                "status": "manual_required",
                "raw_text": "",
                "raw_html": "",
                "content_type": content_type,
                "error": "PDF detected. Manual/download PDF parser required later."
            }

        html = response.text
        raw_text = extract_text_from_html(html)

        return {
            "status": "success",
            "raw_text": raw_text,
            "raw_html": html,
            "content_type": content_type,
            "error": ""
        }

    except Exception as exc:
        return {
            "status": "failed",
            "raw_text": "",
            "raw_html": "",
            "content_type": "",
            "error": str(exc)
        }


def build_raw_document(source: Dict[str, Any], fetch_result: Dict[str, Any]) -> Dict[str, Any]:
    document_id = f"doc_{source['source_id']}"

    return {
        "document_id": document_id,
        "source_id": source["source_id"],
        "source_name": source["source_name"],
        "source_family": source["source_family"],
        "source_type": source["source_type"],
        "source_tier": source["source_tier"],
        "url": source["url"],
        "root_domain": source.get("root_domain"),
        "purpose": source.get("purpose"),
        "themes": source.get("themes", []),
        "associated_entities": source.get("associated_entities", []),
        "reliability_score": source.get("reliability_score"),
        "bias_risk": source.get("bias_risk"),
        "license_status": source.get("license_status"),
        "collection_method": source.get("collection_method"),
        "active_status": source.get("active_status"),
        "collected_at": now_iso(),
        "status": fetch_result["status"],
        "content_type": fetch_result.get("content_type", ""),
        "raw_text": fetch_result.get("raw_text", ""),
        "raw_html": fetch_result.get("raw_html", ""),
        "error": fetch_result.get("error", "")
    }


def save_raw_document(document: Dict[str, Any]) -> Path:
    filename = f"{document['document_id']}_{slugify(document['source_name'])}.json"
    path = RAW_DIR / filename

    with path.open("w", encoding="utf-8") as file:
        json.dump(document, file, indent=2, ensure_ascii=False)

    return path


def ingest_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []

    for source in sources:
        print(f"Ingesting {source['source_id']} | {source['source_name']}")

        fetch_result = fetch_url(source["url"])
        document = build_raw_document(source, fetch_result)
        output_path = save_raw_document(document)

        results.append({
            "source_id": source["source_id"],
            "source_name": source["source_name"],
            "status": document["status"],
            "output_path": str(output_path),
            "error": document["error"],
            "text_length": len(document.get("raw_text", ""))
        })

        time.sleep(1)

    return results


def save_ingestion_report(results: List[Dict[str, Any]]) -> None:
    report_path = Path("outputs/ingestion_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "generated_at": now_iso(),
        "total_sources_attempted": len(results),
        "success": sum(1 for r in results if r["status"] == "success"),
        "manual_required": sum(1 for r in results if r["status"] == "manual_required"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results
    }

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)

    print("\nINGESTION SUMMARY")
    print("-" * 40)
    print(f"Total attempted: {summary['total_sources_attempted']}")
    print(f"Success: {summary['success']}")
    print(f"Manual required: {summary['manual_required']}")
    print(f"Failed: {summary['failed']}")
    print(f"Report: {report_path}")


def main() -> None:
    registry = load_registry()
    sources = get_active_sources(registry)

    print(f"Active sources selected for ingestion: {len(sources)}")

    results = ingest_sources(sources)
    save_ingestion_report(results)


if __name__ == "__main__":
    main()