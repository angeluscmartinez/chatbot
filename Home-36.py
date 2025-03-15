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

st.set_page_config(page_title="iRIS AI Agent", layout="wide")

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
############################################################

# Hide Streamlit's default menu and footer
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        max-width: 1600px;
        margin: auto;
        padding-top: 0px !important;
    }
    [data-testid="stSidebar"] {
        display: flex;
        flex-direction: column;
        align-items: left;
    }
    [data-testid="stSidebarNav"] {
        order: 2;
    }
    [data-testid="stSidebar"] > div:first-child {
        order: -1;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Custom CSS to remove padding and center header
st.markdown(
    """
    <style>
        .main .block-container {
            padding-top: 50px !important;
        }
        section[data-testid="stSidebar"] {
            padding-top: 0 !important;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        section[data-testid="stSidebar"] div:first-child {
            display: flex;
            justify-content: flex-start;
            align-items: left;
            flex-direction: column;
            width: 100%;
        h1 {
            position: relative;
            margin-top: 10px;
            padding-bottom: 10px;
            left: 50%;
            transform: translateX(-50%);
            width: auto;
            text-align: center;
            background: white;
            z-index: 1000;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Insert the image at the very top of the sidebar
st.sidebar.image("picture1.png", use_container_width=True)
# Now place the header at the absolute top of the main page
st.markdown("<h1>I'm Your Helpful iRIS AI Agent, Ask Me Anything</h1>", unsafe_allow_html=True)


#################################################################

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
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)  # Add 10px space
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
        st.rerun()

# Add spacing to move chat widget down
st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)  # Adds 10px space before chat messages

# Chat input form
with st.form(key="input_form", clear_on_submit=True):
    user_input = st.text_input("You: ", key="user_input", placeholder="Type your message here...")
    submit_button = st.form_submit_button(label="Submit")

if submit_button and user_input:
    file_context = st.session_state.uploaded_content or (st.session_state.uploaded_df.head(50).to_csv(index=False) if st.session_state.uploaded_df is not None else "")
    st.session_state.messages.append({"role": "user", "content": user_input})
    response_text, suggested_questions = generate_response_and_suggestions(user_input, file_context)
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.session_state.suggested_questions = suggested_questions
    
    # Keep only the last two messages
    if len(st.session_state.messages) > 2:
        st.session_state.messages = st.session_state.messages[-2:]
    
    st.rerun()

# Display last two messages only
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Display suggested questions
if st.session_state.suggested_questions:
    st.subheader("Suggested Questions:")
    for i, question in enumerate(st.session_state.suggested_questions):
        if st.button(question, key=f"suggestion_{i}"):
            file_context = st.session_state.uploaded_content or (st.session_state.uploaded_df.head(50).to_csv(index=False) if st.session_state.uploaded_df is not None else "")
            st.session_state.messages.append({"role": "user", "content": question})
            response_text, new_suggestions = generate_response_and_suggestions(question, file_context)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.session_state.suggested_questions = new_suggestions
            
            # Keep only the last two messages
            if len(st.session_state.messages) > 2:
                st.session_state.messages = st.session_state.messages[-2:]
            
            st.rerun()