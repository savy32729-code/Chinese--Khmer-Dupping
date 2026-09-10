import os
import shutil
import uuid
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
import edge_tts


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Chinese-Khmer Dubbing API",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DIRECTORIES
# =========================================================

UPLOAD_DIR = Path("/tmp/uploads")
AUDIO_DIR = Path("/tmp/audio")
OUTPUT_DIR = Path("/tmp/output")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# SETTINGS
# =========================================================

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v"
}

DEFAULT_VOICE = "km-KH-PisethNeural"

VOICE_MAP = {
    "piseth": "km-KH-PisethNeural",
    "male": "km-KH-PisethNeural",

    # Microsoft Edge Khmer female voice
    "sreymom": "km-KH-SreymomNeural",
    "female": "km-KH-SreymomNeural",
}


# =========================================================
# WHISPER
# =========================================================

# CPU-friendly model for Render
MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")

whisper_model = WhisperModel(
    MODEL_SIZE,
    device="cpu",
    compute_type="int8"
)


# =========================================================
# MODELS
# =========================================================

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = DEFAULT_VOICE


class TranslateRequest(BaseModel):
    text: str


class Segment(BaseModel):
    start: float
    end: float
    text: str
    translation: Optional[str] = None
    audio_filename: Optional[str] = None


class DubbingRequest(BaseModel):
    filename: str
    segments: List[Segment]
    voice: Optional[str] = DEFAULT_VOICE


# =========================================================
# BASIC
# =========================================================

@app.get("/")
async def root():
    return {
        "status": "success",
        "message": "Chinese-Khmer Dubbing API",
        "version": "3.0.0"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


# =========================================================
# UPLOAD VIDEO
# =========================================================

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename"
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format: {extension}"
        )

    # Prevent unsafe filenames
    safe_name = Path(file.filename).name

    # Keep original filename but avoid path traversal
    destination = UPLOAD_DIR / safe_name

    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )

    return {
        "status": "success",
        "filename": safe_name,
        "message": "Video uploaded successfully"
    }


# =========================================================
# TRANSCRIBE
# =========================================================

@app.post("/transcribe")
async def transcribe_video(
    file: Optional[UploadFile] = File(None),
    filename: Optional[str] = None
):

    # -----------------------------------------------------
    # If file is uploaded directly
    # -----------------------------------------------------

    if file is not None:

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No filename"
            )

        safe_name = Path(file.filename).name

        extension = Path(safe_name).suffix.lower()

        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported video format"
            )

        video_path = UPLOAD_DIR / safe_name

        try:
            with video_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {str(e)}"
            )

    # -----------------------------------------------------
    # If filename already uploaded
    # -----------------------------------------------------

    else:

        if not filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )

        safe_name = Path(filename).name
        video_path = UPLOAD_DIR / safe_name

        if not video_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Video file not found"
            )

    # -----------------------------------------------------
    # Transcription
    # -----------------------------------------------------

    try:

        segments, info = whisper_model.transcribe(
            str(video_path),
            language="zh",
            beam_size=1,
            vad_filter=True
        )

        result_segments = []

        for segment in segments:

            text = segment.text.strip()

            if not text:
                continue

            result_segments.append({
                "start": round(float(segment.start), 2),
                "end": round(float(segment.end), 2),
                "text": text
            })

        return {
            "status": "success",
            "filename": safe_name,
            "language": info.language,
            "segments": result_segments
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


# =========================================================
# TRANSLATE ONE TEXT
# =========================================================

def translate_to_khmer(text: str) -> str:

    text = text.strip()

    if not text:
        return ""

    try:

        translator = GoogleTranslator(
            source="zh-CN",
            target="km"
        )

        result = translator.translate(text)

        return result.strip() if result else ""

    except Exception:

        # Retry using auto source
        try:

            translator = GoogleTranslator(
                source="auto",
                target="km"
            )

            result = translator.translate(text)

            return result.strip() if result else ""

        except Exception as e:

            raise RuntimeError(
                f"Translation failed: {str(e)}"
            )


# =========================================================
# TRANSLATE ENDPOINT
# =========================================================

@app.post("/translate")
async def translate_text(data: TranslateRequest):

    if not data.text.strip():

        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )

    try:

        translated = await asyncio.to_thread(
            translate_to_khmer,
            data.text
        )

        return {
            "success": True,
            "original": data.text,
            "translation": translated,
            "source": "auto",
            "target": "km"
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# TRANSLATE ALL SEGMENTS
# =========================================================

@app.post("/translate-segments")
async def translate_segments(
    data: List[Segment]
):

    if not data:

        raise HTTPException(
            status_code=400,
            detail="No segments"
        )

    translated_segments = []

    for segment in data:

        chinese_text = segment.text.strip()

        if not chinese_text:
            continue

        try:

            khmer_text = await asyncio.to_thread(
                translate_to_khmer,
                chinese_text
            )

        except Exception as e:

            raise HTTPException(
                status_code=500,
                detail=f"Translation failed: {str(e)}"
            )

        translated_segments.append({
            "start": segment.start,
            "end": segment.end,
            "text": chinese_text,
            "translation": khmer_text
        })

    return {
        "success": True,
        "segments": translated_segments
    }


# =========================================================
# VOICE
# =========================================================

def get_voice(voice: Optional[str]) -> str:

    if not voice:
        return DEFAULT_VOICE

    voice = voice.strip()

    # User can send full Microsoft voice name
    if voice.startswith("km-KH-"):
        return voice

    key = voice.lower()

    return VOICE_MAP.get(
        key,
        DEFAULT_VOICE
    )


# =========================================================
# TTS
# =========================================================

@app.post("/tts")
async def text_to_speech(data: TTSRequest):

    text = data.text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )

    voice = get_voice(data.voice)

    filename = f"{uuid.uuid4().hex}.mp3"

    filepath = AUDIO_DIR / filename

    try:

        communicate = edge_tts.Communicate(
            text,
            voice
        )

        await communicate.save(
            str(filepath)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"TTS generation failed: {str(e)}"
        )

    return {
        "success": True,
        "filename": filename,
        "voice": voice,
        "audio_url": f"/audio/{filename}"
    }


