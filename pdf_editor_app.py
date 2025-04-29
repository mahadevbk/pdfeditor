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
#st.title("Dev's PDF Editor")
col1, col2 = st.columns([1, 8])
with col1:
    st.image("pdf.png", width=80)  # Adjust width as needed
with col2:
    st.title("Dev's PDF Editor")

st.markdown("Upload PDF files or images and select an operation to manipulate your files.")

# ------------------ FUNCTIONS -------------------
def merge_pdfs(uploaded_files):
    merger = PyPDF2.PdfMerger()
    for file in uploaded_files:
        merger.append(file)
    output = io.BytesIO()
    merger.write(output)
    merger.close()
    output.seek(0)
    return output

def split_pdf(uploaded_file, page_ranges):
    reader = PyPDF2.PdfReader(uploaded_file)
    output_files = []
    for rng in page_ranges.split(','):
        start, end = map(int, rng.split('-'))
        writer = PyPDF2.PdfWriter()
        for i in range(start-1, end):
            writer.add_page(reader.pages[i])
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        output_files.append(buf)
    return output_files

def rotate_pdf(uploaded_file, rotation_angle):
    reader = PyPDF2.PdfReader(uploaded_file)
    writer = PyPDF2.PdfWriter()
    for page in reader.pages:
        page.rotate(rotation_angle)
        writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf

def images_to_pdf(image_files):
    with tempfile.TemporaryDirectory() as tmp:
        paths=[]
        for img in image_files:
            p=os.path.join(tmp, img.name)
            with open(p, 'wb') as f: f.write(img.read())
            paths.append(p)
        out=io.BytesIO()
        out.write(img2pdf.convert(paths))
        out.seek(0)
        return out

def pdf_to_images(uploaded_file):
    tmp=tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    tmp.write(uploaded_file.read()); tmp.close()
    imgs=convert_from_path(tmp.name); os.unlink(tmp.name)
    outs=[]
    for i, im in enumerate(imgs,1):
        buf=io.BytesIO(); im.save(buf, 'PNG'); buf.seek(0)
        outs.append((f'page_{i}.png', buf))
    return outs

def crop_pdf(uploaded_file, box):
    doc=fitz.open(stream=uploaded_file.read(), filetype='pdf')
    for p in doc: p.set_cropbox(fitz.Rect(*box))
    buf=io.BytesIO(); doc.save(buf); doc.close(); buf.seek(0)
    return buf

def ocr_pdf(uploaded_file):
    tmp=tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    tmp.write(uploaded_file.read()); tmp.close()
    imgs=convert_from_path(tmp.name); os.unlink(tmp.name)
    text=''.join(pytesseract.image_to_string(i)+'\n' for i in imgs)
    buf=io.BytesIO(); buf.write(text.encode()); buf.seek(0)
    return buf

def pdf_to_docx(uploaded_file):
    doc=Document(); tmp=tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    tmp.write(uploaded_file.read()); tmp.close()
    imgs=convert_from_path(tmp.name); os.unlink(tmp.name)
    for im in imgs: doc.add_paragraph(pytesseract.image_to_string(im))
    buf=io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf

def pdf_to_spreadsheet(uploaded_file):
    tmp=tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    tmp.write(uploaded_file.read()); tmp.close()
    imgs=convert_from_path(tmp.name); os.unlink(tmp.name)
    data=[]
    for im in imgs:
        for ln in pytesseract.image_to_string(im).splitlines():
            if ln.strip(): data.append(ln.split())
    df=pd.DataFrame(data)
    buf=io.BytesIO(); df.to_excel(buf,index=False); buf.seek(0)
    return buf

def add_watermark(uploaded_file, text):
    doc=fitz.open(stream=uploaded_file.read(), filetype='pdf')
    for p in doc: p.insert_text((50,50), text, fontsize=20, color=(0.5,0.5,0.5), rotate=45)
    buf=io.BytesIO(); doc.save(buf); doc.close(); buf.seek(0)
    return buf

def compress_pdf(uploaded_file):
    doc=fitz.open(stream=uploaded_file.read(), filetype='pdf')
    buf=io.BytesIO(); doc.save(buf, deflate=True); doc.close(); buf.seek(0)
    return buf

