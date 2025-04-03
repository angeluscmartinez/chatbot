import streamlit as st
from openai import OpenAI
import pandas as pd
import PyPDF2
import os
import base64
from datetime import datetime
from PIL import Image
import uuid
import random
import json
import re

TRAINING_DIR = "training"
SUPPORTED_TYPES = [".pdf"]
QUESTIONS_PER_SESSION = 5
PASSING_SCORE = 3

# --- Configuration ---
st.set_page_config(page_title="iRIS Training Assistant", layout="wide")

#################
st.markdown(
    """
    <style>
    /* Sidebar background */
    [data-testid="stSidebar"] {
        background-color: #4380B6;
    }

    /* All nested text & icons white */
    [data-testid="stSidebar"] * {
        color: white !important;
        fill: white !important;
    }

    /* Buttons */
    [data-testid="stSidebar"] button {
        background-color: #4380B6 !important;
        color: white !important;
        border: 1px solid white !important;
    }

    /* Bruteforce override for uploader */
    [data-testid="stSidebar"] .stFileUploader * {
        background-color: #4380B6 !important;
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
        background-color: #4380B6 !important;
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
    st.title("Take the Top Shelf Challenge")
    st.write("#### Trivia titans sip whiskey. 🥃 Everyone else just sips water...")
with col2:
    st.markdown('<div class="image-container">', unsafe_allow_html=True)
    st.image("picture1.png", width=250)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")  # horizontal rule across the full width

client = OpenAI(api_key=st.secrets["API_key"])

# --- Initialize user_name and name_submitted ---
if "user_name" not in st.session_state:
    st.session_state["user_name"] = ""

# --- Module Setup ---
st.session_state.whiskey_selected_module = "whiskey"
current_module = st.session_state.whiskey_selected_module
module_prefix = f"{current_module}_quiz_"

# --- Helper Functions for Namespaced Session State ---
def get_state(key, default=None):
    full_key = module_prefix + key
    if full_key not in st.session_state:
        st.session_state[full_key] = default
    return st.session_state[full_key]

def set_state(key, value):
    st.session_state[module_prefix + key] = value

def reset_module_state():
    keys_to_delete = [k for k in st.session_state if k.startswith(module_prefix)]
    for k in keys_to_delete:
        del st.session_state[k]

# --- Utility Functions ---
def generate_questions_from_text(text):
    variation_token = str(uuid.uuid4())
    prompt = f"""
You are a training assistant. Based on the training material below, generate {QUESTIONS_PER_SESSION} quiz questions.
Only include two formats:
1. Multiple choice with 4 options (A, B, C, D)
2. True or False (only two options: \"True\", \"False\")

Each question must include:
- \"question\": the question text
- \"type\": either \"multiple_choice\" or \"true_false\"
- \"options\": a list of answer options
- \"answer\": the correct answer (must match one of the options exactly)

Make sure the questions vary each time, even if the training text is the same.

Format your response as a raw JSON array—no markdown, no code block.

[seed: {variation_token}]

[
  {{
    "question": "What is the capital of France?",
    "type": "multiple_choice",
    "options": ["A. Berlin", "B. Madrid", "C. Paris", "D. Rome"],
    "answer": "C. Paris"
  }},
  {{
    "question": "The Earth orbits the Sun.",
    "type": "true_false",
    "options": ["True", "False"],
    "answer": "True"
  }}
]

Text:
{text[:5000]}
"""
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"```$", "", raw.strip())
    raw = raw.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    raw = re.sub(r",(\s*[\]}])", r"\1", raw)
    try:
        return json.loads(raw)
    except:
        st.error("\u26a0\ufe0f GPT returned invalid JSON. Please try again.")
        st.text_area("Raw GPT Response:", raw, height=300)
        return []

def extract_text_from_pdf(filepath):
    with open(filepath, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])

def evaluate_answer(user_answer, correct_answer):
    return user_answer.strip().lower() == correct_answer.strip().lower()

def save_progress_global(training_dir, module_name, user_name, score):
    progress_file = os.path.join(training_dir, "progress.csv")
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "module": module_name,
        "user": user_name,
        "score": score,
        "session_id": st.session_state.get("session_id", "")
    }
    df = pd.DataFrame([entry])
    write_header = not os.path.exists(progress_file)
    df.to_csv(progress_file, mode="a", header=write_header, index=False)

# --- Load PDF ---
module_path = os.path.join(TRAINING_DIR, current_module)
pdf_files = [f for f in os.listdir(module_path) if f.endswith(".pdf")]
if not pdf_files:
    st.error("No training material found.")
    st.stop()
pdf_path = os.path.join(module_path, pdf_files[0])
pdf_text = extract_text_from_pdf(pdf_path)

# --- Initialize Questions ---
if get_state("questions") is None:
    with st.spinner("AI is generating questions..."):
        questions = generate_questions_from_text(pdf_text)
        if questions:
            set_state("questions", questions)
            set_state("current_q", 0)
            set_state("answers", [])
            set_state("scores", [])
            set_state("feedback_shown", False)
            set_state("last_correct", None)
            set_state("quiz_complete", False)
            set_state("passed_quiz", False)
        else:
            st.stop()
    st.rerun()

questions = get_state("questions")
current_q = get_state("current_q")
answers = get_state("answers")
scores = get_state("scores")
feedback_shown = get_state("feedback_shown")
last_correct = get_state("last_correct")
quiz_complete = get_state("quiz_complete")
passed_quiz = get_state("passed_quiz")

if current_q >= QUESTIONS_PER_SESSION:
    set_state("quiz_complete", True)
    quiz_complete = True

if quiz_complete:
    with st.chat_message("assistant"):
        total_score = sum(scores)
        if not get_state("progress_saved"):
            save_progress_global(TRAINING_DIR, current_module, st.session_state["user_name"], total_score)
            set_state("progress_saved", True)

        if total_score >= PASSING_SCORE:
            st.markdown("🎉 **Congratulations, you passed!** 🎉")
            trophy_path = os.path.join(module_path, "trophy.png")
            if os.path.exists(trophy_path):
                with open(trophy_path, "rb") as img_file:
                    image = Image.open(img_file)
                    image = image.resize((1200, int(1200 * image.height / image.width)))
                    st.image(image, caption="Well done!")
        else:
            st.markdown("🔁 You missed 3 or more. Try again...")

        missed = [
            (i, q, answers[i])
            for i, (score, q) in enumerate(zip(scores, questions))
            if score == 0
        ]
        if missed:
            st.markdown("### ❌ Review Missed Questions")
            for i, q, user_answer in missed:
                with st.expander(f"Question {i+1}: {q['question']}"):
                    st.markdown(f"- **Your answer:** {user_answer}")
                    st.markdown(f"- **Correct answer:** {q['answer']}")

    if st.button("✅ Try again"):
        reset_module_state()
        st.rerun()
    st.stop()

# --- Show Current Question ---
question = questions[current_q]
with st.chat_message("assistant"):
    st.markdown(f"**Question {current_q + 1}:** {question['question']}")

if not feedback_shown:
    with st.chat_message("user"):
        st.markdown("**Select your answer:**")
        for option in question["options"]:
            if st.button(option):
                answers.append(option)
                correct = evaluate_answer(option, question["answer"])
                scores.append(1 if correct else 0)
                set_state("answers", answers)
                set_state("scores", scores)
                set_state("feedback_shown", True)
                set_state("last_correct", correct)
                st.rerun()

# --- Feedback ---
if feedback_shown:
    with st.chat_message("assistant"):
        if last_correct:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Incorrect. The correct answer was: **{question['answer']}**")

    if current_q < QUESTIONS_PER_SESSION - 1:
        if st.button("Next Question"):
            set_state("current_q", current_q + 1)
            set_state("feedback_shown", False)
            set_state("last_correct", None)
            st.rerun()
    else:
        set_state("quiz_complete", True)
        set_state("passed_quiz", sum(scores) >= PASSING_SCORE)
        st.rerun()
