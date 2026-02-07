from flask import Flask, render_template, request, send_file
from io import BytesIO
import requests
from deep_translator import GoogleTranslator
from gtts import gTTS
import cohere
import base64

app = Flask(__name__)

# ==========================
# OCR (OCR.Space)
# ==========================
def extract_text_from_image(image_bytes):
    try:
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("image.png", image_bytes)},
            data={
                "apikey": "K89919669988957",
                "language": "eng"
            },
            timeout=30
        )

        result = response.json()

        if result.get("IsErroredOnProcessing"):
            return result.get("ErrorMessage", ["OCR failed"])[0]

        parsed = result.get("ParsedResults")
        return parsed[0]["ParsedText"].strip() if parsed else "No text detected"

    except Exception as e:
        return f"OCR Exception: {e}"


# ==========================
# COHERE SUMMARY
# ==========================
def summarize_text(text):
    try:
        if not text or len(text.split()) < 30:
            return text

        co = cohere.Client("b4wwr5UnYk8egX1kgP01rE7bzYfFDv4KtXQiFMUP")

        response = co.chat(
            model="command-a-03-2025",
            message=f"""
Clean OCR text and summarize it in 3–4 sentences.

Rules:
- Remove OCR noise
- Fix broken sentences
- Be concise

Text:
{text}
""",
            temperature=0.3
        )

        return response.text.strip()

    except Exception as e:
        return f"Cohere Error: {e}"


# ==========================
# TRANSLATION
# ==========================
def translate_to_tamil(text):
    try:
        return GoogleTranslator(source="en", target="ta").translate(text)
    except Exception as e:
        return f"Translation Error: {e}"


# ==========================
# TTS (IN-MEMORY)
# ==========================
def generate_audio(text, lang):
    audio = BytesIO()
    gTTS(text=text, lang=lang).write_to_fp(audio)
    audio.seek(0)
    return audio


# ==========================
# ROUTES
# ==========================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    image_bytes = None

    # Camera image (base64)
    if request.form.get("captured_image"):
        base64_data = request.form["captured_image"].split(",")[1]
        image_bytes = base64.b64decode(base64_data)

    # File upload
    elif "image" in request.files:
        image_bytes = request.files["image"].read()

    if not image_bytes:
        return "No image provided"

    extracted_text = extract_text_from_image(image_bytes)
    summarized_text = summarize_text(extracted_text)
    tamil_text = translate_to_tamil(summarized_text)

    return render_template(
        "result.html",
        extracted_text=extracted_text,
        summarized_text=summarized_text,
        tamil_text=tamil_text
    )


@app.route("/audio/en")
def audio_en():
    text = request.args.get("text", "")
    return send_file(
        generate_audio(text, "en"),
        mimetype="audio/mpeg",
        as_attachment=True,
        download_name="summary_english.mp3"
    )


@app.route("/audio/ta")
def audio_ta():
    text = request.args.get("text", "")
    return send_file(
        generate_audio(text, "ta"),
        mimetype="audio/mpeg",
        as_attachment=True,
        download_name="summary_tamil.mp3"
    )


if __name__ == "__main__":
    app.run(debug=True)
