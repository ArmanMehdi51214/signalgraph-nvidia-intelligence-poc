import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


INPUT_PATH = Path("data/chunks/chunks.json")
OUTPUT_PATH = Path("data/chunks/evidence_ready_chunks.json")
REPORT_PATH = Path("outputs/chunk_quality_report.json")


MIN_WORD_COUNT = 250

BLOCKLIST_PHRASES = [
    "request access",
    "your request has been flagged",
    "complete the captcha",
    "captcha",
    "site help",
    "access to these sites is limited",
]

NAV_NOISE_PHRASES = [
    "skip to main content",
    "privacy policy",
    "terms of service",
    "cookie policy",
    "manage cookie settings",
    "copyright ©",
    "email alerts",
    "subscribe",
    "contact us",
    "all rights reserved",
    "follow nvidia",
    "powered by",
]


SOURCE_IDS_TO_EXCLUDE_FROM_EVIDENCE = {
    # SEC submissions JSON is useful for filing discovery,
    # but too structural/noisy for direct evidence extraction.
    "src_004"
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_chunks() -> List[Dict[str, Any]]:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing chunks file: {INPUT_PATH}")

    with INPUT_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return payload.get("chunks", [])


def normalize_for_scoring(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def count_phrase_hits(text: str, phrases: List[str]) -> int:
    normalized = normalize_for_scoring(text)
    return sum(1 for phrase in phrases if phrase in normalized)


def clean_chunk_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    # Remove repeated generic footer/navigation fragments where possible.
    for phrase in NAV_NOISE_PHRASES:
        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)

    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def assess_chunk(chunk: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    reasons = []
    text = chunk.get("text", "")
    normalized = normalize_for_scoring(text)
    word_count = len(text.split())

    blocklist_hits = count_phrase_hits(text, BLOCKLIST_PHRASES)
    nav_hits = count_phrase_hits(text, NAV_NOISE_PHRASES)

    if chunk.get("source_id") in SOURCE_IDS_TO_EXCLUDE_FROM_EVIDENCE:
        reasons.append("excluded_source_for_evidence_extraction")

    if word_count < MIN_WORD_COUNT:
        reasons.append("too_short")

    if blocklist_hits > 0:
        reasons.append("blocked_access_or_captcha_content")

    # If a short/medium chunk has too much nav/footer language, exclude it.
    if nav_hits >= 6 and word_count < 900:
        reasons.append("high_navigation_footer_noise")

    # If the chunk is mostly page shell and has little strategic content.
    strategic_terms = [
        "nvidia",
        "gpu",
        "ai",
        "accelerator",
        "hbm",
        "blackwell",
        "data center",
        "foundry",
        "export",
        "tsmc",
        "memory",
        "packaging",
        "cuda",
        "hyperscaler",
        "cloud",
        "revenue",
        "risk",
        "supply",
        "demand",
        "partnership",
    ]

    strategic_hits = sum(1 for term in strategic_terms if term in normalized)

    if strategic_hits < 2 and word_count < 700:
        reasons.append("low_strategic_signal")

    keep = len(reasons) == 0

    quality = {
        "word_count": word_count,
        "blocklist_hits": blocklist_hits,
        "nav_noise_hits": nav_hits,
        "strategic_signal_hits": strategic_hits,
        "quality_status": "kept" if keep else "filtered",
        "filter_reasons": reasons,
    }

    return keep, reasons, quality


def filter_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    kept = []
    filtered = []

    for chunk in chunks:
        keep, reasons, quality = assess_chunk(chunk)

        cleaned_text = clean_chunk_text(chunk.get("text", ""))

        enriched_chunk = {
            **chunk,
            "text": cleaned_text,
            "filtered_at": now_iso(),
            "quality": quality,
        }

        if keep:
            kept.append(enriched_chunk)
        else:
            filtered.append({
                "chunk_id": chunk.get("chunk_id"),
                "document_id": chunk.get("document_id"),
                "source_id": chunk.get("source_id"),
                "source_name": chunk.get("source_name"),
                "source_tier": chunk.get("source_tier"),
                "word_count": quality["word_count"],
                "filter_reasons": reasons,
            })

    return {
        "generated_at": now_iso(),
        "input_chunks": len(chunks),
        "kept_chunks": len(kept),
        "filtered_chunks": len(filtered),
        "filters": {
            "min_word_count": MIN_WORD_COUNT,
            "excluded_source_ids": sorted(list(SOURCE_IDS_TO_EXCLUDE_FROM_EVIDENCE)),
            "blocklist_phrases": BLOCKLIST_PHRASES,
            "navigation_noise_phrases": NAV_NOISE_PHRASES,
        },
        "chunks": kept,
        "filtered": filtered,
    }


def save_outputs(result: Dict[str, Any]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "generated_at": result["generated_at"],
                "input_chunks": result["input_chunks"],
                "kept_chunks": result["kept_chunks"],
                "chunks": result["chunks"],
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    report = {
        "generated_at": result["generated_at"],
        "input_chunks": result["input_chunks"],
        "kept_chunks": result["kept_chunks"],
        "filtered_chunks": result["filtered_chunks"],
        "filters": result["filters"],
        "filtered": result["filtered"],
        "kept_by_source": summarize_by_source(result["chunks"]),
        "filtered_by_reason": summarize_filtered_reasons(result["filtered"]),
    }

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)


def summarize_by_source(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary = {}

    for chunk in chunks:
        source_id = chunk.get("source_id")
        if source_id not in summary:
            summary[source_id] = {
                "source_id": source_id,
                "source_name": chunk.get("source_name"),
                "source_tier": chunk.get("source_tier"),
                "kept_chunks": 0,
            }

        summary[source_id]["kept_chunks"] += 1

    return sorted(summary.values(), key=lambda x: (x["source_tier"], x["source_id"]))


def summarize_filtered_reasons(filtered: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {}

    for item in filtered:
        for reason in item.get("filter_reasons", []):
            counts[reason] = counts.get(reason, 0) + 1

    return counts


def main() -> None:
    chunks = load_chunks()
    result = filter_chunks(chunks)
    save_outputs(result)

    print("\nCHUNK QUALITY FILTER SUMMARY")
    print("-" * 40)
    print(f"Input chunks: {result['input_chunks']}")
    print(f"Kept chunks: {result['kept_chunks']}")
    print(f"Filtered chunks: {result['filtered_chunks']}")
    print(f"Evidence-ready output: {OUTPUT_PATH}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()