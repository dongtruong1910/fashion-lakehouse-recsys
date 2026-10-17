"""Streamlit Multi-Tab Application for Demo & Pooled Street-to-Shop Evaluation.

Run locally:
    streamlit run src/frontend/app.py
"""

from __future__ import annotations

import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="Fashion Lakehouse: Visual Search & Real-Time RecSys",
        layout="wide",
    )
    st.title("Fashion Lakehouse — Visual Search & Real-Time Personalized Recommendation")

    tab_search, tab_feed, tab_stream, tab_label = st.tabs(
        [
            "1. Visual Search & Outfit",
            "2. Real-Time Personalized Feed",
            "3. Lakehouse & Streaming Monitor",
            "4. VN Streetwear Pooled Labeling",
        ]
    )

    with tab_search:
        st.subheader("Street-to-Shop Visual Search (YOLO11 + SigLIP-2 + Qdrant)")
        st.info("Upload a street-style photo to detect garments, filter by category, and retrieve H&M items.")

    with tab_feed:
        st.subheader("Hybrid Two-Stage Personalized Recommendations (LightGBM + Two-Tower)")
        st.info("Select a customer_id and click items to observe real-time session re-ranking.")

    with tab_stream:
        st.subheader("Kafka + Spark Structured Streaming Real-Time KPIs (15m Sliding Window)")
        st.info("Displays live throughput, 15-minute trending products, and omnichannel breakdown from Redis.")

    with tab_label:
        st.subheader("Pooled Relevance Labeling Tool (0-3 Scale for nDCG@10 & Cohen's Kappa)")
        st.markdown(
            """
            **Grading Rubric (Section 2.4):**
            - `0`: Wrong garment category
            - `1`: Correct garment category, wrong color/style
            - `2`: Correct garment category + matching color
            - `3`: Near-identical match (category + color + pattern/cut)
            """
        )


if __name__ == "__main__":
    main()
