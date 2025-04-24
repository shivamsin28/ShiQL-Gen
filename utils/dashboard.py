import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import seaborn as sns

st.title("Dashboard")
df= sns.load_dataset('titanic')
st.dataframe(df)

