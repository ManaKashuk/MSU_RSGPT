import base64, os
import pandas as pd
from difflib import SequenceMatcher, get_close_matches
from PIL import Image
from io import BytesIO
import streamlit as st

# ---------- Page + minimal CSS ----------
st.set_page_config(page_title="MSU Research Security Assistant", page_icon="🦉", layout="centered")
st.markdown("""
<style>
#MainMenu, header, footer {visibility: hidden;}
section[data-testid="stSidebar"] {display:none !important;}
.block-container {max-width: 900px; padding-top: .5rem;}
.hero {text-align:center; margin: .5rem 0 .75rem;}
.hero .logo {width:72px; opacity:.95;}
.hero h1 {margin:.25rem 0; font-size:2rem;}
.hero .subtitle {color:#4b5563; margin:0 0 .2rem;}
.hero .trained {color:#6b7280; font-size:.95rem;}
.answer {background:#f6f6f6; padding:12px; border-radius:12px; max-width:75%;}
.user {text-align:right; margin:10px 0;}
.user > div {display:inline-block; background:#e6f7ff; padding:12px; border-radius:12px; max-width:70%;}
</style>
""", unsafe_allow_html=True)

# ---------- Logo helpers ----------
def _img_to_b64(img: Image.Image) -> str:
    buf = BytesIO(); img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def load_logo_b64(path: str) -> str:
    try:
        return _img_to_b64(Image.open(path))
    except Exception:
        return ""

LOGO_B64 = load_logo_b64("logo.png")  # ensure this file is beside app.py

def show_answer_with_logo(html_answer: str):
    st.markdown(
        f"""
        <div style='display:flex;align-items:flex-start;margin:10px 0;'>
            <img src='data:image/png;base64,{LOGO_B64}' width='40' style='margin-right:10px;border-radius:8px;'/>
            <div class='answer'>{html_answer}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------- Hero ----------
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

# ---------- Load CSV (never crash) ----------
CSV_PATH = "msu_faq.csv"
csv_error = None
try:
    DF = pd.read_csv(CSV_PATH).fillna("")
except Exception as e:
    DF = pd.DataFrame(columns=["Category","Question","Answer"])
    csv_error = str(e)

# ---------- Session ----------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "suggested_list" not in st.session_state:
    st.session_state.suggested_list = []

# ---------- Fusion helpers ----------
def best_csv_match(question: str, df: pd.DataFrame):
    best_q, best_score = "", 0.0
    for q in df["Question"].tolist():
        sc = SequenceMatcher(None, question.lower(), q.lower()).ratio()
        if sc > best_score:
            best_q, best_score = q, sc
    return best_q, best_score

def retrieve_stub(query: str, k: int = 3):
    return [
        {"title":"MSU Research Security (public page)","url":"https://www.morgan.edu/office-of-research-administration/research-compliance/research-security","snippet":"Research Security supports disclosures, training, and risk management aligned to NSPM-33."},
        {"title":"NSPM-33 (overview)","url":"https://www.whitehouse.gov/ostp/","snippet":"Federal standard for research security: disclosures, training, cybersecurity, risk management."},
    ][:k]

def fuse_answer(question: str, category: str):
    df = DF
    if category and category != "All Categories" and not DF.empty:
        df = DF[DF["Category"].str.strip().str.lower() == category.strip().lower()]
        if df.empty: df = DF

    if not df.empty:
        best_q, score = best_csv_match(question, df)
        if score >= 0.85:
            row = df[df["Question"] == best_q].iloc[0]
            return f"<b>Answer:</b> {row['Answer']}<br><i>(Category: {row['Category']})</i>", []

        if 0.60 <= score < 0.85:
            top3 = get_close_matches(question, df['Question'].tolist(), n=3, cutoff=0.4)
            if top3:
                guessed_cat = df[df['Question'] == top3[0]].iloc[0]['Category']
                html = f"I couldn't find an exact match, but your question seems related to <b>{guessed_cat}</b>.<br><br>"
                html += "Here are some similar questions:<br>" + "<br>".join([f"{i+1}. {q}" for i, q in enumerate(top3)])
                html += "<br><br>Select one below to see its answer."
                st.session_state.suggested_list = top3
                return html, []

    hits = retrieve_stub(question, k=3)
    bullets = "<br>".join([f"- <i>{h['title']}</i>: {h['snippet']}" for h in hits])
    cites = [(h["title"], h["url"]) for h in hits]
    return f"<b>Summary (from public sources, demo):</b><br>{bullets}", cites

# ---------- Controls (ALWAYS render) ----------
categories = ["All Categories"]
if not DF.empty:
    categories += sorted([c for c in DF["Category"].unique() if str(c).strip()])

st.markdown("### 📂 Select a category:")
category = st.selectbox("Category", categories, index=0, label_visibility="collapsed")

question = st.text_input("💬 Start typing your question...", value="")

# Example buttons (if CSV present)
if not question.strip() and not DF.empty:
    st.markdown("💬 Try asking one of these:")
    for i, q in enumerate(DF["Question"].head(3)):
        if st.button(q, key=f"example_{i}"):
            st.session_state.chat_history.append({"role":"user","content":q})
            html, cites = fuse_answer(q, category)
            st.session_state.chat_history.append({"role":"assistant","content":html,"cites":cites})

# Submit
if st.button("Submit") and question.strip():
    st.session_state.chat_history.append({"role":"user","content":question})
    html, cites = fuse_answer(question, category)
    st.session_state.chat_history.append({"role":"assistant","content":html,"cites":cites})

# Chat render
st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.markdown(f"<div class='user'><div><b>You:</b> {msg['content']}</div></div>", unsafe_allow_html=True)
    else:
        show_answer_with_logo(msg["content"])
        for title, url in msg.get("cites", []):
            st.markdown(f"- [{title}]({url})")

# Suggestion buttons after a soft match
if st.session_state.suggested_list:
    st.markdown("<div style='margin-top:8px;'><b>Choose a question:</b></div>", unsafe_allow_html=True)
    for i, q in enumerate(st.session_state.suggested_list):
        if st.button(q, key=f"choice_{i}"):
            row = DF[DF["Question"] == q].iloc[0]
            html = f"<b>Answer:</b> {row['Answer']}<br><i>(Category: {row['Category']})</i>"
            st.session_state.chat_history.append({"role":"user","content":q})
            st.session_state.chat_history.append({"role":"assistant","content":html,"cites":[]})
    # clear list only after rendering buttons (so they persist if not clicked)

# ---------- Debug panel (helps diagnose blank screens) ----------
with st.expander("🔧 Debug info (hide before demo)"):
    st.write({"csv_path": CSV_PATH, "csv_exists": os.path.exists(CSV_PATH), "rows": len(DF)})
    if csv_error: st.error(f"CSV load error: {csv_error}")
    st.write("Session keys:", list(st.session_state.keys()))
