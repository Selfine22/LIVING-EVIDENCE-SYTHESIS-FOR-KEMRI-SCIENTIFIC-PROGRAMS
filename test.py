import pymysql
import fitz  # PyMuPDF
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "test"
DB_NAME = "kash_books"

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

# Extract specific info from PDF text
def extract_key_info(text):
    info = {
        "county": None,
        "disease": None,
        "conclusion": None,
        "recommendation": None,
        "authors": None
    }

    # COUNTY
    match = re.search(r"(?:Venue\s*[:\-]?\s*)([A-Z][a-z]+)", text)
    if match:
        info["county"] = match.group(1)

    # DISEASE FOCUS
    for disease in ["TB", "Malaria", "HIV", "COVID", "Pneumonia"]:
        if disease.lower() in text.lower():
            info["disease"] = disease
            break

    # CONCLUSION
    conclusion_match = re.search(r"(?:Conclusion[s]?[:\-]?\s*)(.*?)(?:Recommendation|Background|$)", text, re.IGNORECASE | re.DOTALL)
    if conclusion_match:
        info["conclusion"] = conclusion_match.group(1).strip()

    # RECOMMENDATION
    recommendation_match = re.search(r"(?:Recommendation[s]?[:\-]?\s*)(.*?)(?:Background|$)", text, re.IGNORECASE | re.DOTALL)
    if recommendation_match:
        info["recommendation"] = recommendation_match.group(1).strip()

    # AUTHORS
    author_match = re.search(r"(?:By|Author[s]?)[:\-]?\s*([\w\s,.\-&]+)", text, re.IGNORECASE)
    if author_match:
        info["authors"] = author_match.group(1).strip()

    return info

# Read and process PDF
def process_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        info = extract_key_info(full_text)

        print("\n=== KEMRI KASH Conference Proceedings ===")
        print(f"(1) Name of the County: {info['county']}")
        print(f"(2) Disease of Focus: {info['disease']}")
        print(f"(3) Study Conclusion: {info['conclusion']}")
        print(f"(4) Recommendation: {info['recommendation']}")
        print(f"(5) Author(s): {info['authors']}")
        print("=========================================\n")

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")

# Main entry point
if __name__ == "__main__":
    pdf_paths = get_pdf_paths()
    for path in pdf_paths:
        process_pdf(path)