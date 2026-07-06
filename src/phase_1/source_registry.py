import json
from pathlib import Path
from typing import Any, Dict, List


REGISTRY_PATH = Path("data/source_registry.json")


REQUIRED_SOURCE_FIELDS = [
    "source_id",
    "source_name",
    "source_family",
    "source_type",
    "source_tier",
    "url",
    "purpose",
    "reliability_score",
    "bias_risk",
    "license_status",
    "collection_method",
    "active_status",
    "ingestion_priority",
]


def load_registry(path: Path = REGISTRY_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Source registry not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        registry = json.load(file)

    if "sources" not in registry or not isinstance(registry["sources"], list):
        raise ValueError("Invalid registry: missing 'sources' list")

    return registry


def validate_registry(registry: Dict[str, Any]) -> List[str]:
    errors = []
    seen_ids = set()

    for index, source in enumerate(registry["sources"], start=1):
        for field in REQUIRED_SOURCE_FIELDS:
            if field not in source:
                errors.append(f"Source #{index} missing field: {field}")

        source_id = source.get("source_id")
        if source_id in seen_ids:
            errors.append(f"Duplicate source_id found: {source_id}")
        seen_ids.add(source_id)

        tier = source.get("source_tier")
        if not isinstance(tier, int) or tier < 0 or tier > 5:
            errors.append(f"{source_id}: invalid source_tier: {tier}")

        reliability = source.get("reliability_score")
        if not isinstance(reliability, (int, float)) or not 0 <= reliability <= 1:
            errors.append(f"{source_id}: invalid reliability_score: {reliability}")

    return errors


def get_active_sources(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        source for source in registry["sources"]
        if source.get("active_status") == "active_now"
    ]


def get_sources_by_tier(registry: Dict[str, Any], tier: int) -> List[Dict[str, Any]]:
    return [
        source for source in registry["sources"]
        if source.get("source_tier") == tier
    ]


def print_registry_summary(registry: Dict[str, Any]) -> None:
    sources = registry["sources"]
    active_sources = get_active_sources(registry)

    print("\nSOURCE REGISTRY SUMMARY")
    print("-" * 40)
    print(f"Registry name: {registry.get('registry_name')}")
    print(f"Primary entity: {registry.get('primary_entity')}")
    print(f"Total sources: {len(sources)}")
    print(f"Active now: {len(active_sources)}")

    print("\nSources by tier:")
    for tier in range(0, 6):
        count = len(get_sources_by_tier(registry, tier))
        print(f"  Tier {tier}: {count}")

    print("\nActive sources:")
    for source in active_sources:
        print(
            f"  {source['source_id']} | "
            f"Tier {source['source_tier']} | "
            f"{source['source_name']}"
        )


def main() -> None:
    registry = load_registry()
    errors = validate_registry(registry)

    if errors:
        print("\nVALIDATION ERRORS")
        print("-" * 40)
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print_registry_summary(registry)


if __name__ == "__main__":
    main()