import pymysql
import fitz  # PyMuPDF
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "kash_books"

OUTPUT_PDF = "kash_summary_output.pdf"

def get_pdf_paths():
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT file_path FROM books")
            results = cursor.fetchall()
            return [row[0] for row in results]
    finally:
        connection.close()

def extract_key_info(text):
    info = {
        "county": None,
        "disease": None,
        "conclusion": None,
        "recommendation": None,
        "authors": None
    }

    match = re.search(r"(?:Venue\s*[:\-]?\s*)([A-Z][a-z]+)", text)
    if match:
        info["county"] = match.group(1)

    for disease in ["TB", "Malaria", "HIV", "COVID", "Pneumonia"]:
        if disease.lower() in text.lower():
            info["disease"] = disease
            break

    conclusion_match = re.search(r"(?:Conclusion[s]?[:\-]?\s*)(.*?)(?:Recommendation|Background|$)", text, re.IGNORECASE | re.DOTALL)
    if conclusion_match:
        info["conclusion"] = conclusion_match.group(1).strip()

    recommendation_match = re.search(r"(?:Recommendation[s]?[:\-]?\s*)(.*?)(?:Background|$)", text, re.IGNORECASE | re.DOTALL)
    if recommendation_match:
        info["recommendation"] = recommendation_match.group(1).strip()

    author_match = re.search(r"(?:By|Author[s]?)[:\-]?\s*([\w\s,.\-&]+)", text, re.IGNORECASE)
    if author_match:
        info["authors"] = author_match.group(1).strip()

    return info

def process_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        return extract_key_info(full_text)

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return None

def write_summary_to_pdf(data_list):
    c = canvas.Canvas(OUTPUT_PDF, pagesize=A4)
    width, height = A4
    y = height - 50

    for idx, info in enumerate(data_list, start=1):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, f"KEMRI KASH Conference Proceeding #{idx}")
        y -= 20

        c.setFont("Helvetica", 11)
        c.drawString(50, y, f"(1) County: {info['county'] or 'N/A'}")
        y -= 15
        c.drawString(50, y, f"(2) Disease: {info['disease'] or 'N/A'}")
        y -= 15
        c.drawString(50, y, f"(3) Conclusion:")
        y -= 15
        y = write_multiline_text(c, info['conclusion'], y)

        c.drawString(50, y, f"(4) Recommendation:")
        y -= 15
        y = write_multiline_text(c, info['recommendation'], y)

        c.drawString(50, y, f"(5) Authors: {info['authors'] or 'N/A'}")
        y -= 30

        if y < 100:
            c.showPage()
            y = height - 50

    c.save()
    print(f"✅ PDF summary saved to: {OUTPUT_PDF}")

def write_multiline_text(c, text, y_start):
    if not text:
        return y_start
    lines = text.splitlines()
    for line in lines:
        c.drawString(60, y_start, line.strip())
        y_start -= 15
    return y_start - 5

# Main
if __name__ == "__main__":
    pdf_paths = get_pdf_paths()
    extracted_data = []

    for path in pdf_paths:
        info = process_pdf(path)
        if info:
            extracted_data.append(info)

    if extracted_data:
        write_summary_to_pdf(extracted_data)
