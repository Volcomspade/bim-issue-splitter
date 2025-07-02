
import streamlit as st
from PyPDF2 import PdfReader
import tempfile
import os
from utils_bim_only import extract_bim360_issues_fixed, generate_filename_options, zip_files_with_custom_names

st.set_page_config(page_title="BIM 360 Issue Report Splitter", layout="wide")
st.title("📄 BIM 360 Issue Report Splitter")
st.caption("Upload a BIM 360 Issue Report PDF")

uploaded_file = st.file_uploader("Choose a PDF", type=["pdf"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        input_path = tmp_file.name

    with st.spinner("Analyzing PDF..."):
        reader = PdfReader(input_path)
        if not any("Issue Report" in (page.extract_text() or "") for page in reader.pages[:3]):
            st.error("❌ Only BIM 360 reports are supported in this version.")
        else:
            files = extract_bim360_issues_fixed(input_path)

            if files:
                st.success(f"✅ Extracted {len(files)} issues from report.")
                options = generate_filename_options(files)

                with st.form("filename_form"):
                    st.write("**Custom Filename Structure**")
                    order = st.multiselect("Select and order filename parts", options, default=options)
                    submitted = st.form_submit_button("Download ZIP")
                    if submitted:
                        zip_path = zip_files_with_custom_names(files, order)
                        with open(zip_path, "rb") as f:
                            st.download_button("📦 Download ZIP", f, file_name="bim360_issues.zip")
            else:
                st.error("❌ No issues found in this BIM 360 report.")
