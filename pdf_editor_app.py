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
    /* Legibility for sortable items - ensures white text on dark primary color */
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

def crop_pdf(uploaded_file, box):
    doc = fitz.open(stream=uploaded_file.read(), filetype='pdf')
    for p in doc:
        p.set_cropbox(fitz.Rect(*box))
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf

def add_watermark(uploaded_file, text):
    doc = fitz.open(stream=uploaded_file.read(), filetype='pdf')
    for p in doc:
        p.insert_text((50, 50), text, fontsize=20, color=(0.5, 0.5, 0.5), rotate=45)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf

def compress_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype='pdf')
    buf = io.BytesIO()
    doc.save(buf, deflate=True)
    doc.close()
    buf.seek(0)
    return buf

def encrypt_pdf(uploaded_file, pwd):
    rdr = PyPDF2.PdfReader(uploaded_file)
    w = PyPDF2.PdfWriter()
    for pg in rdr.pages:
        w.add_page(pg)
    w.encrypt(pwd)
    buf = io.BytesIO()
    w.write(buf)
    buf.seek(0)
    return buf

def decrypt_pdf(uploaded_file, pwd):
    rdr = PyPDF2.PdfReader(uploaded_file)
    if rdr.is_encrypted:
        rdr.decrypt(pwd)
    w = PyPDF2.PdfWriter()
    for pg in rdr.pages:
        w.add_page(pg)
    buf = io.BytesIO()
    w.write(buf)
    buf.seek(0)
    return buf

def delete_pages(uploaded_file, pages):
    rdr = PyPDF2.PdfReader(uploaded_file)
    w = PyPDF2.PdfWriter()
    for i, pg in enumerate(rdr.pages, 1):
        if i not in pages:
            w.add_page(pg)
    buf = io.BytesIO()
    w.write(buf)
    buf.seek(0)
    return buf

def extract_images(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype='pdf')
    imgs = []
    for p in range(len(doc)):
        for img in doc.get_page_images(p):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            imgs.append((f'p{p+1}_x{xref}.png', pix.tobytes('png')))
    out = io.BytesIO()
    z = zipfile.ZipFile(out, 'w')
    for n, b in imgs:
        z.writestr(n, b)
    z.close()
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
        if st.sidebar.button("Crop PDF"): st.session_state.operation = "Crop PDF"
        if st.sidebar.button("Add Watermark"): st.session_state.operation = "Add Watermark"
        if st.sidebar.button("Compress PDF"): st.session_state.operation = "Compress PDF"
    with st.sidebar.expander("🔒 Security"):
        if st.sidebar.button("Encrypt PDF"): st.session_state.operation = "Encrypt PDF"
        if st.sidebar.button("Decrypt PDF"): st.session_state.operation = "Decrypt PDF"
    with st.sidebar.expander("✂️ Pages"):
        if st.sidebar.button("Delete Pages"): st.session_state.operation = "Delete Pages"
        if st.sidebar.button("Extract Images"): st.session_state.operation = "Extract Images"
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

elif op == "Images to PDF":
    imgs = st.file_uploader("Upload images", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
    if imgs:
        if st.button("Convert to PDF"):
            out = images_to_pdf(imgs)
            st.success("✅ Converted!")
            st.download_button("Download PDF", data=out, file_name='images.pdf')

elif op == "PDF to Images":
    f = st.file_uploader("Upload PDF", type='pdf')
    if st.button("Convert to Images") and f:
        imgs = convert_from_bytes(f.read())
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            for i, im in enumerate(imgs, 1):
                page_buf = io.BytesIO()
                im.save(page_buf, 'PNG')
                z.writestr(f'page_{i}.png', page_buf.getvalue())
        buf.seek(0)
        st.download_button("Download ZIP", data=buf, file_name='pages.zip')

elif op == "OCR Image to Text":
    files = st.file_uploader("Upload Image(s) or PDF(s)", type=['png', 'jpg', 'pdf'], accept_multiple_files=True)
    if files and st.button("Extract"):
        for f in files:
            if f.type == "application/pdf":
                imgs = convert_from_bytes(f.read())
                text = ''.join(pytesseract.image_to_string(i) + '\n' for i in imgs)
            else:
                text = pytesseract.image_to_string(Image.open(f))
            st.text_area(f"Text from {f.name}", text, height=200)

st.markdown("---")
st.markdown("Dev's PDF Editor | Support: [mahadevbk/pdfeditor](https://github.com/mahadevbk/pdfeditor)")
