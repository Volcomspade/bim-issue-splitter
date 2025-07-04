
import streamlit as st
import tempfile
import os
from utils import extract_bim360_issues, generate_filename_from_pattern
import zipfile
import datetime
import pandas as pd

st.set_page_config(page_title="📄 BIM 360 Issue Report Splitter", layout="wide")
st.title("📄 BIM 360 Issue Report Splitter")

with st.sidebar:
    st.markdown("### Upload a BIM 360 Issue Report")
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    field_tags = ["{IssueID}", "{Location}", "{LocationDetail}", "{EquipmentID}"]
    st.markdown("### Customize Filename Format")
    st.markdown("You can insert field tags into your desired naming format. Example: `Issue_{IssueID}_{LocationDetail}`")
    custom_format = st.text_input("Filename format", value="Issue_{IssueID}_{LocationDetail}_{EquipmentID}")

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Available Fields")
        for tag in field_tags:
            if st.button(tag):
                custom_format += tag

    preview = []
    apply = st.button("✅ Apply Format and Preview")

if uploaded_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())

        issues = extract_bim360_issues(file_path)
        if issues:
            if apply:
                example_names = [generate_filename_from_pattern(issue, custom_format) for issue in issues[:10]]
                df = pd.DataFrame({"Example Filenames": example_names})
                st.dataframe(df, use_container_width=True)

            if st.button("📦 Generate ZIP"):
                zip_name = f"Issue Report - {datetime.date.today()}.zip"
                zip_path = os.path.join(tmpdir, zip_name)
                with zipfile.ZipFile(zip_path, "w") as zipf:
                    for issue in issues:
                        output_path = os.path.join(tmpdir, f"{generate_filename_from_pattern(issue, custom_format)}.pdf")
                        issue["pdf"].write(output_path)
                        zipf.write(output_path, arcname=os.path.basename(output_path))

                with open(zip_path, "rb") as f:
                    st.download_button("⬇️ Download ZIP", f, file_name=zip_name)
        else:
            st.error("❌ No issues found in the uploaded file.")
else:
    st.info("Upload a BIM 360 PDF report to begin.")
