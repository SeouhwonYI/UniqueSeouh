import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components


	
st.title("보행 약자를 위한 Extended Map Application")
DATE_COLUMN = 'date/time'
	
@st.cache_data
def load_data(nrows):
    data = pd.read_csv("subway.csv", nrows=nrows)
    return data
	
data_load_state = st.text('Loading data...')
data = load_data(500)
data_load_state.text("Done! 500 Data have been loaded")
	
if st.checkbox('Show raw data'):
    st.subheader('지하철 위경도 데이터')
    st.write(data)

st.header("최적 경로 추천")
path_to_html = "./prototype/html/index.html" 

# Read file and keep in variable
with open(path_to_html, encoding='utf-8') as f:
    html_data = f.read()

## Show in webpage
st.components.v1.html(html_data,height=500)