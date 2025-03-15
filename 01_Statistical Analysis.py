import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import t

st.set_page_config(page_title="iRIS-Sage", page_icon=":guardsman:")
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            #header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
image = st.image("Picture1.png", use_container_width=False)
header = st.title("iRIS Sage Statistical Analysis")

def t_distribution_analysis(data, column, confidence_level):
    mean = data[column].mean()
    std = data[column].std()
    n = len(data[column])
    df = n - 1
    t_critical = t.ppf((1 + confidence_level) / 2, df)
    margin_of_error = t_critical * std / np.sqrt(n)
    lower_bound = mean - margin_of_error
    upper_bound = mean + margin_of_error
    return mean, lower_bound, upper_bound

def rss_analysis(data, column):
    mean = np.sqrt(np.mean(data[column]**2))
    std = np.sqrt(np.mean(data[column]**2))
    n = len(data[column])
    margin_of_error = 1.96 * std / np.sqrt(n)
    lower_bound = mean - margin_of_error
    upper_bound = mean + margin_of_error
    return mean, lower_bound, upper_bound

def plot_t_distribution(data, column, confidence_level):
    mean, lower_bound, upper_bound = t_distribution_analysis(data, column, confidence_level)
    fig, ax = plt.subplots()
    ax.hist(data[column], bins=30, density=True)
    x = np.linspace(data[column].min(), data[column].max(), 100)
    y = t.pdf(x, df=len(data[column]) - 1, loc=mean, scale=data[column].std())
    ax.plot(x, y, label='t-distribution')
    ax.axvline(x=lower_bound, color='red', label='lower bound')
    ax.axvline(x=upper_bound, color='green', label='upper bound')
    ax.axvline(x=mean, color='blue', label='mean')
    ax.legend(loc='center right')
    ax.text(0.95, 0.95, "Max: {:.2f}".format(data[column].max()), transform=ax.transAxes, ha='right', va='top')
    ax.text(0.95, 0.90, "Mean: {:.2f}".format(mean), transform=ax.transAxes, ha='right', va='top')
    ax.text(0.95, 0.85, "Min: {:.2f}".format(data[column].min()), transform=ax.transAxes, ha='right', va='top')

    ax.set_title(f"T-Square Analysis for {column} Column")

    st.pyplot(fig)

def plot_rss_distribution(data, column):
    mean = data[column].mean()
    std = np.sqrt(np.mean(data[column]**2))
    upper_bound = data[column].quantile(0.95)
    x = np.linspace(data[column].min(), data[column].max(), 1000)
    y = np.exp(-0.5 * ((x - mean) / np.sqrt(mean**2 + upper_bound**2 - 2 * mean * upper_bound))**2) / (np.sqrt(2 * np.pi) * std)
    fig, ax = plt.subplots()
    ax.hist(data[column], bins=30, density=True)
    ax.plot(x, y, label='RSS')
    ax.axvline(x=upper_bound, color='red', label='upper bound')
    ax.axvline(x=mean, color='blue', label='mean')
    ax.legend(loc='center right')
    ax.text(0.95, 0.95, "Max: {:.2f}".format(data[column].max()), transform=ax.transAxes, ha='right', va='top')
    ax.text(0.95, 0.90, "Mean: {:.2f}".format(mean), transform=ax.transAxes, ha='right', va='top')
    ax.text(0.95, 0.85, "Min: {:.2f}".format(data[column].min()), transform=ax.transAxes, ha='right', va='top')

    ax.set_title(f"RSS Analysis for {column} Column")

    st.pyplot(fig)


def main():
    uploaded_file = st.sidebar.file_uploader("", type="csv")
    
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        columns = data.columns

        analysis_type = st.sidebar.selectbox("Select analysis type", ["T-square", "RSS"])

        if analysis_type == "T-square":
            selected_column = st.sidebar.selectbox("Select a column", columns)
            confidence_level = st.sidebar.slider("Confidence level", 0.0, 1.0, 0.95)
            plot_t_distribution(data, selected_column, confidence_level)

        elif analysis_type == "RSS":
            selected_column = st.sidebar.selectbox("Select a column", columns)
            plot_rss_distribution(data, selected_column)

        st.sidebar.write(data[selected_column].to_frame().style.set_caption("Data"))

if __name__ == "__main__":
    main()
