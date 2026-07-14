
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.ui.data_loader import (
    load_all_data,
    metric_summary,
    evidence_dataframe,
    relationship_dataframe,
    intelligence_dataframe,
)
from src.ui.graph_view import build_relationship_graph_html


st.set_page_config(
    page_title="SignalGraph — NVIDIA Intelligence POC",
    page_icon="🧠",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    .small-note {font-size: 0.86rem; opacity: 0.75;}
    .intel-card {
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 12px;
        padding: 1rem 1.1rem;
        margin-bottom: 0.8rem;
    }
    .trace-box {
        border-left: 4px solid rgba(128,128,128,.45);
        padding: .55rem .85rem;
        margin: .4rem 0;
        background: rgba(128,128,128,.05);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_ROOT = Path(".")


@st.cache_data(show_spinner=False)
def get_data():
    return load_all_data(DATA_ROOT)


def show_traceability(item: dict, evidence_index: dict, relationship_index: dict) -> None:
    st.markdown("#### Traceability")

    for relationship_id in item.get("supporting_relationship_ids", []):
        rel = relationship_index.get(relationship_id)
        if not rel:
            continue

        st.markdown(
            f"""
            <div class="trace-box">
            <b>{relationship_id}</b><br>
            {rel.get('source_entity')} → <b>{rel.get('relationship_type')}</b> →
            {rel.get('target_entity')}<br>
            Confidence: {rel.get('confidence_score')}
            </div>
            """,
            unsafe_allow_html=True,
        )

    for evidence_id in item.get("supporting_evidence_ids", []):
        evidence = evidence_index.get(evidence_id)
        if not evidence:
            continue

        with st.expander(f"{evidence_id} — {evidence.get('source_name', 'Source')}"):
            st.write(evidence.get("claim", ""))
            st.caption(
                f"Source: {evidence.get('source_name')} | "
                f"Tier: {evidence.get('source_tier')} | "
                f"Confidence: {evidence.get('confidence_score')}"
            )
            st.markdown("**Supporting snippet**")
            st.code(evidence.get("evidence_snippet", ""), language=None)

            source_url = evidence.get("source_url")
            if source_url:
                st.link_button("Open source", source_url)


data = get_data()
summary = metric_summary(data)

st.title("SignalGraph — NVIDIA Intelligence POC")
st.caption(
    "Validation console for source traceability, evidence inspection, "
    "relationship discovery, and intelligence synthesis."
)

missing = data.get("missing_files", [])
if missing:
    st.warning(
        "Some expected files are missing. Available sections will still load.\n\n"
        + "\n".join(f"- {path}" for path in missing)
    )

overview_tab, evidence_tab, graph_tab, intelligence_tab, validation_tab = st.tabs(
    [
        "Overview",
        "Evidence Explorer",
        "Relationship Graph",
        "Intelligence",
        "Validation",
    ]
)

with overview_tab:
    cols = st.columns(6)
    labels = [
        ("Registered sources", summary["registered_sources"]),
        ("Ingested documents", summary["ingested_documents"]),
        ("Generated chunks", summary["generated_chunks"]),
        ("Evidence-ready chunks", summary["evidence_ready_chunks"]),
        ("Approved evidence", summary["approved_evidence"]),
        ("Relationships", summary["relationships"]),
    ]

    for col, (label, value) in zip(cols, labels):
        col.metric(label, value)

    st.metric("Intelligence objects", summary["intelligence_objects"])

    st.markdown("### Validated flow")
    st.code(
        "Sources → Documents → Normalized Corpus → Chunks → "
        "Evidence → Relationships → Intelligence Objects",
        language=None,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Relationship distribution")
        rel_df = relationship_dataframe(data)
        if not rel_df.empty:
            counts = (
                rel_df["relationship_type"]
                .value_counts()
                .rename_axis("relationship_type")
                .reset_index(name="count")
            )
            st.bar_chart(counts, x="relationship_type", y="count")
        else:
            st.info("No relationship data available.")

    with col2:
        st.markdown("### Intelligence distribution")
        intel_df = intelligence_dataframe(data)
        if not intel_df.empty:
            counts = (
                intel_df["intelligence_type"]
                .value_counts()
                .rename_axis("intelligence_type")
                .reset_index(name="count")
            )
            st.bar_chart(counts, x="intelligence_type", y="count")
        else:
            st.info("No intelligence data available.")

    st.markdown("### What this POC demonstrates")
    st.success(
        "The system can transform trusted market sources into traceable evidence, "
        "discover evidence-backed relationships, and synthesize confidence-scored "
        "intelligence that explains why a signal matters."
    )

with evidence_tab:
    evidence_df = evidence_dataframe(data)

    if evidence_df.empty:
        st.info("No approved evidence found.")
    else:
        st.markdown("### Filter approved evidence")
        c1, c2, c3, c4 = st.columns(4)

        themes = sorted(evidence_df["theme"].dropna().unique().tolist())
        entities = sorted(evidence_df["primary_entity"].dropna().unique().tolist())
        sources = sorted(evidence_df["source_name"].dropna().unique().tolist())
        verification = sorted(
            evidence_df["verification_status"].dropna().unique().tolist()
        )

        selected_themes = c1.multiselect("Theme", themes)
        selected_entities = c2.multiselect("Entity", entities)
        selected_sources = c3.multiselect("Source", sources)
        selected_verification = c4.multiselect(
            "Verification status", verification
        )

        minimum_confidence = st.slider(
            "Minimum confidence score",
            min_value=0.0,
            max_value=1.0,
            value=0.70,
            step=0.05,
        )

        filtered = evidence_df.copy()

        if selected_themes:
            filtered = filtered[filtered["theme"].isin(selected_themes)]
        if selected_entities:
            filtered = filtered[
                filtered["primary_entity"].isin(selected_entities)
            ]
        if selected_sources:
            filtered = filtered[filtered["source_name"].isin(selected_sources)]
        if selected_verification:
            filtered = filtered[
                filtered["verification_status"].isin(selected_verification)
            ]

        filtered = filtered[
            filtered["confidence_score"].fillna(0) >= minimum_confidence
        ]

        st.caption(f"{len(filtered)} evidence objects match the current filters.")

        for _, row in filtered.iterrows():
            with st.expander(
                f"{row['evidence_id']} — {row['claim'][:110]}"
            ):
                left, right = st.columns([3, 1])

                with left:
                    st.markdown("**Claim**")
                    st.write(row["claim"])

                    st.markdown("**Why it matters**")
                    st.write(row.get("why_it_matters", ""))

                    st.markdown("**Supporting snippet**")
                    st.code(row.get("evidence_snippet", ""), language=None)

                with right:
                    st.metric("Confidence", row.get("confidence_score", 0))
                    st.write(f"**Entity:** {row.get('primary_entity')}")
                    st.write(f"**Theme:** {row.get('theme')}")
                    st.write(
                        f"**Verification:** {row.get('verification_status')}"
                    )
                    st.write(f"**Source tier:** {row.get('source_tier')}")
                    st.write(f"**Chunk:** {row.get('chunk_id')}")

                    url = row.get("source_url")
                    if url:
                        st.link_button("Open source", url)

with graph_tab:
    relationships = data["relationships"].get("relationships", [])

    if not relationships:
        st.info("No relationships found.")
    else:
        st.markdown("### Interactive relationship graph")

        rel_df = relationship_dataframe(data)
        all_types = sorted(rel_df["relationship_type"].dropna().unique())
        selected_types = st.multiselect(
            "Relationship types",
            all_types,
            default=all_types,
        )

        min_graph_confidence = st.slider(
            "Minimum graph confidence",
            0.0,
            1.0,
            0.70,
            0.05,
            key="graph_confidence",
        )

        graph_relationships = [
            item
            for item in relationships
            if item.get("relationship_type") in selected_types
            and float(item.get("confidence_score", 0)) >= min_graph_confidence
        ]

        html = build_relationship_graph_html(graph_relationships)

        # PyVis requires JavaScript execution, so the static Streamlit HTML
        # component is intentionally used here.
        import streamlit.components.v1 as components

        components.html(html, height=720, scrolling=True)

        st.markdown("### Relationship details")
        relationship_lookup = {
            item["relationship_id"]: item for item in graph_relationships
        }

        selected_relationship_id = st.selectbox(
            "Inspect relationship",
            list(relationship_lookup),
            format_func=lambda rid: (
                f"{rid}: "
                f"{relationship_lookup[rid]['source_entity']} → "
                f"{relationship_lookup[rid]['relationship_type']} → "
                f"{relationship_lookup[rid]['target_entity']}"
            ),
        )

        relationship = relationship_lookup[selected_relationship_id]

        c1, c2, c3 = st.columns(3)
        c1.metric("Confidence", relationship.get("confidence_score", 0))
        c2.metric(
            "Supporting evidence",
            len(relationship.get("supporting_evidence_ids", [])),
        )
        c3.write(
            f"**Verification:** {relationship.get('verification_status')}"
        )

        st.write(relationship.get("relationship_statement"))
        st.markdown("**Why it matters**")
        st.write(relationship.get("why_it_matters"))
        st.markdown("**Business impact**")
        st.write(relationship.get("business_impact"))

        st.markdown("**Supporting evidence IDs**")
        st.code(
            ", ".join(relationship.get("supporting_evidence_ids", [])),
            language=None,
        )

with intelligence_tab:
    objects = data["intelligence"].get("intelligence_objects", [])
    evidence_index = {
        item["evidence_id"]: item
        for item in data["approved_evidence"].get("evidence", [])
    }
    relationship_index = {
        item["relationship_id"]: item
        for item in data["relationships"].get("relationships", [])
    }

    if not objects:
        st.info("No intelligence objects found.")
    else:
        intel_types = sorted(
            {item.get("intelligence_type") for item in objects}
        )
        selected_intel_types = st.multiselect(
            "Intelligence types",
            intel_types,
            default=intel_types,
        )

        filtered_objects = [
            item
            for item in objects
            if item.get("intelligence_type") in selected_intel_types
        ]

        for item in filtered_objects:
            st.markdown('<div class="intel-card">', unsafe_allow_html=True)
            st.subheader(
                f"{item['intelligence_id']} — {item['event_or_signal']}"
            )

            c1, c2, c3 = st.columns(3)
            c1.write(f"**Entity:** {item.get('entity')}")
            c2.write(f"**Type:** {item.get('intelligence_type')}")
            c3.metric("Confidence", item.get("confidence_score", 0))

            st.markdown("**Strategic interpretation**")
            st.write(item.get("strategic_interpretation"))

            st.markdown("**Why it matters**")
            st.write(item.get("why_it_matters"))

            st.markdown("**Business impact**")
            st.write(item.get("business_impact"))

            st.markdown("**Risk or opportunity**")
            st.write(item.get("risk_or_opportunity"))

            watch_items = item.get("watch_items", [])
            if watch_items:
                st.markdown("**Watch next**")
                for watch_item in watch_items:
                    st.write(f"• {watch_item}")

            show_traceability(
                item,
                evidence_index,
                relationship_index,
            )
            st.markdown("</div>", unsafe_allow_html=True)

with validation_tab:
    st.markdown("### POC validation questions")

    questions = [
        (
            "Can trusted Nvidia intelligence sources be organized?",
            summary["registered_sources"] > 0,
            f"{summary['registered_sources']} sources registered.",
        ),
        (
            "Can the system ingest and normalize market information?",
            summary["ingested_documents"] > 0,
            f"{summary['ingested_documents']} documents ingested.",
        ),
        (
            "Can documents become evidence-ready units?",
            summary["evidence_ready_chunks"] > 0,
            f"{summary['evidence_ready_chunks']} evidence-ready chunks.",
        ),
        (
            "Can AI extract traceable structured evidence?",
            summary["approved_evidence"] > 0,
            f"{summary['approved_evidence']} approved evidence objects.",
        ),
        (
            "Can meaningful relationships be discovered?",
            summary["relationships"] > 0,
            f"{summary['relationships']} evidence-backed relationships.",
        ),
        (
            "Can evidence and relationships become intelligence?",
            summary["intelligence_objects"] > 0,
            f"{summary['intelligence_objects']} intelligence objects.",
        ),
    ]

    for question, passed, detail in questions:
        icon = "✅" if passed else "⚠️"
        st.markdown(f"### {icon} {question}")
        st.write(detail)

    st.markdown("### Known POC limitations")
    st.info(
        "The relationship vocabulary is intentionally narrow; some company-to-"
        "product edges remain semantically awkward; supplier and competitor "
        "coverage is limited; and most evidence currently comes from official "
        "company sources. These are calibration and coverage improvements, not "
        "blockers to the core validation."
    )
