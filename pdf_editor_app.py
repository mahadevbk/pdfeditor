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

# Functions (Same as your current ones)
# [Functions block omitted for brevity]
# (We'll reinsert them if needed, but they are unchanged)

# Streamlit UI
st.title("Dev's PDF Editor")
st.markdown("Upload PDF files or images and select an operation to manipulate your files.")

# Initialize session state for operation selection
if 'operation' not in st.session_state:
    st.session_state.operation = None

# Sidebar buttons for operations
st.sidebar.title("Menu")

if st.session_state.operation is None:
    with st.sidebar.expander("\ud83d\udd04 Convert"):
        if st.button("Images to PDF", key="sidebar_images_to_pdf"):
            st.session_state.operation = "Images to PDF"
        if st.button("PDF to Images", key="sidebar_pdf_to_images"):
            st.session_state.operation = "PDF to Images"
        if st.button("PDF to DOCX", key="sidebar_pdf_to_docx"):
            st.session_state.operation = "PDF to DOCX"
        if st.button("PDF to Spreadsheet", key="sidebar_pdf_to_spreadsheet"):
            st.session_state.operation = "PDF to Spreadsheet"

    with st.sidebar.expander("\ud83d\udd27 Edit"):
        if st.button("Merge PDFs", key="sidebar_merge"):
            st.session_state.operation = "Merge PDFs"
        if st.button("Split PDF", key="sidebar_split"):
            st.session_state.operation = "Split PDF"
        if st.button("Rotate PDF", key="sidebar_rotate"):
            st.session_state.operation = "Rotate PDF"
        if st.button("Crop PDF", key="sidebar_crop"):
            st.session_state.operation = "Crop PDF"
        if st.button("Add Watermark", key="sidebar_add_watermark"):
            st.session_state.operation = "Add Watermark"
        if st.button("Compress PDF", key="sidebar_compress"):
            st.session_state.operation = "Compress PDF"

    with st.sidebar.expander("\ud83d\udd0d Extract"):
        if st.button("OCR PDF to Text", key="sidebar_ocr"):
            st.session_state.operation = "OCR PDF to Text"
        if st.button("Extract Metadata", key="sidebar_extract_metadata"):
            st.session_state.operation = "Extract Metadata"
else:
    if st.sidebar.button("\u2b05\ufe0f Back to Menu", key="sidebar_back"):
        st.session_state.operation = None

# Assign operation
operation = st.session_state.operation

# Handle different operations
if operation == "Merge PDFs":
    uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)
    if st.button("Merge PDFs", key="main_merge") and uploaded_files:
        with st.spinner("Merging PDFs..."):
            output = merge_pdfs(uploaded_files)
            st.download_button("Download Merged PDF", data=output, file_name="merged.pdf", mime="application/pdf")

elif operation == "Split PDF":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    page_ranges = st.text_input("Enter page ranges (e.g., 1-3,5-7)")
    if st.button("Split PDF", key="main_split") and uploaded_file and page_ranges:
        with st.spinner("Splitting PDF..."):
            output_files = split_pdf(uploaded_file, page_ranges)
            if output_files:
                for i, output in enumerate(output_files):
                    st.download_button(f"Download Split PDF {i+1}", data=output, file_name=f"split_{i+1}.pdf", mime="application/pdf")

elif operation == "Rotate PDF":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    rotation_angle = st.selectbox("Rotation Angle", [90, 180, 270])
    if st.button("Rotate PDF", key="main_rotate") and uploaded_file:
        with st.spinner("Rotating PDF..."):
            output = rotate_pdf(uploaded_file, rotation_angle)
            st.download_button("Download Rotated PDF", data=output, file_name="rotated.pdf", mime="application/pdf")

elif operation == "Images to PDF":
    image_files = st.file_uploader("Upload image files", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    if st.button("Convert Images to PDF", key="main_images_to_pdf") and image_files:
        with st.spinner("Converting images to PDF..."):
            output = images_to_pdf(image_files)
            st.download_button("Download PDF", data=output, file_name="images_to_pdf.pdf", mime="application/pdf")

elif operation == "PDF to Images":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("Convert PDF to Images", key="main_pdf_to_images") and uploaded_file:
        with st.spinner("Converting PDF to images..."):
            output_files = pdf_to_images(uploaded_file)
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for filename, output in output_files:
                    zip_file.writestr(filename, output.getvalue())
            zip_buffer.seek(0)
            st.download_button("Download Images (ZIP)", data=zip_buffer, file_name="pdf_images.zip", mime="application/zip")

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
    if st.button("Crop PDF", key="main_crop") and uploaded_file:
        with st.spinner("Cropping PDF..."):
            output = crop_pdf(uploaded_file, crop_box)
            st.download_button("Download Cropped PDF", data=output, file_name="cropped.pdf", mime="application/pdf")

elif operation == "OCR PDF to Text":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("Perform OCR on PDF", key="main_ocr") and uploaded_file:
        with st.spinner("Performing OCR..."):
            output = ocr_pdf(uploaded_file)
            st.download_button("Download Text File", data=output, file_name="ocr_output.txt", mime="text/plain")

elif operation == "PDF to DOCX":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("Convert PDF to DOCX", key="main_pdf_to_docx") and uploaded_file:
        with st.spinner("Converting to DOCX..."):
            output = pdf_to_docx(uploaded_file)
            st.download_button("Download DOCX", data=output, file_name="output.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

elif operation == "PDF to Spreadsheet":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("Convert PDF to Spreadsheet", key="main_pdf_to_spreadsheet") and uploaded_file:
        with st.spinner("Converting to Spreadsheet..."):
            output = pdf_to_spreadsheet(uploaded_file)
            st.download_button("Download Spreadsheet", data=output, file_name="output.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

elif operation == "Add Watermark":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    watermark_text = st.text_input("Watermark Text", value="Confidential")
    if st.button("Add Watermark to PDF", key="main_add_watermark") and uploaded_file:
        with st.spinner("Adding Watermark..."):
            output = add_watermark(uploaded_file, watermark_text)
            st.download_button("Download Watermarked PDF", data=output, file_name="watermarked.pdf", mime="application/pdf")

elif operation == "Compress PDF":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("Compress PDF", key="main_compress") and uploaded_file:
        with st.spinner("Compressing PDF..."):
            output = compress_pdf(uploaded_file)
            st.download_button("Download Compressed PDF", data=output, file_name="compressed.pdf", mime="application/pdf")

elif operation == "Extract Metadata":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if st.button("Extract PDF Metadata", key="main_extract_metadata") and uploaded_file:
        with st.spinner("Extracting Metadata..."):
            output = extract_metadata(uploaded_file)
            st.download_button("Download Metadata", data=output, file_name="metadata.txt", mime="text/plain")

# Footer
st.markdown("---")
st.markdown("Dev's PDF Editor | Built with Streamlit | © 2025")
