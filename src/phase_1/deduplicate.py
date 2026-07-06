import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


PROCESSED_DIR = Path("data/processed")
OUTPUT_PATH = Path("data/processed/deduped_documents.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def text_hash(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_processed_documents() -> List[Dict[str, Any]]:
    docs = []

    for path in PROCESSED_DIR.glob("doc_*.json"):
        with path.open("r", encoding="utf-8") as file:
            doc = json.load(file)

        if doc.get("status") == "normalized" and doc.get("clean_text"):
            doc["_processed_path"] = str(path)
            docs.append(doc)

    return docs


def deduplicate_documents(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    seen_hashes = {}
    unique_docs = []
    duplicates = []

    for doc in docs:
        doc_hash = text_hash(doc["clean_text"])
        doc["content_hash"] = doc_hash

        if doc_hash in seen_hashes:
            duplicates.append({
                "duplicate_document_id": doc["document_id"],
                "original_document_id": seen_hashes[doc_hash],
                "source_name": doc["source_name"],
                "reason": "exact_text_duplicate"
            })
        else:
            seen_hashes[doc_hash] = doc["document_id"]
            unique_docs.append(doc)

    return {
        "generated_at": now_iso(),
        "total_input_documents": len(docs),
        "unique_documents": len(unique_docs),
        "duplicates_removed": len(duplicates),
        "duplicates": duplicates,
        "documents": unique_docs
    }


def save_deduped(result: Dict[str, Any]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=2, ensure_ascii=False)


def save_report(result: Dict[str, Any]) -> None:
    report_path = Path("outputs/deduplication_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": result["generated_at"],
        "total_input_documents": result["total_input_documents"],
        "unique_documents": result["unique_documents"],
        "duplicates_removed": result["duplicates_removed"],
        "duplicates": result["duplicates"]
    }

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\nDEDUPLICATION SUMMARY")
    print("-" * 40)
    print(f"Input documents: {report['total_input_documents']}")
    print(f"Unique documents: {report['unique_documents']}")
    print(f"Duplicates removed: {report['duplicates_removed']}")
    print(f"Deduped output: {OUTPUT_PATH}")
    print(f"Report: {report_path}")


def main() -> None:
    docs = load_processed_documents()
    result = deduplicate_documents(docs)
    save_deduped(result)
    save_report(result)


if __name__ == "__main__":
    main()