import streamlit as st
from openai import OpenAI
import pandas as pd
import PyPDF2
import random
import string
import json
import os
import base64

# ✅ 1. Set initial page config (you can keep this static)
st.set_page_config(page_title="iRIS AI Agent", layout="wide")

# ✅ 2. Optional CSS: Push content down to account for custom banner
st.markdown("""
    <style>
        .block-container {
            padding-top: 5rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Constants
DEFAULT_TITLE = "Select a project from the drop-down menu"
PAGES_FILE = "pages.json"

# Utilities
def generate_random_page_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def load_pages():
    if os.path.exists(PAGES_FILE):
        with open(PAGES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_pages():
    with open(PAGES_FILE, "w") as f:
        json.dump(st.session_state["pages"], f)

def extract_text_from_file(uploaded_file):
    file_text = ""
    if uploaded_file.type == "text/plain":
        file_text = uploaded_file.read().decode("utf-8")
    elif uploaded_file.type == "application/pdf":
        reader = PyPDF2.PdfReader(uploaded_file)
        file_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    elif uploaded_file.type in ["text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        df = pd.read_csv(uploaded_file) if "csv" in uploaded_file.type else pd.read_excel(uploaded_file)
        file_text = df.to_string()
    return file_text if file_text else "⚠️ No readable content found."

# ✅ 3. Initialize session state and determine selected page + title
if "pages" not in st.session_state:
    st.session_state["pages"] = load_pages()

if "current_page_id" not in st.session_state:
    st.session_state["current_page_id"] = generate_random_page_id()

if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = None

# --- Sidebar: Select a Page ---
#st.sidebar.markdown("### 📄 Select a Page")

# ✅ Handle a newly created page (before selectbox is rendered)
if "pending_new_page_id" in st.session_state:
    st.session_state["selected_page"] = st.session_state["pending_new_page_id"]
    del st.session_state["pending_new_page_id"]
    st.rerun()

if st.session_state["pages"]:
    page_keys = list(st.session_state["pages"].keys())

    st.sidebar.selectbox(
        "Choose a Project",
        options=page_keys,
        format_func=lambda x: st.session_state["pages"][x].get("name", f"Untitled Page ({x})"),
        key="selected_page"
    )

    if "last_selected_page" not in st.session_state:
        st.session_state["last_selected_page"] = st.session_state["selected_page"]

    if st.session_state["selected_page"] != st.session_state["last_selected_page"]:
        st.session_state["last_selected_page"] = st.session_state["selected_page"]
        st.rerun()
else:
    st.session_state["selected_page"] = None

# Refresh page title if changed
if st.session_state["selected_page"]:
    page_id = st.session_state["selected_page"]
    page_title = st.session_state["pages"].get(page_id, {}).get("name", DEFAULT_TITLE)
else:
    page_title = DEFAULT_TITLE

# ✅ 4. Render custom top banner with dynamic title
image_path = "picture1.png"
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

image_html = ""
if os.path.exists(image_path):
    encoded_image = get_base64_image(image_path)
    image_html = f'<img src="data:image/png;base64,{encoded_image}" style="height:60px; margin-left: 20px;">'

st.markdown(
    f"""
    <style>
        .top-banner {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 1rem;
            background-color: white;
            z-index: 9999;
        }}
        .top-banner h1 {{
            font-size: 3em;
            font-weight: bold;
            margin: 0;
        }}
    </style>
    <div class="top-banner">
        <h1>{page_title}</h1>
        {image_html}
    </div>
    """,
    unsafe_allow_html=True
)

# ✅ 5. Spacer to avoid content being hidden under banner
st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)

# --- Sidebar: Page Management ---
if "show_page_management" not in st.session_state:
    st.session_state["show_page_management"] = False

if st.sidebar.button("⚙️ Manage Pages"):
    st.session_state["show_page_management"] = not st.session_state["show_page_management"]

if st.session_state["show_page_management"]:
    st.sidebar.markdown("### 🗂️ Page Management")
    new_page_name = st.sidebar.text_input("New Page Name")

    if st.sidebar.button("➕ Create New Page") and new_page_name.strip():
        new_page_id = generate_random_page_id()
        st.session_state["pages"][new_page_id] = {"name": new_page_name.strip()}
        save_pages()
        st.session_state[f"messages_{new_page_id}"] = []
        st.session_state[f"uploaded_content_{new_page_id}"] = ""
        st.session_state[f"file_uploaded_{new_page_id}"] = False

        # ✅ Safe update using pending flag
        st.session_state["pending_new_page_id"] = new_page_id
        st.rerun()

    if st.session_state["selected_page"]:
        page_id = st.session_state["selected_page"]
        page_title = st.session_state["pages"].get(page_id, {}).get("name", DEFAULT_TITLE)

        st.sidebar.markdown("### ✏️ Rename Page")
        rename_input = st.sidebar.text_input("New Page Name", value=page_title)

        if st.sidebar.button("🔄 Rename Page"):
            st.session_state["pages"][page_id]["name"] = rename_input.strip()
            save_pages()
            st.rerun()

        st.sidebar.markdown("### ❌ Delete Page")
        if st.sidebar.button("🗑️ Delete This Page"):
            del st.session_state["pages"][page_id]
            save_pages()
            keys_to_delete = [key for key in st.session_state.keys() if page_id in key]
            for key in keys_to_delete:
                del st.session_state[key]

            if st.session_state["pages"]:
                st.session_state["pending_new_page_id"] = list(st.session_state["pages"].keys())[0]
            else:
                st.session_state["pending_new_page_id"] = None

            st.rerun()

# Ensure a page exists
if st.session_state["selected_page"] is None:
    #st.warning("Create a page to start!")
    st.stop()

# Session keys
page_id = st.session_state["selected_page"]
session_keys = {
    "messages": f"messages_{page_id}",
    "uploaded_content": f"uploaded_content_{page_id}",
    "file_uploaded": f"file_uploaded_{page_id}",
}

# Init session keys
for key in session_keys.values():
    if key not in st.session_state:
        st.session_state[key] = [] if "messages" in key else ""

# Clear chat
st.sidebar.markdown("### 🧹 Clear Chat")
if st.sidebar.button("🗑️ Clear Chat", key=f"clear_chat_button_{page_id}"):
    st.session_state[session_keys["messages"]] = []
    st.rerun()

# File upload
#st.sidebar.markdown("### 📂 Upload a File")
if not st.session_state[session_keys["file_uploaded"]]:  
    uploaded_file = st.sidebar.file_uploader(
        "Upload a text, PDF, CSV, or Excel file",
        type=["txt", "pdf", "csv", "xls", "xlsx"],
        key=f"file_uploader_{page_id}"
    )
    if uploaded_file:
        content = extract_text_from_file(uploaded_file)
        st.session_state[session_keys["uploaded_content"]] = content
        st.session_state[session_keys["file_uploaded"]] = True
        st.success("✅ File uploaded and analyzed successfully!")
        st.rerun()

# API Client
client = OpenAI(api_key=st.secrets["API_key"])

# Display chat history
messages = st.session_state.get(session_keys["messages"], [])
for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
prompt = st.chat_input("Say something", key=f"chat_input_{page_id}")
if prompt:
    modified_prompt = prompt.replace("Solaris", "Celeris").replace("solaris", "Celeris")
    with st.chat_message("user"):
        st.markdown(modified_prompt)
    st.session_state[session_keys["messages"]].append({"role": "user", "content": modified_prompt})
    file_context = st.session_state.get(session_keys["uploaded_content"], "")
    context = f"\n\nContext from Uploaded File:\n{file_context}" if file_context else ""

    with st.chat_message("assistant"):
        response_stream = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": modified_prompt + context}],
            stream=True
        )
        response = st.write_stream(response_stream)

    st.session_state[session_keys["messages"]].append({"role": "assistant", "content": response})
    st.rerun()
