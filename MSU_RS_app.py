
import os
import re
import time
import json
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Dict, Optional

import streamlit as st

# ---- Optional: Uncomment these when running locally ----
# from langchain_community.document_loaders import WebBaseLoader
# from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import FAISS
# from langchain.embeddings import HuggingFaceEmbeddings
# from langchain_community.docstore.document import Document

# Fallback no-langchain tiny helpers so app can render without deps
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore
    HAVE_LANGCHAIN = True
except Exception:
    HAVE_LANGCHAIN = False

# -----------------------
# Config & Constants
# -----------------------
MSU_ROOT = "https://www.morgan.edu/office-of-research-administration/research-compliance/research-security"
ALLOWED_DOMAINS = ["morgan.edu", "whitehouse.gov", "ostp.gov", "dni.gov", "nsf.gov"]
DATA_DIR = "data/msu"
INDEX_DIR = "index/msu"
META_PATH = os.path.join(INDEX_DIR, "meta.json")

DEFAULT_SEED_URLS = [
    MSU_ROOT,
    # Add other relevant MSU Research Security pages here as they exist
    # e.g., training link pages, Research Security Program Committee, TCP info, etc.
    # Federal context pages (NSPM-33/OSTP etc.) can be added for answers that need national policy alignment
    "https://www.whitehouse.gov/ostp/" ,
    "https://www.dni.gov/" ,
    "https://new.nsf.gov/" ,
]

# -----------------------
# Tiny cache for demo
# -----------------------
@dataclass
class DocChunk:
    content: str
    source: str
    title: str
    crawled_at: str  # ISO timestamp

# In-memory store used when vector DB is unavailable (for demo rendering)
INMEMORY_CHUNKS: List[DocChunk] = []

# -----------------------
# Utility helpers
# -----------------------

def domain_allowed(url: str) -> bool:
    return any(d in url for d in ALLOWED_DOMAINS)


def sanitize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def ts_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(INDEX_DIR, exist_ok=True)


