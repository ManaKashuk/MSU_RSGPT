import os, re, base64
import pandas as pd
from difflib import SequenceMatcher, get_close_matches
from PIL import Image
from io import BytesIO
from datetime import datetime
import streamlit as st

pip install -r requirements.txt
streamlit run app.py

# -----------------------
# Page setup & minimal styling (no sidebar)
# -----------------------
st.set_page_config(page_title="MSU Research Security Assistant", page_icon="🦉", layout="centered")
st.markdown(
    """
    <style>
    #MainMenu, header, footer {visibility: hidden;}
    section[data-testid="stSidebar"] {display:none !important;}
    .block-container {max-width: 900px; padding-top: 0.5rem;}
    .hero {text-align:center; margin: 0.5rem 0 0.75rem;}
    .hero .logo {width:72px; opacity:0.95;}
    .hero h1 {margin: 0.25rem 0; font-size: 2.0rem;}
    .hero .subtitle {color:#4b5563; margin: 0 0 0.2rem;}
    .hero .trained {color:#6b7280; font-size:0.95rem;}
    .chips button {margin-right: 0.5rem; margin-bottom: 0.5rem;}
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------
# Logo helpers
# -----------------------
def _img_to_b64(img: Image.Image) -> str:
    buf = BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def load_logo_b64(path: str) -> str:
    try:
        return _img_to_b64(Image.open(path))
    except Exception:
        return ""

LOGO_B64 = load_logo_b64("logo.png")  # put your logo.png next to app.py

def show_answer_with_logo(html_answer: str):
    st.markdown(
        f"""
        <div style='display:flex;align-items:flex-start;margin:10px 0;'>
            <img src='data:image/png;base64,{LOGO_B64}' width='40' style='margin-right:10px;border-radius:8px;'/>
            <div style='background:#f6f6f6;padding:12px;border-radius:12px;max-width:75%;'>
                {html_answer}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------
# Hero header
# -----------------------
st.markdown(
    f"""
    <div class='hero'>
        <img src='data:image/png;base64,{LOGO_B64}' class='logo' />
        <h1>MSU Research Security Assistant</h1>
        <p class='subtitle'>Smart Assistant for Pre- &amp; Post-Award Support at Morgan State University</p>
        <p class='trained'>Trained on MSU Research Security topics and federal guidance (demo).</p>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------
# CSV knowledge base
# -----------------------
CSV_PATH = "msu_faq.csv"
try:
    DF = pd.read_csv(CSV_PATH).fillna("")
except Exception as e:
    st.error(f"Could not read {CSV_PATH}: {e}")
    DF = pd.DataFrame(columns=["Category","Question","Answer"])

# Session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "suggested_list" not in st.session_state:
    st.session_state.suggested_list = []
if "last_category" not in st.session_state:
    st.session_state.last_category = ""

# -----------------------
# Fusion helpers (CSV first, then RAG stub)
# -----------------------
def best_csv_match(question: str, df: pd.DataFrame):
    best_q, best_score = "", 0.0
    for q in df["Question"].tolist():
        sc = SequenceMatcher(None, question.lower(), q.lower()).ratio()
        if sc > best_score:
            best_q, best_score = q, sc
    return best_q, best_score

def retrieve_stub(query: str, k: int = 5):
    # placeholder “retrieval” — swap with your real RAG later
    demo = [
        {
            "title": "MSU Research Security (public page)",
            "url": "https://www.morgan.edu/office-of-research-administration/research-compliance/research-security",
            "snippet": "Research Security supports disclosures, training, and risk management aligned to NSPM-33."
        },
        {
            "title": "NSPM-33 (overview)",
            "url": "https://www.whitehouse.gov/ostp/",
            "snippet": "Federal standard for research security: disclosure, training, cybersecurity, and risk management."
        }
    ][:k]
    return demo

def fuse_answer(question: str, category: str):
    # Category filter
    df = DF
    if category and category != "All Categories" and not DF.empty:
        df = DF[DF["Category"].str.strip().str.lower() == category.strip().lower()]
