import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

# Streamlit Page Configuration
st.set_page_config(page_title="iRIS AI Agent", layout="wide")

#################
st.markdown(
    """
    <style>
    /* Sidebar background */
    [data-testid="stSidebar"] {
        background-color: #4380B6;
    }

    /* Force dropdown text color to black */
    .stSelectbox div[data-baseweb="select"] * {
        color: black !important;
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
    st.title("Linear Regression")
    st.write("#### Select data to analyze...")
with col2:
    st.markdown('<div class="image-container">', unsafe_allow_html=True)
    st.image("picture1.png", width=250)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")  # horizontal rule across the full width

# Define a function to generate a linear regression plot
def generate_plot(df, x_col, y_col):
    x = df[x_col].values.reshape(-1, 1)
    y = df[y_col].values.reshape(-1, 1)
    model = LinearRegression()
    model.fit(x, y)
    y_pred = model.predict(x)
    fig, ax = plt.subplots()
    ax.scatter(x, y)
    ax.plot(x, y_pred, color='red')
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title("Linear Regression Plot")
    #ax.set_ylim(2.0, 4.0)  # Set the y-axis limits to 0 and 1
    st.pyplot(fig)

# Set the page title to the name of the CSV file
#def get_title(filename):
#    return "iRIS Sage Linear Regression: " + filename

# Define the streamlit app
def app():
    # Set the page title and file upload widget
    #st.set_page_config(page_title="iRIS-Sage", page_icon=":guardsman:")
    #image = st.image("Picture1.png", use_container_width=False)
    hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
    st.markdown(hide_st_style, unsafe_allow_html=True)
    
    # Create a new sidebar for the file upload widget
    with st.sidebar:
        file = st.file_uploader("", type=["csv"])

    # If a file is uploaded, read it and perform linear regression
    if file is not None:
        # Read the CSV file and set the first column as the target variable
        df = pd.read_csv(file)
        target_col = df.columns[0]
        X = df.iloc[:, 1:].values
        y = df[target_col].values
        
        # Fit a linear regression model
        regressor = LinearRegression()
        regressor.fit(X, y)
        
        # Compute the success probability and prediction confidence
        success_prob = regressor.predict(X).mean()
        confidence = regressor.score(X, y)
        
        # Set the page title to the name of the CSV file
        #title = get_title(file.name)
        #st.title(title)
        
        # Display the success probability and prediction confidence
        st.write(f"Threshold: {success_prob:.2f} - Confidence: {confidence:.2f}")
        
        # Create a dropdown to select the variable to plot
        options = df.columns[1:]
        x_col = st.selectbox("Select X variable", options)
        y_col = target_col
        
        # Create sliders to vary the independent variables
        st.sidebar.markdown("## Vary Independent Variables")
        values = {}
        for col in options:
            min_val = float(df[col].min())
            max_val = float(df[col].max())
            val = st.sidebar.slider(col, min_val, max_val)
            values[col] = val
            
        # Generate the default plot based on the initial slider values
        for col, val in values.items():
            df[col] = np.where(df[col] == val, val, df[col])
        generate_plot(df, x_col, y_col)
        
# Run the streamlit app
if __name__ == "__main__":
    app()