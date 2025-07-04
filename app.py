diff --git a/app.py b/app.py
index 44733a9a604edb29f8868f7956105dc36e991d84..a754fdd85be2c1e0e3ca2bd8e009f9edfa01a20d 100644
--- a/app.py
+++ b/app.py
@@ -1,167 +1,139 @@
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
 
+
+def sanitize(value: str) -> str:
+    """Return a filesystem friendly representation of value."""
+    return re.sub(r"[^\w\-]", "", unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode())
+
 if uploaded_file:
     pdf_reader = PdfReader(uploaded_file)
     pages_text = [page.extract_text() for page in pdf_reader.pages]
 
-    # Extract page ranges
+    # Determine page ranges for each issue
     issue_ids = []
     issue_starts = []
     for i, text in enumerate(pages_text):
         if text:
             match = re.search(r"ID\s+(\d{6})", text)
             if match:
-                issue_id = match.group(1)
+                issue_raw = match.group(1)
+                issue_id = issue_raw.lstrip("0").rstrip("0") or "0"
                 if not issue_ids or issue_id != issue_ids[-1]:
                     issue_ids.append(issue_id)
                     issue_starts.append(i)
 
     issue_starts.append(len(pages_text))
     issue_ranges = [
-        {"Issue ID": issue_ids[i], "start": issue_starts[i], "end": issue_starts[i+1]}
+        {"Issue ID": issue_ids[i], "start": issue_starts[i], "end": issue_starts[i + 1]}
         for i in range(len(issue_ids))
     ]
 
     # Extract metadata from each issue's first page
     metadata_list = []
-    
-    st.markdown("### 🔧 Customize Filename Format")
-    st.markdown("Use curly braces like `{ID}`, `{Location}`, `{Location Detail}`, `{Equipment ID}`, `{Status}`")
-
-    default_pattern = "Issue_{ID}_{Location Detail}"
-    filename_pattern = st.text_input("Filename Pattern", value=default_pattern, help="Use available fields in {braces} to generate filenames.")
-
-    st.markdown("**Insert Field:**")
-    col1, col2, col3, col4, col5 = st.columns(5)
-    if col1.button("{ID}"):
-        st.session_state.filename_pattern = st.session_state.get("filename_pattern", default_pattern) + "{ID}"
-    if col2.button("{Location}"):
-        st.session_state.filename_pattern = st.session_state.get("filename_pattern", default_pattern) + "{Location}"
-    if col3.button("{Location Detail}"):
-        st.session_state.filename_pattern = st.session_state.get("filename_pattern", default_pattern) + "{Location Detail}"
-    if col4.button("{Equipment ID}"):
-        st.session_state.filename_pattern = st.session_state.get("filename_pattern", default_pattern) + "{Equipment ID}"
-    if col5.button("{Status}"):
-        st.session_state.filename_pattern = st.session_state.get("filename_pattern", default_pattern) + "{Status}"
-
-    if "filename_pattern" in st.session_state:
-        filename_pattern = st.session_state.filename_pattern
-
-    # Preview logic
-    def preview_filename(issue_meta, pattern):
-        try:
-            return pattern.format(**issue_meta)
-        except KeyError:
-            return "Missing fields"
-
-    st.markdown("#### 📂 Filename Previews")
-    for meta in metadata_list[:5]:
-        st.markdown("- " + preview_filename(meta, filename_pattern))
-
-
-for issue in issue_ranges:
+    for issue in issue_ranges:
         text = pages_text[issue["start"]]
         data = {"Issue ID": issue["Issue ID"]}
         if text:
-            def match_field(field):
+            def match_field(field: str):
                 m = re.search(fr"{re.escape(field)}\s+(.*?)\n", text)
                 return m.group(1).strip() if m else None
 
             fields = [
                 ("Location", "Location"),
                 ("Location Detail", "Location Detail"),
                 ("Equipment ID", "Equipment ID"),
                 ("Equipment Type", "Equipment Type"),
                 ("Project Activity", "Project Activity.*?"),
                 ("Responsible Person", "Responsible Person"),
-                ("Rework Required", "Rework Required\\?"),
+                ("Rework Required", "Rework Required\?"),
                 ("Root Cause", "Root cause"),
-                ("Priority", "Priority")
+                ("Priority", "Priority"),
             ]
             for key, field in fields:
                 val = match_field(field)
                 if val:
                     data[key] = val
         metadata_list.append(data)
 
     st.success(f"Detected {len(issue_ranges)} issues.")
 