# =========================================================
# TTS AUDIO FILE
# =========================================================

@app.get("/audio/{filename}")
async def get_audio(filename: str):

    safe_name = Path(filename).name

    filepath = AUDIO_DIR / safe_name

    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail="Audio file not found"
        )

    return FileResponse(
        filepath,
        media_type="audio/mpeg"
    )


# =========================================================
# GET VIDEO DURATION
# =========================================================

def get_video_duration(video_path: Path) -> float:

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr
        )

    return float(
        result.stdout.strip()
    )


# =========================================================
# CREATE DUBBING
# =========================================================

@app.post("/create-dubbing")
async def create_dubbing(
    data: DubbingRequest
):

    safe_filename = Path(
        data.filename
    ).name

    video_file = UPLOAD_DIR / safe_filename

    if not video_file.exists():

        raise HTTPException(
            status_code=404,
            detail="Video file not found"
        )

    if not data.segments:

        raise HTTPException(
            status_code=400,
            detail="No dubbing segments"
        )

    # -----------------------------------------------------
    # Job directory
    # -----------------------------------------------------

    job_id = uuid.uuid4().hex

    work_dir = Path(
        f"/tmp/dubbing_{job_id}"
    )

    work_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    try:

        duration = get_video_duration(
            video_file
        )

        # -------------------------------------------------
        # Generate Khmer TTS for every segment
        # -------------------------------------------------

        audio_segments = []

        voice = get_voice(data.voice)

        for index, segment in enumerate(
            data.segments
        ):

            khmer_text = (
                segment.translation
                or segment.text
            ).strip()

            if not khmer_text:
                continue

            audio_filename = (
                f"{index:04d}.mp3"
            )

            audio_path = (
                work_dir /
                audio_filename
            )

            communicate = edge_tts.Communicate(
                khmer_text,
                voice
            )

            await communicate.save(
                str(audio_path)
            )

            audio_segments.append({
                "start": float(segment.start),
                "end": float(segment.end),
                "audio": audio_path
            })

        if not audio_segments:

            raise HTTPException(
                status_code=400,
                detail="No valid Khmer audio segments"
            )

        # -------------------------------------------------
        # Create silent base audio
        # -------------------------------------------------

        base_audio = (
            work_dir /
            "base.wav"
        )

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=48000:cl=stereo",
                "-t",
                str(duration),
                "-c:a",
                "pcm_s16le",
                str(base_audio)
            ],
            check=True,
            capture_output=True
        )

        # -------------------------------------------------
        # Build FFmpeg inputs
        # -------------------------------------------------

        inputs = [
            "-i",
            str(video_file),

            "-i",
            str(base_audio)
        ]

        filter_parts = []

        # Base silent audio
        filter_parts.append(
            "[1:a]volume=0.0[base]"
        )

        mix_labels = ["[base]"]

        for index, item in enumerate(
            audio_segments
        ):

            audio_path = item["audio"]

            start = max(
                0,
                item["start"]
            )

            end = min(
                duration,
                item["end"]
            )

            inputs.extend([
                "-i",
                str(audio_path)
            ])

            input_number = index + 2

            delay_ms = int(
                start * 1000
            )

            segment_duration = max(
                0.1,
                end - start
            )

            label = f"a{index}"

            filter_parts.append(
                f"[{input_number}:a]"
                f"adelay={delay_ms}|{delay_ms},"
                f"apad=pad_dur={segment_duration},"
                f"atrim=duration={duration}"
                f"[{label}]"
            )

            mix_labels.append(
                f"[{label}]"
            )

        # -------------------------------------------------
        # Mix Khmer voices
        # -------------------------------------------------

        filter_parts.append(
            "".join(mix_labels)
            + f"amix=inputs={len(mix_labels)}:"
              f"duration=longest:"
              f"dropout_transition=0"
              f"[dub]"
        )

        filter_complex = ";".join(
            filter_parts
        )

        output_file = (
            OUTPUT_DIR /
            f"dubbed_{job_id}.mp4"
        )

        command = [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,

            "-map",
            "0:v:0",

            "-map",
            "[dub]",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "28",

            "-c:a",
            "aac",

            "-b:a",
            "128k",

            "-shortest",

            str(output_file)
        ]

        subprocess.run(
            command,
            check=True,
            capture_output=True
        )

        return {
            "success": True,
            "job_id": job_id,
            "filename": output_file.name,
            "video_url": (
                f"/output/{output_file.name}"
            ),
            "voice": voice
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Dubbing failed: {str(e)}"
        )

    finally:

        # -------------------------------------------------
        # Clean temporary job directory
        # -------------------------------------------------

        shutil.rmtree(
            work_dir,
            ignore_errors=True
        )


# =========================================================
# OUTPUT VIDEO
# =========================================================

@app.get("/output/{filename}")
async def get_output(filename: str):

    safe_name = Path(filename).name

    filepath = OUTPUT_DIR / safe_name

    if not filepath.exists():

        raise HTTPException(
            status_code=404,
            detail="Output video not found"
        )

    return FileResponse(
        filepath,
        media_type="video/mp4",
        filename=safe_name
    )
