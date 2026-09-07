import os
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from gtts import gTTS
import uuid
import os
app = FastAPI(
    title="Chinese-Khmer Dubbing API",
    version="1.0.0"
)
class TranslateRequest(BaseModel):
    text: str
    source: str = "auto"
    target: str = "km"


class TTSRequest(BaseModel):
    text: str
    lang: str = "en"
UPLOAD_DIR = Path("/tmp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
# Whisper model for Chinese speech-to-text
model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )

@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Chinese-Khmer Dubbing API is running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    safe_name = Path(file.filename).name
    output_file = UPLOAD_DIR / safe_name

    with output_file.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
@app.post("/transcribe")
async def transcribe_video(filename: str):
    video_file = UPLOAD_DIR / Path(filename).name

    if not video_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Video file not found. Please upload the video first."
        )
# =========================
# TRANSLATE API
# =========================

@app.post("/translate")
async def translate(data: TranslateRequest):

    if not data.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )

    try:
        translated = GoogleTranslator(
            source=data.source,
            target=data.target
        ).translate(data.text)

        return {
            "success": True,
            "translation": translated
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# TEXT TO SPEECH API
# =========================

@app.post("/tts")
async def text_to_speech(data: TTSRequest):

    if not data.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )

    try:
        os.makedirs("uploads", exist_ok=True)

        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join("uploads", filename)

        tts = gTTS(
            text=data.text,
            lang=data.lang
        )

        tts.save(filepath)

        return {
            "success": True,
            "audio_url": f"/audio/{filename}"
        }
@app.get("/audio/{filename}")
async def get_audio(filename: str):
    filepath = Path("uploads") / Path(filename).name

    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail="Audio file not found"
        )

    return FileResponse(
        filepath,
        media_type="audio/mpeg"
    )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    try:
        segments, info = model.transcribe(
            str(video_file),
            language="zh",
            beam_size=5
        )

        transcript = []

        for segment in segments:
            transcript.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip()
            })

        full_text = " ".join(
            item["text"] for item in transcript
        )

        return {
            "status": "transcribed",
            "filename": video_file.name,
            "language": info.language,
            "text": full_text,
            "segments": transcript
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )
    return {
        "status": "uploaded",
        "filename": safe_name,
        "message": "Video uploaded successfully"
    }
    
    
    try:
        segments, info = model.transcribe(
            str(video_file),
            language="zh",
            beam_size=5
        )

        transcript = []

        for segment in segments:
            transcript.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip()
            })

        full_text = " ".join(
            item["text"] for item in transcript
        )

        return {
            "status": "transcribed",
            "filename": video_file.name,
            "language": info.language,
            "text": full_text,
            "segments": transcript
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )
    if not file.filename:
        return JSONResponse(
            status_code=400,
            content={"error": "No file selected"}
        )

    allowed = {
        ".mp4",
        ".mov",
        ".mkv",
        ".avi",
        ".webm"
    }

    extension = Path(file.filename).suffix.lower()

    if extension not in allowed:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Unsupported video format",
                "allowed": list(allowed)
            }
        )

    safe_name = Path(file.filename).name
    output_file = UPLOAD_DIR / safe_name

    with output_file.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "status": "uploaded",
        "filename": safe_name,
        "message": "Video uploaded successfully",
        "next_step": "Chinese speech-to-text and Khmer dubbing"
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
