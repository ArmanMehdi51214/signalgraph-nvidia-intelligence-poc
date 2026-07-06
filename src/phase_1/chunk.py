import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


INPUT_PATH = Path("data/processed/deduped_documents.json")
OUTPUT_PATH = Path("data/chunks/chunks.json")
REPORT_PATH = Path("outputs/chunking_report.json")

CHUNK_SIZE_WORDS = 1000
CHUNK_OVERLAP_WORDS = 150


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_deduped_documents() -> List[Dict[str, Any]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing deduped file: {INPUT_PATH}")

    with INPUT_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return data.get("documents", [])


def chunk_words(words: List[str], chunk_size: int, overlap: int) -> List[List[str]]:
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = words[start:end]

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start = end - overlap

    return chunks


def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = doc.get("clean_text", "")
    words = text.split()

    word_chunks = chunk_words(words, CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS)
    chunks = []

    for idx, word_chunk in enumerate(word_chunks, start=1):
        chunk_id = f"chunk_{doc['document_id']}_{idx:03d}"

        chunks.append({
            "chunk_id": chunk_id,
            "document_id": doc["document_id"],
            "source_id": doc["source_id"],
            "source_name": doc["source_name"],
            "source_family": doc.get("source_family"),
            "source_type": doc.get("source_type"),
            "source_tier": doc.get("source_tier"),
            "url": doc.get("url"),
            "themes": doc.get("themes", []),
            "associated_entities": doc.get("associated_entities", []),
            "reliability_score": doc.get("reliability_score"),
            "bias_risk": doc.get("bias_risk"),
            "license_status": doc.get("license_status"),
            "chunk_index": idx,
            "chunk_word_count": len(word_chunk),
            "text": " ".join(word_chunk),
            "created_at": now_iso()
        })

    return chunks


def create_chunks(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_chunks = []

    for doc in docs:
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)

        print(
            f"Chunked {doc['document_id']} | "
            f"{doc['source_name']} | "
            f"{len(chunks)} chunks"
        )

    return all_chunks


def save_chunks(chunks: List[Dict[str, Any]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": now_iso(),
        "chunk_size_words": CHUNK_SIZE_WORDS,
        "chunk_overlap_words": CHUNK_OVERLAP_WORDS,
        "total_chunks": len(chunks),
        "chunks": chunks
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


def save_report(docs: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    by_document = {}

    for chunk in chunks:
        doc_id = chunk["document_id"]
        by_document.setdefault(doc_id, {
            "document_id": doc_id,
            "source_id": chunk["source_id"],
            "source_name": chunk["source_name"],
            "source_tier": chunk["source_tier"],
            "chunks": 0,
            "total_chunk_words": 0
        })

        by_document[doc_id]["chunks"] += 1
        by_document[doc_id]["total_chunk_words"] += chunk["chunk_word_count"]

    report = {
        "generated_at": now_iso(),
        "input_documents": len(docs),
        "total_chunks": len(chunks),
        "chunk_size_words": CHUNK_SIZE_WORDS,
        "chunk_overlap_words": CHUNK_OVERLAP_WORDS,
        "documents": list(by_document.values())
    }

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\nCHUNKING SUMMARY")
    print("-" * 40)
    print(f"Input documents: {report['input_documents']}")
    print(f"Total chunks: {report['total_chunks']}")
    print(f"Chunk size: {CHUNK_SIZE_WORDS} words")
    print(f"Overlap: {CHUNK_OVERLAP_WORDS} words")
    print(f"Chunks output: {OUTPUT_PATH}")
    print(f"Report: {REPORT_PATH}")


def main() -> None:
    docs = load_deduped_documents()
    chunks = create_chunks(docs)
    save_chunks(chunks)
    save_report(docs, chunks)


if __name__ == "__main__":
    main()