def extract_metadata(uploaded_file):
    md=PyPDF2.PdfReader(uploaded_file).metadata
    txt='\n'.join(f"{k}: {v}" for k,v in md.items())
    buf=io.BytesIO(); buf.write(txt.encode()); buf.seek(0)
    return buf

# Advanced features
def encrypt_pdf(uploaded_file, pwd):
    rdr=PyPDF2.PdfReader(uploaded_file); w=PyPDF2.PdfWriter()
    for pg in rdr.pages: w.add_page(pg)
    w.encrypt(pwd)
    buf=io.BytesIO(); w.write(buf); buf.seek(0)
    return buf

def decrypt_pdf(uploaded_file, pwd):
    rdr=PyPDF2.PdfReader(uploaded_file)
    if rdr.is_encrypted: rdr.decrypt(pwd)
    w=PyPDF2.PdfWriter()
    for pg in rdr.pages: w.add_page(pg)
    buf=io.BytesIO(); w.write(buf); buf.seek(0)
    return buf

def delete_pages(uploaded_file, pages):
    rdr=PyPDF2.PdfReader(uploaded_file); w=PyPDF2.PdfWriter()
    for i,pg in enumerate(rdr.pages,1):
        if i not in pages: w.add_page(pg)
    buf=io.BytesIO(); w.write(buf); buf.seek(0)
    return buf

def insert_pages(base, ins, pos):
    br=PyPDF2.PdfReader(base); ir=PyPDF2.PdfReader(ins); w=PyPDF2.PdfWriter()
    for i in range(pos): w.add_page(br.pages[i])
    for pg in ir.pages: w.add_page(pg)
    for i in range(pos, len(br.pages)): w.add_page(br.pages[i])
    buf=io.BytesIO(); w.write(buf); buf.seek(0)
    return buf

def extract_images(uploaded_file):
    doc=fitz.open(stream=uploaded_file.read(), filetype='pdf'); imgs=[]
    for p in range(len(doc)):
        for img in doc.get_page_images(p):
            xref=img[0]; pix=fitz.Pixmap(doc, xref)
            imgs.append((f'p{p+1}_x{xref}.png', pix.tobytes('png')))
    out=io.BytesIO(); z=zipfile.ZipFile(out,'w')
    for n,b in imgs: z.writestr(n,b)
    z.close(); out.seek(0); return out

def add_page_numbers(uploaded_file):
    doc=fitz.open(stream=uploaded_file.read(), filetype='pdf')
    for i,p in enumerate(doc,1): p.insert_text((72,20), str(i), fontsize=12)
    buf=io.BytesIO(); doc.save(buf); doc.close(); buf.seek(0)
    return buf

def flatten_pdf(uploaded_file):
    doc=fitz.open(stream=uploaded_file.read(), filetype='pdf')
    for p in doc: p.flatten_annotations()
    buf=io.BytesIO(); doc.save(buf); doc.close(); buf.seek(0)
    return buf

# ------------------ SIDEBAR & MENU -------------------
if 'operation' not in st.session_state:
    st.session_state.operation = None

