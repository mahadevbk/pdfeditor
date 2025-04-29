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
import ebooklib
from ebooklib import epub
import subprocess
import uuid
import mimetypes
from contextlib import contextmanager

try:
    from pypandoc import convert_file, ensure_pandoc_installed
    PANDOC_AVAILABLE = True
except (ImportError, OSError):
    PANDOC_AVAILABLE = False

# ------------------ PAGE SETTINGS -------------------
st.set_page_config(page_title="Dev's PDF Editor", layout="wide")
col1, col2 = st.columns([1, 8])
with col1:
    st.image("pdf.png", width=80)  # Adjust width as needed
with col2:
    st.title("Dev's PDF Editor")

st.markdown("Upload PDF files or images and select an operation to manipulate your files.")

# ------------------ HELPER FUNCTIONS -------------------

def check_calibre_installed():
    """Check if Calibre's ebook-convert is available."""
    try:
        subprocess.run(['ebook-convert', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_pandoc_installed():
    """Check if Pandoc is available."""
    try:
        ensure_pandoc_installed()  # Ensures Pandoc binary is available
        return True
    except Exception:
        return False

@contextmanager
def temp_files(*suffixes):
    """Context manager for creating and cleaning up temporary files."""
    files = [tempfile.NamedTemporaryFile(delete=False, suffix=suffix) for suffix in suffixes]
    try:
        for f in files:
            f.close()
        yield [f.name for f in files]
    finally:
        for f in files:
            try:
                os.unlink(f.name)
            except OSError:
                pass

def validate_ebook_file(uploaded_file):
    """Validate if the uploaded file is a supported eBook format."""
    supported_formats = {'.pdf', '.epub', '.mobi', '.docx', '.txt', '.html'}
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in supported_formats:
        return False, f"Unsupported file format: {ext}"
    
    # Optional: Check MIME type for additional validation
    mime_type, _ = mimetypes.guess_type(uploaded_file.name)
    if mime_type and not any(fmt in mime_type for fmt in ['pdf', 'epub', 'mobi', 'word', 'text', 'html']):
        return False, f"Invalid file type: {mime_type}"
    
    return True, None

def convert_ebook(uploaded_file, target_format):
    """Convert uploaded file to target format (pdf, epub, or mobi)."""
    try:
        # Validate input file
        is_valid, error_msg = validate_ebook_file(uploaded_file)
        if not is_valid:
            st.error(error_msg)
            return None

        # Check dependencies
        calibre_available = check_calibre_installed()
        pandoc_available = check_pandoc_installed()
        if not (calibre_available or pandoc_available):
            st.error("""
            Conversion requires either:
            1. Calibre - install with: `sudo apt-get install calibre`
            2. Pandoc - install with: `pip install pypandoc` and ensure Pandoc binary is installed
            """)
            return None

        # Create temporary files
        input_ext = os.path.splitext(uploaded_file.name)[1].lower()
        output_ext = f".{target_format.lower()}"
        with temp_files(input_ext, output_ext) as (input_path, output_path):
            # Write uploaded file to temp input
            with open(input_path, 'wb') as f:
                f.write(uploaded_file.read())

            # Attempt conversion
            if calibre_available:
                try:
                    subprocess.run([
                        'ebook-convert',
                        input_path,
                        output_path,
                        '--enable-heuristics'
                    ], check=True, timeout=300)  # 5-minute timeout
                except subprocess.TimeoutExpired:
                    st.error("Conversion timed out after 5 minutes.")
                    return None
                except subprocess.CalledProcessError as e:
                    st.warning(f"Calibre conversion failed: {e}. Attempting Pandoc...")
                    calibre_available = False

            if not calibre_available and pandoc_available:
                try:
                    convert_file(input_path, target_format.lower(), outputfile=output_path)
                except Exception as e:
                    st.error(f"Pandoc conversion failed: {str(e)}")
                    return None

            if not os.path.exists(output_path):
                st.error("Conversion failed: Output file not generated.")
                return None

            # Read and return the converted file
            with open(output_path, 'rb') as f:
                return io.BytesIO(f.read())

    except Exception as e:
        st.error(f"Conversion failed: {str(e)}")
        return None

def merge_pdfs(uploaded_files):
    """Merge multiple PDF files into one."""
    merger = PyPDF2.PdfMerger()
    for uploaded_file in uploaded_files:
        merger.append(uploaded_file)
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    output.seek(0)
    return output

def split_pdf(uploaded_file, start_page, end_page):
    """Split a PDF into a range of pages."""
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    pdf_writer = PyPDF2.PdfWriter()
    for page_num in range(start_page - 1, end_page):
        if page_num < len(pdf_reader.pages):
            pdf_writer.add_page(pdf_reader.pages[page_num])
    output = io.BytesIO()
    pdf_writer.write(output)
    output.seek(0)
    return output

def extract_text(uploaded_file):
    """Extract text from a PDF file."""
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_images(uploaded_file):
    """Extract images from a PDF file."""
    pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    images = []
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            images.append((f"image_{page_num+1}_{img_index+1}.{image_ext}", image_bytes))
    pdf_document.close()
    return images

def pdf_to_images(uploaded_file):
    """Convert PDF pages to images."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(uploaded_file.read())
        temp_pdf_path = temp_pdf.name
    images = convert_from_path(temp_pdf_path)
    os.unlink(temp_pdf_path)
    output_images = []
    for i, image in enumerate(images):
        output = io.BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        output_images.append((f"page_{i+1}.png", output))
    return output_images

def ocr_pdf(uploaded_file):
    """Perform OCR on a PDF file."""
    images = pdf_to_images(uploaded_file)
    text = ""
    for _, image_data in images:
        image = Image.open(image_data)
        text += pytesseract.image_to_string(image) + "\n"
    return text

def images_to_pdf(uploaded_files):
    """Convert images to a single PDF."""
    with tempfile.TemporaryDirectory() as temp_dir:
        image_paths = []
        for uploaded_file in uploaded_files:
            image = Image.open(uploaded_file)
            image_path = os.path.join(temp_dir, f"{uuid.uuid4()}.jpg")
            image.convert("RGB").save(image_path, "JPEG")
            image_paths.append(image_path)
        output = io.BytesIO()
        with open(image_paths[0], "rb") as f:
            output.write(img2pdf.convert([f.read() for f in [open(path, "rb") for path in image_paths]]))
        output.seek(0)
        return output

def export_to_docx(text):
    """Export text to a DOCX file."""
    doc = Document()
    doc.add_paragraph(text)
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

def export_to_excel(data):
    """Export data to an Excel file."""
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output

# ------------------ MAIN APP -------------------

op = st.selectbox(
    "Select Operation",
    [
        "Merge PDFs",
        "Split PDF",
        "Extract Text",
        "Extract Images",
        "PDF to Images",
        "OCR PDF",
        "Images to PDF",
        "Convert Ebook Format",
    ],
)

if op == "Merge PDFs":
    uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)
    if uploaded_files:
        if st.button("Merge"):
            with st.spinner("Merging..."):
                merged_pdf = merge_pdfs(uploaded_files)
                st.success("✅ Merged!")
                st.download_button(
                    "Download Merged PDF",
                    data=merged_pdf,
                    file_name="merged.pdf",
                    mime="application/pdf",
                )

elif op == "Split PDF":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if uploaded_file:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        num_pages = len(pdf_reader.pages)
        st.write(f"Total pages: {num_pages}")
        start_page = st.number_input("Start page", min_value=1, max_value=num_pages, value=1)
        end_page = st.number_input("End page", min_value=start_page, max_value=num_pages, value=num_pages)
        if st.button("Split"):
            with st.spinner("Splitting..."):
                split_pdf_file = split_pdf(uploaded_file, start_page, end_page)
                st.success("✅ Split!")
                st.download_button(
                    "Download Split PDF",
                    data=split_pdf_file,
                    file_name="split.pdf",
                    mime="application/pdf",
                )

elif op == "Extract Text":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if uploaded_file:
        if st.button("Extract"):
            with st.spinner("Extracting text..."):
                text = extract_text(uploaded_file)
                st.success("✅ Text extracted!")
                st.text_area("Extracted Text", text, height=300)
                docx_file = export_to_docx(text)
                st.download_button(
                    "Download as DOCX",
                    data=docx_file,
                    file_name="extracted_text.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

elif op == "Extract Images":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if uploaded_file:
        if st.button("Extract"):
            with st.spinner("Extracting images..."):
                images = extract_images(uploaded_file)
                if images:
                    st.success("✅ Images extracted!")
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for image_name, image_bytes in images:
                            zip_file.writestr(image_name, image_bytes)
                    zip_buffer.seek(0)
                    st.download_button(
                        "Download Images (ZIP)",
                        data=zip_buffer,
                        file_name="extracted_images.zip",
                        mime="application/zip",
                    )
                else:
                    st.warning("No images found in the PDF.")

elif op == "PDF to Images":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if uploaded_file:
        if st.button("Convert"):
            with st.spinner("Converting to images..."):
                images = pdf_to_images(uploaded_file)
                st.success("✅ Converted to images!")
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for image_name, image_data in images:
                        zip_file.writestr(image_name, image_data.getvalue())
                zip_buffer.seek(0)
                st.download_button(
                    "Download Images (ZIP)",
                    data=zip_buffer,
                    file_name="pdf_images.zip",
                    mime="application/zip",
                )

elif op == "OCR PDF":
    uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
    if uploaded_file:
        if st.button("Perform OCR"):
            with st.spinner("Performing OCR..."):
                text = ocr_pdf(uploaded_file)
                st.success("✅ OCR completed!")
                st.text_area("OCR Text", text, height=300)
                docx_file = export_to_docx(text)
                st.download_button(
                    "Download as DOCX",
                    data=docx_file,
                    file_name="ocr_text.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

elif op == "Images to PDF":
    uploaded_files = st.file_uploader("Upload images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    if uploaded_files:
        if st.button("Convert"):
            with st.spinner("Converting to PDF..."):
                pdf_file = images_to_pdf(uploaded_files)
                st.success("✅ Converted to PDF!")
                st.download_button(
                    "Download PDF",
                    data=pdf_file,
                    file_name="images_to_pdf.pdf",
                    mime="application/pdf",
                )

elif op == "Convert Ebook Format":
    f = st.file_uploader("Upload file", type=['pdf', 'epub', 'mobi', 'docx', 'txt', 'html'])
    if f:
        target_format = st.selectbox("Convert to", ['PDF', 'EPUB', 'MOBI'])
        
        if not PANDOC_AVAILABLE:
            st.warning("""
            For best results, install Calibre:
            ```
            sudo apt-get install calibre
            ```
            or install Pandoc:
            ```
            pip install pypandoc
            python -c "import pypandoc; pypandoc.ensure_pandoc_installed()"
            ```
            """)
        
        if st.button("Convert"):
            with st.spinner("Converting..."):
                out = convert_ebook(f, target_format.lower())
                if out:
                    st.success("✅ Converted!")
                    st.download_button(
                        "Download",
                        data=out,
                        file_name=f'converted.{target_format.lower()}'
                    )
