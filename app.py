import streamlit as st
import os
import zipfile
from datetime import datetime
from utils import detect_report_type, extract_bim360_issues
from io import BytesIO

st.set_page_config(page_title="Issue Report Splitter")

st.title("📄 Issue Report Splitter")

uploaded_file = st.file_uploader("Upload a BIM 360 Issue Report PDF", type="pdf")

if uploaded_file:
    with st.spinner("Analyzing report..."):
        file_bytes = uploaded_file.read()
        report_type = detect_report_type(file_bytes)
        if report_type != "bim360":
            st.error("Only BIM 360 reports are supported in this version.")
        else:
            st.success("BIM 360 report detected!")
            filename_option = st.selectbox("Choose filename format:", [
                "{IssueID}_{Location}",
                "{IssueID}_{Location}_{EquipmentID}",
                "{IssueID}_{Location}_{LocationDetail}_{EquipmentID}"
            ])
            if st.button("Split Report"):
                with st.spinner("Splitting issues..."):
                    issues = extract_bim360_issues(file_bytes, filename_option)
                    if not issues:
                        st.error("No issues found.")
                    else:
                        zip_buffer = BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w") as zipf:
                            for name, pdf_bytes in issues.items():
                                zipf.writestr(f"{name}.pdf", pdf_bytes)
                        zip_filename = f"Issue_Report_{datetime.now().strftime('%Y%m%d')}.zip"
                        st.download_button("📦 Download ZIP", zip_buffer.getvalue(), file_name=zip_filename)
