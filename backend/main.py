import os
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Chinese-Khmer Dubbing API",
    version="1.0.0"
)

UPLOAD_DIR = Path("/tmp/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
@app.post("/upload/")
async def upload_video(file: UploadFile = File(...)):

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
