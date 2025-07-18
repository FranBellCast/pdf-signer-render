from flask import Flask, request, jsonify
import base64
import tempfile
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import os
import requests

app = Flask(__name__)

def add_signature_to_pdf(pdf_data, signature_data):
    # Read original PDF
    pdf_reader = PdfReader(BytesIO(pdf_data))
    pdf_writer = PdfWriter()

    # Decode the signature image
    signature_image = BytesIO(base64.b64decode(signature_data))

    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]

        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)

        # Position: lower right corner
        width = 150
        height = 50
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        x = page_width - width - 40
        y = 40

        can.drawImage(signature_image, x, y, width, height, mask='auto')
        can.save()

        packet.seek(0)
        overlay_pdf = PdfReader(packet)
        overlay_page = overlay_pdf.pages[0]
        page.merge_page(overlay_page)

        pdf_writer.add_page(page)

    output_stream = BytesIO()
    pdf_writer.write(output_stream)
    output_stream.seek(0)
    return output_stream.read()

@app.route("/sign-pdf", methods=["POST"])
def sign_pdf():
    try:
        data = request.get_json()
        pdf_b64 = data["pdf_base64"]
        signature_b64 = data["signature_base64"]
        filename = data.get("filename", "signed_bill.pdf")
        access_token = data["access_token"]  # MS Graph access token

        pdf_bytes = base64.b64decode(pdf_b64)
        signed_pdf = add_signature_to_pdf(pdf_bytes, signature_b64)

        # Upload to OneDrive
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/pdf"
        }

        upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/Signed/{filename}:/content"
        response = requests.put(upload_url, headers=headers, data=signed_pdf)

        if response.status_code in (200, 201):
            return jsonify({"success": True, "message": "Signed PDF uploaded to OneDrive", "onedrive_response": response.json()}), 200
        else:
            return jsonify({"success": False, "error": response.text}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# (your Flask app code remains unchanged above)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
