# Web interface (app/ui.py)

import streamlit as st
import requests

st.set_page_config(page_title="Hybrid NOC & DevOps Assistant", layout="wide")

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 1rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        h1 { font-size: 1.7rem !important; margin-bottom: 0.2rem !important; }
        p, label, .stMarkdown, .stAlert { font-size: 1.05rem !important; }
        textarea, input, code { font-size: 1.05rem !important; line-height: 1.4 !important; }

        /* Цвет фона и текста для кнопки Jira */
        .st-key-jira_btn button {
            background-color: #0052CC !important;
            color: #FFFFFF !important;
            border: none !important;
        }
        .st-key-jira_btn button:hover {
            background-color: #0747A6 !important;
            color: #FFFFFF !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


st.title("Hybrid AI Assistant for NOC & DevOps")
st.caption("Zero-Trust Scrubber | Qdrant Vector RAG | FinOps Normalized Cache")

mode = st.sidebar.selectbox("Inference mode (LLM Router)", ["mock", "local", "cloud"])

LOG_NGINX = '2026/11/17 14:22:01 [error] 1024#0: *88 connect() failed (111: Connection refused) while connecting to upstream, client: 10.24.15.8, upstream: "http://192.168.50", token=sk-live-987654321'
LOG_K8S = '2026/11/17 15:10:44 [error] 4096#0: Pod auth-service-7d9f8b crashed with Exit Code 137 (OOMKilled) on node 172.16.40.11, db_password=ProdSecretPass99'

if "selected_log" not in st.session_state:
    st.session_state.selected_log = LOG_NGINX

col_btn1, col_btn2, _ = st.columns([1.2, 1.4, 3])
with col_btn1:
    if st.button("Load Scenario 1: Nginx 502"):
        st.session_state.selected_log = LOG_NGINX
with col_btn2:
    if st.button("Load Scenario 2: K8s OOMKilled"):
        st.session_state.selected_log = LOG_K8S

raw_log = st.text_area("Raw Incident Log:", value=st.session_state.selected_log, height=85)

if st.button("Analyze Incident", type="primary"):
    response = requests.post("http://localhost:8000/analyze", json={"raw_log": raw_log, "mode": mode})
    if response.status_code != 200:
        st.error(f"Server error ({response.status_code})")
        st.stop()
    st.session_state.last_res = response.json()

if "last_res" in st.session_state:
    res = st.session_state.last_res
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Structured Incident Report")
        rep = res["report"]
        st.error(f"Severity: {rep['severity']}")
        st.write(f"**Root Cause:** {rep['root_cause']}")
        st.write(f"**Matched Runbook (Qdrant):** `{rep['runbook_reference']}`")
        st.code(rep["cli_command"], language="bash")

        if st.button("Create Jira/ServiceNow Ticket (Idempotent Tool)", key="jira_btn"):
            t_res = requests.post(
                "http://localhost:8000/create-ticket",
                json={
                    "severity": rep["severity"],
                    "root_cause": rep["root_cause"],
                    "runbook_reference": rep["runbook_reference"],
                },
            ).json()
            if t_res.get("duplicate_prevented"):
                st.warning(f"🛡️ Duplicate prevented! Existing ticket returned: **{t_res['ticket_id']}**")
            else:
                st.success(f"✅ Ticket created once: **{t_res['ticket_id']}**")

    with col2:
        st.subheader("Security & FinOps Telemetry")
        if res["finops"].get("cache_hit"):
            st.success("CACHE HIT (Redis): Normalized pattern matched | Cost: $0.00")
        else:
            st.warning("CACHE MISS: Full RAG + LLM pipeline executed")

        st.info(f"Masked entities (IP/Secrets): {res['security_preview']['masked_entities']}")
        st.text_area("Payload sent to LLM (Scrubbed):", res["security_preview"]["cleaned_log"], height=80)
        st.json(res["finops"])
