import streamlit as st
import pandas as pd
from difflib import SequenceMatcher, get_close_matches
from PIL import Image
import base64
from io import BytesIO
# Streamlit rerun shim (works on old & new versions)
try:
    rerun = st.rerun           # Streamlit ≥ 1.27-ish
except AttributeError:
    rerun = st.experimental_rerun  # older versions

# ...later in your code, use:
# rerun()

SUPPORT_EMAIL = "ask.ora@morgan.edu"
CONTACT_NOTE = f"If you still need help, email <a href='mailto:{SUPPORT_EMAIL}'>{SUPPORT_EMAIL}</a>."

# ---------- Helper: Convert Logo to Base64 ----------
def get_image_base64(img):
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

# ---------- Helper: Show Answer with Logo ----------
def show_answer_with_logo(answer_html):
    st.markdown(
        f"""
        <div style='display:flex;align-items:flex-start;margin:10px 0;'>
            <img src='data:image/png;base64,{logo_base64}' width='40' style='margin-right:10px;border-radius:8px;'/>
            <div style='background:#f6f6f6;padding:12px;border-radius:12px;max-width:75%;'>
                {answer_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------- Config & Logo ----------
st.set_page_config(page_title="MSU Research Security Assistant", layout="centered")

try:
    # Place your MSU logo file beside this script as: logo.png
    logo = Image.open("logo.png")
    logo_base64 = get_image_base64(logo)
except Exception:
    logo_base64 = ""

st.markdown(
    f"""
    <div style='text-align:left;'>
        <img src='data:image/png;base64,{logo_base64}' width='150'/>
        <h2>MSU Research Security Assistant</h2>
        <h5><i>Smart Assistant for Research Integrity, Compliance & Security Support</i></h5>
        <p>🛡️ Trained on Morgan State University Research Security topics and federal guidance.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------- File Upload (optional, visual only) ----------
uploaded_file = st.file_uploader("📎 Upload a file for reference (optional)", type=["pdf", "docx", "txt"])
if uploaded_file:
    st.success(f"Uploaded file: {uploaded_file.name}")

# ---------- Load CSV ----------
# Put a file named msu_faq.csv next to this script with columns: Category,Question,Answer
try:
    df = pd.read_csv("msu_faq.csv").fillna("")
except Exception as e:
    st.error("Could not read 'msu_faq.csv'. Make sure it exists and has columns: Category, Question, Answer.")
    df = pd.DataFrame(columns=["Category","Question","Answer"])

# ---------- Session State ----------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "suggested_list" not in st.session_state:
    st.session_state.suggested_list = []
if "last_category" not in st.session_state:
    st.session_state.last_category = ""
if "clear_input" not in st.session_state:
    st.session_state.clear_input = False

# ---------- Category Selection ----------
categories = ["All Categories"] + (sorted(df["Category"].unique()) if not df.empty else [])
category = st.selectbox("📂 Select a category:", categories)

# Reset session if category changes
if st.session_state.last_category != category:
    st.session_state.chat_history = []
    st.session_state.suggested_list = []
    st.session_state.last_category = category
    st.rerun()

selected_df = df if (df.empty or category == "All Categories") else df[df["Category"] == category]

# ---------- Chat Input ----------
question = st.text_input("💬 Start typing your question...", value="" if st.session_state.clear_input else "")
st.session_state.clear_input = False

# ---------- Show Example Questions as Buttons ----------
if not question.strip() and not selected_df.empty:
    st.markdown("💬 Try asking one of these:")
    for i, q in enumerate(selected_df["Question"].head(3)):
        if st.button(q, key=f"example_{i}"):
            st.session_state.chat_history.append({"role": "user", "content": q})
            ans = selected_df[selected_df["Question"] == q].iloc[0]["Answer"]
            st.session_state.chat_history.append({"role": "assistant", "content": f"<b>Answer:</b> {ans}"})
            st.session_state.clear_input = True
            st.rerun()

# ---------- Display Chat ----------
st.markdown("<div style='margin-top:20px;'>", unsafe_allow_html=True)
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.markdown(
            f"""
            <div style='text-align:right;margin:10px 0;'>
                <div style='display:inline-block;background:#e6f7ff;padding:12px;border-radius:12px;max-width:70%;'>
                    <b>You:</b> {msg['content']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        show_answer_with_logo(msg["content"])
st.markdown("</div>", unsafe_allow_html=True)

# ---------- Autocomplete Suggestions ----------
if question.strip() and not selected_df.empty:
    suggestions = [q for q in selected_df["Question"].tolist() if question.lower() in q.lower()][:5]
    if suggestions:
        st.markdown("<div style='margin-top:5px;'><b>Suggestions:</b></div>", unsafe_allow_html=True)
        for s in suggestions:
            if st.button(s, key=f"suggest_{s}"):
                st.session_state.chat_history.append({"role": "user", "content": s})
                ans = selected_df[selected_df["Question"] == s].iloc[0]["Answer"]
                st.session_state.chat_history.append({"role": "assistant", "content": f"<b>Answer:</b> {ans}"})
                st.session_state.clear_input = True
                st.rerun()

# ---------- Submit Question ----------
if st.button("Submit") and question.strip():
    st.session_state.chat_history.append({"role": "user", "content": question})

    previous_suggestions = st.session_state.suggested_list
    st.session_state.suggested_list = []
    st.session_state.clear_input = True  # Clear input after submit

    # Check for exact or close match
    all_questions = selected_df["Question"].tolist() if not selected_df.empty else []
    best_match = None
    best_score = 0
    for q in all_questions:
        score = SequenceMatcher(None, question.lower(), q.lower()).ratio()
        if score > best_score:
            best_match = q
            best_score = score

    if best_match and best_score >= 0.85:  # Only answer if confidence is high
        row = selected_df[selected_df["Question"] == best_match].iloc[0]
        ans = row["Answer"]
        category_note = row["Category"]
        response_text = f"<b>Answer:</b> {ans}<br><i>(Note: This question belongs to the '{category_note}' category.)</i>"
        st.session_state.chat_history.append({"role": "assistant", "content": response_text})
    else:
        if previous_suggestions:
            # User ignored suggestions previously → show best prior global match
            match_q = previous_suggestions[0]
            row = df[df["Question"] == match_q].iloc[0]
            ans = row["Answer"]
            category_note = row["Category"]
            response_text = f"<b>Answer:</b> {ans}<br><i>(Note: This question belongs to the '{category_note}' category.)</i>"
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        else:
            # Suggest top 3 questions instead of giving a wrong answer
            all_q_global = df["Question"].tolist() if not df.empty else []
            top_matches = get_close_matches(question, all_q_global, n=3, cutoff=0.4)
            if top_matches:
                guessed_category = df[df["Question"] == top_matches[0]].iloc[0]["Category"]
                response_text = (f"I couldn't find an exact match, but your question seems related to <b>{guessed_category}</b>.<br><br>" 
                 "Here are some similar questions:<br>"
                 + "".join(f"{i}. {q}<br>" for i, q in enumerate(top_matches, start=1))
                 + "<br>Select one below to see its answer.<br><br>"
                 + CONTACT_NOTE
               )
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})
                st.session_state.suggested_list = top_matches
            else:
                st.session_state.chat_history.append({     "role": "assistant",     "content": "I couldn't find a close match. Please try rephrasing.<br><br>" + CONTACT_NOTE })

    st.rerun()

# ---------- Show Buttons for Top Suggestions ----------
if st.session_state.suggested_list:
    st.markdown("<div style='margin-top:15px;'><b>Choose a question:</b></div>", unsafe_allow_html=True)
    for i, q in enumerate(st.session_state.suggested_list):
        if st.button(q, key=f"choice_{i}"):
            row = df[df["Question"] == q].iloc[0]
            ans = row["Answer"]
            st.session_state.chat_history.append({"role": "assistant", "content": f"<b>Answer:</b> {ans}"})
            st.session_state.suggested_list = []
            st.session_state.clear_input = True
            st.rerun()

# ---------- Download Chat History ----------
if st.session_state.chat_history:
    chat_text = ""
    for msg in st.session_state.chat_history:
        role = "You" if msg["role"] == "user" else "Assistant"
        chat_text += f"{role}: {msg['content']}\n\n"
    b64 = base64.b64encode(chat_text.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="chat_history.txt">📥 Download Chat History</a>'
    st.markdown(href, unsafe_allow_html=True)
