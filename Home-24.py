import streamlit as st
from openai import OpenAI
import pandas as pd
import json
from streamlit_lottie import st_lottie
import io
import time

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["API_key"])

def load_lottiefile(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)

# Function to generate response and suggestions based on the uploaded file
def generate_response_and_suggestions(prompt, context):
    """Generate a response and two suggested follow-up questions that can be answered from the file"""
    full_query = f"Context from the uploaded file:\n{context}\n\nUser question: {prompt}"
    
    try:
        # Generate AI response
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": full_query}],
            max_tokens=1000,
            temperature=0.7
        )
        response_text = response.choices[0].message.content
        
        # Generate follow-up questions strictly related to the file
        suggestion_prompt = f"Based only on this content, generate two unique follow-up questions that can be answered using the provided document:\n{context}"
        suggestion_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "Suggest two follow-up questions based strictly on the document."},
                      {"role": "user", "content": suggestion_prompt}],
            max_tokens=100,
            temperature=0.7
        )
        suggestions = suggestion_response.choices[0].message.content.split("\n")
        return response_text, [q.strip() for q in suggestions if q.strip()][:2]
    
    except Exception as e:
        return f"Error: {e}", []

st.set_page_config(page_title="iRIS Agent", page_icon=":guardsman:")

# Hide Streamlit default style
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .upload-container {
                position: fixed;
                bottom: 10px;
                left: 50%;
                transform: translateX(-50%);
                background-color: white;
                padding: 10px;
                border-radius: 8px;
                box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

col1, col2 = st.columns([2.5, 1.5])
with col1:
    st.title("I'm Your Helpful iRIS AI Agent, Ask Me Anything")
with col2:
    lottie_coding = load_lottiefile("coding.json")
    st_lottie(lottie_coding, speed=2, reverse=False, loop=True, quality="high", height=210, width=210, key="lottie_coding")

# Initialize session state for messages, file uploads, and suggested questions
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_content" not in st.session_state:
    st.session_state.uploaded_content = ""
    st.session_state.uploaded_df = None
    st.session_state.show_upload_widget = True
    st.session_state.suggested_questions = []

# File upload handling
if st.session_state.show_upload_widget:
    with st.container():
        st.markdown('<div class="upload-container">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload Training Data", type=["pdf", "txt", "csv"], label_visibility='hidden')
        st.markdown('</div>', unsafe_allow_html=True)

        if uploaded_file is not None:
            progress_bar = st.progress(0)
            for percent_complete in range(0, 101, 10):
                time.sleep(0.2)  # Simulating upload progress
                progress_bar.progress(percent_complete)

            # Process uploaded file
            if uploaded_file.type == "application/pdf":
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    full_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
                    st.session_state.uploaded_content = full_text[:9000]
                except ModuleNotFoundError:
                    st.error("PyPDF2 module is not installed. Please run 'pip install PyPDF2'.")
            elif uploaded_file.type == "text/plain":
                full_text = uploaded_file.read().decode("utf-8")
                st.session_state.uploaded_content = full_text[:9000]
            elif uploaded_file.type == "text/csv":
                uploaded_df = pd.read_csv(uploaded_file)
                st.session_state.uploaded_df = uploaded_df

            st.success("File uploaded successfully!")
            time.sleep(1)
            st.session_state.show_upload_widget = False
            
            # Generate initial suggested questions based on the uploaded file
            if st.session_state.uploaded_content or st.session_state.uploaded_df is not None:
                file_context = st.session_state.uploaded_content or st.session_state.uploaded_df.head(50).to_csv(index=False)
                _, suggested_questions = generate_response_and_suggestions("What insights can I get from this data?", file_context)
                st.session_state.suggested_questions = suggested_questions
            
            st.rerun()  # Reload page after upload

# Chat input form
with st.form(key="input_form", clear_on_submit=True):
    user_input = st.text_input("You: ", key="user_input", placeholder="Type your message here...", label_visibility='hidden')
    submit_button = st.form_submit_button(label="Submit")

if submit_button and user_input:
    file_context = st.session_state.uploaded_content or (st.session_state.uploaded_df.head(50).to_csv(index=False) if st.session_state.uploaded_df is not None else "")

    st.session_state.messages.insert(0, {"role": "user", "content": user_input})
    response_text, suggested_questions = generate_response_and_suggestions(user_input, file_context)
    st.session_state.messages.insert(0, {"role": "assistant", "content": response_text})
    st.session_state.suggested_questions = suggested_questions
    st.rerun()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Display suggested questions after each response or file upload
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
