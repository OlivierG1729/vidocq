# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 12:04:24 2025

@author: olivi
"""

import streamlit as st

st.title("Explorator of concepts into a corpus")

uploaded_files = st.file_uploader("Upload your text documents", type=["txt"], accept_multiple_files=True)
search_terms = st.text_input("Givre your concepts (with a comma to separate them): ")

if uploaded_files and search_terms:
    with st.spinner("Analysis in progress..."):
        # traitement à venir
        pass




