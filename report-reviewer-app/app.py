import os
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document
from dotenv import load_dotenv
from flask import Flask, render_template, request
from openai import OpenAI
from werkzeug.utils import secure_filename

load_dotenv()

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
MAX_CHARS = int(os.getenv("MAX_REPORT_CHARS", "120000"))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_pdf(path: Path) -> str:
    text_parts = []
    with fitz.open(path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n\n".join(text_parts)


def extract_docx(path: Path) -> str:
    document = Document(path)
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".docx":
        return extract_docx(path)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError("Unsupported file type")


def build_review_prompt(report_text: str, filename: str) -> str:
    return f"""
You are a careful report reviewer. Review the uploaded report named {filename!r}.

Focus on:
1. Executive summary quality
2. Structure and readability
3. Evidence, assumptions, and unsupported claims
4. Risks, omissions, and inconsistencies
5. Practical recommendations for improvement
6. A concise list of priority edits

Return the review in Markdown with these headings:
- Overall assessment
- Strengths
- Issues and risks
- Missing information or evidence
- Recommended edits
- Questions for the author

Report text:
---
{report_text}
---
""".strip()


def review_report(report_text: str, filename: str) -> str:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")

    trimmed_text = report_text[:MAX_CHARS]
    if len(report_text) > MAX_CHARS:
        trimmed_text += "\n\n[Document truncated because it exceeded MAX_REPORT_CHARS.]"

    response = client.responses.create(
        model=MODEL,
        instructions="You review reports with a professional, practical, constructive tone.",
        input=build_review_prompt(trimmed_text, filename),
    )
    return response.output_text


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    uploaded = request.files.get("report")
    if not uploaded or uploaded.filename == "":
        return render_template("index.html", error="Please choose a report file to upload."), 400

    if not allowed_file(uploaded.filename):
        return render_template(
            "index.html",
            error="Unsupported file type. Upload a PDF, DOCX, TXT, or MD file.",
        ), 400

    filename = secure_filename(uploaded.filename)
    suffix = Path(filename).suffix
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            uploaded.save(temp_file.name)
            temp_path = Path(temp_file.name)

        report_text = extract_text(temp_path)
        if not report_text.strip():
            return render_template("index.html", error="No readable text was found in the file."), 400

        review = review_report(report_text, filename)
        return render_template("result.html", filename=filename, review=review)
    except Exception as exc:
        return render_template("index.html", error=f"Could not review the report: {exc}"), 500
    finally:
        if temp_path:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
