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

# Set page config
st.set_page_config(page_title="Dev's PDF Editor", layout="wide")

# Function to merge PDFs
def merge_pdfs(uploaded_files):
    merger = PyPDF2.PdfMerger()
    for file in uploaded_files:
        merger.append(file)
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    output.seek(0)
    return output

# Function to split PDF
def split_pdf(uploaded_file, page_ranges):
    reader = PyPDF2.PdfReader(uploaded_file)
    output_files = []
    ranges = page_ranges.split(',')
    for range_str in ranges:
        try:
            parts = range_str.split('-')
            if len(parts) != 2:
                st.error(f"Invalid page range format: '{range_str}'. Use format like '1-3'.")
                return None
            start, end = map(int, parts)
            start -= 1  # Convert to 0-based indexing
            if start < 0 or end > len(reader.pages) or start >= end:
                st.error(f"Invalid page range: {range_str}. Pages must be between 1 and {len(reader.pages)} and start must be less than end.")
                return None
            writer = PyPDF2.PdfWriter()
            for i in range(start, end):
                writer.add_page(reader.pages[i])
            output = io.BytesIO()
            writer.write(output)
            output.seek(0)
            output_files.append(output)
        except ValueError:
            st.error(f"Invalid page range: '{range_str}'. Please use numbers in format like '1-3'.")
            return None
    return output_files

# Function to rotate PDF pages
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

# Function to convert images to PDF
def images_to_pdf(image_files):
    with tempfile.TemporaryDirectory() as temp_dir:
        image_paths = []
        for img in image_files:
            img_path = os.path.join(temp_dir, img.name)
            with open(img_path, "wb") as f:
                f.write(img.read())
            image_paths.append(img_path)
        output = io.BytesIO()
        output.write(img2pdf.convert(image_paths))
        output.seek(0)
        return output

# Function to convert PDF to images
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

# Function to crop PDF
def crop_pdf(uploaded_file, crop_box):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    output = io.BytesIO()
    for page in doc:
        page.set_cropbox(fitz.Rect(*crop_box))
    doc.save(output)
    doc.close()
    output.seek(0)
    return output

# Function to OCR PDF to text
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

# Function to convert PDF to DOCX
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

# Function to convert PDF to spreadsheet
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

# Function to add watermark
def add_watermark(uploaded_file, watermark_text):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in doc:
        page.insert_text((50, 50), watermark_text, fontsize=20, color=(0.5, 0.5, 0.5), rotate=45)
    output = io.BytesIO()
    doc.save(output)
    doc.close()
    output.seek(0)
    return output

