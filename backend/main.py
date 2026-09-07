import os
import shutil
import uuid
from pathlib import Path
BASE_DIR = 
Path(_file_).resolve().parent
AUDIO_DIR = BASE_DIR / "audio"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from faster_whisper import WhisperModel
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from gtts import gTTS


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
    lang: str = "km"


UPLOAD_DIR = Path("/tmp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_DIR = Path("uploads")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


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
    return {
        "status": "healthy"
    }


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):

    if not file.filename:
        return JSONResponse(
            status_code=400,
            content={
                "error": "No file selected"
            }
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

    try:
        with output_file.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "status": "uploaded",
            "filename": safe_name,
            "message": "Video uploaded successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@app.post("/transcribe")
async def transcribe_video(filename: str):

    video_file = UPLOAD_DIR / Path(filename).name

    if not video_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Video file not found"
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
            item["text"]
            for item in transcript
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
            "original": data.text,
            "translation": translated,
            "source": data.source,
            "target": data.target
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )


@app.post("/tts")
async def text_to_speech(data: TTSRequest):

    if not data.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )

    try:
        filename = f"{uuid.uuid4()}.mp3"
        filepath = AUDIO_DIR / filename

        tts = gTTS(
            text=data.text,
            lang=data.lang
        )

        tts.save(str(filepath))

        return {
            "success": True,
            "filename": filename,
            "audio_url": f"/audio/{filename}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"TTS failed: {str(e)}"
        )


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    filename = Path(filename).name
    filepath = AUDIO_DIR / filename

    # បើ URL មិនមាន .mp3 សូមបន្ថែម
    if not filepath.exists() and not filename.endswith(".mp3"):
        filepath = AUDIO_DIR / f"{filename}.mp3"

    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail="Audio file not found"
        )

    return FileResponse(
        str(filepath),
        media_type="audio/mpeg"
    )

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