st.sidebar.title("📑 Menu")
if st.session_state.operation is None:
    with st.sidebar.expander("🔄 Convert"):
        if st.sidebar.button("Images to PDF", key="s_img2pdf"): st.session_state.operation="Images to PDF"
        if st.sidebar.button("PDF to Images", key="s_pdf2img"): st.session_state.operation="PDF to Images"
        if st.sidebar.button("PDF to DOCX", key="s_pdf2docx"): st.session_state.operation="PDF to DOCX"
        if st.sidebar.button("PDF to Spreadsheet", key="s_pdf2xls"): st.session_state.operation="PDF to Spreadsheet"
    with st.sidebar.expander("🔧 Edit"):
        if st.sidebar.button("Merge PDFs", key="s_merge"): st.session_state.operation="Merge PDFs"
        if st.sidebar.button("Split PDF", key="s_split"): st.session_state.operation="Split PDF"
        if st.sidebar.button("Rotate PDF", key="s_rotate"): st.session_state.operation="Rotate PDF"
        if st.sidebar.button("Crop PDF", key="s_crop"): st.session_state.operation="Crop PDF"
        if st.sidebar.button("Add Watermark", key="s_wm"): st.session_state.operation="Add Watermark"
        if st.sidebar.button("Compress PDF", key="s_compress"): st.session_state.operation="Compress PDF"
    with st.sidebar.expander("🔒 Security"):
        if st.sidebar.button("Encrypt PDF", key="s_enc"): st.session_state.operation="Encrypt PDF"
        if st.sidebar.button("Decrypt PDF", key="s_dec"): st.session_state.operation="Decrypt PDF"
    with st.sidebar.expander("✂️ Pages"):
        if st.sidebar.button("Delete Pages", key="s_delpg"): st.session_state.operation="Delete Pages"
        if st.sidebar.button("Insert Pages", key="s_inspg"): st.session_state.operation="Insert Pages"
        if st.sidebar.button("Add Page Numbers", key="s_pgnum"): st.session_state.operation="Add Page Numbers"
        if st.sidebar.button("Flatten PDF", key="s_flatten"): st.session_state.operation="Flatten PDF"
    with st.sidebar.expander("🖼️ Images"):
        if st.sidebar.button("Extract Images", key="s_extimg"): st.session_state.operation="Extract Images"
    with st.sidebar.expander("🔍 Extract"):
        if st.sidebar.button("OCR PDF to Text", key="s_ocr"): st.session_state.operation="OCR PDF to Text"
        if st.sidebar.button("Extract Metadata", key="s_meta"): st.session_state.operation="Extract Metadata"
else:
    if st.sidebar.button("⬅️ Back to Menu", key="s_back"): st.session_state.operation=None

# ------------------ MAIN UI -------------------
op=st.session_state.operation
if not op:
    st.write("Select an operation from the sidebar to get started.")
