# Web interface (app/ui.py)

import streamlit as st
import requests 

st.set_page_config(page_title="Hybrid NOC & DevOps Assistant", layout="wide")

st.markdown(
    """
    <style>
        /* Убираем лишние отступы сверху и по краям экрана */
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        /* Делаем заголовок компактнее */
        h1 {
            font-size: 1.8rem !important;
            margin-bottom: 0.2rem !important;
        }
        /* Увеличиваем основной текст, подписи и поля ввода */
        p, label, .stMarkdown, .stAlert {
            font-size: 1.05rem !important;
        }
        textarea, input {
            font-size: 1.05rem !important;
            line-height: 1.4 !important;
        }
        /* Увеличиваем текст внутри черных блоков кода */
        code {
            font-size: 1.05rem !important;
        }
    </style>
    
        """,
    unsafe_allow_html=True,
)

st.set_page_config(page_title="Hybrid NOC & DevOps Assistant", layout="wide")
st.title("      Hybrid AI Assistant for NOC & DevOps")
st.caption("Security Scrubber (CSP) • RAG Runbooks (Qdrant) • FinOps Cache (Redis)")

mode = st.sidebar.selectbox("Inference mode (LLM Router)", ["mock", "local", "cloud"])
sample_log = '2026/11/17 14:22:01 [error] 1024#0: *88 connect() failed (111: Connection refused) while connecting to upstream, client: 10.24.15.8, server: api.prod.local, upstream: "http://192.168.50", token=sk-live-987654321'

raw_log = st.text_area("Paste the raw incident log:", value=sample_log, height=130)

if st.button("Analyze Incident", type="primary"):
    with st.spinner("Scrubbing secrets -> Searching Runbook -> Analyzing..."):
        response = requests.post("http://localhost:8000/analyze", json={"raw_log": raw_log, "mode": mode})
        if response.status_code != 200:
            st.error(f"Server error ({response.status_code}): check if Ollama/Redis is running or switch to mock mode.")
            st.stop()
        res = response.json()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Structured Report")
        rep = res["report"]
        st.error(f"Criticality: {rep['severity']}")
        st.write(f"**Reason:** {rep['root_cause']}")
        st.write(f"**Runbook (RAG):** `{rep['runbook_reference']}`")
        st.code(rep["cli_command"], language="bash")

    with col2:
        st.subheader("Security & FinOps Telemetry")
        if res["finops"].get("cache_hit"):
            st.success("⚡ CACHE HIT (Redis): Served from cache in 0.01s • Cost: $0.00")
        else:
            st.warning("🔄 CACHE MISS: Full RAG + LLM pipeline executed")

        st.info(f"Hidden entities (IP/Secrets): {res['security_preview']['masked_entities']}")
        st.text_area("What really went into LLM (after Scrubber):", res["security_preview"]["cleaned_log"], height=90)
        st.json(res["finops"])
