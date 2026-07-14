
from __future__ import annotations

import html
from typing import Any

from pyvis.network import Network


RELATIONSHIP_LABELS = {
    "partners_with": "partners with",
    "adopts": "adopts",
    "targets": "targets",
    "enabled_by": "enabled by",
    "integrates_with": "integrates with",
    "supports": "supports",
    "supplies_to": "supplies to",
    "depends_on": "depends on",
    "manufactured_by": "manufactured by",
    "regulated_by": "regulated by",
    "exposed_to": "exposed to",
    "constrained_by": "constrained by",
    "competes_with": "competes with",
    "influences": "influences",
}


def _node_group(entity: str) -> str:
    name = entity.lower()

    if "nvidia" in name:
        return "nvidia"
    if "amazon" in name or name == "aws":
        return "customer_partner"
    if "tsmc" in name:
        return "supplier"
    if "bureau" in name or "regulation" in name:
        return "regulator"
    if "ai" in name or "supercomputing" in name or "arm" in name:
        return "market_technology"

    return "entity"


def _node_size(entity: str, degree: int) -> int:
    base = 38 if entity == "NVIDIA" else 22
    return min(base + (degree * 3), 65)


def build_relationship_graph_html(
    relationships: list[dict[str, Any]],
) -> str:
    network = Network(
        height="700px",
        width="100%",
        directed=True,
        bgcolor="#0e1117",
        font_color="#fafafa",
        cdn_resources="remote",
    )

    degree: dict[str, int] = {}

    for item in relationships:
        source = item.get("source_entity", "")
        target = item.get("target_entity", "")

        degree[source] = degree.get(source, 0) + 1
        degree[target] = degree.get(target, 0) + 1

    added_nodes: set[str] = set()

    for item in relationships:
        for entity in [
            item.get("source_entity", ""),
            item.get("target_entity", ""),
        ]:
            if not entity or entity in added_nodes:
                continue

            group = _node_group(entity)
            title = (
                f"<b>{html.escape(entity)}</b><br>"
                f"Connected relationships: {degree.get(entity, 0)}"
            )

            network.add_node(
                entity,
                label=entity,
                title=title,
                group=group,
                size=_node_size(entity, degree.get(entity, 0)),
                shape="dot",
            )

            added_nodes.add(entity)

    for item in relationships:
        source = item.get("source_entity")
        target = item.get("target_entity")
        relationship_type = item.get("relationship_type", "related_to")
        confidence = float(item.get("confidence_score", 0))

        title = (
            f"<b>{html.escape(relationship_type)}</b><br>"
            f"{html.escape(item.get('relationship_statement', ''))}<br>"
            f"Confidence: {confidence:.3f}<br>"
            f"Evidence: "
            f"{html.escape(', '.join(item.get('supporting_evidence_ids', [])))}"
        )

        network.add_edge(
            source,
            target,
            label=RELATIONSHIP_LABELS.get(
                relationship_type,
                relationship_type.replace("_", " "),
            ),
            title=title,
            value=max(1, int(confidence * 8)),
            arrows="to",
        )

    network.set_options(
        """
        {
          "nodes": {
            "borderWidth": 1,
            "font": {
              "size": 15,
              "face": "Arial",
              "color": "#f3f4f6"
            }
          },
          "edges": {
            "smooth": {
              "enabled": true,
              "type": "dynamic"
            },
            "font": {
              "size": 11,
              "align": "middle",
              "color": "#d1d5db",
              "strokeWidth": 3,
              "strokeColor": "#0e1117"
            }
          },
          "interaction": {
            "hover": true,
            "navigationButtons": true,
            "keyboard": true,
            "tooltipDelay": 150
          },
          "physics": {
            "enabled": true,
            "barnesHut": {
              "gravitationalConstant": -9000,
              "centralGravity": 0.25,
              "springLength": 180,
              "springConstant": 0.04,
              "damping": 0.12
            },
            "stabilization": {
              "enabled": true,
              "iterations": 600
            }
          }
        }
        """
    )

    return network.generate_html(notebook=False)