def load_meta() -> Dict:
    if os.path.exists(META_PATH):
        try:
            with open(META_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_meta(meta: Dict):
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


# -----------------------
# Ingestion (placeholder)
# -----------------------

def ingest_sources(seed_urls: List[str], chunk_size: int = 2000, chunk_overlap: int = 200) -> int:
    """Crawl/download and chunk sources. For real use, enable LangChain loaders & embeddings.
    Returns number of chunks created.
    """
    ensure_dirs()

    created = 0
    meta = load_meta()
    now = ts_now_iso()

    # DEMO: Statically create one chunk per URL (no network) unless LangChain is installed
    if not HAVE_LANGCHAIN:
        for url in seed_urls:
            if not domain_allowed(url):
                continue
            fake_text = f"This is a placeholder summary for {url}. Replace with real crawl/loader content. " \
                        f"Cites MSU Research Security or federal guidance as available."
            INMEMORY_CHUNKS.append(DocChunk(content=fake_text, source=url, title=url, crawled_at=now))
            created += 1
        meta["last_ingest"] = now
        meta["doc_count"] = len(INMEMORY_CHUNKS)
        save_meta(meta)
        return created

    # REAL PATH (uncomment dependencies at top):
    # loader = WebBaseLoader(seed_urls)
    # docs = loader.load()
    # splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    # split_docs = splitter.split_documents(docs)
    #
    # # Build embeddings & vectorstore
    # embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    # vectordb = FAISS.from_documents(split_docs, embedder)
    # vectordb.save_local(INDEX_DIR)
    #
    # meta["last_ingest"] = now
    # meta["doc_count"] = len(split_docs)
    # save_meta(meta)
    # return len(split_docs)


# -----------------------
# Retrieval (placeholder)
# -----------------------

def retrieve(query: str, k: int = 5) -> List[DocChunk]:
    """Return top-k chunks. Placeholder uses naive keyword match over INMEMORY_CHUNKS."""
    if HAVE_LANGCHAIN and os.path.exists(INDEX_DIR):
        pass  # In real path you'd load FAISS and use similarity_search

    if not INMEMORY_CHUNKS:
        ingest_sources(DEFAULT_SEED_URLS)

    q = query.lower()
    scored = []
    for ch in INMEMORY_CHUNKS:
        score = sum(ch.content.lower().count(tok) for tok in q.split())
        scored.append((score, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for s, c in scored[:k] if s >= 0]


# -----------------------
# Answer synthesis (LLM call placeholder)
# -----------------------

def synthesize_answer(query: str, chunks: List[DocChunk]) -> Tuple[str, List[Tuple[str, str]]]:
    """Create an answer and return (markdown, citations). Replace with real LLM call.
    Citations format: List of (title, url)
    """
    header = (
        "**Assistant (demo):**\n"
        "I found guidance related to your question below. This demo uses stubbed text; "
        "wire it to your approved LLM and embeddings for production.\n\n"
    )

    bullet_lines = []
    cites: List[Tuple[str, str]] = []
    for ch in chunks:
        bullet_lines.append(f"- From **{ch.title}** (crawled {ch.crawled_at}): _{sanitize_text(ch.content[:180])}…_")
        cites.append((ch.title, ch.source))

    body = "\n".join(bullet_lines) if bullet_lines else "- No matching sources yet."
    md = f"{header}{body}\n\n"
    return md, cites


# -----------------------
# UI Components
# -----------------------

def ui_header():
    c1, c2 = st.columns([0.8, 0.2])
    with c1:
        st.markdown("# MSU Research Security Smart Assistant")
        st.markdown(
            "*AI-Driven Research Integrity, Compliance & Security — built for under-resourced teams.*\n\n"
            "**Demo:** answers from public MSU pages and federal guidance; shows sources & crawl time; "
            "no uploads; no sensitive data."
        )
    with c2:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Morgan_State_University_seal.svg/1200px-Morgan_State_University_seal.svg.png",
                 caption="Morgan State University (seal)", use_container_width=True)

    st.divider()


def ui_footer():
    st.divider()
    st.caption(
        "Disclaimer: This assistant provides convenience summaries and links and does not replace official MSU policy. "
        "If unsure, contact the Office of Research Administration."
    )


def render_citations(cites: List[Tuple[str, str]]):
    if not cites:
        return
    st.markdown("### Sources")
    for title, url in cites:
        st.markdown(f"- [{title}]({url})")


# --------- Modes ---------

def mode_ask():
    st.subheader("Ask a Question")
    q = st.text_input("What do you want to know? (e.g., ‘What does NSPM-33 require at MSU?’)")
    if st.button("Search") and q.strip():
        chunks = retrieve(q, k=5)
        md, cites = synthesize_answer(q, chunks)
        st.markdown(md)
        render_citations(cites)


def mode_find():
    st.subheader("Find a Form / Policy")
    q = st.text_input("Type a keyword (e.g., ‘Technology Control Plan’, ‘training’, ‘disclosure’)")
    if st.button("Find") and q.strip():
        chunks = retrieve(q, k=8)
        st.markdown("### Suggested Links")
        for ch in chunks:
            st.markdown(f"- [{ch.title}]({ch.source}) — crawled {ch.crawled_at}")


def mode_checklists():
    st.subheader("Pre- & Post-Award Checklists (Demo)")
    role = st.selectbox("Your role", ["PI/Co-PI", "Department Admin", "ORA Staff"]) 
    phase = st.radio("Phase", ["Pre-Award", "Post-Award"], horizontal=True)

    items_pre = [
        "Complete research security training (CITI/NSF).",
        "Disclose appointments, affiliations, and support per NSPM-33.",
        "Add data management & cybersecurity notes to your proposal.",
        "If controlled tech/data: start a Technology Control Plan (TCP).",
    ]
    items_post = [
        "Confirm all personnel completed required training.",
        "Monitor foreign travel and data handling.",
        "Maintain disclosures/current & pending updates.",
        "If export-controlled: follow TCP and access controls.",
    ]

    items = items_pre if phase == "Pre-Award" else items_post

    done = []
    for i, it in enumerate(items, 1):
        if st.checkbox(it, key=f"chk_{phase}_{i}"):
            done.append(it)

    st.info(f"Checked off {len(done)}/{len(items)} items")


def mode_training():
    st.subheader("Training Tracker (Demo)")
    st.write("Mark completion locally (no server, resets on reload).")
    ppl = st.text_area("Team emails (comma-separated)")
    if st.button("Generate Status"):
        emails = [e.strip() for e in ppl.split(",") if e.strip()]
        if not emails:
            st.warning("Add at least one email.")
        else:
            for em in emails:
                # random-ish demo status
                h = int(hashlib.md5(em.encode()).hexdigest(), 16)
                done = (h % 2 == 0)
                st.write(f"- {em}: {'✅ Completed' if done else '❗ Not recorded'} (demo)")
            st.caption("Connect to CITI/NSF exports or HRIS later for real checks (subject to policy).")


def mode_tcp():
    st.subheader("Technology Control Plan Helper (Demo)")
    proj = st.text_input("Project title")
    pi = st.text_input("PI name")
    data_types = st.multiselect("Controlled items involved", [
        "EAR-controlled tech/data", "ITAR-controlled tech/data", "Export-restricted software",
        "Human-subjects identifiable data", "Other controlled data"
    ])
    controls = st.multiselect("Proposed controls", [
        "Physical lab access restrictions", "Secure data enclave/VPN", "No BYOD for controlled data",
        "Sponsor-approved visitor policy", "Whitelisted collaborators only"
    ])
    if st.button("Generate TCP Summary"):
        if not proj or not pi:
            st.warning("Enter project title and PI.")
        else:
            md = [
                f"### TCP Summary (Demo)",
                f"**Project:** {proj}",
                f"**PI:** {pi}",
                f"**Controlled items:** {', '.join(data_types) if data_types else '—'}",
                f"**Controls:** {', '.join(controls) if controls else '—'}",
                f"**Next step:** Review with ORA; if export-controlled, finalize TCP and access lists.",
            ]
            st.markdown("\n".join(md))


# -----------------------
# Main App
# -----------------------

def main():
    st.set_page_config(page_title="MSU Research Security Smart Assistant", page_icon="🛡️", layout="wide")
    ui_header()

    with st.sidebar:
        st.markdown("### Content")
        if st.button("Ingest/Refresh Sources"):
            n = ingest_sources(DEFAULT_SEED_URLS)
            st.success(f"Ingested {n} source chunks (demo)")
        st.caption("Only public *.morgan.edu and federal policy pages are ingested.")

        st.markdown("### About")
        st.write("This poster demo shows how AI can help answer compliance questions with citations.")

    tabs = st.tabs(["Ask", "Find a Form/Policy", "Checklists", "Training Tracker", "TCP Helper"])
    with tabs[0]:
        mode_ask()
    with tabs[1]:
        mode_find()
    with tabs[2]:
        mode_checklists()
    with tabs[3]:
        mode_training()
    with tabs[4]:
        mode_tcp()

    ui_footer()

