import os
import shutil
import uuid
from pathlib import Path

from deep_translator import GoogleTranslator
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from faster_whisper import WhisperModel
from gtts import gTTS
from pydantic import BaseModel


app = FastAPI(
    title="Chinese-Khmer Dubbing API",
    version="1.1.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Folders
# =========================================================

UPLOAD_DIR = Path("/tmp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_DIR = Path("uploads")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# Supported video formats
# =========================================================

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
}


# =========================================================
# Whisper Model
# =========================================================

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8",
)


# =========================================================
# Request Models
# =========================================================

class TranslateRequest(BaseModel):
    text: str
    source: str = "auto"
    target: str = "km"


class TTSRequest(BaseModel):
    text: str
    lang: str = "km"


# =========================================================
# Home
# =========================================================

@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Chinese-Khmer Dubbing API is running",
    }


# =========================================================
# Health
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# =========================================================
# Upload Video
# =========================================================

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported video format. "
                f"Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}"
            ),
        )

    # Safe filename
    original_name = Path(file.filename).name
    stem = Path(original_name).stem or "video"

    filename = (
        f"{stem}_{uuid.uuid4().hex[:8]}"
        f"{extension}"
    )

    output_file = UPLOAD_DIR / filename

    try:

        with output_file.open("wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer,
            )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {exc}",
        ) from exc

    finally:

        await file.close()

    return {
        "status": "uploaded",
        "filename": filename,
        "message": "Video uploaded successfully",
    }


# =========================================================
# Transcribe Chinese Video
# =========================================================

@app.post("/transcribe")
async def transcribe_video(
    filename: str
):

    safe_filename = Path(filename).name

    video_file = (
        UPLOAD_DIR /
        safe_filename
    )

    if not video_file.exists():

        raise HTTPException(
            status_code=404,
            detail="Video file not found",
        )

    try:

        segments, info = model.transcribe(
            str(video_file),
            language="zh",
            beam_size=5,
        )

        transcript = []

        for segment in segments:

            transcript.append(
                {
                    "start": round(
                        segment.start,
                        2,
                    ),
                    "end": round(
                        segment.end,
                        2,
                    ),
                    "text": segment.text.strip(),
                }
            )

        full_text = " ".join(
            item["text"]
            for item in transcript
        )

        return {
            "status": "transcribed",
            "filename": video_file.name,
            "language": info.language,
            "text": full_text,
            "segments": transcript,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {exc}",
        ) from exc


# =========================================================
# Translate Chinese → Khmer
# =========================================================

@app.post("/translate")
async def translate(
    data: TranslateRequest
):

    text = data.text.strip()

    if not text:

        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty",
        )

    source = data.source or "auto"
    target = data.target or "km"

    try:

        translated = GoogleTranslator(
            source=source,
            target=target,
        ).translate(text)

        return {
            "success": True,
            "original": text,
            "translation": translated,
            "source": source,
            "target": target,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {exc}",
        ) from exc


# =========================================================
# Khmer Text To Speech
# =========================================================

@app.post("/tts")
async def text_to_speech(
    data: TTSRequest
):

    text = data.text.strip()

    if not text:

        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty",
        )

    lang = (
        data.lang or "km"
    ).strip()

    try:

        filename = (
            f"{uuid.uuid4().hex}.mp3"
        )

        filepath = (
            AUDIO_DIR /
            filename
        )

        tts = gTTS(
            text=text,
            lang=lang,
        )

        tts.save(
            str(filepath)
        )

        return {
            "success": True,
            "filename": filename,
            "audio_url": f"/audio/{filename}",
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"TTS generation failed: {exc}",
        ) from exc


# =========================================================
# Get Audio
# =========================================================

@app.get("/audio/{filename}")
async def get_audio(
    filename: str
):

    safe_filename = Path(
        filename
    ).name

    filepath = (
        AUDIO_DIR /
        safe_filename
    )

    if not filepath.exists():

        raise HTTPException(
            status_code=404,
            detail="Audio file not found",
        )

    return FileResponse(
        path=str(filepath),
        media_type="audio/mpeg",
        filename=safe_filename,
    )


# =========================================================
# Run Server
# =========================================================

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.environ.get(
            "PORT",
            "10000",
        )
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
    )
