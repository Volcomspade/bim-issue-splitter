import streamlit as st
import zipfile
import pdfplumber
from PyPDF2 import PdfWriter, PdfReader
import io
import re
import pandas as pd

st.set_page_config(page_title="BIM 360 Issue Splitter", layout="wide")
st.title("📄 BIM 360 Issue Report Splitter")

uploaded_file = st.file_uploader("Upload BIM 360 Issue Report PDF", type=["pdf"])

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        pages_text = [page.extract_text() for page in pdf.pages]

    # Extract page ranges
    issue_ids = []
    issue_starts = []
    for i, text in enumerate(pages_text):
        if text:
            match = re.search(r"ID\s+(\d{6})", text)
            if match:
                issue_id = match.group(1)
                if not issue_ids or issue_id != issue_ids[-1]:
                    issue_ids.append(issue_id)
                    issue_starts.append(i)

    issue_starts.append(len(pages_text))
    issue_ranges = [
        {"Issue ID": issue_ids[i], "start": issue_starts[i], "end": issue_starts[i+1]}
        for i in range(len(issue_ids))
    ]

    # Extract metadata from each issue's first page
    metadata_list = []
    for issue in issue_ranges:
        text = pages_text[issue["start"]]
        data = {"Issue ID": issue["Issue ID"]}
        if text:
            def match_field(field):
                m = re.search(fr"{re.escape(field)}\s+(.*?)\n", text)
                return m.group(1).strip() if m else None

            fields = [
                ("Location", "Location"),
                ("Location Detail", "Location Detail"),
                ("Equipment ID", "Equipment ID"),
                ("Equipment Type", "Equipment Type"),
                ("Project Activity", "Project Activity.*?"),
                ("Responsible Person", "Responsible Person"),
                ("Rework Required", "Rework Required\?"),
                ("Root Cause", "Root cause"),
                ("Priority", "Priority")
            ]
            for key, field in fields:
                val = match_field(field)
                if val:
                    data[key] = val
        metadata_list.append(data)

    st.success(f"Detected {len(issue_ranges)} issues.")

    # Choose fields and separator with editable table interface
    all_fields = list(metadata_list[0].keys())
    all_fields.remove("Issue ID")

    st.write("### Customize Filename Fields")
    default_df = pd.DataFrame({"Field": ["Location Detail"] + [f for f in all_fields if f != "Location Detail"]})
    field_df = st.data_editor(default_df, num_rows="dynamic", use_container_width=True)
    reordered_fields = field_df["Field"].dropna().tolist()

    separator = st.text_input("Filename separator (e.g. _ or -):", value="_")

    # Show example filename using selected fields
    example_meta = metadata_list[0]
    example_parts = [example_meta.get(field, "NA") for field in reordered_fields]
    example_filename = f"ISSUE{separator}{example_meta['Issue ID']}"
    if example_parts:
        example_filename += separator + separator.join(example_parts).upper().replace(" ", "_")
    example_filename += ".pdf"
    st.info(f"Example filename: {example_filename}")

    # Generate ZIP
    if st.button("Generate Issue PDFs"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            with pdfplumber.open(uploaded_file) as pdf:
                for issue, meta in zip(issue_ranges, metadata_list):
                    writer = PdfWriter()
                    for p in range(issue["start"], issue["end"]):
                        pdf_page = pdf.pages[p].pdf
                        reader = PdfReader(io.BytesIO(pdf_page))
                        writer.add_page(reader.pages[0])

                    values = [meta.get(field, "NA") for field in reordered_fields]
                    filename = f"ISSUE{separator}{meta['Issue ID']}"
                    if values:
                        filename += separator + separator.join(values).upper().replace(" ", "_")
                    filename += ".pdf"

                    pdf_output = io.BytesIO()
                    writer.write(pdf_output)
                    zipf.writestr(filename, pdf_output.getvalue())

        st.download_button("Download ZIP of All Issues", data=zip_buffer.getvalue(), file_name="ISSUE_REPORTS.ZIP")