else:
    st.subheader(f"▶️ Current Operation: {op}")
    # Basic operations
    if op=="Images to PDF":
        imgs=st.file_uploader("Upload images", accept_multiple_files=True,type=['png','jpg','jpeg'])
        if st.button("Convert Images to PDF") and imgs:
            out=images_to_pdf(imgs); st.success("✅ Converted!"); st.download_button("Download PDF",data=out,file_name='images.pdf')
    elif op=="PDF to Images":
        f=st.file_uploader("Upload PDF", type='pdf')
        if st.button("Convert PDF to Images") and f:
            outs=pdf_to_images(f); buf=io.BytesIO();
            with zipfile.ZipFile(buf,'w') as z:
                for n,b in outs: z.writestr(n,b.getvalue())
            buf.seek(0); st.success("✅ Converted!"); st.download_button("Download ZIP",data=buf,file_name='pages.zip')
    elif op=="PDF to DOCX":
        f=st.file_uploader("Upload PDF", type='pdf')
        if st.button("Convert to DOCX") and f:
            out=pdf_to_docx(f); st.success("✅ Converted!"); st.download_button("Download DOCX",data=out,file_name='out.docx')
    elif op=="PDF to Spreadsheet":
        f=st.file_uploader("Upload PDF", type='pdf')
        if st.button("Convert to XLSX") and f:
            out=pdf_to_spreadsheet(f); st.success("✅ Converted!"); st.download_button("Download XLSX",data=out,file_name='out.xlsx')
    elif op=="Merge PDFs":
        fs=st.file_uploader("Upload PDFs", accept_multiple_files=True,type='pdf')
        if st.button("Merge PDFs") and fs:
            out=merge_pdfs(fs); st.success("✅ Merged!"); st.download_button("Download",data=out,file_name='merged.pdf')
    elif op=="Split PDF":
        f=st.file_uploader("Upload PDF", type='pdf')
        rng=st.text_input("Ranges e.g. 1-3,5-7")
        if st.button("Split PDF") and f and rng:
            ofs=split_pdf(f,rng); st.success("✅ Split!")
            for i,b in enumerate(ofs,1): st.download_button(f"Part {i}",data=b,file_name=f'part{i}.pdf')
    elif op=="Rotate PDF":
        f=st.file_uploader("Upload PDF", type='pdf')
        ang=st.selectbox("Angle",[90,180,270])
        if st.button("Rotate PDF") and f:
            out=rotate_pdf(f,ang); st.success("✅ Rotated!"); st.download_button("Download",data=out,file_name='rotated.pdf')
    elif op=="Crop PDF":
        f=st.file_uploader("Upload PDF", type='pdf')
        c1,c2,c3,c4=st.columns(4)
        x0=c1.number_input("X0",value=0.0)
        y0=c2.number_input("Y0",value=0.0)
        x1=c3.number_input("X1",value=612.0)
        y1=c4.number_input("Y1",value=792.0)
        if st.button("Crop PDF") and f:
            out=crop_pdf(f,(x0,y0,x1,y1)); st.success("✅ Cropped!"); st.download_button("Download",data=out,file_name='cropped.pdf')
    elif op=="Add Watermark":
        f=st.file_uploader("Upload PDF", type='pdf')
        txt=st.text_input("Watermark Text","Confidential")
        if st.button("Add Watermark") and f:
            out=add_watermark(f,txt); st.success("✅ Watermarked!"); st.download_button("Download",data=out,file_name='wm.pdf')
    elif op=="Compress PDF":
        f=st.file_uploader("Upload PDF", type='pdf')
        if st.button("Compress PDF") and f:
            out=compress_pdf(f); st.success("✅ Compressed!"); st.download_button("Download",data=out,file_name='compressed.pdf')
    elif op=="Extract Metadata":
        f=st.file_uploader("Upload PDF", type='pdf')
        if st.button("Extract Metadata") and f:
            out=extract_metadata(f); st.success("✅ Metadata!"); st.download_button("Download",data=out,file_name='metadata.txt')
    # Advanced
    elif op=="Encrypt PDF":
        f=st.file_uploader("Upload PDF to Encrypt", type='pdf')
        pwd=st.text_input("Password", type='password')
        if st.button("Encrypt PDF") and f and pwd:
            out=encrypt_pdf(f,pwd); st.success("✅ Encrypted!"); st.download_button("Download",data=out,file_name='encrypted.pdf')
    elif op=="Decrypt PDF":
        f=st.file_uploader("Upload Encrypted PDF", type='pdf')
        pwd=st.text_input("Password", type='password')
        if st.button("Decrypt PDF") and f and pwd:
            out=decrypt_pdf(f,pwd); st.success("✅ Decrypted!"); st.download_button("Download",data=out,file_name='decrypted.pdf')
    elif op=="Delete Pages":
        f=st.file_uploader("Upload PDF", type='pdf')
        rng=st.text_input("Pages to delete, e.g. 1,3,5")
        if st.button("Delete Pages") and f and rng:
            try:
                pages=[int(x) for x in rng.split(',')]
                out=delete_pages(f,pages); st.success("✅ Pages deleted!"); st.download_button("Download",data=out,file_name='deleted.pdf')
            except:
                st.error("Invalid pages input")
    elif op=="Insert Pages":
        base=st.file_uploader("Upload Base PDF", type='pdf')
        ins=st.file_uploader("Upload PDF to Insert", type='pdf')
        pos=st.number_input("Position (0-based)",min_value=0,step=1)
        if st.button("Insert Pages") and base and ins:
            out=insert_pages(base,ins,pos); st.success("✅ Pages inserted!"); st.download_button("Download",data=out,file_name='inserted.pdf')
    elif op=="Extract Images":
        f=st.file_uploader("Upload PDF", type='pdf')
        if st.button("Extract Images") and f:
            out=extract_images(f); st.success("✅ Images extracted!"); st.download_button("Download ZIP",data=out,file_name='images.zip')
    elif op=="Add Page Numbers":
        f=st.file_uploader("Upload PDF", type='pdf')
        if st.button("Add Page Numbers") and f:
            out=add_page_numbers(f); st.success("✅ Page numbers added!"); st.download_button("Download",data=out,file_name='pgnums.pdf')
    elif op=="Flatten PDF":
        f=st.file_uploader("Upload PDF to Flatten", type='pdf')
        if st.button("Flatten PDF") and f:
            out=flatten_pdf(f); st.success("✅ PDF flattened!"); st.download_button("Download",data=out,file_name='flattened.pdf')

# ------------------ FOOTER -------------------
st.markdown("---")
st.markdown("Dev's PDF Editor | © 2025")
