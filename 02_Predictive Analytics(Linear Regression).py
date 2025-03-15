import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt


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
def get_title(filename):
    return "iRIS Sage Linear Regression: " + filename

# Define the streamlit app
def app():
    # Set the page title and file upload widget
    st.set_page_config(page_title="iRIS-Sage", page_icon=":guardsman:")
    image = st.image("Picture1.png", use_container_width=False)
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
        title = get_title(file.name)
        st.title(title)
        
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