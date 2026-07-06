import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\u00a0", " ", text)
    text = text.strip()

    return text


def load_raw_documents() -> List[Dict[str, Any]]:
    docs = []

    for path in RAW_DIR.glob("*.json"):
        with path.open("r", encoding="utf-8") as file:
            doc = json.load(file)

        if doc.get("status") == "success":
            doc["_raw_path"] = str(path)
            docs.append(doc)

    return docs


def normalize_document(raw_doc: Dict[str, Any]) -> Dict[str, Any]:
    clean = clean_text(raw_doc.get("raw_text", ""))

    return {
        "document_id": raw_doc["document_id"],
        "source_id": raw_doc["source_id"],
        "source_name": raw_doc["source_name"],
        "source_family": raw_doc.get("source_family"),
        "source_type": raw_doc.get("source_type"),
        "source_tier": raw_doc.get("source_tier"),
        "url": raw_doc.get("url"),
        "root_domain": raw_doc.get("root_domain"),
        "themes": raw_doc.get("themes", []),
        "associated_entities": raw_doc.get("associated_entities", []),
        "reliability_score": raw_doc.get("reliability_score"),
        "bias_risk": raw_doc.get("bias_risk"),
        "license_status": raw_doc.get("license_status"),
        "collected_at": raw_doc.get("collected_at"),
        "normalized_at": now_iso(),
        "raw_path": raw_doc.get("_raw_path"),
        "clean_text": clean,
        "char_count": len(clean),
        "word_count": len(clean.split()),
        "status": "normalized" if clean else "empty"
    }


def save_processed_document(doc: Dict[str, Any]) -> Path:
    path = PROCESSED_DIR / f"{doc['document_id']}.json"

    with path.open("w", encoding="utf-8") as file:
        json.dump(doc, file, indent=2, ensure_ascii=False)

    return path


def normalize_all() -> List[Dict[str, Any]]:
    raw_docs = load_raw_documents()
    results = []

    for raw_doc in raw_docs:
        processed = normalize_document(raw_doc)
        output_path = save_processed_document(processed)

        results.append({
            "document_id": processed["document_id"],
            "source_id": processed["source_id"],
            "source_name": processed["source_name"],
            "status": processed["status"],
            "word_count": processed["word_count"],
            "char_count": processed["char_count"],
            "output_path": str(output_path)
        })

        print(
            f"Normalized {processed['document_id']} | "
            f"{processed['source_name']} | "
            f"{processed['word_count']} words"
        )

    return results


def save_normalization_report(results: List[Dict[str, Any]]) -> None:
    path = Path("outputs/normalization_report.json")
    path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": now_iso(),
        "total_raw_success_docs": len(results),
        "normalized": sum(1 for r in results if r["status"] == "normalized"),
        "empty": sum(1 for r in results if r["status"] == "empty"),
        "results": results
    }

    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\nNORMALIZATION SUMMARY")
    print("-" * 40)
    print(f"Total docs: {report['total_raw_success_docs']}")
    print(f"Normalized: {report['normalized']}")
    print(f"Empty: {report['empty']}")
    print(f"Report: {path}")


def main() -> None:
    results = normalize_all()
    save_normalization_report(results)


if __name__ == "__main__":
    main()