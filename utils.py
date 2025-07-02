import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
import re

def detect_report_type(file_bytes):
    try:
        pdf = PdfReader(BytesIO(file_bytes))
        first_page_text = pdf.pages[0].extract_text()
        if "Issue ID" in first_page_text:
            return "bim360"
    except:
        pass
    return "unknown"

def extract_bim360_issues(file_bytes, filename_option="{IssueID}_{Location}"):
    pdf = PdfReader(BytesIO(file_bytes))
    issues = {}
    issue_starts = []

    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "Issue ID:" in text:
            match = re.search(r"Issue ID:\s*(\d+)", text)
            if match:
                issue_id = match.group(1)
                issue_starts.append((i, issue_id))

    for idx, (start_page, issue_id) in enumerate(issue_starts):
        end_page = issue_starts[idx + 1][0] if idx + 1 < len(issue_starts) else len(pdf.pages)
        writer = PdfWriter()
        location = location_detail = equipment_id = "Unknown"

        for i in range(start_page, end_page):
            writer.add_page(pdf.pages[i])
            if i == start_page:
                text = pdf.pages[i].extract_text() or ""
                location_match = re.search(r"Location:\s*(.+)", text)
                detail_match = re.search(r"Location Detail:\s*(.+)", text)
                equip_match = re.search(r"Equipment ID:\s*(.+)", text)
                if location_match: location = location_match.group(1).strip()
                if detail_match: location_detail = detail_match.group(1).strip()
                if equip_match: equipment_id = equip_match.group(1).strip()

        filename = filename_option.format(
            IssueID=issue_id,
            Location=location.replace("/", "_"),
            LocationDetail=location_detail.replace("/", "_"),
            EquipmentID=equipment_id.replace("/", "_")
        )

        pdf_buffer = BytesIO()
        writer.write(pdf_buffer)
        issues[filename] = pdf_buffer.getvalue()

    return issues
