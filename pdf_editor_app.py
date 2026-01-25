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

# Custom CSS for UI Legibility
st.markdown(f"""
    <style>
    .stSortableList div div div, .stSortableList span, .stSortableList p {{
        color: #ffffff !important; 
        font-weight: 600 !important;
    }}
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

st.title("📑 Dev's PDF Editor")

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

def add_watermark(uploaded_file, text):
    doc = fitz.open(stream=uploaded_file.read(), filetype='pdf')
    for p in doc:
        p.insert_text((50, 50), text, fontsize=30, color=(0.7, 0.7, 0.7), rotate=45)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf

def flatten_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype='pdf')
    for p in doc:
        p.flatten_annotations()
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf

# ------------------ SIDEBAR MENU -------------------
st.sidebar.title("🔧 Tools")
if st.session_state.operation is None:
    with st.sidebar.expander("🔄 Convert & OCR"):
        if st.sidebar.button("Images to PDF"): st.session_state.operation = "Images to PDF"
        if st.sidebar.button("PDF to Images"): st.session_state.operation = "PDF to Images"
        if st.sidebar.button("OCR PDF/Image to Text"): st.session_state.operation = "OCR"
    with st.sidebar.expander("✏️ Edit & Merge"):
        if st.sidebar.button("Visual Merge & Rotate"): st.session_state.operation = "Merge"
        if st.sidebar.button("Add Watermark"): st.session_state.operation = "Watermark"
        if st.sidebar.button("Flatten PDF"): st.session_state.operation = "Flatten"
else:
    if st.sidebar.button("⬅️ Back to Menu"):
        st.session_state.operation = None
        st.session_state.rotation_data = {}
        st.session_state.thumbs = {}
        st.rerun()

# ------------------ MAIN UI LOGIC -------------------
op = st.session_state.operation

if op == "Merge":
    st.subheader("▶️ Visual PDF Merger")
    fs = st.file_uploader("Upload PDFs", accept_multiple_files=True, type='pdf')
    if fs:
        file_names = [f.name for f in fs]
        file_map = {f.name: f for f in fs}
        
        # Thumbnail generation
        for file in fs:
            if file.name not in st.session_state.thumbs:
                imgs = convert_from_bytes(file.getvalue(), first_page=1, last_page=1)
                buf = io.BytesIO()
                imgs[0].save(buf, format="PNG")
                st.session_state.thumbs[file.name] = base64.b64encode(buf.getvalue()).decode()

        sorted_filenames = sort_items(file_names, direction="horizontal")
        
        # Grid View
        cols = st.columns(5)
        for i, name in enumerate(sorted_filenames):
            with cols[i % 5]:
                rot = st.session_state.rotation_data.get(name, 0)
                img_b64 = st.session_state.thumbs.get(name)
                st.markdown(f'<div class="thumb-container"><img src="data:image/png;base64,{img_b64}" style="transform: rotate({rot}deg);"></div>', unsafe_allow_html=True)
                if st.button(f"Rotate ↻", key=f"rot_{name}"):
                    st.session_state.rotation_data[name] = (rot + 90) % 360
                    st.rerun()
                st.markdown(f'<div class="file-label"><b>{name}</b></div>', unsafe_allow_html=True)

        if st.button("Merge and Download", type="primary"):
            out = get_visual_merge_output(sorted_filenames, file_map, st.session_state.rotation_data)
            st.download_button("📥 Download Result", data=out, file_name="merged.pdf")

elif op == "Watermark":
    f = st.file_uploader("Upload PDF", type='pdf')
    txt = st.text_input("Watermark Text", "DRAFT")
    if f and st.button("Apply Watermark"):
        out = add_watermark(f, txt)
        st.download_button("Download Watermarked PDF", data=out, file_name="watermarked.pdf")

elif op == "Flatten":
    f = st.file_uploader("Upload PDF", type='pdf')
    if f and st.button("Flatten"):
        out = flatten_pdf(f)
        st.download_button("Download Flattened PDF", data=out, file_name="flattened.pdf")

elif op == "OCR":
    files = st.file_uploader("Upload Image or PDF", accept_multiple_files=True)
    if files and st.button("Extract Text"):
        for f in files:
            if f.type == "application/pdf":
                imgs = convert_from_bytes(f.read())
                text = "".join([pytesseract.image_to_string(img) for img in imgs])
            else:
                text = pytesseract.image_to_string(Image.open(f))
            st.text_area(f"Result: {f.name}", text, height=200)

elif op == "Images to PDF":
    imgs = st.file_uploader("Upload Images", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
    if imgs and st.button("Generate PDF"):
        # We need to save to temp files for img2pdf specifically
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for img in imgs:
                p = os.path.join(tmpdir, img.name)
                with open(p, "wb") as f: f.write(img.read())
                paths.append(p)
            pdf_bytes = img2pdf.convert(paths)
            st.download_button("Download PDF", data=pdf_bytes, file_name="images.pdf")

elif op == "PDF to Images":
    f = st.file_uploader("Upload PDF", type='pdf')
    if f and st.button("Convert to Images"):
        imgs = convert_from_bytes(f.read())
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as z:
            for i, img in enumerate(imgs):
                img_buf = io.BytesIO()
                img.save(img_buf, format="PNG")
                z.writestr(f"page_{i+1}.png", img_buf.getvalue())
        st.download_button("Download ZIP of Images", data=zip_buf.getvalue(), file_name="pages.zip")

else:
    st.info("Select a tool from the sidebar to begin.")
