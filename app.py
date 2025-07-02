import streamlit as st
from utils_bim_only import detect_report_type, extract_bim_issues, get_available_fields, save_issues_as_zip
import os

st.set_page_config(page_title="BIM 360 Issue Splitter", layout="wide")

st.title("📄 BIM 360 Issue Report Splitter")

uploaded_file = st.file_uploader("Upload a BIM 360 Issue Report PDF", type=["pdf"])

if uploaded_file:
    with open("temp_input.pdf", "wb") as f:
        f.write(uploaded_file.read())

    report_type = detect_report_type("temp_input.pdf")

    if report_type != "BIM 360":
        st.error("❌ Only BIM 360 reports are supported in this version.")
    else:
        st.success("✅ BIM 360 Report detected.")
        issue_pages, issue_meta = extract_bim_issues("temp_input.pdf")

        if not issue_pages:
            st.error("⚠️ No issues found in this file.")
        else:
            st.subheader("Filename Settings")
            available_fields = get_available_fields(issue_meta)
            selected_fields = st.multiselect("Choose filename components", available_fields, default=available_fields)
            field_order = st.text_input("Enter field order separated by commas (e.g. IssueID,Location,EquipmentID)",
                                        ",".join(selected_fields))

            if st.button("📦 Generate ZIP"):
                save_path = "bim360_split_output.zip"
                save_issues_as_zip("temp_input.pdf", issue_pages, issue_meta, field_order.split(","), save_path)
                with open(save_path, "rb") as f:
                    st.download_button("⬇️ Download Split Issues ZIP", f, file_name="bim360_split_issues.zip")

                st.success("ZIP file created.")