# Function to compress PDF
def compress_pdf(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    output = io.BytesIO()
    doc.save(output, deflate=True)
    doc.close()
    output.seek(0)
    return output

# Function to extract metadata
def extract_metadata(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    metadata = reader.metadata
    text = "\n".join([f"{key}: {value}" for key, value in metadata.items()])
    output = io.BytesIO()
    output.write(text.encode('utf-8'))
    output.seek(0)
    return output

# Streamlit UI
st.title("Dev's PDF Editor")
st.markdown("Upload PDF files or images and select an operation to manipulate your files.")

operation = st.selectbox(
    "Select Operation",
    [
        "Merge PDFs",
        "Split PDF",
        "Rotate PDF",
        "Images to PDF",
        "PDF to Images",
        "Crop PDF",
        "OCR PDF to Text",
        "PDF to DOCX",
        "PDF to Spreadsheet",
        "Add Watermark",
        "Compress PDF",
        "Extract Metadata"
    ]
)

# Handle different operations
if operation == "Merge PDFs":
    uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)
    if st.button("Merge") and uploaded_files:
        with st.spinner("Merging PDFs..."):
            output = merge_pdfs(uploaded_files)
            st.download_button(
                label="Download Merged PDF",
                data=output,
                file_name="merged.pdf",
                mime="application/pdf"
            )

elif operation == "Split PDF":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    page_ranges = st.text_input("Enter page ranges (e.g., 1-3,5-7)")
    if st.button("Split") and uploaded_file and page_ranges:
        with st.spinner("Splitting PDF..."):
            output_files = split_pdf(uploaded_file, page_ranges)
            if output_files:
                for i, output in enumerate(output_files):
                    st.download_button(
                        label=f"Download Split PDF {i+1}",
                        data=output,
                        file_name=f"split_{i+1}.pdf",
                        mime="application/pdf"
                    )

elif operation == "Rotate PDF":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    rotation_angle = st.selectbox("Rotation Angle", [90, 180, 270])
    if st.button("Rotate") and uploaded_file:
        with st.spinner("Rotating PDF..."):
            output = rotate_pdf(uploaded_file, rotation_angle)
            st.download_button(
                label="Download Rotated PDF",
                data=output,
                file_name="rotated.pdf",
                mime="application/pdf"
            )

elif operation == "Images to PDF":
    image_files = st.file_uploader("Upload image files", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    if st.button("Convert") and image_files:
        with st.spinner("Converting images to PDF..."):
            output = images_to_pdf(image_files)
            st.download_button(
                label="Download PDF",
                data=output,
                file_name="images_to_pdf.pdf",
                mime="application/pdf"
            )

elif operation == "PDF to Images":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("Convert") and uploaded_file:
        with st.spinner("Converting PDF to images..."):
            output_files = pdf_to_images(uploaded_file)
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for filename, output in output_files:
                    zip_file.writestr(filename, output.getvalue())
            zip_buffer.seek(0)
            st.download_button(
                label="Download Images (ZIP)",
                data=zip_buffer,
                file_name="pdf_images.zip",
                mime="application/zip"
            )

elif operation == "Crop PDF":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        x0 = st.number_input("X0 (left)", value=50.0)
    with col2:
        y0 = st.number_input("Y0 (top)", value=50.0)
    with col3:
        x1 = st.number_input("X1 (right)", value=550.0)
    with col4:
        y1 = st.number_input("Y1 (bottom)", value=750.0)
    crop_box = (x0, y0, x1, y1)
    if st.button("Crop") and uploaded_file:
        with st.spinner("Cropping PDF..."):
            output = crop_pdf(uploaded_file, crop_box)
            st.download_button(
                label="Download Cropped PDF",
                data=output,
                file_name="cropped.pdf",
                mime="application/pdf"
            )

elif operation == "OCR PDF to Text":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("OCR") and uploaded_file:
        with st.spinner("Performing OCR..."):
            output = ocr_pdf(uploaded_file)
            st.download_button(
                label="Download Text File",
                data=output,
                file_name="ocr_output.txt",
                mime="text/plain"
            )

elif operation == "PDF to DOCX":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("Convert") and uploaded_file:
        with st.spinner("Converting to DOCX..."):
            output = pdf_to_docx(uploaded_file)
            st.download_button(
                label="Download DOCX",
                data=output,
                file_name="output.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

elif operation == "PDF to Spreadsheet":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("Convert") and uploaded_file:
        with st.spinner("Converting to Spreadsheet..."):
            output = pdf_to_spreadsheet(uploaded_file)
            st.download_button(
                label="Download Spreadsheet",
                data=output,
                file_name="output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

elif operation == "Add Watermark":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    watermark_text = st.text_input("Watermark Text", value="Confidential")
    if st.button("Add Watermark") and uploaded_file:
        with st.spinner("Adding Watermark..."):
            output = add_watermark(uploaded_file, watermark_text)
            st.download_button(
                label="Download Watermarked PDF",
                data=output,
                file_name="watermarked.pdf",
                mime="application/pdf"
            )

elif operation == "Compress PDF":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("Compress") and uploaded_file:
        with st.spinner("Compressing PDF..."):
            output = compress_pdf(uploaded_file)
            st.download_button(
                label="Download Compressed PDF",
                data=output,
                file_name="compressed.pdf",
                mime="application/pdf"
            )

elif operation == "Extract Metadata":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("Extract") and uploaded_file:
        with st.spinner("Extracting Metadata..."):
            output = extract_metadata(uploaded_file)
            st.download_button(
                label="Download Metadata",
                data=output,
                file_name="metadata.txt",
                mime="text/plain"
            )

# Footer
st.markdown("---")
st.markdown("Dev's PDF Editor | Built with Streamlit | © 2025")
