from PyPDF2 import PdfReader, PdfWriter
import re
from io import BytesIO
from zipfile import ZipFile
import os

def detect_report_type(filepath):
    try:
        reader = PdfReader(filepath)
        first_text = reader.pages[0].extract_text()
        if "Issue ID" in first_text and "Location" in first_text:
            return "BIM 360"
    except Exception:
        pass
    return "Unknown"

def extract_bim_issues(filepath):
    reader = PdfReader(filepath)
    issue_pages = {}
    issue_meta = {}
    current_issue = None
    buffer_pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        issue_match = re.search(r"Issue ID\s*:?\s*(\d+)", text)
        if issue_match:
            if current_issue:
                issue_pages[current_issue] = buffer_pages
            current_issue = issue_match.group(1)
            buffer_pages = [i]
            # Extract metadata
            location = re.search(r"Location\s*:?\s*(.+)", text)
            detail = re.search(r"Location Detail\s*:?\s*(.+)", text)
            equipment = re.search(r"Equipment ID\s*:?\s*(.+)", text)
            issue_meta[current_issue] = {
                "IssueID": current_issue,
                "Location": clean(location.group(1)) if location else "",
                "LocationDetail": clean(detail.group(1)) if detail else "",
                "EquipmentID": clean(equipment.group(1)) if equipment else "",
            }
        elif current_issue:
            buffer_pages.append(i)

    if current_issue:
        issue_pages[current_issue] = buffer_pages
    return issue_pages, issue_meta

def clean(s):
    return re.sub(r"[\\/:*?\"<>|]", "_", s.strip())

def get_available_fields(issue_meta):
    if not issue_meta:
        return []
    first = next(iter(issue_meta.values()))
    return list(first.keys())

def save_issues_as_zip(filepath, issue_pages, issue_meta, field_order, output_zip):
    reader = PdfReader(filepath)
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w") as zipf:
        for issue_id, pages in issue_pages.items():
            writer = PdfWriter()
            for p in pages:
                writer.add_page(reader.pages[p])
            meta = issue_meta.get(issue_id, {})
            filename_parts = [meta.get(k, "") for k in field_order]
            filename = "_".join([part for part in filename_parts if part]).strip("_") or issue_id
            buffer = BytesIO()
            writer.write(buffer)
            buffer.seek(0)
            zipf.writestr(f"{filename}.pdf", buffer.read())
    with open(output_zip, "wb") as f:
        f.write(zip_buffer.getvalue())
