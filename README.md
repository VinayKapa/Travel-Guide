# AI-Powered Travel Guide using Murf.AI

The project keeps its frontend and backend in separate folders. The frontend
provides the destination gallery, destination search, Summary or Detailed guide
selection, English/Hindi/Tamil/Telugu language selection, Male/Female voice
selection, transcript, and audio player. The Flask backend uses Gemini to write
the guide and Murf.AI FALCON to synthesize the MP3 audio.

## Backend setup

1. Copy `Backend/.env.example` to `Backend/.env`.
2. Put your real `GEMINI_API_KEY` and `MURF_API_KEY` values in `Backend/.env`.
   Do not commit or share that file. `GEMINI_MODEL` is optional and defaults to
   `gemini-3.1-flash-lite`.
3. Open a terminal in `Backend` and install `requirements.txt`.
4. Start the service with `python app.py`. It listens at
   `http://127.0.0.1:5000`.

For deployment, add `GEMINI_API_KEY` and `MURF_API_KEY` as secrets/environment
variables in the hosting provider's settings. Do not upload `Backend/.env`.

The frontend calls `POST /generate-audio-guide` and sends `place`, `answerType`,
`language`, `voiceId`, and `locale`. A successful response contains `description`
and Base64-encoded `audioBase64`.

## Frontend

Open `Frontend/index.html` in a browser while the backend is running. Search
selects matching destinations already present in the gallery. The guide names
complete itinerary planning as a desired capability, but does not specify its
interface or API implementation steps.
