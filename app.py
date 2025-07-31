from flask import Flask, render_template, request
from abstract import search_abstracts, build_index
from transformers import pipeline

app = Flask(__name__)

# Initialize summarizer once
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def summarize_text(text, max_length=130, min_length=30):
    try:
        summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        print(f"Summarization error: {e}")
        return ""

@app.route("/", methods=["GET", "POST"])
def index():
    query = request.values.get("q", "").strip()
    results = search_abstracts(query) if query else []
    ai_summary = ""
    summarized_title = ""
    if request.method == "POST":
        abs_id = int(request.form.get("summarize_id", -1))
        if 0 <= abs_id < len(results):
            abstract = results[abs_id]
            abstract_text = abstract.get("text", "") or abstract.get("content", "")
            ai_summary = summarize_text(abstract_text) if abstract_text else ""
            summarized_title = abstract.get("title", "")
    return render_template("index.html", query=query, results=results, ai_summary=ai_summary, summarized_title=summarized_title)

@app.route("/abstract/<int:abs_id>")
def view_abstract(abs_id):
    query = request.args.get("q", "")
    results = search_abstracts(query)
    if 0 <= abs_id < len(results):
        abstract = results[abs_id]
        abstract_text = abstract.get("text", "") or abstract.get("content", "")
        summary = summarize_text(abstract_text) if abstract_text else ""
        return render_template("abstract.html", abstract=abstract, summary=summary, query=query)
    return "Abstract not found", 404

if __name__ == "__main__":
    build_index()
    app.run(debug=True)