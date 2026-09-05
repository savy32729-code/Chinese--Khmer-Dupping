import os
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel

app = FastAPI(
    title="Chinese-Khmer Dubbing API",
    version="1.0.0"
)

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
@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
@app.post("/transcribe")
async def transcribe_video(filename: str):
    video_file = UPLOAD_DIR / Path(filename).name

    if not video_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Video file not found. Please upload the video first."
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
