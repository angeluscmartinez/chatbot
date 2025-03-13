import streamlit as st
from openai import OpenAI
import pandas as pd
import json
from streamlit_lottie import st_lottie
import io

# Properly initialize OpenAI client

client = OpenAI(api_key=st.secrets["API_key"])

def load_lottiefile(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)

st.set_page_config(page_title="iRIS Agent", page_icon=":guardsman:")

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

col1, col2 = st.columns([2, 1])

with col1:
    header = st.title("I'm Your Helpful iRIS AI Agent, Ask Me Anything")

with col2:
    lottie_coding = load_lottiefile("coding.json")
    st_lottie(
        lottie_coding,
        speed=2,
        reverse=False,
        loop=True,
        quality="high",
        height=200,
        width=200,
        key=None,
    )

if "uploaded_content" not in st.session_state:
    st.session_state.uploaded_content = ""
    st.session_state.uploaded_df = None
    st.session_state.show_upload_widget = True
    st.session_state.needs_rerun = False

if st.session_state.show_upload_widget:
    with st.container():
        st.markdown('<div class="upload-container">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload Training Data", type=["pdf", "txt", "csv"], label_visibility='visible')
        st.markdown('</div>', unsafe_allow_html=True)

        if uploaded_file is not None:
            if uploaded_file.type == "application/pdf":
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    full_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
                    st.session_state.uploaded_content = full_text[:9000]
                except ModuleNotFoundError:
                    st.error("PyPDF2 module is not installed. Please run 'pip install PyPDF2' in your environment.")
            elif uploaded_file.type == "text/plain":
                full_text = uploaded_file.read().decode("utf-8")
                st.session_state.uploaded_content = full_text[:9000]
            elif uploaded_file.type == "text/csv":
                uploaded_df = pd.read_csv(uploaded_file)
                st.session_state.uploaded_df = uploaded_df
            
            st.session_state.show_upload_widget = False
            st.session_state.needs_rerun = True

if st.session_state.needs_rerun:
    st.session_state.needs_rerun = False
    try:
        st.rerun()
    except Exception as e:
        st.error(f"Rerun failed: {e}")

if "messages" not in st.session_state:
    st.session_state.messages = []

def generate_response(prompt):
    query_context = prompt

    if st.session_state.uploaded_content:
        query_context = f"Relevant document content: {st.session_state.uploaded_content}\nUser question: {prompt}"
    elif st.session_state.uploaded_df is not None:
        limited_df = st.session_state.uploaded_df.head(50)
        csv_snippet = limited_df.to_csv(index=False)
        query_context = f"Relevant data from CSV:\n{csv_snippet}\nUser question: {prompt}"

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query_context}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content  

    except Exception as e:
        return f"Error: {e}"

with st.form(key="input_form", clear_on_submit=True):
    user_input = st.text_input("You: ", key="user_input", placeholder="Type your message here...", label_visibility='visible')
    submit_button = st.form_submit_button(label="Submit")

if submit_button and user_input:
    st.session_state.messages.insert(0, {"role": "user", "content": user_input})
    response = generate_response(user_input)
    st.session_state.messages.insert(0, {"role": "assistant", "content": response})

for message in st.session_state.messages:
    if message["role"] == "user":
        st.write(f"You: {message['content']}")
    elif message["role"] == "assistant":
        st.write(f"iRIS AI: {message['content']}")

st.components.v1.html(
    """
    <script>
        setTimeout(function() {
            const inputField = window.parent.document.querySelector('input[type="text"]');
            if (inputField) {
                inputField.focus();
            }
        }, 100);
    </script>
    """,
    height=0,
)
