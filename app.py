import streamlit as st
import zipfile
from PyPDF2 import PdfReader, PdfWriter
import io
import re
import pandas as pd
import csv
import unicodedata

st.set_page_config(page_title="BIM 360 Issue Splitter", layout="wide")
st.title("\U0001F4C4 BIM 360 Issue Report Splitter")

uploaded_file = st.file_uploader("Upload BIM 360 Issue Report PDF", type=["pdf"])


def sanitize(value: str) -> str:
    """Return a filesystem friendly representation of value."""
    return re.sub(r"[^\w\-]", "", unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode())


def normalize_issue_id(raw: str) -> str:
    """Return the issue ID without any leading zeros."""
    cleaned = str(raw).lstrip("0")
    return cleaned or "0"

if uploaded_file:
    pdf_reader = PdfReader(uploaded_file)
    pages_text = [page.extract_text() for page in pdf_reader.pages]

    # Determine page ranges for each issue
    issue_ids = []
    issue_starts = []
    for i, text in enumerate(pages_text):
        if text:
            match = re.search(r"ID\s+(\d+)", text)
            if match:
                issue_id = normalize_issue_id(match.group(1))
                if not issue_ids or issue_id != issue_ids[-1]:
                    issue_ids.append(issue_id)
                    issue_starts.append(i)

    issue_starts.append(len(pages_text))
    issue_ranges = [
        {"Issue ID": issue_ids[i], "start": issue_starts[i], "end": issue_starts[i + 1]}
        for i in range(len(issue_ids))
    ]

    # Extract metadata from each issue's first page
    metadata_list = []
    for issue in issue_ranges:
        text = pages_text[issue["start"]]
        data = {"Issue ID": issue["Issue ID"]}
        if text:
            def match_field(field: str):
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
                ("Priority", "Priority"),
            ]
            for key, field in fields:
                val = match_field(field)
                if val:
                    data[key] = val
        metadata_list.append(data)

    st.success(f"Detected {len(issue_ranges)} issues.")

    # ---------------- Filename customization -----------------
    available_fields = sorted({k for meta in metadata_list for k in meta.keys()})
    st.markdown("### 🔧 Customize Filename Format")
    st.markdown(
        "Use curly braces to reference fields. Available fields: "
        + ", ".join(f"`{{{f}}}`" for f in available_fields)
    )

    default_pattern = "ISSUE_{Issue ID}_{Location Detail}"
    if "filename_pattern" not in st.session_state:
        st.session_state.filename_pattern = default_pattern

    st.text_input(
        "Filename Pattern",
        key="filename_pattern",
    )

    st.markdown("**Insert Field:**")
    cols = st.columns(len(available_fields))
    for col, field in zip(cols, available_fields):
        if col.button(f"{{{field}}}"):
            st.session_state.filename_pattern += f"{{{field}}}"

    # Preview example filename
    def build_filename(meta: dict) -> str:
        clean_meta = {}
        for key in available_fields:
            value = meta.get(key, "NA")
            if key == "Issue ID":
                value = normalize_issue_id(value)
            clean_meta[key] = sanitize(value)
        try:
            return st.session_state.filename_pattern.format(**clean_meta) + ".pdf"
        except KeyError as e:
            return f"Missing {e.args[0]}"

    st.markdown("#### 📂 Filename Preview")
    if metadata_list:
        st.info(build_filename(metadata_list[0]))

    # ---------------- Generate files -----------------
    if st.button("Generate Issue PDFs"):
        zip_buffer = io.BytesIO()
        csv_output = io.StringIO()
        csv_writer = csv.writer(csv_output)
        csv_writer.writerow(["Filename"] + available_fields)

        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            uploaded_file.seek(0)
            pdf = PdfReader(uploaded_file)
            for issue, meta in zip(issue_ranges, metadata_list):
                writer = PdfWriter()
                for p in range(issue["start"], issue["end"]):
                    writer.add_page(pdf.pages[p])

                clean_meta = {}
                for key in available_fields:
                    value = meta.get(key, "NA")
                    if key == "Issue ID":
                        value = normalize_issue_id(value)
                    clean_meta[key] = sanitize(value)

                filename = (
                    st.session_state.filename_pattern.format(**clean_meta) + ".pdf"
                )

                pdf_output = io.BytesIO()
                writer.write(pdf_output)
                pdf_output.seek(0)
                zipf.writestr(filename, pdf_output.getvalue())

                row_values = []
                for key in available_fields:
                    value = meta.get(key, "")
                    if key == "Issue ID":
                        value = normalize_issue_id(value)
                    row_values.append(value)

                csv_writer.writerow([filename] + row_values)

        st.download_button(
            "Download ZIP of All Issues",
            data=zip_buffer.getvalue(),
            file_name="ISSUE_REPORTS.ZIP",
        )

        summary_df = pd.read_csv(io.StringIO(csv_output.getvalue()))
        st.write("### \U0001F4CB Summary of Generated Issues")
        st.dataframe(summary_df, use_container_width=True)
