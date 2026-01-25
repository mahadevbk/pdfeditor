import streamlit as st
import PyPDF2
import os
import io
import fitz  # PyMuPDF
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
from docx import Document
import pandas as pd
import img2pdf
import tempfile
import zipfile
import base64
from streamlit_sortables import sort_items

# ------------------ PAGE SETTINGS -------------------
st.set_page_config(page_title="Dev's PDF Editor", layout="wide")

# Custom CSS for UI Polish and Reorder Bar Legibility
st.markdown(f"""
    <style>
    /* Fix legibility for sortable items: white text on dark primary color */
    .stSortableList div div div, .stSortableList span, .stSortableList p {{
        color: #ffffff !important; 
        font-weight: 600 !important;
    }}
    /* Card style for thumbnails */
    .thumb-container {{
        background-color: #0d5384;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #ccff0033;
        margin-bottom: 8px;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 220px;
        overflow: hidden;
    }}
    .thumb-container img {{
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
    }}
    .file-label {{
        font-size: 0.8rem;
        color: #ffffff;
        text-align: center;
        height: 2.5rem;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }}
    </style>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([1, 8])
with col1:
    st.write("## 📑") 
with col2:
    st.title("Dev's PDF Editor")

# ------------------ SESSION STATE -------------------
if 'operation' not in st.session_state:
    st.session_state.operation = None
if 'rotation_data' not in st.session_state:
    st.session_state.rotation_data = {}
if 'thumbs' not in st.session_state:
    st.session_state.thumbs = {}

# ------------------ CORE FUNCTIONS -------------------

def get_visual_merge_output(sorted_filenames, file_map, rotation_data):
    writer = PyPDF2.PdfWriter()
    for name in sorted_filenames:
        pdf_bytes = file_map[name].getvalue()
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        angle = rotation_data.get(name, 0)
        for page in reader.pages:
            if angle != 0:
                page.rotate(angle)
            writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

def split_pdf(uploaded_file, page_ranges):
    reader = PyPDF2.PdfReader(uploaded_file)
    output_files = []
    for rng in page_ranges.split(','):
        try:
            start, end = map(int, rng.split('-'))
            writer = PyPDF2.PdfWriter()
            for i in range(start-1, min(end, len(reader.pages))):
                writer.add_page(reader.pages[i])
            buf = io.BytesIO()
            writer.write(buf)
            buf.seek(0)
            output_files.append(buf)
        except: continue
    return output_files

def images_to_pdf(image_files):
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for img in image_files:
            p = os.path.join(tmp, img.name)
            with open(p, 'wb') as f:
                f.write(img.read())
            paths.append(p)
        out = io.BytesIO()
        out.write(img2pdf.convert(paths, rotation=img2pdf.Rotation.ifvalid))
        out.seek(0)
        return out

# ------------------ SIDEBAR & MENU -------------------
st.sidebar.title("📑 Menu")
if st.session_state.operation is None:
    with st.sidebar.expander("🔄 Convert"):
        if st.sidebar.button("Image to Text"): st.session_state.operation = "OCR Image to Text"
        if st.sidebar.button("Images to PDF"): st.session_state.operation = "Images to PDF"
        if st.sidebar.button("PDF to Images"): st.session_state.operation = "PDF to Images"
    with st.sidebar.expander("🔧 Edit"):
        if st.sidebar.button("Merge PDFs"): st.session_state.operation = "Merge PDFs"
        if st.sidebar.button("Split PDF"): st.session_state.operation = "Split PDF"
else:
    if st.sidebar.button("⬅️ Back to Menu"):
        st.session_state.operation = None
        st.session_state.rotation_data = {}
        st.session_state.thumbs = {}
        st.rerun()

# ------------------ MAIN UI -------------------
op = st.session_state.operation

if not op:
    st.write("Select an operation from the sidebar to get started.")
elif op == "Merge PDFs":
    st.subheader("▶️ Visual PDF Merger & Rotator")
    fs = st.file_uploader("Upload PDFs", accept_multiple_files=True, type='pdf')
    
    if fs:
        file_names = []
        file_map = {}
        for file in fs:
            file_names.append(file.name)
            file_map[file.name] = file
            if file.name not in st.session_state.thumbs:
                try:
                    imgs = convert_from_bytes(file.getvalue(), first_page=1, last_page=1)
                    buf = io.BytesIO()
                    imgs[0].save(buf, format="PNG")
                    st.session_state.thumbs[file.name] = base64.b64encode(buf.getvalue()).decode()
                except Exception as e:
                    st.error(f"Error previewing {file.name}: {e}")

        st.write("### 1. Set Order")
        sorted_filenames = sort_items(file_names, direction="horizontal")

        st.write("### 2. Preview & Rotation")
        max_cols = 5
        for i in range(0, len(sorted_filenames), max_cols):
            batch = sorted_filenames[i:i + max_cols]
            cols = st.columns(max_cols)
            for j, name in enumerate(batch):
                with cols[j]:
                    rot = st.session_state.rotation_data.get(name, 0)
                    img_b64 = st.session_state.thumbs.get(name)
                    if img_b64:
                        st.markdown(f'''<div class="thumb-container">
                            <img src="data:image/png;base64,{img_b64}" style="transform: rotate({rot}deg); transition: transform 0.3s ease;">
                            </div>''', unsafe_allow_html=True)
                    if st.button(f"Rotate ↻", key=f"rot_{name}_{i}_{j}"):
                        st.session_state.rotation_data[name] = (rot + 90) % 360
                        st.rerun()
                    st.markdown(f'<div class="file-label"><b>{name}</b><br>Current: {rot}°</div>', unsafe_allow_html=True)

        st.divider()
        if st.button("Merge and Download PDF", type="primary", use_container_width=True):
            output = get_visual_merge_output(sorted_filenames, file_map, st.session_state.rotation_data)
            st.success("✅ Merged!")
            st.download_button("Download Merged PDF", data=output, file_name='merged.pdf', use_container_width=True)

# [Other operation blocks like Split PDF or OCR would go here as per the local version]

st.markdown("---")
st.markdown("Dev's PDF Editor | Support: [mahadevbk/pdfeditor](https://github.com/mahadevbk/pdfeditor)")
