"""
MSU Research Security Smart Assistant — Clean UI (no sidebar)
Poster demo styled like your Rice RBLPgpt.
"""

import os, re, json, hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Dict
import streamlit as st

# -----------------------
# Minimal demo data layer (kept from your stub)
# -----------------------
MSU_ROOT = "https://www.morgan.edu/office-of-research-administration/research-compliance/research-security"
ALLOWED_DOMAINS = ["morgan.edu", "whitehouse.gov", "ostp.gov", "dni.gov", "nsf.gov"]
DEFAULT_SEED_URLS = [MSU_ROOT, "https://www.whitehouse.gov/ostp/", "https://www.dni.gov/", "https://new.nsf.gov/"]

@dataclass
class DocChunk:
    content: str
    source: str
    title: str
    crawled_at: str

INMEMORY_CHUNKS: List[DocChunk] = []

def domain_allowed(url: str) -> bool:
    return any(d in url for d in ALLOWED_DOMAINS)

def sanitize_text(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()

def ts_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def ingest_sources(seed_urls: List[str]) -> int:
    created, now = 0, ts_now_iso()
    for url in seed_urls:
        if not domain_allowed(url): 
            continue
        txt = f"This is a placeholder summary for {url}. Replace with real crawl/loader content. " \
              f"Cites MSU Research Security or federal guidance as available."
        INMEMORY_CHUNKS.append(DocChunk(txt, url, url, now))
        created += 1
    return created

def retrieve(query: str, k: int = 5) -> List[DocChunk]:
    if not INMEMORY_CHUNKS:
        ingest_sources(DEFAULT_SEED_URLS)
    q = query.lower()
    scored = []
    for ch in INMEMORY_CHUNKS:
        score = sum(ch.content.lower().count(tok) for tok in q.split())
        scored.append((score, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for s, c in scored[:k]]

def synthesize_answer(query: str, chunks: List[DocChunk]) -> Tuple[str, List[Tuple[str, str]]]:
    header = ("**Assistant (demo):**\n"
              "I found guidance related to your question below. This demo uses stubbed text; "
              "wire it to your approved LLM and embeddings for production.\n\n")
    bullets, cites = [], []
    for ch in chunks:
        bullets.append(f"- From **{ch.title}** (crawled {ch.crawled_at}): _{sanitize_text(ch.content[:180])}…_")
        cites.append((ch.title, ch.source))
    body = "\n".join(bullets) if bullets else "- No matching sources yet."
    return header + body + "\n\n", cites

# -----------------------
# UI (no sidebar, centered)
# -----------------------
def hero_header():
    st.markdown(
        """
        <div class="hero">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Morgan_State_University_seal.svg/512px-Morgan_State_University_seal.svg.png" class="logo" />
            <h1>MSU Research Security Assistant</h1>
            <p class="subtitle">Smart Assistant for Pre- &amp; Post-Award Support at Morgan State University</p>
            <p class="trained">Trained on public MSU Research Security pages and federal guidance (demo).</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_sources(cites: List[Tuple[str, str]]):
    if not cites: 
        return
    st.markdown("### Sources")
    for title, url in cites:
        st.markdown(f"- [{title}]({url})")

def main():
    st.set_page_config(page_title="MSU Research Security Assistant", page_icon="🦉", layout="centered")

    # Hide Streamlit chrome + sidebar, add simple style
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

    if "bootstrapped" not in st.session_state:
        ingest_sources(DEFAULT_SEED_URLS)
        st.session_state.bootstrapped = True

    hero_header()

    # Upload (visual only in demo)
    st.markdown("### Upload a file for reference (optional)")
    st.file_uploader("Drag and drop file here (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"], label_visibility="collapsed")

    # Category (visual filter only in demo)
    st.markdown("### Select a category:")
    category = st.selectbox("Select a category", ["All Categories", "Research Security", "Training", "TCP", "Disclosures"], label_visibility="collapsed")

    # Prompt input
    st.markdown("### Start typing your question…")
    if "prompt" not in st.session_state:
        st.session_state.prompt = ""
    prompt = st.text_input("Start typing your question…", value=st.session_state.prompt, label_visibility="collapsed")

    # Suggested prompts (chips)
    st.markdown("### Try asking one of these:")
    suggestions = [
        "What internal documents are needed before submitting a Cayuse proposal at MSU?",
        "How do I route for Chair/Dean approval?",
        "What does NSPM-33 require for disclosures?",
    ]
    c1, c2, c3 = st.columns(3)
    if c1.button(suggestions[0]): st.session_state.prompt = suggestions[0]; st.experimental_rerun()
    if c2.button(suggestions[1]): st.session_state.prompt = suggestions[1]; st.experimental_rerun()
    if c3.button(suggestions[2]): st.session_state.prompt = suggestions[2]; st.experimental_rerun()

    # Search button (aligned to right like a CTA)
    col_q, col_btn = st.columns([0.8, 0.2])
    with col_q:
        q = st.session_state.prompt if st.session_state.prompt else prompt
    with col_btn:
        do_search = st.button("Search", use_container_width=True)

    if do_search and (q or prompt):
        chunks = retrieve(q or prompt, k=5)
        md, cites = synthesize_answer(q or prompt, chunks)
        st.markdown("---")
        st.markdown(md)
        render_sources(cites)

    st.caption("Disclaimer: Demo only; refer to official MSU policy for authoritative guidance.")

if __name__ == "__main__":
    main()
