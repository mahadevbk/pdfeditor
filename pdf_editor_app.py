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

try:
    from pypandoc import convert_file, download_pandoc
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

# ... (keep all your existing functions until convert_ebook)

def convert_ebook(uploaded_file, target_format):
    """Convert uploaded file to target format (pdf, mobi, or epub)"""
    try:
        # Create temp files
        input_ext = os.path.splitext(uploaded_file.name)[1].lower()
        input_file = tempfile.NamedTemporaryFile(delete=False, suffix=input_ext)
        input_file.write(uploaded_file.read())
        input_file.close()
        
        output_ext = f".{target_format.lower()}"
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=output_ext)
        output_file.close()
        
        # First try calibre's ebook-convert
        try:
            subprocess.run([
                'ebook-convert', 
                input_file.name, 
                output_file.name,
                '--enable-heuristics'
            ], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to pypandoc if calibre not available
            if not PANDOC_AVAILABLE:
                st.error("""
                Conversion requires either:
                1. Calibre (recommended) - install with: `sudo apt-get install calibre`
                2. Pandoc - install with: `pip install pypandoc` and `pypandoc.download_pandoc()`
                """)
                return None
            
            try:
                if target_format.lower() == 'pdf':
                    convert_file(input_file.name, 'pdf', outputfile=output_file.name)
                else:
                    convert_file(input_file.name, target_format, outputfile=output_file.name)
            except Exception as e:
                st.error(f"Pandoc conversion failed: {str(e)}")
                return None
        
        # Read the converted file
        with open(output_file.name, 'rb') as f:
            result = io.BytesIO(f.read())
        
        # Cleanup
        os.unlink(input_file.name)
        os.unlink(output_file.name)
        
        return result
    except Exception as e:
        st.error(f"Conversion failed: {str(e)}")
        return None

# ... (keep the rest of your code exactly the same until the Convert Ebook Format section)

    elif op=="Convert Ebook Format":
        f=st.file_uploader("Upload file", type=['pdf', 'epub', 'mobi', 'docx', 'txt', 'html'])
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
                python -c "import pypandoc; pypandoc.download_pandoc()"
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

# ... (keep the rest of your code exactly the same)