-    # Prepare field selection and order
-    all_fields = list(metadata_list[0].keys())
-    all_fields.remove("Issue ID")
-
-    st.write("### Customize Filename Fields")
-    selected_fields = st.multiselect(
-        "Select metadata fields to include in filenames:",
-        options=all_fields,
-        default=["Location Detail", "Location"]
+    # ---------------- Filename customization -----------------
+    available_fields = sorted({k for meta in metadata_list for k in meta.keys()})
+    st.markdown("### 🔧 Customize Filename Format")
+    st.markdown(
+        "Use curly braces to reference fields. Available fields: "
+        + ", ".join(f"`{{{f}}}`" for f in available_fields)
     )
 
-    reordered_fields = selected_fields
+    default_pattern = "ISSUE_{Issue ID}_{Location Detail}"
+    if "filename_pattern" not in st.session_state:
+        st.session_state.filename_pattern = default_pattern
 
-    separator = st.text_input("Filename separator (e.g. _ or -):", value="_", key="separator_input")
+    st.text_input(
+        "Filename Pattern",
+        key="filename_pattern",
+    )
 
-    # Use actual metadata to build example filename
+    st.markdown("**Insert Field:**")
+    cols = st.columns(len(available_fields))
+    for col, field in zip(cols, available_fields):
+        if col.button(f"{{{field}}}"):
+            st.session_state.filename_pattern += f"{{{field}}}"
+
+    # Preview example filename
+    def build_filename(meta: dict) -> str:
+        clean_meta = {k: sanitize(meta.get(k, "NA")) for k in available_fields}
+        try:
+            return st.session_state.filename_pattern.format(**clean_meta) + ".pdf"
+        except KeyError as e:
+            return f"Missing {e.args[0]}"
+
+    st.markdown("#### 📂 Filename Preview")
     if metadata_list:
-        first_issue_meta = metadata_list[0]
-        example_values = [
-            re.sub(r'[^\w\-]', '', unicodedata.normalize('NFKD', str(first_issue_meta.get(f, 'NA'))).encode('ascii', 'ignore').decode())
-            for f in reordered_fields
-        ]
-        example_filename = f"ISSUE{separator}{first_issue_meta['Issue ID']}"
-        if example_values:
-            example_filename += separator + separator.join(example_values)
-        example_filename += ".pdf"
-        st.info(f"Example filename: {example_filename}")
-
-    # Generate ZIP and CSV
+        st.info(build_filename(metadata_list[0]))
+
+    # ---------------- Generate files -----------------
     if st.button("Generate Issue PDFs"):
         zip_buffer = io.BytesIO()
         csv_output = io.StringIO()
         csv_writer = csv.writer(csv_output)
-        csv_writer.writerow(["Filename", "Issue ID"] + reordered_fields)
+        csv_writer.writerow(["Filename"] + available_fields)
 
         with zipfile.ZipFile(zip_buffer, "w") as zipf:
             uploaded_file.seek(0)
             pdf = PdfReader(uploaded_file)
-
             for issue, meta in zip(issue_ranges, metadata_list):
                 writer = PdfWriter()
                 for p in range(issue["start"], issue["end"]):
                     writer.add_page(pdf.pages[p])
 
-                values = [meta.get(field, "NA") for field in reordered_fields]
-                cleaned_values = [
-                    re.sub(r'[^\w\-]', '', unicodedata.normalize('NFKD', str(v)).encode('ascii', 'ignore').decode())
-                    for v in values
-                ]
-                filename = f"ISSUE{separator}{meta['Issue ID']}"
-                if cleaned_values:
-                    filename += separator + separator.join(cleaned_values)
-                filename += ".pdf"
+                clean_meta = {k: sanitize(meta.get(k, "NA")) for k in available_fields}
+                filename = st.session_state.filename_pattern.format(**clean_meta) + ".pdf"
 
                 pdf_output = io.BytesIO()
                 writer.write(pdf_output)
                 pdf_output.seek(0)
                 zipf.writestr(filename, pdf_output.getvalue())
 
-                csv_writer.writerow([filename, meta['Issue ID']] + values)
+                csv_writer.writerow([filename] + [meta.get(f, "") for f in available_fields])
 
-        st.download_button("Download ZIP of All Issues", data=zip_buffer.getvalue(), file_name="ISSUE_REPORTS.ZIP")
+        st.download_button(
+            "Download ZIP of All Issues",
+            data=zip_buffer.getvalue(),
+            file_name="ISSUE_REPORTS.ZIP",
+        )
 
-        # Show summary table using selected fields
         summary_df = pd.read_csv(io.StringIO(csv_output.getvalue()))
         st.write("### \U0001F4CB Summary of Generated Issues")
         st.dataframe(summary_df, use_container_width=True)
