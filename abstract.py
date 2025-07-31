# abstract_engine.py
import os
import re
import fitz
import pymysql
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import MultifieldParser

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "test"
DB_NAME = "kash_books"
INDEX_DIR = "abstract_index"

def get_pdf_paths():
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT file_path FROM books")
            return [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()

def extract_abstracts_from_pdf(path):
    doc = fitz.open(path)
    full_text = "\n".join([page.get_text("text") for page in doc])
    doc.close()
    full_text = full_text.replace("\r", "\n").strip()

    pattern = re.compile(r"""(?P<label>^(\d{1,2}\.\d{2}|Abstract No:\s*\d+).*\n)?
                             (?P<title>^[^\n]{5,100}\n)?
                             (?P<authors>^[^\n]*?\b(KEMRI|Institute|University|Email:).*\n)?
                             (?P<body>(?:(?!^\d{1,2}\.\d{2}|^Abstract No:|\Z).*\n?)+)
                          """, re.MULTILINE | re.VERBOSE)

    seen_hashes = set()
    abstracts = []

    for match in pattern.finditer(full_text):
        label = match.group('label') or ''
        title = match.group('title') or ''
        authors = match.group('authors') or ''
        body = match.group('body') or ''
        combined = (label + title + authors + body).strip()

        if len(combined.split()) < 30:
            continue

        normalized = re.sub(r'\s+', ' ', combined).lower()
        hash_key = hash(normalized)
        if hash_key in seen_hashes:
            continue
        seen_hashes.add(hash_key)

        title_line = title.strip() if title.strip() else combined.splitlines()[0].strip()
        if len(title_line) > 150:
            title_line = "Untitled Abstract"

        abstracts.append({
            "title": title_line,
            "content": combined,
            "path": path
        })

    return abstracts

def get_schema():
    return Schema(title=TEXT(stored=True), content=TEXT(stored=True), path=ID(stored=True))

def build_index():
    paths = get_pdf_paths()
    abstracts = []
    for path in paths:
        abstracts.extend(extract_abstracts_from_pdf(path))

    if not os.path.exists(INDEX_DIR):
        os.mkdir(INDEX_DIR)
        ix = create_in(INDEX_DIR, get_schema())
    else:
        ix = open_dir(INDEX_DIR)

    writer = ix.writer()
    for abs in abstracts:
        writer.add_document(title=abs["title"], content=abs["content"], path=abs["path"])
    writer.commit()
    

def search_abstracts(term):
    if not os.path.exists(INDEX_DIR):
        return []

    ix = open_dir(INDEX_DIR)
    parser = MultifieldParser(["title", "content"], schema=ix.schema)
    query = parser.parse(term)

    with ix.searcher() as searcher:
        results = searcher.search(query, limit=100)
        return [
            {
                "id": i,
                "title": hit["title"],
                "content": hit["content"],
                "snippet": hit.highlights("content") or hit["content"][:300] + "...",
                "path": hit["path"]
            }
            for i, hit in enumerate(results)
        ]
