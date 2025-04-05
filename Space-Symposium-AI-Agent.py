import streamlit as st
from openai import OpenAI
import pandas as pd
import PyPDF2
import json
import time
import os

# Streamlit Page Configuration
st.set_page_config(page_title="iRIS AI Agent", layout="wide")

# Constants for default file loading
CORPORATE_FOLDER = "corporate"
DEFAULT_FILE = "web.txt"  # Change this to your actual file name

def extract_text_from_file(uploaded_file):
    if uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.type == "application/pdf":
        reader = PyPDF2.PdfReader(uploaded_file)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    elif uploaded_file.type in ["text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        df = pd.read_csv(uploaded_file) if "csv" in uploaded_file.type else pd.read_excel(uploaded_file)
        return df.to_string()
    return ""

@st.cache_data(show_spinner=False)
def generate_questions(uploaded_content):
    """Generate two unique and insightful questions quickly."""
    if uploaded_content:
        with st.spinner("Generating questions..."):
            prompt = f"Generate two unique and insightful questions based on the following text:\n{uploaded_content[:1000]}"
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            questions = response.choices[0].message.content.strip().split("\n")
            return [q for q in questions if q.strip()][:2]
    return []

def load_default_file(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            if path.endswith(".pdf"):
                reader = PyPDF2.PdfReader(f)
                return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            elif path.endswith(".txt"):
                return f.read().decode("utf-8")
            elif path.endswith(".csv"):
                df = pd.read_csv(f)
                return df.to_string()
            elif path.endswith((".xls", ".xlsx")):
                df = pd.read_excel(f)
                return df.to_string()
    return ""

# API Client
client = OpenAI(api_key=st.secrets["API_key"])

# Initialize Session State Variables
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_content" not in st.session_state:
    st.session_state.uploaded_content = ""
if "generated_questions" not in st.session_state:
    st.session_state.generated_questions = []
if "show_calendar" not in st.session_state:
    st.session_state.show_calendar = False
if "show_dashboard" not in st.session_state:
    st.session_state.show_dashboard = False
if "show_ml_dashboard" not in st.session_state:
    st.session_state.show_ml_dashboard = False
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False

# Load default file from /corporate directory
default_file_path = os.path.join(CORPORATE_FOLDER, DEFAULT_FILE)
if not st.session_state.get("file_uploaded"):
    loaded_content = load_default_file(default_file_path)
    if loaded_content:
        st.session_state.uploaded_content = loaded_content
        st.session_state.generated_questions = generate_questions(loaded_content)
        st.session_state.file_uploaded = True

# Sidebar Configuration (Remove uploader, keep buttons)
with st.sidebar:
    if st.button("\U0001F5D1️ Clear Chat", key="clear_chat_sidebar"):
        st.session_state.messages = []
        st.session_state.show_calendar = False
        st.session_state.show_dashboard = False
        st.session_state.show_ml_dashboard = False
        if st.session_state.uploaded_content:
            st.session_state.generated_questions = generate_questions(st.session_state.uploaded_content)
        st.rerun()

    if st.button("\U0001F504 Generate New Questions", key="generate_questions_btn"):
        if st.session_state.uploaded_content:
            st.session_state.generated_questions = generate_questions(st.session_state.uploaded_content)

#################
st.markdown(
    """
    <style>
    /* Sidebar background */
    [data-testid="stSidebar"] {
        background-color: #CC6600;
    }

    /* All nested text & icons white */
    [data-testid="stSidebar"] * {
        color: white !important;
        fill: white !important;
    }

    /* Buttons */
    [data-testid="stSidebar"] button {
        background-color: #CC6600 !important;
        color: white !important;
        border: 1px solid white !important;
    }

    /* Bruteforce override for uploader */
    [data-testid="stSidebar"] .stFileUploader * {
        background-color: #CC6600 !important;
        color: white !important;
        border: none !important;
        box-shadow: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    [data-testid="stSidebar"] .stFileUploader label,
    [data-testid="stSidebar"] .stFileUploader label > div,
    [data-testid="stSidebar"] .stFileUploader label > div > div,
    [data-testid="stSidebar"] .stFileUploader div div div div div {
        background-color: #CC6600 !important;
        color: white !important;
    }

    [data-testid="stSidebar"] .stFileUploader svg {
        fill: white !important;
    }

    [data-testid="stSidebar"] input[type="file"] {
        opacity: 0.0001;
        background: transparent !important;
    }

    /* ✅ Restore safe spacing to prevent page shift */
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


#########################
st.markdown(
    """
    <style>
    /* Restore vertical spacing to main content area */
    [data-testid="stAppViewContainer"] > .main {
        padding-top: 1.5rem !important;
    }

    /* Optional: Add spacing under the title if needed */
    h1 {
        margin-top: 0 !important;
        margin-bottom: 0.5rem !important;
    }

    /* Restore vertical spacing in the main area only */
    .block-container {
        padding-top: 1rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

######################

# Custom CSS for precise logo positioning
st.markdown(
    """
    <style>
    .image-container {
        position: relative;
        left: -5px;
        top: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Layout for title with image
col1, col2 = st.columns([5, 1], gap="medium")

with col1:
    st.title("I'm Your Helpful iRIS AI Agent, Ask Me Anything")
    st.write("#### Let’s Talk Mission Readiness! 🚀 Discover how we can enhance your mission preparedness with expert engineering services and our AI-enabled mission integration platform, iRIS!")
with col2:
    st.markdown('<div class="image-container">', unsafe_allow_html=True)
    st.image("picture1.png", width=250)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")  # horizontal rule across the full width

# API Client
client = OpenAI(api_key=st.secrets["API_key"])

# Initialize Session State Variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_content" not in st.session_state:
    st.session_state.uploaded_content = ""

if "generated_questions" not in st.session_state:
    st.session_state.generated_questions = []

if "show_calendar" not in st.session_state:
    st.session_state.show_calendar = False

if "show_dashboard" not in st.session_state:
    st.session_state.show_dashboard = False

if "show_ml_dashboard" not in st.session_state:  # 
    st.session_state.show_ml_dashboard = False

if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False  # ✅ Initialize file upload tracking

# Embed URLs
calendly_embed_url = "https://calendly.com/angel-martinez-celeris-systems/meeting-request?embed_domain=www.celeris-systems.com&embed_type=Inline"
power_bi_embed_url = "https://app.powerbi.com/view?r=eyJrIjoiNGFkM2EzZTUtNDdlZi00MmFiLWJlMzMtM2ZjNjg0Y2U5NGJiIiwidCI6ImI4MzcyZThhLTJmZDYtNDYxYi04ZjY2LTk5MGNiNmNlMjcyNiIsImMiOjZ9"
power_bi_ml_embed_url = "https://app.powerbi.com/view?r=eyJrIjoiNTA2NTlkMzctYWJhOS00ZjY1LWE1ZTItNTM5NmJlMzA1ZTI0IiwidCI6ImI4MzcyZThhLTJmZDYtNDYxYi04ZjY2LTk5MGNiNmNlMjcyNiIsImMiOjZ9"

# File Processing Function
def extract_text_from_file(uploaded_file):
    if uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.type == "application/pdf":
        reader = PyPDF2.PdfReader(uploaded_file)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    elif uploaded_file.type in ["text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        df = pd.read_csv(uploaded_file) if "csv" in uploaded_file.type else pd.read_excel(uploaded_file)
        return df.to_string()
    return ""

# Optimized Question Generation Function
@st.cache_data(show_spinner=False)  # Cache to speed up repeated calls
def generate_questions(uploaded_content):
    """Generate two unique and insightful questions quickly."""
    if uploaded_content:
        with st.spinner("Generating questions..."):
            prompt = f"Generate two unique and insightful questions based on the following text:\n{uploaded_content[:1000]}"  # Limit text length
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            questions = response.choices[0].message.content.strip().split("\n")
            return [q for q in questions if q.strip()][:2]  # Return first 2 clean questions
    return []

# Question Generation Function
def generate_questions():
    """Generates two new questions based on uploaded content and updates session state."""
    if st.session_state.uploaded_content:
        prompt = f"Generate two unique and insightful questions based on the following text:\n{st.session_state.uploaded_content}"
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}]
        )

        # ✅ Extract questions and update session state
        questions = response.choices[0].message.content.strip().split("\n")
        st.session_state.generated_questions = [q.strip() for q in questions if q.strip()][:2]

    # ✅ Upload a file (Only if not already uploaded)
    if not st.session_state.file_uploaded:
        uploaded_file = st.file_uploader(
            "Upload a text, PDF, CSV, or Excel file",
            type=["txt", "pdf", "csv", "xls", "xlsx"],
            key="file_uploader"
        )

        if uploaded_file:
            content = extract_text_from_file(uploaded_file)
            if content:
                st.session_state.uploaded_content = content
                generate_questions()  # ✅ Ensures questions are generated immediately
            st.session_state.file_uploaded = True
            st.success("✅ File uploaded successfully!")
            st.rerun()

    # ✅ "Clear Chat" button (Preserves Uploads & Regenerates Questions)
    if st.button("🗑️ Clear Chat", key="clear_chat_btn_sidebar"):
        st.session_state.messages = []  # ✅ Clears only chat history
        st.session_state.show_calendar = False
        st.session_state.show_dashboard = False
        st.session_state.show_ml_dashboard = False

        # ✅ Regenerate questions if a file is uploaded
        if st.session_state.uploaded_content:
            generate_questions()  # ✅ This now properly updates the session state

        st.rerun()  # ✅ UI refresh to reflect new questions

    # ✅ Button to Generate Suggested Questions Manually
    #if st.button("🔄 Generate New Questions", key="generate_questions_button"):
    #    if st.session_state.uploaded_content:
    #        generate_questions()  # ✅ Ensures new questions are generated
    #        st.rerun()  # ✅ UI refresh to reflect new questions
    #    else:
    #        st.warning("⚠️ Please upload a file first before generating questions.")

# Layout for Chat Window
col1, col2 = st.columns([4, 1])

with col1:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat Input
prompt = st.chat_input("Say something")
if prompt:
    modified_prompt = prompt.replace("Solaris", "Celeris").replace("solaris", "Celeris")

    with st.chat_message("user"):
        st.markdown(modified_prompt)
    st.session_state.messages.append({"role": "user", "content": modified_prompt})

    intent_prompt = f"""
    Analyze this user query: {repr(modified_prompt)}. 
    Does it indicate an intent to:
    - Schedule a meeting? Reply with 'schedule'.
    - View a dashboard, report, or metrics? Reply with 'dashboard'.
    - View machine learning? Reply with 'ml_dashboard'.
    - Neither? Reply with 'none'.
    """

    intent_response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": intent_prompt}]
    )

    detected_intent = intent_response.choices[0].message.content.strip().lower()

    with st.chat_message("assistant"):
        if detected_intent == "schedule":
            st.session_state.show_calendar = True
            response = "Sure! You can schedule an appointment using the embedded calendar below."
            st.markdown(response)
        elif detected_intent == "dashboard":
            st.session_state.show_dashboard = True
            response = "Here is the live **Dashboard** with real-time metrics."
            st.markdown(response)
        elif detected_intent == "ml_dashboard":
            st.session_state.show_ml_dashboard = True
            st.write(f"Debug: Detected Intent - {detected_intent}")
            response = "Here is your **ml_dashboard** with mission success predictions based on various input scenarios."
            st.markdown(response)
        else:
            context = ""
            if st.session_state.uploaded_content:
                context = f"\n\nAdditional Context from Uploaded File:\n{st.session_state.uploaded_content}"

            stream = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": modified_prompt + context}],
                stream=True
            )
            response = st.write_stream(stream)

    st.session_state.messages.append({"role": "assistant", "content": response})
    generate_questions()
    st.rerun()

# Display Embedded Calendly Scheduler in Chat
if st.session_state.show_calendar:
    st.markdown("### Book an Appointment Below:")
    st.components.v1.iframe(
        src=calendly_embed_url,
        width=800,
        height=900
    )
    if st.button("✅ Close scheduler", key="close_scheduler"):
        st.session_state.show_calendar = False
        st.rerun()

# Display Embedded Power BI Dashboard in Chat
if st.session_state.show_dashboard:
    st.markdown("### Live Dashboard:")
    st.components.v1.iframe(
        src=power_bi_embed_url,
        width=1000,
        height=650
    )
    if st.button("❌ Close Dashboard", key="close_dashboard"):
        st.session_state.show_dashboard = False
        st.rerun()

# Display Embedded ML Dashboard in Chat
if st.session_state.show_ml_dashboard:
    st.markdown("### Machine Learning Dashboard:")
    st.components.v1.iframe(
        src=power_bi_ml_embed_url,
        width=1000,
        height=650
    )
    if st.button("❌ Close Dashboard", key="close_ml_dashboard"):
        st.session_state.show_ml_dashboard = False
        st.rerun()

# Display Suggested Questions After Chat Response
if st.session_state.generated_questions:
    st.markdown("### Click Suggested Questions or enter your own in the chat window below:")
    for i, question in enumerate(st.session_state.generated_questions):
        if st.button(question, key=f"question_{i}"):
            st.session_state.messages.append({"role": "user", "content": question})

            with st.chat_message("assistant"):
                stream = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=st.session_state.messages,
                    stream=True
                )
                response = st.write_stream(stream)

            st.session_state.messages.append({"role": "assistant", "content": response})
            generate_questions()
            st.rerun()
