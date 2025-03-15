import streamlit as st
import os
import pandas as pd
import pickle
import altair as alt
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

#st.set_page_config(page_title="iRIS-Sage", page_icon=":guardsman:")
image = st.image("Picture1.png", use_container_width=False)
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
#Set the page title to the name of the CSV file
def get_title(filename):
    return "iRIS Sage Logistic Regression: " + filename

def main():
    # Load the available pickle files
    pickles = load_pickles()

    st.sidebar.title("Input Data")

    # Display file uploader widget in the left sidebar and load the data into a pandas dataframe
    file = st.sidebar.file_uploader("", type=["csv"])
    if file is not None:
        data = pd.read_csv(file)
        # Set the page title to the name of the CSV file
        title = get_title(file.name)
        title_placeholder = st.empty()
        title_placeholder.title(title)

        # Allow the user to choose whether to retrain the model with new data
        train_model = st.sidebar.checkbox("Train new model or retrain existing model with new data")

        # Construct the path to the pickle file based on the CSV filename
        pickle_path = os.path.splitext(file.name)[0] + ".pkl"

        if train_model:
            # Separate the features and target variable
            X = data.drop('success', axis=1)
            y = data['success']
            # Initialize the logistic regression model
            model = LogisticRegression()
            # Fit the model on the training data
            model.fit(X, y)
            st.sidebar.write("Model trained on the updated data.")
            # Save the trained model
            save_model(model, pickle_path)
        # Initialize inputs
        inputs = {}
        # Check if a pre-trained model exists for the uploaded CSV file
        pickle_path = os.path.splitext(file.name)[0] + ".pkl"
        if os.path.exists(pickle_path):
            st.sidebar.write("Pre-trained model found.")
            # Load the pre-trained model
            model = load_model(pickle_path)
            # Create input form to get feature values for new data to predict
            st.sidebar.header("New Data")
            for column in data.columns:
                if column == 'success':
                    continue
                if data[column].dtype == object:
                    # Categorical column
                    values = data[column].unique()
                    inputs[column] = st.sidebar.selectbox(column, values)
                else:
                    # Numerical column
                    min_value = int(data[column].min())
                    max_value = int(data[column].max())
                    if min_value == max_value:
                        max_value += 1  # add an offset to the max value to avoid RangeError
                    default_value = int((min_value + max_value) / 2)
                    inputs[column] = st.sidebar.slider(column, min_value, max_value, default_value, key=column)
        else:
            # Create input form to get feature values for training a new model
            st.sidebar.write("No pre-trained model found.")
            st.sidebar.header("Input Data")
            for column in data.columns:
                if column == 'success':
                    continue
                if data[column].dtype == object:
                    # Categorical column
                    values = data[column].unique()
                    inputs[column] = st.sidebar.selectbox(column, values)
                else:
                    # Numerical column
                    min_value = int(data[column].min())
                    max_value = int(data[column].max())
                    if min_value == max_value:
                        max_value += 1  # add an offset to the max value to avoid RangeError
                    default_value = int((min_value + max_value) / 2)
                    inputs[column] = st.sidebar.slider(column, min_value, max_value, default_value, key=column)

            # Train a new model
            X = data.drop('success', axis=1)
            y = data['success']

        # Add a button to upload the new CSV file
        st.sidebar.write("OR")
        file_upload = st.sidebar.file_uploader("Upload new CSV for prediction", type=["csv"])
        if file_upload is not None:
            # Load the new data into a pandas dataframe
            new_data = pd.read_csv(file_upload)
            # Fill the missing values with zeros
            new_data = new_data.fillna(value=0)
            # Use the trained model to predict the probability of success for the new data
            new_prob_success = model.predict_proba(new_data.drop('success', axis=1))[:, 1]
            # Update the inputs dictionary with the values from the uploaded file
            for column in new_data.columns:
                if column == 'success':
                    continue
                if new_data[column].dtype == object:
                    # Categorical column
                    values = new_data[column].unique()
                    inputs[column] = st.sidebar.selectbox(column, values, index=0)
                else:
                    # Numerical column
                    min_value = int(new_data[column].min())
                    max_value = int(new_data[column].max())
                    if min_value == max_value:
                        max_value += 1  # add an offset to the max value to avoid RangeError
                    default_value = int((min_value + max_value) / 2)
                    inputs[column] = st.sidebar.slider(column, min_value, max_value, default_value)
            # Set the page title to the name of the CSV file
            title = get_title(file_upload.name)
            #st.title(title)
            title_placeholder.empty()
            title_placeholder.title(title)

        else:
            new_prob_success = None

        try:
            new_data = pd.DataFrame(inputs, index=[0])
            prob_success = model.predict_proba(new_data.fillna(value=0))[:, 1]
            auc = roc_auc_score(data['success'], model.predict_proba(data.fillna(value=0).drop('success', axis=1))[:, 1])
            st.markdown("<p style='color: blue; font-size: 20px; font-weight: bold'>Success probability: <b>{:.4f}</b></p>".format(float(prob_success)), unsafe_allow_html=True)
            st.markdown("<p style='color: blue; font-size: 20px; font-weight: bold'>Prediction Confidence: <b>{:.4f}</b></p>".format(float(auc)), unsafe_allow_html=True)

            # Display the result
            # Create a drop-down for selecting the variable to plot against the probability of success
            var_to_plot = st.selectbox("Select a variable to plot against the probability of success", [col for col in data.columns if col != 'success'], key='var_to_plot', index=0, help="Select a variable to plot against the probability of success", )
            st.markdown("<div style='text-align: center'><p style='color: black; font-size: 18px; font-weight: bold;'>{}</p></div>".format(var_to_plot), unsafe_allow_html=True)
            chart_data = pd.DataFrame({var_to_plot: data[var_to_plot], 'Probability of Success': model.predict_proba(data.drop('success', axis=1))[:, 1]})
            if data[var_to_plot].dtype == object:
                chart = alt.Chart(chart_data).mark_circle(size=60).encode(
                    x=alt.X(var_to_plot, title=var_to_plot),
                    y=alt.Y('Probability of Success', title='Probability of Success', scale=alt.Scale(domain=(0, 1.1))),
                    tooltip=[var_to_plot, 'Probability of Success']
                ).interactive()
            else:
                chart = alt.Chart(chart_data).mark_circle(size=60).encode(
                    x=alt.X(var_to_plot, title=var_to_plot, scale=alt.Scale(zero=False)),
                    y=alt.Y('Probability of Success', title='Probability of Success', scale=alt.Scale(domain=(0, 1.1))),
                    tooltip=[var_to_plot, 'Probability of Success']
                ).interactive()

            # Add a black dot to the plot corresponding to the selected input
            select_data = pd.DataFrame(inputs, index=[0])
            select_data['Probability of Success'] = prob_success
            red_dot = alt.Chart(select_data).mark_circle(size=100, color='black').encode(
                x=alt.X(var_to_plot, title=var_to_plot),
                y=alt.Y('Probability of Success', title='Probability of Success')
            )

            legend = alt.Chart(pd.DataFrame({'legend': ['Selected Input']})).mark_circle(size=100, color='black').encode(y=alt.Y('legend', axis=None), x=alt.value(650))

            if data[var_to_plot].dtype == object:
                chart = chart + red_dot + legend
            else:
                chart = chart + red_dot

            st.altair_chart(chart, use_container_width=True)
        except UnboundLocalError as e:
            st.warning("Please train a model before attempting to make predictions.")

def save_model(model, csv_filename):
    # Extract the filename without the extension
    base_filename = os.path.splitext(csv_filename)[0]
    # Construct the pickle filename by appending .pkl to the base filename
    pickle_filename = base_filename + ".pkl"
    # Save the model as a pickle file
    with open(pickle_filename, "wb") as file:
        pickle.dump(model, file)

def load_pickles():
    pickles = []
    # Scan the directory for pickle files
    for file in os.listdir():
        if file.endswith(".pkl"):
            pickles.append(file)
    return pickles

def load_model(model_path):
    try:
        # Load the saved model
        with open(model_path, "rb") as file:
            model = pickle.load(file)
        return model
    except:
        return None

if __name__ == '__main__':
    main()