import streamlit as st
from openai import OpenAI
import pandas as pd
import json
import io
import time
import pdfplumber
from streamlit_lottie import st_lottie

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["API_key"])

def load_lottiefile(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)

def generate_response_and_suggestions(prompt, context):
    """Generate a response and suggested follow-up questions in a single call."""
    full_query = f"Context from the uploaded file:\n{context}\n\nUser question: {prompt}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": full_query}
            ],
            max_tokens=1100,
            temperature=0.3  # More deterministic responses
        )
        response_text = response.choices[0].message.content
        
        # Generate follow-up questions in the same call
        follow_up_prompt = "Based on the response above, suggest two relevant follow-up questions."
        follow_up_response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Suggest two follow-up questions strictly related to the document."},
                {"role": "user", "content": response_text + "\n" + follow_up_prompt}
            ],
            max_tokens=100,
            temperature=0.3
        )
        suggestions = follow_up_response.choices[0].message.content.split("\n")

        return response_text, [q.strip() for q in suggestions if q.strip()][:2]
    
    except Exception as e:
        return f"Error: {e}", []

def process_uploaded_file(uploaded_file):
    """Process uploaded file efficiently."""
    try:
        if uploaded_file.type == "application/pdf":
            with pdfplumber.open(uploaded_file) as pdf:
                full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            return full_text[:9000]
        
        elif uploaded_file.type == "text/plain":
            return uploaded_file.read().decode("utf-8")[:9000]

        elif uploaded_file.type == "text/csv":
            return pd.read_csv(io.StringIO(uploaded_file.getvalue().decode()))
        
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return None

st.set_page_config(page_title="iRIS Agent", page_icon=":guardsman:", layout="wide")

# Hide Streamlit default style
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        max-width: 1600px;
        margin: auto;
    }
    .stChatMessage, .stMarkdown, .stTextArea, .stButton, .stTextInput, .stSubheader, .stChatMessage {
        max-width: 1500px;
    }
    .stFileUploader {
        max-width: 450px;
        margin-left: 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns([1, 3, 1.5], gap='medium')
with col1:
    st.markdown("<div style='display: flex; align-items: center; justify-content: center; height: auto; align-items: flex-end;'>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 75px;'></div>", unsafe_allow_html=True)
    st.image("Picture1.png", width=316)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height: 92px;'></div>", unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div style="text-align: center; display: flex; align-items: center; justify-content: center; height: auto; align-items: flex-end;">
        <h1 style="margin: auto; margin-top: 50px; margin-left: 50px;">I'm Your Helpful iRIS AI Agent, Ask Me Anything</h1>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("<div style='display: flex; align-items: center; justify-content: center; height: auto; align-items: flex-end;'>", unsafe_allow_html=True)
    try:
        lottie_coding = load_lottiefile("coding.json")
    except FileNotFoundError:
        lottie_coding = None
    if lottie_coding:
        st.markdown("<div style='margin-bottom: -25px;'></div>", unsafe_allow_html=True)
        st_lottie(lottie_coding, speed=2, reverse=False, loop=True, quality="high", height=180, width=410, key="lottie_coding")
    st.markdown("</div>", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_content" not in st.session_state:
    st.session_state.uploaded_content = ""
    st.session_state.uploaded_df = None
    st.session_state.show_upload_widget = True
    st.session_state.suggested_questions = []

# File upload handling
if st.session_state.show_upload_widget:
    uploaded_file = st.file_uploader("Upload Training Data", type=["pdf", "txt", "csv"], label_visibility='hidden')
    if uploaded_file:
        processed_content = process_uploaded_file(uploaded_file)
        if processed_content is not None:
            if isinstance(processed_content, pd.DataFrame):
                st.session_state.uploaded_df = processed_content
            else:
                st.session_state.uploaded_content = processed_content
            st.session_state.show_upload_widget = False
            file_context = st.session_state.uploaded_content or st.session_state.uploaded_df.head(50).to_csv(index=False)
            _, suggested_questions = generate_response_and_suggestions("What insights can I get from this data?", file_context)
            st.session_state.suggested_questions = suggested_questions
        st.markdown("<script>window.scrollTo(0, 0);</script>", unsafe_allow_html=True)

st.rerun()

# Chat input form
with st.form(key="input_form", clear_on_submit=True):
    user_input = st.text_input("You: ", key="user_input", placeholder="Type your message here...")
    submit_button = st.form_submit_button(label="Submit")

if submit_button and user_input:
    file_context = st.session_state.uploaded_content or (st.session_state.uploaded_df.head(50).to_csv(index=False) if st.session_state.uploaded_df is not None else "")
    st.session_state.messages.insert(0, {"role": "user", "content": user_input})
    response_text, suggested_questions = generate_response_and_suggestions(user_input, file_context)
    st.session_state.messages.insert(0, {"role": "assistant", "content": response_text})
    st.session_state.suggested_questions = suggested_questions
    st.rerun()

# Display last 10 messages only
for message in st.session_state.messages[-10:]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Display suggested questions
if st.session_state.suggested_questions:
    st.subheader("Suggested Questions:")
    for i, question in enumerate(st.session_state.suggested_questions):
        if st.button(question, key=f"suggestion_{i}"):
            file_context = st.session_state.uploaded_content or (st.session_state.uploaded_df.head(50).to_csv(index=False) if st.session_state.uploaded_df is not None else "")
            st.session_state.messages.insert(0, {"role": "user", "content": question})
            response_text, new_suggestions = generate_response_and_suggestions(question, file_context)
            st.session_state.messages.insert(0, {"role": "assistant", "content": response_text})
            st.session_state.suggested_questions = new_suggestions
            st.rerun()


