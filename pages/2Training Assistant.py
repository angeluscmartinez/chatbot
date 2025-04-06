import streamlit as st
from openai import OpenAI
import pandas as pd
import PyPDF2
import os
import base64
from datetime import datetime
from PIL import Image
import uuid

# --- Configuration ---
st.set_page_config(page_title="iRIS Training Assistant", layout="wide")

TRAINING_DIR = "training"
SUPPORTED_TYPES = [".pdf"]
QUESTIONS_PER_SESSION = 10
PASSING_SCORE = 7

client = OpenAI(api_key=st.secrets["API_key"])

# --- Utility Functions ---
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def extract_text_from_pdf(filepath):
    with open(filepath, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])

def generate_questions_from_text(text):
    import json, re
    prompt = f"""
You are a training assistant. Based on the training material below, generate {QUESTIONS_PER_SESSION} quiz questions.
Only include two formats:
1. Multiple choice with 4 options (A, B, C, D)
2. True or False (only two options: "True", "False")

Each question must include:
- "question": the question text
- "type": either "multiple_choice" or "true_false"
- "options": a list of answer options
- "answer": the correct answer (must match one of the options exactly)

Format your response as a raw JSON array—no markdown, no code block.

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
        messages=[{"role": "user", "content": prompt}]
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

# --- UI Layout ---
st.markdown("""
<style>
.block-container { padding-top: 5rem !important; }
.top-banner {
    position: absolute; top: 0; left: 0; width:  100%;
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.5rem 1rem; background-color: white; z-index: 9999;
}
.top-banner h1 { font-size: 3em; font-weight: bold; margin: 0; }
</style>
""", unsafe_allow_html=True)

# --- Module & User Selection ---
modules = sorted([m for m in os.listdir(TRAINING_DIR) if os.path.isdir(os.path.join(TRAINING_DIR, m))])
if "selected_module" not in st.session_state:
    st.session_state.selected_module = modules[0]

# --- User Name Input and Persistence ---
if "user_name" not in st.session_state:
    name_input = st.sidebar.text_input("Enter Your Name", key="name_input")
    submit_name = st.sidebar.button("✅ Submit")

    if submit_name and name_input:
        st.session_state["user_name"] = name_input
        st.session_state["session_id"] = str(uuid.uuid4())
        st.rerun()
    elif submit_name and not name_input:
        st.sidebar.warning("⚠️ Please enter your name before submitting.")

else:
    st.sidebar.markdown(f"👤 **User:** {st.session_state['user_name']}")

# --- Banner (always show) ---
image_path = "picture1.png"
image_html = ""
if os.path.exists(image_path):
    encoded_image = get_base64_image(image_path)
    image_html = f'<img src="data:image/png;base64,{encoded_image}" style="height:60px; margin-left: 20px;">'

st.markdown(f"""
<div class="top-banner">
    <h1>{'Welcome to iRIS Training! Enter your name to get started...' if 'user_name' not in st.session_state else st.session_state.selected_module}</h1>
    {image_html}
