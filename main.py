from flask import Flask, request, jsonify
import smtplib
import ssl
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

app = Flask(__name__)

# --- CONFIGURATION ---
SMTP_SERVER = "mail.touatgaz.com"
SMTP_PORT = 587  # STARTTLS
USERNAME = "tgs.hse"
PASSWORD = ".touat123"
SENDER_EMAIL = "tgs.hse@touatgaz.com"

GOOGLE_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwxqgOGs-X7g6h2sxU2SmCUUyG4Cf4v0VZovUBm8lykfzmTFdbQ1qwKLbadn_VRgKljPA/exec"

RECIPIENTS_TO = ["boucenna.othman@gmail.com"]
RECIPIENTS_CC = [
    "akayno21@gmail.com",
    "akayno23@gmail.com"
]


@app.route("/", methods=["GET"])
def home():
    return jsonify({"ok": True, "message": "Render bot is running!"})


@app.route("/odm", methods=["POST"])
def generate_and_send():
    try:
        data = request.get_json()
        agents = data.get("agents", [])
        signature = data.get("signature", "")

        # 1️⃣ Send data to Google App Script
        response = requests.post(GOOGLE_WEB_APP_URL, json={"agents": agents})
        result = response.json()

        if not result.get("ok"):
            return jsonify({"error": "Failed to generate PDFs", "details": result}), 500

        pdfs = result.get("results", [])

        # 2️⃣ Create the email body
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

        # 3️⃣ Send the email
        msg = MIMEMultipart()
        msg["Subject"] = "Activation de Badge"
        msg["From"] = SENDER_EMAIL
        msg["To"] = ", ".join(RECIPIENTS_TO)
        msg["Cc"] = ", ".join(RECIPIENTS_CC)
        msg.attach(MIMEText(email_body, "plain"))

        # Attach PDFs
        for pdf in pdfs:
            pdf_url = pdf.get("pdfUrl")
            if not pdf_url:
                continue
            file_data = requests.get(pdf_url).content
            part = MIMEApplication(file_data, Name=pdf["pdfName"])
            part["Content-Disposition"] = f'attachment; filename="{pdf["pdfName"]}"'
            msg.attach(part)

        # --- EMAIL SENDING (STARTTLS) ---
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(USERNAME, PASSWORD)
            server.send_message(msg)

        return jsonify({"ok": True, "sent": True, "pdfs": len(pdfs)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
