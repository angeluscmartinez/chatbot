import streamlit as st
from openai import OpenAI
import pandas as pd
import PyPDF2
import json
import time  # Import time for simulated async effect

# Streamlit Page Configuration
st.set_page_config(page_title="iRIS AI Agent", layout="wide")

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

with col2:
    st.markdown('<div class="image-container">', unsafe_allow_html=True)
    st.image("picture1.png", width=250)
    st.markdown('</div>', unsafe_allow_html=True)

# API Client
client = OpenAI(api_key=st.secrets["API_key"])

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Uploaded File Content and Questions
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False
if "uploaded_content" not in st.session_state:
    st.session_state.uploaded_content = ""
if "generated_questions" not in st.session_state:
    st.session_state.generated_questions = []

# Store Appointment Scheduling Request
if "show_calendar" not in st.session_state:
    st.session_state.show_calendar = False  # Ensures the calendar can be toggled per request

# Calendly Scheduling Embed URL
calendly_embed_url = "https://calendly.com/angel-martinez-celeris-systems/60-minute-iris-demo?embed_domain=www.celeris-systems.com&embed_type=Inline"

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

def generate_questions():
    if st.session_state.uploaded_content:
        prompt = f"Generate two unique and insightful questions based on the following text:\n{st.session_state.uploaded_content}"
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        questions = response.choices[0].message.content.strip().split("\n")
        st.session_state.generated_questions = [q for q in questions if q.strip()][:2]

# File Upload Widget
if not st.session_state.file_uploaded:
    uploaded_file = st.file_uploader("Upload a text, PDF, CSV, or Excel file", type=["txt", "pdf", "csv", "xls", "xlsx"], key="file_uploader")
    if uploaded_file:
        content = extract_text_from_file(uploaded_file)
        if content:
            st.session_state.uploaded_content = content
            generate_questions()
        st.session_state.file_uploaded = True
        st.rerun()

# Layout for Chat Window
col1, col2 = st.columns([4, 1])

with col1:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

with st.sidebar:
    st.markdown("### Settings")
    if st.button("🗑️ Clear Chat", key="clear_chat_button"):
        st.session_state.messages = []
        st.session_state.show_calendar = False  # Reset calendar view
        st.session_state.generated_questions = []  # Clear suggested questions
        generate_questions()
        st.rerun()

# Chat Input
prompt = st.chat_input("Say something")
if prompt:
    # Replace 'Solaris' or 'solaris' with 'Celeris'
    modified_prompt = prompt.replace("Solaris", "Celeris").replace("solaris", "Celeris")
    
    with st.chat_message("user"):
        st.markdown(modified_prompt)
    st.session_state.messages.append({"role": "user", "content": modified_prompt})
    
    # Detect Intent Using OpenAI GPT
    intent_prompt = f"Analyze this user query: '{modified_prompt}'. Does it indicate an intent to schedule a meeting? Reply with just one word: 'yes' or 'no'."
    
    intent_response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": intent_prompt}]
    )
    
    detected_intent = intent_response.choices[0].message.content.strip().lower()

    with st.chat_message("assistant"):
        if detected_intent == "yes":
            st.session_state.show_calendar = True  # Allow multiple scheduling requests
            response = "Sure! You can schedule an appointment using the embedded calendar below."
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

# Display Embedded Calendly Scheduler in Chat (Async Load Simulation)
if st.session_state.show_calendar:
    st.markdown("### Book an Appointment Below:")
    
    # Simulating async loading with Streamlit placeholder
    with st.spinner("📅 Loading calendar..."):
        time.sleep(1)  # Small delay to simulate async effect

    st.components.v1.iframe(
        src=calendly_embed_url,
        width=800,
        height=900
    )

    # Button to Hide Calendar After Scheduling
    if st.button("✅ I Have Scheduled My Appointment", key=f"confirm_appointment_{len(st.session_state.messages)}"):
        st.session_state.show_calendar = False  # Hide the calendar
        st.rerun()

# Display Suggested Questions After Chat Response
if st.session_state.generated_questions:
    st.markdown("### Suggested Questions:")
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
