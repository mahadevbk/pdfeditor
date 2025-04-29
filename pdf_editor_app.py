import streamlit as st
import PyPDF2
import os
import io
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from docx import Document
import pandas as pd
import img2pdf
import tempfile
import zipfile
import shutil

# ------------------ PAGE SETTINGS -------------------
st.set_page_config(page_title="Dev's PDF Editor", layout="wide")
st.title("Dev's PDF Editor")
st.markdown("Upload PDF files or images and select an operation to manipulate your files.")

# ------------------ FUNCTIONS -------------------

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

# Encrypt PDF
def encrypt_pdf(uploaded_file, password):
    reader = PyPDF2.PdfReader(uploaded_file)
    writer = PyPDF2.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

# Decrypt PDF
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

# Delete Pages
def delete_pages(uploaded_file, pages_to_delete):
    reader = PyPDF2.PdfReader(uploaded_file)
    writer = PyPDF2.PdfWriter()
    for i, page in enumerate(reader.pages):
        if (i + 1) not in pages_to_delete:
            writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

# Insert Pages
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

# Extract Images
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

# Add Page Numbers
def add_page_numbers(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page_num, page in enumerate(doc, start=1):
        page.insert_text((72, 20), str(page_num), fontsize=12)
    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)
    return output

# Flatten PDF
def flatten_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in doc:
        page.flatten_annotations()
    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)
    return output
