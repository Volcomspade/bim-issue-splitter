import streamlit as st
import zipfile
from PyPDF2 import PdfReader, PdfWriter
import io
import re
import pandas as pd
import csv
import unicodedata

st.set_page_config(page_title="BIM 360 Issue Splitter", layout="wide")
st.title("📄 BIM 360 Issue Report Splitter")

uploaded_file = st.file_uploader("Upload BIM 360 Issue Report PDF", type=["pdf"])

if uploaded_file:
    pdf_reader = PdfReader(uploaded_file)
    pages_text = [page.extract_text() for page in pdf_reader.pages]

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
                ("Rework Required", "Rework Required\\?"),
                ("Root Cause", "Root cause"),
                ("Priority", "Priority")
            ]
            for key, field in fields:
                val = match_field(field)
                if val:
                    data[key] = val
        metadata_list.append(data)

    st.success(f"Detected {len(issue_ranges)} issues.")

    # Choose fields and separator
    all_fields = list(metadata_list[0].keys())
    all_fields.remove("Issue ID")

    st.write("### Customize Filename Fields")
    default_df = pd.DataFrame({"Field": ["Location Detail"] + [f for f in all_fields if f != "Location Detail"]})
    field_df = st.data_editor(default_df, num_rows="dynamic", use_container_width=True, key="field_editor")
    reordered_fields = field_df["Field"].dropna().tolist()

    separator = st.text_input("Filename separator (e.g. _ or -):", value="_", key="separator_input")

    # Show dynamic example filename using only selected fields
    example_values = [f"{f.upper().replace(' ', '_')}_EXAMPLE" for f in reordered_fields]
    example_filename = f"ISSUE{separator}000216"
    if example_values:
        example_filename += separator + separator.join(example_values)
    example_filename += ".pdf"
    st.info(f"Example filename: {example_filename}")

    # Generate ZIP and CSV
    if st.button("Generate Issue PDFs"):
        zip_buffer = io.BytesIO()
        csv_output = io.StringIO()
        csv_writer = csv.writer(csv_output)
        csv_writer.writerow(["Filename"] + ["Issue ID"] + reordered_fields)

        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            uploaded_file.seek(0)
            pdf = PdfReader(uploaded_file)

            for issue, meta in zip(issue_ranges, metadata_list):
                writer = PdfWriter()
                for p in range(issue["start"], issue["end"]):
                    writer.add_page(pdf.pages[p])

                values = [meta.get(field, "NA") for field in reordered_fields if field in meta]
                filename = f"ISSUE{separator}{meta['Issue ID']}"
                if values:
                    cleaned_values = [
                        re.sub(r'[^\w\-]', '', unicodedata.normalize('NFKD', v).encode('ascii', 'ignore').decode())
                        for v in values
                    ]
                    filename += separator + separator.join(cleaned_values)
                filename += ".pdf"

                pdf_output = io.BytesIO()
                writer.write(pdf_output)
                pdf_output.seek(0)
                zipf.writestr(filename, pdf_output.getvalue())

                csv_writer.writerow([filename, meta['Issue ID']] + values)

            zipf.writestr("summary.csv", csv_output.getvalue())

        st.download_button("Download ZIP of All Issues", data=zip_buffer.getvalue(), file_name="ISSUE_REPORTS.ZIP")
