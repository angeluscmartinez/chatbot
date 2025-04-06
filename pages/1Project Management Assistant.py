import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
import os
import re
from collections import OrderedDict
import glob
import time

# Set default font sizes and family for better readability
plt.rcParams.update({
    "font.size": 12,         # Increase font size
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "font.family": "DejaVu Sans"  # Safe cross-platform font
})

# Try secrets first, then fallback to environment
api_key = None
if "API_key" in st.secrets:
    api_key = st.secrets["API_key"]
elif os.getenv("API_key"):
    api_key = os.getenv("API_key")

if not api_key:
    st.error("❌ OpenAI API key not found in Streamlit secrets or environment variables.")
    st.stop()

# ✅ Initialize the OpenAI client
client = OpenAI(api_key=api_key)

st.set_page_config(page_title="iRIS AI Agent", layout="wide")
#st.title("iRIS Project Management Assistant")
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

    /* Force dropdown text color to black */
    .stSelectbox div[data-baseweb="select"] * {
        color: black !important;
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

    /* ✅ Make default horizontal rule in sidebar white */
    [data-testid="stSidebar"] hr {
        border-top: 2px solid white !important;
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
    st.title("🤖 iRIS Project Management Assistant")
    st.write("#### I can analyze any of your iRIS data and give you reports & assessments")
with col2:
    st.markdown('<div class="image-container">', unsafe_allow_html=True)
    st.image("picture1.png", width=250)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")  # horizontal rule across the full width




















# Initialize session state
if "project_dataframe" not in st.session_state:
    st.session_state.project_dataframe = None
if "project_messages" not in st.session_state:
    st.session_state.project_messages = []
if "last_chart" not in st.session_state:
    st.session_state.last_chart = None
if "charts_to_render" not in st.session_state:
    st.session_state.charts_to_render = []
if "export_results" not in st.session_state:
    st.session_state.export_results = {}

def get_filtered_dataframe(label, df):
    prompt = f"""
You are an expert assistant generating pandas DataFrame filters from intent labels.

Given a label like "reliability_requirements", generate a valid one-line pandas expression that filters the DataFrame `df`.

Rules:
- Do NOT include explanations, return statements, or print.
- Only return a single line Python expression.
- Infer column names such as "Requirement Type", "Verification Method", or "Verification Status" based on the label.
- Use `.str.lower()` when comparing strings.
- If needed, use `.str.contains("<keyword>")` for flexible matches.

Examples:
- For label 'closed_requirements', return: df[df["Verification Status"].str.lower() == "closed"]
- For label 'safety_requirements', return: df[df["Requirement Type"].str.lower().str.contains("safety")]
- For label 'analysis_verification_requirements', return: df[df["Verification Method"].str.lower() == "analysis"]

Now generate the filter for:
Label: "{label}"

Schema:
{dict(df.dtypes)}

Sample:
{df.head(5).to_dict(orient='records')}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": "You return Python pandas filtering expressions only. No explanations."},
                      {"role": "user", "content": prompt}],
            temperature=0
        )
        code = response.choices[0].message.content.strip()
        # Basic sanity check: don't accept identity return like just 'df'
        if code.strip() == "df" or "return" in code or len(code) < 10:
            print("⚠️ GPT returned a non-filtering expression. Defaulting to full dataset.")
            return None
        if filtered_df is not None and not filtered_df.empty:
            st.markdown(f"### 🔍 Filtered Preview for **{label}**")
            st.dataframe(filtered_df.head(10))

        # Evaluate the expression safely
        local_vars = {"df": df.copy()}
        filtered_df = eval(code, {"__builtins__": {}}, local_vars)

        if isinstance(filtered_df, pd.DataFrame) and not filtered_df.empty:
            return filtered_df
        else:
            return None

    except Exception as e:
        print("Error in GPT filter generation:", e)
        return None

def get_filtered_dataframe(label, df):
    # Create the prompt for GPT
    prompt = f"""
You are a Python assistant that converts a natural language label into a one-line pandas expression
to filter a DataFrame called `df`.

Only return the filtering expression (no comments, print, return, etc).

If the label mentions "reliability", "safety", "closed", or "analysis", match those against the appropriate column values.

Rules:
- Use .str.lower() for string comparisons
- Use .str.contains() for partial/fuzzy matches
- If the match is numeric, use equality or comparison
- Don't explain anything — only return a line like: df[df["Column"].str.lower() == "value"]

Examples:
- "closed_requirements" → df[df["Verification Status"].str.lower() == "closed"]
- "safety_requirements" → df[df["Requirement Type"].str.lower().str.contains("safety")]
- "analysis_verification_requirements" → df[df["Verification Method"].str.lower() == "analysis"]

Now generate the correct pandas filter for this:
Label: "{label}"

Column types:
{dict(df.dtypes)}

Sample data:
{df.head(5).to_dict(orient='records')}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You only return valid pandas filtering expressions. No comments or explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        code = response.choices[0].message.content.strip()
        print("🧠 GPT returned:", code)

        # Reject fallback 'df' or empty responses
        if code.lower().strip() == "df" or len(code) < 10 or "df[" not in code:
            print("⚠️ GPT returned an invalid filter. Falling back to contains search...")
            raise ValueError("Unusable filter")

        # Evaluate the filtering expression safely
        local_vars = {"df": df.copy()}
        filtered_df = eval(code, {"__builtins__": {}}, local_vars)

        if isinstance(filtered_df, pd.DataFrame) and not filtered_df.empty:
            return filtered_df

    except Exception as e:
        print(f"❌ GPT filtering failed: {e}")
        print("🔁 Attempting fallback search across object columns...")

        # Fallback: search all object columns for the label
        label_lower = label.lower()
        for col in df.select_dtypes(include="object").columns:
            try:
                mask = df[col].astype(str).str.lower().str.contains(label_lower, na=False)
                fallback_df = df[mask]
                if not fallback_df.empty:
                    print(f"✅ Fallback match on column: {col}")
                    return fallback_df
            except Exception as fallback_error:
                continue

        print("⚠️ Fallback search also failed.")

    return None

def export_dataframe_to_csv(filtered_df, filename="filtered_data.csv"):
    import io
    import base64

    towrite = io.BytesIO()
    filtered_df.to_csv(towrite, index=False)
    towrite.seek(0)

    b64 = base64.b64encode(towrite.read()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Download CSV</a>'
    st.markdown(href, unsafe_allow_html=True)

# Load the default project file
def load_all_sheets(path):
    print("📥 Loading file:", path)  # ✅ Add this as the first line
    try:
        if path.endswith(".xlsx") or path.endswith(".xls"):
            xls = pd.ExcelFile(path)
            return {sheet_name.strip(): xls.parse(sheet_name) for sheet_name in xls.sheet_names}
        elif path.endswith(".csv"):
            return {"Sheet1": pd.read_csv(path)}
        else:
            st.error(f"Unsupported file type: {path}")
            return None
    except Exception as e:
        st.error(f"❌ Failed to load file: {e}")
        return None

def export_dataframe_to_csv(filtered_df, filename="filtered_data.csv"):
    import io
    import base64

    towrite = io.BytesIO()
    filtered_df.to_csv(towrite, index=False)
    towrite.seek(0)

    b64 = base64.b64encode(towrite.read()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Download CSV</a>'
    st.markdown(href, unsafe_allow_html=True)

import glob
def discover_project_files(base_dir="PROJECT"):
    project_files = {}
    for folder in os.listdir(base_dir):
        full_path = os.path.join(base_dir, folder)
        if os.path.isdir(full_path):
            # Look for .csv or .xls/.xlsx files in the subfolder
            files = glob.glob(os.path.join(full_path, "*.csv")) + \
                    glob.glob(os.path.join(full_path, "*.xls")) + \
                    glob.glob(os.path.join(full_path, "*.xlsx"))
            if files:
                project_files[folder] = files[0]  # Use first matching file
    return project_files

# Ask GPT-4 Turbo to analyze the data
def ask_gpt_about_data(prompt, sheets_dict):
    def summarize_dataframe(df):
        col_types = {col: str(df[col].dtype) for col in df.columns}
        col_values = {}
        for col in df.columns:
            try:
                col_values[col] = {
                    "value_counts": df[col].value_counts(dropna=False).to_dict(),
                    "dtype": str(df[col].dtype),
                    "sample": df[col].dropna().astype(str).unique().tolist()[:10]
                }
            except Exception as e:
                col_values[col] = f"Could not summarize: {e}"
        return col_types, col_values

    system_msg = {
        "role": "system",
        "content": (
        "You are a professional aerospace project analyst embedded in a Streamlit app. "
        "You analyze Excel data across multiple sheets. When the user enters a prompt, you:\n"
        "- Search ALL sheets\n"
        "- Review string columns in each sheet\n"
        "- If the prompt seems like a keyword search (e.g. 'angel', 'tolerance', 'power'), "
        "search for that word in all string columns and report matches per column per sheet\n"
        "- If the prompt is asking for a project overview, generate a mission-style formal briefing\n"
        "- Use chart triggers like [RENDER_PIE:<col>] or export triggers like [EXPORT_CSV:<label>]\n"
        "- If no data matches, say so clearly"
        "When the user asks how many requirements relate to a keyword (e.g. power), search all string columns using a case-insensitive contains match."
        "Return the count of matching rows and the column(s) where they appeared."
        "You are an AI Mission Analyst embedded within a United States Space Force operational environment. "
        "You analyze project requirement data and generate clear, formal briefings suitable for readiness reviews, command updates, and flight recertification briefings. "
        "Maintain a tone that is disciplined, concise, technically accurate, and focused on operational impact. "
        "You have access to a DataFrame that includes engineering, verification, and requirement tracking data. "
        "If the user's question cannot be answered from the available data, "
        "politely say: 'I'm sorry, I couldn't find that information in the current project data.' "
        "If the user asks for a project overview, respond with a structured and formal briefing that includes metrics and counts:\n"
        "- Overview\n- Metrics\n- Risk Considerations\n- Pending Requirement Changes\n- Charts (use [RENDER_PIE:<column name>] if appropriate)\n- Recommendations\n"
        "When responding with a chart, use [RENDER_PIE:<column>] or [RENDER_BAR:<column>] to trigger a chart render."
        "Briefings should be mission-focused. Avoid overly casual phrasing. Always consider risk posture, verification status, and interface readiness."
        "To indicate overall risk posture or mission readiness, include a tag like [RISK_FLAG:GREEN], [RISK_FLAG:YELLOW], or [RISK_FLAG:RED] based on your analysis."
        "Do not explain how you reasoned it out. Just present the formal output.\n"
        "To export filtered data, include [EXPORT_CSV:<label>] in your response. "
        "To render a cumulative trend chart for a date column (like completed requirements over time), use [RENDER_LINE:<column name> cumulative]."
        )
    }

    chat_history = [system_msg]
    print("🧾 Loaded sheets:", list(sheets_dict.keys()))
    all_responses = []
    print("📎 Looping over these sheets:", [(k, df.shape if hasattr(df, 'shape') else 'N/A') for k, df in sheets_dict.items()])
    for sheet_name, df in sheets_dict.items():
        print(f"📄 Looping into sheet: {sheet_name}")
        print(f"📋 {sheet_name} shape: {df.shape}")

        if df is None or df.empty:
            print(f"⚠️ Skipping sheet '{sheet_name}' because it is empty or None")
            continue

        col_types, col_values = summarize_dataframe(df)

        # ✅ Determine if it's a strategic prompt
        strategic_keywords = ["overview", "risk", "readiness", "posture", "status", "summary", "recommendation", "assessment"]
        is_strategic = any(kw in prompt.lower() for kw in strategic_keywords)
        print(f"📊 Strategic analysis mode: {is_strategic}")

        if is_strategic:
            user_content = f"""
            The user has submitted the following strategic prompt:
            ---
            {prompt}
            ---

            You are analyzing sheet: **{sheet_name}**

            Please provide a high-level mission-style analysis focused on:
            - Risk posture
            - Verification completion
            - Requirement readiness
            - Open issues or red flags

            Use the schema and sample values below to inform your response.

            Column Types:
            {col_types}

            Column Value Samples:
            {col_values}
            """
        else:
            user_content = f"""
            The user has submitted the following prompt:
            ---
            {prompt}
            ---

            You are analyzing sheet: **{sheet_name}**

            Column Types:
            {col_types}

            Column Value Samples:
            {col_values}

            Please search all string-type columns in this sheet for the keyword(s) in the user prompt.
            Use a case-insensitive match (like .str.contains(..., case=False)).
            Report exact matches by column and row count.
            If there are no matches, say so clearly.
            """

        try:
            print(f"🧪 About to process: {sheet_name}")
            messages = chat_history + [{"role": "user", "content": user_content}]
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages,
                temperature=0.2
            )
            output = response.choices[0].message.content.strip()

            print(f"✅ GPT finished processing: {sheet_name}")
            print(f"🧠 GPT Response from {sheet_name}:\n{output}\n{'-'*40}")
            all_responses.append((sheet_name, output))

        except Exception as e:
            print(f"🔥 GPT error in sheet '{sheet_name}' — continuing loop")
            print(f"❌ {e}")

    # ✅ Final response after ALL sheets processed
    if all_responses:
        combined = "\n\n".join(f"📄 **{sheet}**\n{resp}" for sheet, resp in all_responses)
        return combined

    return "🤖 I'm sorry, I couldn't find that information in any sheet."

def render_bar_chart(counts, title):
    import matplotlib.pyplot as plt
    import io
    import base64

    st.subheader("📊 " + title)

    # Create bar chart in memory
    fig, ax = plt.subplots(figsize=(8, 5))
    counts.plot(kind='bar', ax=ax)
    ax.set_title(title)
    ax.set_xlabel("Category")
    ax.set_ylabel("Count")
    plt.xticks(rotation=45, ha='right')

    # Save figure to buffer
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)

    # Display in Streamlit
    st.image(buf, caption=title, use_container_width=False)

    # Add download button
    b64 = base64.b64encode(buf.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{title}.png" target="_blank">📥 Download Chart</a>'
    st.markdown(href, unsafe_allow_html=True)

def render_pie_chart(counts, title):
    import matplotlib.pyplot as plt
    import io
    import base64

    st.subheader("📊 " + title)

    # Create pie chart in memory
    fig, ax = plt.subplots(figsize=(6, 6))  # Moderate size
    ax.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=140)
    ax.axis("equal")  # Equal aspect ratio ensures it's a circle
    plt.title(title)

    # Save figure to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)

    # Display in Streamlit with download & expand icons
    st.image(buf, caption=title, use_container_width=False)

    # Add download button
    b64 = base64.b64encode(buf.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{title}.png" target="_blank">📥 Download Chart</a>'
    st.markdown(href, unsafe_allow_html=True)

def render_line_chart(series, title, cumulative=False):
    import matplotlib.pyplot as plt
    import io
    import base64

    series = series.sort_index()

    if cumulative:
        series = series.cumsum()
        title += " (Cumulative)"

    st.subheader("📈 " + title)

    fig, ax = plt.subplots(figsize=(8, 5))
    print("📅 Line chart series head:\n", series.head(10))
    print("🧮 Is cumulative:", cumulative)
    series.plot(ax=ax, marker="o")
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Count")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    st.image(buf, caption=title, use_container_width=False)

    b64 = base64.b64encode(buf.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{title}.png" target="_blank">📥 Download Chart</a>'
    st.markdown(href, unsafe_allow_html=True)

#########
def typewriter_effect(text, delay=0.05):
    placeholder = st.empty()
    typed_text = ""
    for char in text:
        typed_text += char
        placeholder.markdown(
            f'<div style="font-size: 24px; font-weight: bold;">{typed_text}</div>',
            unsafe_allow_html=True
        )
        time.sleep(delay)

def get_combined_dataframe(sheet_dict):
    frames = []
    for name, df in sheet_dict.items():
        if isinstance(df, pd.DataFrame):
            df = df.copy()
            df["__Sheet__"] = name  # Tag origin sheet
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else None

def process_chart_tags(response_text, dataframe_dict):
    pie_matches = re.findall(r"\[RENDER_PIE:(.*?)\]", response_text)
    bar_matches = re.findall(r"\[RENDER_BAR:(.*?)\]", response_text)
    line_matches = re.findall(r"\[RENDER_LINE:(.*?)\]", response_text)

    st.session_state.charts_to_render = []

    def make_pie_chart(counts, title):
        return lambda: render_pie_chart(counts, f"Distribution of {title}")

    def make_bar_chart(counts, title):
        return lambda: render_bar_chart(counts, f"Bar Chart of {title}")

    def find_column(df, requested_title):
        for col in df.columns:
            if col.strip().lower() == requested_title.strip().lower():
                return col
        return None

    for chart_title in pie_matches:
        chart_title_clean = chart_title.strip()
        found = False
        for sheet_name, df in dataframe_dict.items():
            if df is not None:
                matched_col = find_column(df, chart_title_clean)
                if matched_col:
                    col_counts = df[matched_col].dropna().value_counts()
                    if not col_counts.empty:
                        st.session_state.charts_to_render.append(make_pie_chart(col_counts, matched_col))
                        found = True
                        break
        if found:
            response_text = response_text.replace(f"[RENDER_PIE:{chart_title}]", f"📊 Pie chart of **{chart_title}** — see below.")

    for chart_title in bar_matches:
        chart_title_clean = chart_title.strip()
        found = False
        for sheet_name, df in dataframe_dict.items():
            if df is not None:
                matched_col = find_column(df, chart_title_clean)
                if matched_col:
                    col_counts = df[matched_col].dropna().value_counts()
                    if not col_counts.empty:
                        st.session_state.charts_to_render.append(make_bar_chart(col_counts, matched_col))
                        found = True
                        break
        if found:
            response_text = response_text.replace(f"[RENDER_BAR:{chart_title}]", f"📊 Bar chart of **{chart_title}** — see below.")
    def make_line_chart(series, title, cumulative=False):
        return lambda: render_line_chart(series, f"Line Chart of {title}", cumulative=cumulative)

    line_matches = re.findall(r"\[RENDER_LINE:(.*?)\]", response_text)

    for chart_title in line_matches:
        chart_title_clean = chart_title.strip()
        cumulative = "cumulative" in chart_title_clean.lower()
        chart_title_clean = chart_title_clean.replace("cumulative", "", 1).strip()

        found = False
        for sheet_name, df in dataframe_dict.items():
            if df is not None:
                matched_col = find_column(df, chart_title_clean)
                if matched_col:
                    col_data = df[matched_col].dropna()
                    try:
                        date_series = pd.to_datetime(col_data, errors='coerce').dropna()
                        trend = date_series.dt.to_period("D").value_counts().sort_index()
                        trend.index = trend.index.to_timestamp()

                        if not trend.empty:
                            st.session_state.charts_to_render.append(
                                lambda s=trend, t=matched_col, cum=cumulative: render_line_chart(s, f"Line Chart of {t}", cumulative=cum)
                            )
                            response_text = response_text.replace(
                                f"[RENDER_LINE:{chart_title}]",
                                f"📈 Line chart of **{chart_title_clean}** — see below."
                            )
                            found = True
                            break
                    except Exception as e:
                        print(f"⚠️ Could not parse {matched_col} as dates: {e}")
        if not found:
            print(f"❌ Could not generate line chart for '{chart_title_clean}'")


    for chart_title in bar_matches:
        chart_title = chart_title.strip()
        for sheet_name, df in dataframe_dict.items():
            if df is not None and chart_title in df.columns:
                col_counts = df[chart_title].value_counts()
                # ✅ Append to chart list
                st.session_state.charts_to_render.append(lambda c=col_counts, t=chart_title: render_bar_chart(c, f"Bar Chart of {t}"))
                response_text = response_text.replace(f"[RENDER_BAR:{chart_title}]", f"📊 Bar chart of **{chart_title}** — see below.")
                break

    return response_text


########

# Discover available project data files
project_files = discover_project_files()

# Sidebar project selection
st.sidebar.title("📁 Project Selector")

project_options = ["-- Select a project --"] + sorted(project_files.keys())
selected_project = st.sidebar.selectbox("Choose a project:", project_options)

# Don't treat selection as valid if it's the placeholder
valid_project_selected = selected_project != "-- Select a project --"


# Load the selected project file
df = None
# Load the selected project file and trigger auto-briefing once
df = None
# Load the selected project file and trigger auto-briefing once
df = None
if valid_project_selected:
    # ✅ Reset if switching projects
    if "current_project" not in st.session_state:
        st.session_state.current_project = selected_project
    elif st.session_state.current_project != selected_project:
        st.session_state.current_project = selected_project
        st.session_state.auto_briefing_rendered = False
        st.session_state.project_messages.clear()
        st.session_state.last_chart = None
        st.session_state.suppress_briefing = False

    # ✅ Load the file + trigger briefing
    project_name = selected_project
    data_path = project_files[selected_project]

    with st.spinner(""):
        sheet_dfs = load_all_sheets(data_path)
        typewriter_effect("🧠 AI is analyzing your project data...", delay=0.07)

            # ✅ Safety check here
        if sheet_dfs is None:
            st.error("❌ Failed to load sheets. Check the file format or contents.")
            st.stop()
        else:
            print("🧪 Sheet keys loaded for briefing:", list(sheet_dfs.keys()))
            st.session_state.project_dataframe = sheet_dfs  # Store dict of sheets
            st.session_state.combined_df = get_combined_dataframe(sheet_dfs)

            # ✅ Only run auto briefing once per project — cache it
            if (
                sheet_dfs is not None
                and len(sheet_dfs) > 0
                and not st.session_state.get("auto_briefing_rendered", False)
                and not st.session_state.get("suppress_briefing", False)
            ):
                auto_prompt = "Provide me a project overview briefing"

                # 🧠 Cache the result per project name
                if "briefing_cache" not in st.session_state:
                    st.session_state.briefing_cache = {}

                if project_name not in st.session_state.briefing_cache:
                    auto_response = ask_gpt_about_data(auto_prompt, sheet_dfs)
                    st.session_state.briefing_cache[project_name] = auto_response
                else:
                    auto_response = st.session_state.briefing_cache[project_name]

                if not auto_response or not isinstance(auto_response, str):
                    st.sidebar.error("❌ Failed to generate an auto-briefing response.")
                else:
                    # 🧠 Force-inject a pie chart for Requirement Type at the end if it's missing
                    # 🧼 Remove all pie and bar tags to control the visuals
                    auto_response = re.sub(r"\[RENDER_(PIE|BAR):.*?\]", "", auto_response)

                    # ✅ Inject both custom chart tags
                    auto_response += "\n\n[RENDER_PIE:Requirement Type]"
                    auto_response += "\n\n[RENDER_BAR:Verification Method]"

                    # 🧠 Process chart tags (this renders + replaces them in text)
                    auto_response = process_chart_tags(auto_response, st.session_state.project_dataframe)

                    # ✅ Save messages and flags
                    st.session_state.project_messages.append({"role": "user", "content": auto_prompt})
                    st.session_state.project_messages.append({"role": "assistant", "content": auto_response})
                    st.session_state.auto_briefing_rendered = True
                    st.session_state.suppress_briefing = False

                if not auto_response or not isinstance(auto_response, str):
                    st.sidebar.error("❌ Failed to generate an auto-briefing response.")
                else:
                    # ✅ Process any [RENDER_PIE] / [RENDER_BAR] tags inside auto_response
                    auto_response = process_chart_tags(auto_response, st.session_state.project_dataframe)

                    # ✅ Append the messages after processing
                    st.session_state.project_messages.append({"role": "user", "content": auto_prompt})
                    st.session_state.project_messages.append({"role": "assistant", "content": auto_response})
                    st.session_state.auto_briefing_rendered = True
                    st.session_state.suppress_briefing = False

            st.success(f"✅ Analysis of **{project_name}** complete.")

if not valid_project_selected:
    st.info("👈 Please select a project from the sidebar to see a project overview.")

prompt = st.chat_input("Ask me anything about your project...")
if prompt:
    st.session_state.export_results = {}
    st.session_state.project_messages.append({"role": "user", "content": prompt})

    if st.session_state.project_dataframe is not None:
        response_text = ask_gpt_about_data(prompt, st.session_state.project_dataframe)

        # ✅ Handle chart trigger tags
        response_text = process_chart_tags(response_text, st.session_state.project_dataframe)

        # ✅ Handle export tags
        export_matches = re.findall(r"\[EXPORT_CSV:(.*?)\]", response_text)
        for label in export_matches:
            label = label.strip()
            filtered_df = get_filtered_dataframe(label, st.session_state.combined_df)
            st.session_state.export_results[label] = filtered_df if filtered_df is not None and not filtered_df.empty else st.session_state.combined_df
            response_text = response_text.replace(
                f"[EXPORT_CSV:{label}]",
                f"📥 Preview your download below **{label}** — if it looks correct click download."
            )

        # ✅ Handle risk flags
        risk_flag_match = re.search(r"\[RISK_FLAG:(GREEN|YELLOW|RED)\]", response_text, re.IGNORECASE)
        if risk_flag_match:
            color = risk_flag_match.group(1).upper()
            flag_map = {
                "GREEN": "🔵 Readiness Status: **GO** (Low Risk)",
                "YELLOW": "🟡 Readiness Status: **CAUTION** (Moderate Risk)",
                "RED": "🔴 Readiness Status: **NO GO** (High Risk)"
            }
            response_text = response_text.replace(risk_flag_match.group(0), flag_map[color])
            getattr(st.sidebar, {
                "RED": "error",
                "YELLOW": "warning",
                "GREEN": "success"
            }[color])("Readiness: " + flag_map[color].split(":")[1])

        st.session_state.project_messages.append({"role": "assistant", "content": response_text})

# ✅ Display chat messages and render charts if needed
# ✅ Display chat messages and render charts if needed
for i, message in enumerate(st.session_state.project_messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        is_latest = i == len(st.session_state.project_messages) - 1

        # ✅ Only render charts for the latest assistant message
        if is_latest and message["role"] == "assistant":
            for j, chart_fn in enumerate(st.session_state.charts_to_render):
                chart_fn()
                if j < len(st.session_state.charts_to_render) - 1:
                    st.markdown("---")

        # ✅ Auto-overview charts (e.g. pie/bar default briefing)
        is_auto_overview = (
            st.session_state.get("auto_briefing_rendered", False)
            and message["role"] == "assistant"
            and st.session_state.project_messages[i - 1]["content"].strip().lower() == "provide me a project overview briefing"
        )

        # ✅ 🚫 Skip fallback chart rendering if charts were already triggered by tags
        if (
            is_latest
            and is_auto_overview
            and st.session_state.get("combined_df") is not None
            and not st.session_state.charts_to_render  # <- the key line to prevent duplicates
        ):
            df = st.session_state.combined_df

            if "Requirement Type" in df.columns and "Verification Method" in df.columns:
                st.divider()
                col1, col2 = st.columns(2)

                with col1:
                    pie_counts = df["Requirement Type"].dropna().value_counts()
                    if not pie_counts.empty:
                        render_pie_chart(pie_counts, "Distribution of Requirement Type")

                with col2:
                    bar_counts = df["Verification Method"].dropna().value_counts()
                    if not bar_counts.empty:
                        render_bar_chart(bar_counts, "Bar Chart of Verification Method")

st.sidebar.markdown("---")
if st.sidebar.button("🧹 Clear Chat History", key="clear_chat"):
    st.session_state.project_messages.clear()
    st.session_state.export_results = {}
    st.session_state.last_chart = None
    st.session_state.auto_briefing_rendered = True  # Prevent auto rerun
    st.session_state.suppress_briefing = True
    st.rerun()
# 🔽 Show all export previews at the bottom
if st.session_state.get("export_results"):
    for label, result_df in st.session_state.export_results.items():
        with st.expander(f"🔍 Preview: {label.replace('_', ' ').title()}"):
            st.dataframe(result_df.head(10))
            st.markdown(f"Showing up to 10 rows of **{len(result_df)}** total.")
            export_dataframe_to_csv(result_df, filename=f"{label.replace(' ', '_').lower()}.csv")
