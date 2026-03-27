from __future__ import annotations

import json

import pandas as pd
import requests
import streamlit as st


API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="Market ChatGPT Next Gen", page_icon="chart", layout="wide")

st.title("Market ChatGPT - Next Gen")
st.caption("Portfolio-aware Indian investor intelligence with hybrid RAG and source citations")

with st.sidebar:
    st.header("Settings")
    user_id = st.text_input("User ID", value="demo-user")
    st.markdown("Upload portfolio CSV with columns: symbol, allocation, quantity(optional)")
    uploaded = st.file_uploader("Portfolio CSV", type=["csv"])
    if st.button("Upload Portfolio"):
        if uploaded is None:
            st.warning("Please choose a CSV file first.")
        else:
            files = {"file": (uploaded.name, uploaded.getvalue(), "text/csv")}
            res = requests.post(f"{API_BASE}/portfolio/upload-csv", params={"user_id": user_id}, files=files, timeout=60)
            if res.ok:
                st.success("Portfolio uploaded successfully.")
                st.json(res.json())
            else:
                st.error(f"Upload failed: {res.text}")

col1, col2 = st.columns([2, 1])

with col1:
    query = st.text_area(
        "Ask a market question",
        value="Which stock in my portfolio is most risky?",
        height=120,
    )
    if st.button("Run Analysis"):
        payload = {"user_id": user_id, "query": query}
        with st.spinner("Running portfolio-aware RAG pipeline..."):
            res = requests.post(f"{API_BASE}/chat", json=payload, timeout=180)
        if not res.ok:
            st.error(f"Request failed: {res.text}")
        else:
            data = res.json()
            st.subheader("Verdict")
            st.write(data["verdict"])

            st.subheader("Key Insights")
            for line in data.get("key_insights", []):
                st.write(f"- {line}")

            st.subheader("Portfolio Impact")
            st.write(data.get("portfolio_impact", ""))

            st.subheader("LLM Synthesis")
            st.write(data.get("answer", ""))

            st.subheader("Sources")
            cite_df = pd.DataFrame(data.get("citations", []))
            st.dataframe(cite_df, use_container_width=True)

            with st.expander("Debug"):
                st.json(data.get("debug", {}))

with col2:
    st.subheader("Quick Examples")
    for q in [
        "Compare TATAMOTORS vs M_M",
        "Which stock in my portfolio is most risky?",
        "What risks were mentioned in last concall?",
    ]:
        st.code(q)

    st.subheader("CSV Template")
    sample = pd.DataFrame(
        [
            {"symbol": "TATAMOTORS", "allocation": 40, "quantity": 10},
            {"symbol": "M_M", "allocation": 30, "quantity": 8},
            {"symbol": "INFY", "allocation": 30, "quantity": 15},
        ]
    )
    st.dataframe(sample, use_container_width=True)
    st.download_button(
        "Download sample CSV",
        data=sample.to_csv(index=False),
        file_name="portfolio_sample.csv",
        mime="text/csv",
    )
