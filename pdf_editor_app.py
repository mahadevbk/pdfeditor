import streamlit as st
import PyPDF2
import os
import io
import fitz  # PyMuPDF
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image
import pytesseract
from docx import Document
import pandas as pd
import img2pdf
import tempfile
import zipfile
import shutil
from datetime import datetime

# ------------------- PAGE CONFIG -------------------
st.set_page_config(page_title="Dev's PDF Editor", layout="wide")
st.title("Dev's PDF Editor")
st.markdown("Upload PDF files or images and select an operation to manipulate your files.")

# ------------------- FUNCTIONS -------------------

# Merge PDFs
def merge_pdfs(uploaded_files):
    merger = PyPDF2.PdfMerger()
    for file in uploaded_files:
        merger.append(file)
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    output.seek(0)
    return output

# Split PDF
def split_pdf(uploaded_file, page_ranges):
    reader = PyPDF2.PdfReader(uploaded_file)
    output_files = []
    ranges = page_ranges.split(',')
    for range_str in ranges:
        parts = range_str.split('-')
        start, end = map(int, parts)
        start -= 1
        writer = PyPDF2.PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        output_files.append(output)
    return output_files

# Rotate PDF
def rotate_pdf(uploaded_file, rotation_angle):
    reader = PyPDF2.PdfReader(uploaded_file)
    writer = PyPDF2.PdfWriter()
    for page in reader.pages:
        page.rotate(rotation_angle)
        writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

# Images to PDF
def images_to_pdf(image_files):
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = []
        for img in image_files:
            path = os.path.join(temp_dir, img.name)
            with open(path, "wb") as f:
                f.write(img.read())
            paths.append(path)
        output = io.BytesIO()
        output.write(img2pdf.convert(paths))
        output.seek(0)
        return output

# PDF to Images
def pdf_to_images(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    images = convert_from_path(tmp_path)
    os.unlink(tmp_path)
    output_files = []
    for i, img in enumerate(images):
        output = io.BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        output_files.append((f"page_{i+1}.png", output))
    return output_files

# Crop PDF
def crop_pdf(uploaded_file, crop_box):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in doc:
        page.set_cropbox(fitz.Rect(*crop_box))
    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)
    return output