</div>
""", unsafe_allow_html=True)

st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)

st.markdown("---")  # horizontal rule across the full width

if "user_name" not in st.session_state:
    st.stop()

selected_module = st.sidebar.selectbox("Select Training Module", modules, index=modules.index(st.session_state.selected_module), key="module_select")

# If the selected module is different from the current one in session, update and rerun
if selected_module != st.session_state.selected_module:
    st.session_state.selected_module = selected_module
    st.rerun()

current_module = st.session_state.selected_module

st.session_state.selected_module = selected_module
current_module = st.session_state.selected_module

# --- Initialize Quiz State ---
default_quiz_state = {
    "questions": [],
    "current_q": 0,
    "answers": [],
    "scores": [],
    "feedback_shown": False,
    "last_correct": None,
    "quiz_complete": False,
    "passed_quiz": False,
    "questions_loading": False
}
for key, value in default_quiz_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- Load PDF ---
module_path = os.path.join(TRAINING_DIR, current_module)
pdf_files = [f for f in os.listdir(module_path) if f.endswith(".pdf")]
if not pdf_files:
    st.error("No training material found.")
    st.stop()

#selected_module = st.sidebar.selectbox("Select Training Module", modules, index=modules.index(st.session_state.selected_module))
#st.session_state.selected_module = selected_module
#current_module = st.session_state.selected_module
#module_path = os.path.join(TRAINING_DIR, current_module)

# PDF and optional video detection
pdf_files = [f for f in os.listdir(module_path) if f.endswith(".pdf")]
mp4_files = [f for f in os.listdir(module_path) if f.endswith(".mp4")]
if not pdf_files:
    st.error("No training material found.")
    st.stop()
pdf_path = os.path.join(module_path, pdf_files[0])
mp4_path = os.path.join(module_path, mp4_files[0]) if mp4_files else None

# --- Sidebar: Training Content Controls ---
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🎓 Training Materials")

    with open(pdf_path, "rb") as f:
        st.download_button("📄 Download Training Material", f, file_name=pdf_files[0], key="download_pdf")

    if mp4_path:
        if "show_video" not in st.session_state:
            st.session_state["show_video"] = False

        if not st.session_state["show_video"]:
            if st.button("▶️ Watch Video", key="watch_video_btn"):
                st.session_state["show_video"] = True
                st.rerun()

    if not st.session_state.questions:
        if st.button("📋 Start Quiz", key="start_quiz_btn"):
            st.session_state.questions_loading = True
            with st.spinner("Analyzing training material and generating questions..."):
                pdf_text = extract_text_from_pdf(pdf_path)
                questions = generate_questions_from_text(pdf_text)
                if questions:
                    st.session_state.questions = questions
                    st.session_state.current_q = 0
                    st.session_state.answers = []
                    st.session_state.scores = []
                    st.session_state.feedback_shown = False
                    st.session_state.last_correct = None
                    st.session_state.quiz_complete = False
                    st.session_state.passed_quiz = False
                    st.session_state.questions_loading = False
                    st.rerun()
                else:
                    st.session_state.questions_loading = False
                    st.error("❌ No questions were generated. Please try again.")

if mp4_path:
    if "show_video" not in st.session_state:
        st.session_state["show_video"] = True  # Trigger on load

    if st.session_state["show_video"]:
        st.markdown("### 🎬 Training Video")

        video_url = os.path.join(module_path, mp4_files[0]).replace("\\", "/")
        video_bytes = open(video_url, "rb").read()
        base64_video = base64.b64encode(video_bytes).decode()

        video_html = f"""
        <video width="100%" height="auto" autoplay muted controls>
            <source src="data:video/mp4;base64,{base64_video}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
        """
        st.markdown(video_html, unsafe_allow_html=True)

        if st.button("❌ Close Video"):
            st.session_state["show_video"] = False
            st.rerun()

# --- Defensive Check ---
if not st.session_state.questions or st.session_state.current_q >= len(st.session_state.questions):
    st.stop()

# --- Show Current Question ---
question = st.session_state.questions[st.session_state.current_q]
with st.chat_message("assistant"):
    st.markdown(f"**Question {st.session_state.current_q + 1}:** {question['question']}")

if not st.session_state.feedback_shown:
    with st.chat_message("user"):
        st.markdown("**Select your answer:**")
        for option in question["options"]:
            if st.button(option):
                st.session_state.answers.append(option)
                correct = evaluate_answer(option, question["answer"])
                st.session_state.scores.append(1 if correct else 0)
                st.session_state.last_correct = correct
                st.session_state.feedback_shown = True
                st.rerun()

# --- Show Feedback ---
if st.session_state.feedback_shown:
    with st.chat_message("assistant"):
        if st.session_state.last_correct:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Incorrect. The correct answer was: **{question['answer']}**")

    if st.session_state.current_q < QUESTIONS_PER_SESSION - 1:
        if st.button("Next Question"):
            st.session_state.current_q += 1
            st.session_state.feedback_shown = False
            st.session_state.last_correct = None
            st.rerun()
    else:
        total = sum(st.session_state.scores)
        st.session_state.quiz_complete = True
        st.session_state.passed_quiz = total >= PASSING_SCORE

# --- Completion ---
if st.session_state.quiz_complete:
    with st.chat_message("assistant"):
        total_score = sum(st.session_state.scores)

        # ✅ Save progress only once per quiz session
        if not st.session_state.get("progress_saved", False):
            try:
                save_progress_global(TRAINING_DIR, current_module, st.session_state["user_name"], total_score)
                st.session_state["progress_saved"] = True
            except Exception as e:
                st.error(f"⚠️ Failed to save progress: {e}")
        if st.session_state.passed_quiz:
            st.markdown("🎉 **Congratulations! You passed the quiz!** 🎉")
            trophy_path = os.path.join(module_path, "trophy.png")
            if os.path.exists(trophy_path):
                with open(trophy_path, "rb") as img_file:
                    image = Image.open(img_file)
                    image = image.resize((300, int(300 * image.height / image.width)))
                    st.image(image, caption="Well done!")
            st.markdown("🎯 You may now proceed to the next training module.")
        else:
            st.markdown("🔁 You missed 3 or more. A new quiz has been generated for you.")
            pdf_text = extract_text_from_pdf(pdf_path)
            st.session_state.questions = generate_questions_from_text(pdf_text)
            st.session_state.current_q = 0
            st.session_state.answers = []
            st.session_state.scores = []
            st.session_state.feedback_shown = False
            st.session_state.last_correct = None
            st.session_state.quiz_complete = False
            st.session_state.passed_quiz = False
            st.rerun()
##############
        # --- Review Mode for Missed Questions ---
        missed = [
            (i, q, user_answer)
            for i, (score, q, user_answer) in enumerate(
                zip(st.session_state.scores, st.session_state.questions, st.session_state.answers)
            )
            if score == 0
        ]

        if missed:
            st.markdown("### ❌ Review Missed Questions")
            for i, q, user_answer in missed:
                with st.expander(f"Question {i+1}: {q['question']}"):
                    st.markdown(f"- **Your answer:** {user_answer}")
                    st.markdown(f"- **Correct answer:** {q['answer']}")

##################
    if st.button("✅ Continue"):
        try:
            current_index = modules.index(current_module)
            if current_index < len(modules) - 1:
                st.session_state.selected_module = modules[current_index + 1]
            else:
                st.info("✅ You’ve completed all modules.")
        except ValueError:
            st.warning("⚠️ Could not determine next module.")

        # 🔄 Reset quiz state and progress flag
        for key in default_quiz_state:
            st.session_state[key] = default_quiz_state[key]
        st.session_state["progress_saved"] = False
        st.rerun()