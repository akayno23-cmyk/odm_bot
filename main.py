from flask import Flask, request, jsonify
import requests
from email.mime.application import MIMEApplication
import base64
import os

app = Flask(__name__)

# --- CONFIGURATION ---
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")  # Read from Render env variables
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

SENDER_EMAIL = "tgs.hse@touatgaz.com"
RECIPIENTS_TO = ["boucenna.othman@gmail.com"]
RECIPIENTS_CC = [
    "akayno21@gmail.com",
    "akayno23@gmail.com"
]

GOOGLE_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwxqgOGs-X7g6h2sxU2SmCUUyG4Cf4v0VZovUBm8lykfzmTFdbQ1qwKLbadn_VRgKljPA/exec"


@app.route("/", methods=["GET"])
def home():
    return jsonify({"ok": True, "message": "Render bot is running!"})


@app.route("/odm", methods=["POST"])
def generate_and_send():
    try:
        data = request.get_json()
        agents = data.get("agents", [])
        signature = data.get("signature", "")

        if not agents:
            return jsonify({"error": "No agents provided"}), 400

        # 1️⃣ Get PDFs from Google App Script
        response = requests.post(GOOGLE_WEB_APP_URL, json={"agents": agents})
        result = response.json()
        if not result.get("ok"):
            return jsonify({"error": "Failed to generate PDFs", "details": result}), 500

        pdfs = result.get("results", [])

        # 2️⃣ Build email body
        body_lines = [
            "Bonjour,",
            "",
            "Merci de prolonger l’autorisation d’accès au CPF, EPC Camp, WH2 et YARD pour les agents TGS suivant :",
            ""
        ]
        for agent in agents:
            line = f"{agent['nom'].upper()} {agent['prenom'].upper()} badge {agent['badge']}"
            body_lines.append(line)
        body_lines += ["", "Cordialement,", signature]
        email_body = "\n".join(body_lines)

        # 3️⃣ Prepare attachments (base64)
        attachments = []
        for pdf in pdfs:
            pdf_url = pdf.get("pdfUrl")
            pdf_name = pdf.get("pdfName")
            if pdf_url and pdf_name:
                file_data = requests.get(pdf_url).content
                encoded = base64.b64encode(file_data).decode("utf-8")
                attachments.append({
                    "content": encoded,
                    "name": pdf_name
                })

        # 4️⃣ Send email via Brevo API
        payload = {
            "sender": {"email": SENDER_EMAIL, "name": "TGS HSE"},
            "to": [{"email": email} for email in RECIPIENTS_TO],
            "cc": [{"email": email} for email in RECIPIENTS_CC],
            "subject": "Activation de Badge",
            "textContent": email_body,
            "attachment": attachments
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": BREVO_API_KEY
        }

        res = requests.post(BREVO_API_URL, json=payload, headers=headers)
        res.raise_for_status()

        return jsonify({
            "ok": True,
            "sent": True,
            "pdfs": len(pdfs),
            "brevo_status": res.status_code
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