# OCR PDF
def ocr_pdf(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    images = convert_from_path(tmp_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img) + "\n"
    os.unlink(tmp_path)
    output = io.BytesIO()
    output.write(text.encode('utf-8'))
    output.seek(0)
    return output

# PDF to DOCX
def pdf_to_docx(uploaded_file):
    doc = Document()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    images = convert_from_path(tmp_path)
    for img in images:
        text = pytesseract.image_to_string(img)
        doc.add_paragraph(text)
    output = io.BytesIO()
    doc.save(output)
    os.unlink(tmp_path)
    output.seek(0)
    return output

# PDF to Spreadsheet
def pdf_to_spreadsheet(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    images = convert_from_path(tmp_path)
    data = []
    for img in images:
        text = pytesseract.image_to_string(img)
        lines = text.split('\n')
        data.extend([line.split() for line in lines if line.strip()])
    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_excel(output, index=False)
    os.unlink(tmp_path)
    output.seek(0)
    return output

# Add Watermark
def add_watermark(uploaded_file, watermark_text):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in doc:
        page.insert_text((50, 50), watermark_text, fontsize=20, color=(0.5, 0.5, 0.5), rotate=45)
    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)
    return output

# Compress PDF
def compress_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    output = io.BytesIO()
    doc.save(output, deflate=True)
    doc.close()
    output.seek(0)
    return output

# Extract Metadata
def extract_metadata(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    metadata = reader.metadata
    text = "\n".join([f"{key}: {value}" for key, value in metadata.items()])
    output = io.BytesIO()
    output.write(text.encode('utf-8'))
    output.seek(0)
    return output

# New Features
def encrypt_pdf(uploaded_file, password):
    reader = PyPDF2.PdfReader(uploaded_file)
    writer = PyPDF2.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    output = io.BytesIO()
    writer.encrypt(password)
    writer.write(output)
    output.seek(0)
    return output

def decrypt_pdf(uploaded_file, password):
    reader = PyPDF2.PdfReader(uploaded_file)
    if reader.is_encrypted:
        reader.decrypt(password)
    writer = PyPDF2.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

def delete_pages(uploaded_file, pages_to_delete):
    reader = PyPDF2.PdfReader(uploaded_file)
    writer = PyPDF2.PdfWriter()
    for i, page in enumerate(reader.pages):
        if (i+1) not in pages_to_delete:
            writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

def insert_pages(base_file, insert_file, position):
    base_reader = PyPDF2.PdfReader(base_file)
    insert_reader = PyPDF2.PdfReader(insert_file)
    writer = PyPDF2.PdfWriter()
    for i in range(position):
        writer.add_page(base_reader.pages[i])
    for page in insert_reader.pages:
        writer.add_page(page)
    for i in range(position, len(base_reader.pages)):
        writer.add_page(base_reader.pages[i])
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

def extract_images(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    images = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            img_bytes = pix.tobytes("png")
            images.append((f"page_{i+1}_img_{xref}.png", img_bytes))
    output_zip = io.BytesIO()
    with zipfile.ZipFile(output_zip, 'w') as zipf:
        for name, img in images:
            zipf.writestr(name, img)
    output_zip.seek(0)
    return output_zip

def add_page_numbers(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page_num, page in enumerate(doc, start=1):
        page.insert_text((72, 20), str(page_num), fontsize=12)
    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)
    return output

def flatten_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in doc:
        page.flatten_annotations()
    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)
    return output
# ------------------- SIDEBAR AND MENU -------------------

# Initialize session state
if "operation" not in st.session_state:
    st.session_state.operation = None

st.sidebar.title("📑 Menu")

if st.session_state.operation is None:
    with st.sidebar.expander("🔄 Convert"):
        if st.sidebar.button("Images to PDF", key="sidebar_images_to_pdf"):
            st.session_state.operation = "Images to PDF"
        if st.sidebar.button("PDF to Images", key="sidebar_pdf_to_images"):
            st.session_state.operation = "PDF to Images"
        if st.sidebar.button("PDF to DOCX", key="sidebar_pdf_to_docx"):
            st.session_state.operation = "PDF to DOCX"
        if st.sidebar.button("PDF to Spreadsheet", key="sidebar_pdf_to_spreadsheet"):
            st.session_state.operation = "PDF to Spreadsheet"

    with st.sidebar.expander("🔧 Edit"):
        if st.sidebar.button("Merge PDFs", key="sidebar_merge"):
            st.session_state.operation = "Merge PDFs"
        if st.sidebar.button("Split PDF", key="sidebar_split"):
            st.session_state.operation = "Split PDF"
        if st.sidebar.button("Rotate PDF", key="sidebar_rotate"):
            st.session_state.operation = "Rotate PDF"
        if st.sidebar.button("Crop PDF", key="sidebar_crop"):
            st.session_state.operation = "Crop PDF"
        if st.sidebar.button("Add Watermark", key="sidebar_add_watermark"):
            st.session_state.operation = "Add Watermark"
        if st.sidebar.button("Compress PDF", key="sidebar_compress"):
            st.session_state.operation = "Compress PDF"

    with st.sidebar.expander("🔒 Security"):
        if st.sidebar.button("Encrypt PDF", key="sidebar_encrypt_pdf"):
            st.session_state.operation = "Encrypt PDF"
        if st.sidebar.button("Decrypt PDF", key="sidebar_decrypt_pdf"):
            st.session_state.operation = "Decrypt PDF"

    with st.sidebar.expander("✂️ Pages"):
        if st.sidebar.button("Delete Pages", key="sidebar_delete_pages"):
            st.session_state.operation = "Delete Pages"
        if st.sidebar.button("Insert Pages", key="sidebar_insert_pages"):
            st.session_state.operation = "Insert Pages"
        if st.sidebar.button("Add Page Numbers", key="sidebar_add_page_numbers"):
            st.session_state.operation = "Add Page Numbers"
        if st.sidebar.button("Flatten PDF", key="sidebar_flatten_pdf"):
            st.session_state.operation = "Flatten PDF"

    with st.sidebar.expander("🖼️ Images"):
        if st.sidebar.button("Extract Images", key="sidebar_extract_images"):
            st.session_state.operation = "Extract Images"

    with st.sidebar.expander("🔍 Extract"):
        if st.sidebar.button("OCR PDF to Text", key="sidebar_ocr"):
            st.session_state.operation = "OCR PDF to Text"
        if st.sidebar.button("Extract Metadata", key="sidebar_extract_metadata"):
            st.session_state.operation = "Extract Metadata"
else:
    if st.sidebar.button("⬅️ Back to Menu", key="sidebar_back"):
        st.session_state.operation = None
