from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile
import os
import json

# Existing triage imports
from pdf_utils import pdf_to_pngs
from openai_client import describe_images
from config import START_KEYWORD, STOP_KEYWORD

# Credit report analyzer imports
from misc.app import analyze_credit_report

app = Flask(__name__)
CORS(app)  # Enable CORS for n8n compatibility

# ============================================
# EXISTING TRIAGE SERVICE (UNTOUCHED)
# ============================================

@app.route("/triage", methods=["POST"])
def triage():
    """Original PDF triage service - unchanged"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    pdf_file = request.files["file"]
    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        images = pdf_to_pngs(
            tmp_path,
            START_KEYWORD,
            STOP_KEYWORD
        )
        ai_text = describe_images(images)
        return jsonify({
            "status": "ok",
            "result": ai_text
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        os.unlink(tmp_path)

# ============================================
# NEW CREDIT REPORT ANALYZER SERVICE
# ============================================

@app.route("/", methods=["GET"])
def root():
    """Health check endpoint"""
    return jsonify({
        "status": "online",
        "services": [
            "/triage - PDF triage service",
            "/analyze - Credit report analyzer"
        ],
        "version": "1.0.0"
    })


@app.route("/analyze", methods=["POST"])
def analyze_endpoint():
    """
    Analyze a credit report WITHOUT AI.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        url = data.get("url")
        html = data.get("html")

        if not url and not html:
            return jsonify({
                "error": "Either 'url' or 'html' must be provided"
            }), 400

        if url and html:
            return jsonify({
                "error": "Provide either 'url' or 'html', not both"
            }), 400

        # Run credit report analyzer only
        url_or_html = url if url else html
        credit_analysis = analyze_credit_report(url_or_html)

        return jsonify({
            "credit_analysis": credit_analysis
        })

    except Exception as e:
        return jsonify({
            "error": f"Analysis failed: {str(e)}"
        }), 500



@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)