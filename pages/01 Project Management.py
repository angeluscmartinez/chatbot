import streamlit as st
from openai import OpenAI
import pandas as pd
import PyPDF2
import random
import string
import json
import os

# **✅ FIX: Set Page Config at the Very Top with a Default Title**
st.set_page_config(page_title="iRIS AI Agent", layout="wide")

# Path to JSON file for persistent storage
PAGES_FILE = "pages.json"

# Function to generate a random 5-character alphanumeric page ID
def generate_random_page_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

# Function to load saved pages from file
def load_pages():
    if os.path.exists(PAGES_FILE):
        with open(PAGES_FILE, "r") as f:
            return json.load(f)
    return {}

# Function to save pages to file
def save_pages():
    with open(PAGES_FILE, "w") as f:
        json.dump(st.session_state["pages"], f)

# **Optimized File Processing**
@st.cache_data
def extract_text_from_file(uploaded_file):
    """Extracts and caches text content from uploaded files."""
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

# Load saved pages at startup
if "pages" not in st.session_state:
    st.session_state["pages"] = load_pages()

# Sidebar: Page Selection (Always Visible if Pages Exist)
st.sidebar.markdown("### 📄 Select a Page")

if st.session_state["pages"]:
    selected_page = st.sidebar.selectbox(
        "Choose a Page",
        options=list(st.session_state["pages"].keys()),
        format_func=lambda x: st.session_state["pages"][x]["name"]
    )
    st.session_state["selected_page"] = selected_page
else:
    st.session_state["selected_page"] = None

# **Get the Page Name for UI Display**
if st.session_state["selected_page"]:
    page_id = st.session_state["selected_page"]
    page_title = st.session_state["pages"][page_id]["name"]  # ✅ Get the user-defined title
else:
    page_title = "iRIS AI Agent"  # Default title

# **✅ FIX: Display the Page Title in UI (Instead of Updating st.set_page_config)**
st.title(page_title)

# **Toggle for showing/hiding page management**
if "show_page_management" not in st.session_state:
    st.session_state["show_page_management"] = False

if st.sidebar.button("⚙️ Manage Pages"):
    st.session_state["show_page_management"] = not st.session_state["show_page_management"]

# **Show Page Management Options**
if st.session_state["show_page_management"]:
    st.sidebar.markdown("### 🗂️ Page Management")

    # **Create New Page**
    new_page_name = st.sidebar.text_input("New Page Name")

    if st.sidebar.button("➕ Create New Page") and new_page_name.strip():
        new_page_id = generate_random_page_id()
        st.session_state["pages"][new_page_id] = {"name": new_page_name.strip()}
        save_pages()

        # Initialize session state for new page
        st.session_state[f"messages_{new_page_id}"] = []
        st.session_state[f"uploaded_content_{new_page_id}"] = ""
        st.session_state[f"file_uploaded_{new_page_id}"] = False

        st.session_state["selected_page"] = new_page_id
        st.rerun()

    if st.session_state["selected_page"]:
        # **Rename Page**
        st.sidebar.markdown("### ✏️ Rename Page")
        rename_input = st.sidebar.text_input("New Page Name", value=page_title)

        if st.sidebar.button("🔄 Rename Page"):
            st.session_state["pages"][page_id]["name"] = rename_input.strip()
            save_pages()
            st.rerun()

        # **Delete Page**
        st.sidebar.markdown("### ❌ Delete Page")
        if st.sidebar.button("🗑️ Delete This Page"):
            del st.session_state["pages"][page_id]
            save_pages()

            keys_to_delete = [key for key in st.session_state.keys() if page_id in key]
            for key in keys_to_delete:
                del st.session_state[key]

            if st.session_state["pages"]:
                st.session_state["selected_page"] = list(st.session_state["pages"].keys())[0]
            else:
                st.session_state["selected_page"] = None

            st.rerun()

# Ensure there's a selected page
if st.session_state["selected_page"] is None:
    st.warning("Create a page to start!")
    st.stop()

# Retrieve the current page ID
page_id = st.session_state["selected_page"]

# Define session-specific keys for this page
session_keys = {
    "messages": f"messages_{page_id}",
    "uploaded_content": f"uploaded_content_{page_id}",
    "file_uploaded": f"file_uploaded_{page_id}",
}

# Initialize session state for this page
for key in session_keys.values():
    if key not in st.session_state:
        st.session_state[key] = [] if "messages" in key else ""

# **Restore Clear Chat Button**
st.sidebar.markdown("### 🧹 Clear Chat")
if st.sidebar.button("🗑️ Clear Chat", key=f"clear_chat_button_{page_id}"):
    st.session_state[session_keys["messages"]] = []
    st.rerun()

# **Optimized Upload Button in Sidebar**
st.sidebar.markdown("### 📂 Upload a File")

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

# **API Client**
client = OpenAI(api_key=st.secrets["API_key"])

# **Display Chat History**
messages = st.session_state.get(session_keys["messages"], [])

for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# **Chat Input**
prompt = st.chat_input("Say something", key=f"chat_input_{page_id}")
if prompt:
    modified_prompt = prompt.replace("Solaris", "Celeris").replace("solaris", "Celeris")

    with st.chat_message("user"):
        st.markdown(modified_prompt)

    st.session_state[session_keys["messages"]].append({"role": "user", "content": modified_prompt})

    # **Faster AI Response: Streamed Results**
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
