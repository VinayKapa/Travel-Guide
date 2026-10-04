import base64
import os
import tempfile

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from google import genai


load_dotenv()

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(PROJECT_DIR, "Frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MURF_API_KEY = os.environ.get("MURF_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
MURF_API_URL = "https://global.api.murf.ai/v1/speech/stream"

PROMPTS = {
    "Summary": """
You are a professional tourist guide.
Provide a high-level overview of "{place}" in {language}.

Focus on:
- The historical significance
- Why the place is famous
- Key architectural or cultural highlights

Keep the explanation concise, engaging, and easy to follow. Avoid excessive
details and dates. Limit the response to around 200 words.
Respond ONLY in {language}.
""",
    "Detailed": """
You are a professional tourist guide.
Provide a detailed and immersive explanation of "{place}" in {language}.

Cover:
- Historical background and timeline
- Architectural design and unique features
- Cultural importance and notable events
- Interesting facts and visitor insights

Explain concepts clearly and in a storytelling manner. Include relevant details
and examples to create a rich experience. Limit the response to around 400 words.
Respond ONLY in {language}.
""",
}


@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


def generate_description(place, answer_type, language):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = PROMPTS[answer_type].format(place=place, language=language)
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    if not response.text:
        raise RuntimeError("Gemini returned an empty description.")
    return response.text


def generate_speech(text, voice_id, locale):
    if not MURF_API_KEY:
        raise RuntimeError("MURF_API_KEY is not configured.")

    headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
    payload = {
        "voice_id": voice_id,
        "text": text,
        "locale": locale,
        "model": "FALCON",
        "format": "MP3",
        "sampleRate": 24000,
        "channelType": "MONO",
    }
    response = requests.post(
        MURF_API_URL, headers=headers, json=payload, stream=True, timeout=(10, 120)
    )
    if response.status_code != 200:
        detail = response.text[:500]
        raise RuntimeError(f"Murf API returned {response.status_code}: {detail}")

    temp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    try:
        with temp_audio:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_audio.write(chunk)
        return temp_audio.name
    except Exception:
        os.unlink(temp_audio.name)
        raise
    finally:
        response.close()


@app.route("/generate-audio-guide", methods=["POST"])
def generate_audio_guide():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object."), 400

    place = data.get("place", "").strip()
    answer_type = data.get("answerType")
    language = data.get("language", "").strip()
    voice_id = data.get("voiceId", "").strip()
    locale = data.get("locale", "").strip()
    if not place or not language or not voice_id or not locale:
        return jsonify(error="place, language, voiceId, and locale are required."), 400
    if answer_type not in PROMPTS:
        return jsonify(error="answerType must be Summary or Detailed."), 400

    audio_path = None
    try:
        description = generate_description(place, answer_type, language)
        audio_path = generate_speech(description, voice_id, locale)
        with open(audio_path, "rb") as audio_file:
            audio_base64 = base64.b64encode(audio_file.read()).decode("ascii")
        return jsonify(description=description, audioBase64=audio_base64)
    except RuntimeError as error:
        return jsonify(error=str(error)), 503
    except requests.RequestException:
        app.logger.exception("Murf API request failed")
        return jsonify(error="Could not generate audio with Murf. Please try again."), 502
    except Exception:
        app.logger.exception("Audio guide generation failed")
        return jsonify(error="Could not generate the audio guide. Please try again."), 502
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


if __name__ == "__main__":
    app.run(debug=True)
