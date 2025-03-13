import streamlit as st
import openai

st.title("Angel's Awesome Chatbot")

# Load API key securely from Streamlit Cloud secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]  # ✅ Secure API key retrieval

# Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Say something")
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=st.session_state.messages
        )
        response_text = response["choices"][0]["message"]["content"]
        st.markdown(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})

