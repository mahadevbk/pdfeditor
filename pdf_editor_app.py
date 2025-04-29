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

# Sidebar buttons for operations
st.sidebar.title("Select an Operation")
operation = None
if st.sidebar.button("Merge PDFs", key="sidebar_merge"):
    operation = "Merge PDFs"
elif st.sidebar.button("Split PDF", key="sidebar_split"):
    operation = "Split PDF"
elif st.sidebar.button("Rotate PDF", key="sidebar_rotate"):
    operation = "Rotate PDF"
elif st.sidebar.button("Images to PDF", key="sidebar_images_to_pdf"):
    operation = "Images to PDF"
elif st.sidebar.button("PDF to Images", key="sidebar_pdf_to_images"):
    operation = "PDF to Images"
elif st.sidebar.button("Crop PDF", key="sidebar_crop"):
    operation = "Crop PDF"
elif st.sidebar.button("OCR PDF to Text", key="sidebar_ocr"):
    operation = "OCR PDF to Text"
elif st.sidebar.button("PDF to DOCX", key="sidebar_pdf_to_docx"):
    operation = "PDF to DOCX"
elif st.sidebar.button("PDF to Spreadsheet", key="sidebar_pdf_to_spreadsheet"):
    operation = "PDF to Spreadsheet"
elif st.sidebar.button("Add Watermark", key="sidebar_add_watermark"):
    operation = "Add Watermark"
elif st.sidebar.button("Compress PDF", key="sidebar_compress"):
    operation = "Compress PDF"
elif st.sidebar.button("Extract Metadata", key="sidebar_extract_metadata"):
    operation = "Extract Metadata"

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
