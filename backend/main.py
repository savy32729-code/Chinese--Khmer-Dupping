import os
import shutil
import subprocess
import uuid
import asyncio
from pathlib import Path
from typing import Any

import edge_tts
from deep_translator import GoogleTranslator
from faster_whisper import WhisperModel

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


# =========================================================
# APP
# =========================================================

APP_VERSION = "3.0.0"

app = FastAPI(
    title="Chinese-Khmer Dubbing API",
    version=APP_VERSION,
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
# DIRECTORIES
# =========================================================

BASE_DIR = Path("/tmp")

UPLOAD_DIR = BASE_DIR / "uploads"
AUDIO_DIR = BASE_DIR / "audio"
OUTPUT_DIR = BASE_DIR / "output"

for directory in (UPLOAD_DIR, AUDIO_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)


# =========================================================
# SETTINGS
# =========================================================

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
}

MAX_UPLOAD_BYTES = 500 * 1024 * 1024

WHISPER_MODEL_NAME = os.getenv(
    "WHISPER_MODEL",
    "tiny",
)

WHISPER_DEVICE = os.getenv(
    "WHISPER_DEVICE",
    "cpu",
)

WHISPER_COMPUTE_TYPE = os.getenv(
    "WHISPER_COMPUTE_TYPE",
    "int8",
)

DEFAULT_VOICE = os.getenv(
    "TTS_VOICE",
    "km-KH-PisethNeural",
)


# =========================================================
# WHISPER
# =========================================================

whisper_model = None
whisper_lock = asyncio.Lock()


async def get_whisper_model():
    global whisper_model

    if whisper_model is None:
        async with whisper_lock:
            if whisper_model is None:
                print(
                    f"Loading Whisper model: "
                    f"{WHISPER_MODEL_NAME}"
                )

                whisper_model = WhisperModel(
                    WHISPER_MODEL_NAME,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTE_TYPE,
                )

                print("Whisper model loaded.")

    return whisper_model


# =========================================================
# REQUEST MODELS
# =========================================================

class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source: str = "auto"
    target: str = "km"


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)
    lang: str = "km"
    voice: str = DEFAULT_VOICE


class DubbingRequest(BaseModel):
    filename: str
    segments: list[dict[str, Any]]
    voice: str = DEFAULT_VOICE


# =========================================================
# HELPERS
# =========================================================

def safe_name(filename: str) -> str:
    return Path(filename).name


def run_command(
    command: list[str],
    timeout: int = 600,
) -> subprocess.CompletedProcess:

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Command timeout after {timeout} seconds"
        ) from exc

    if result.returncode != 0:
        error = (
            result.stderr.strip()
            or result.stdout.strip()
            or "Unknown command error"
        )

        raise RuntimeError(
            error[-5000:]
        )

    return result


def split_text(
    text: str,
    max_chars: int = 2500,
) -> list[str]:

    text = text.strip()

    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    parts = []
    current = ""

    # Khmer/Chinese punctuation
    separators = [
        "។",
        "៕",
        "!",
        "?",
        "！",
        "？",
        "，",
        ",",
        " ",
    ]

    words = text

    for char in words:

        current += char

        if (
            len(current) >= max_chars
            and char in separators
        ):
            parts.append(current.strip())
            current = ""

    if current.strip():
        parts.append(current.strip())

    # Safety fallback
    final_parts = []

    for part in parts:
        if len(part) <= max_chars:
            final_parts.append(part)
        else:
            for i in range(
                0,
                len(part),
                max_chars,
            ):
                final_parts.append(
                    part[i:i + max_chars].strip()
                )

    return [
        p for p in final_parts
        if p
    ]


async def generate_tts_with_retry(
    text: str,
    output_file: Path,
    voice: str,
    retries: int = 3,
):

    last_error = None

    chunks = split_text(
        text,
        max_chars=2500,
    )

    if not chunks:
        raise RuntimeError(
            "TTS text is empty"
        )

    # Single chunk
    if len(chunks) == 1:

        for attempt in range(retries):

            try:

                communicate = edge_tts.Communicate(
                    chunks[0],
                    voice,
                )

                await communicate.save(
                    str(output_file)
                )

                if (
                    output_file.exists()
                    and output_file.stat().st_size > 0
                ):
                    return

            except Exception as exc:
                last_error = exc

                if attempt < retries - 1:
                    await asyncio.sleep(
                        2 ** attempt
                    )

        raise RuntimeError(
            f"TTS failed: {last_error}"
        )

    # Multiple chunks
    chunk_files = []

    try:

        for index, chunk in enumerate(chunks):

            chunk_file = (
                output_file.parent
                / f"{output_file.stem}_part_{index}.mp3"
            )

            for attempt in range(retries):

                try:

                    communicate = edge_tts.Communicate(
                        chunk,
                        voice,
                    )

                    await communicate.save(
                        str(chunk_file)
                    )

                    if (
                        chunk_file.exists()
                        and chunk_file.stat().st_size > 0
                    ):
                        break

                except Exception as exc:
                    last_error = exc

                    if attempt < retries - 1:
                        await asyncio.sleep(
                            2 ** attempt
                        )

            if not chunk_file.exists():
                raise RuntimeError(
                    f"TTS chunk failed: {last_error}"
                )

            chunk_files.append(chunk_file)

        concat_file = (
            output_file.parent
            / f"{output_file.stem}_concat.txt"
        )

        with concat_file.open(
            "w",
            encoding="utf-8",
        ) as f:

            for chunk_file in chunk_files:

                escaped = str(
                    chunk_file
                ).replace(
                    "'",
                    "'\\''",
                )

                f.write(
                    f"file '{escaped}'\n"
                )

        run_command(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                str(output_file),
            ],
            timeout=300,
        )

    finally:

        for file in chunk_files:
            file.unlink(
                missing_ok=True
            )


def cleanup_old_files(
    max_age_seconds: int = 3600,
):

    import time

    now = time.time()

    for directory in (
        UPLOAD_DIR,
        AUDIO_DIR,
        OUTPUT_DIR,
    ):

        for file in directory.iterdir():

            try:

                if not file.is_file():
                    continue

                age = (
                    now
                    - file.stat().st_mtime
                )

                if age > max_age_seconds:
                    file.unlink(
                        missing_ok=True
                    )

            except Exception as exc:
                print(
                    f"Cleanup warning: {exc}"
                )


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "status": "ok",
        "message": (
            "Chinese-Khmer Dubbing API "
            "is running"
        ),
        "version": APP_VERSION,
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "version": APP_VERSION,
    }


# =========================================================
# UPLOAD
# =========================================================

@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
):

    cleanup_old_files()

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected",
        )

    extension = (
        Path(file.filename)
        .suffix
        .lower()
    )

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported video format. "
                f"Allowed: "
                f"{', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}"
            ),
        )

    original_name = safe_name(
        file.filename
    )

    stem = (
        Path(original_name).stem
        or "video"
    )

    filename = (
        f"{stem}_"
        f"{uuid.uuid4().hex[:10]}"
        f"{extension}"
    )

    output_file = (
        UPLOAD_DIR / filename
    )

    total_bytes = 0

    try:

        with output_file.open(
            "wb"
        ) as buffer:

            while True:

                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > MAX_UPLOAD_BYTES:

                    output_file.unlink(
                        missing_ok=True
                    )

                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "Video is too large. "
                            "Maximum size is 500 MB."
                        ),
                    )

                buffer.write(chunk)

    except HTTPException:
        raise

    except Exception as exc:

        output_file.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {exc}",
        ) from exc

    finally:
        await file.close()

    return {
        "status": "uploaded",
        "filename": filename,
        "size": total_bytes,
        "message": (
            "Video uploaded successfully"
        ),
    }


# =========================================================
# TRANSCRIBE
# =========================================================

@app.post("/transcribe")
async def transcribe_video(
    filename: str,
):

    cleanup_old_files()

    safe_filename = safe_name(
        filename
    )

    video_file = (
        UPLOAD_DIR / safe_filename
    )

    if not video_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Video file not found",
        )

    work_dir = (
        BASE_DIR
        / f"transcribe_{uuid.uuid4().hex}"
    )

    work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    audio_file = (
        work_dir / "audio.wav"
    )

    try:

        # -----------------------------------------
        # Extract audio
        # -----------------------------------------

        run_command(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_file),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(audio_file),
            ],
            timeout=600,
        )

        if not audio_file.exists():
            raise RuntimeError(
                "FFmpeg did not create audio file"
            )

        # -----------------------------------------
        # Whisper
        # -----------------------------------------

        model = await get_whisper_model()

        segments, info = await asyncio.to_thread(
            model.transcribe,
            str(audio_file),
            language="zh",
            beam_size=1,
            best_of=1,
            temperature=0,
            vad_filter=True,
            condition_on_previous_text=False,
        )

        transcript = []
        full_text_parts = []

        for segment in segments:

            text = (
                segment.text
                .strip()
            )

            if not text:
                continue

            item = {
                "start": float(
                    segment.start
                ),
                "end": float(
                    segment.end
                ),
                "text": text,
            }

            transcript.append(item)
            full_text_parts.append(text)

        full_text = " ".join(
            full_text_parts
        )

        return {
            "status": "transcribed",
            "filename": safe_filename,
            "language": getattr(
                info,
                "language",
                "zh",
            ),
            "duration": getattr(
                info,
                "duration",
                None,
            ),
            "text": full_text,
            "segments": transcript,
            "segment_count": len(
                transcript
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:

        print(
            f"TRANSCRIBE ERROR: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Transcription failed: "
                f"{str(exc)}"
            ),
        ) from exc

    finally:

        shutil.rmtree(
            work_dir,
            ignore_errors=True,
        )


# =========================================================
# TRANSLATE
# =========================================================

@app.post("/translate")
async def translate(
    data: TranslateRequest,
):

    text = data.text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty",
        )

    try:

        chunks = split_text(
            text,
            max_chars=3000,
        )

        translated_parts = []

        for chunk in chunks:

            result = await asyncio.to_thread(
                GoogleTranslator(
                    source=data.source or "auto",
                    target=data.target or "km",
                ).translate,
                chunk,
            )

            if result:
                translated_parts.append(
                    result.strip()
                )

        translated = " ".join(
            translated_parts
        )

        return {
            "success": True,
            "original": text,
            "translation": translated,
            "source": data.source,
            "target": data.target,
        }

    except Exception as exc:

        print(
            f"TRANSLATION ERROR: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Translation failed: "
                f"{str(exc)}"
            ),
        ) from exc


# =========================================================
# TTS
# =========================================================

@app.post("/tts")
async def text_to_speech(
    data: TTSRequest,
):

    cleanup_old_files()

    text = data.text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty",
        )

    voice = (
        data.voice.strip()
        if data.voice
        else DEFAULT_VOICE
    )

    filename = (
        f"{uuid.uuid4().hex}.mp3"
    )

    filepath = (
        AUDIO_DIR / filename
    )

    try:

        await generate_tts_with_retry(
            text=text,
            output_file=filepath,
            voice=voice,
            retries=3,
        )

        return {
            "success": True,
            "filename": filename,
            "voice": voice,
            "audio_url": (
                f"/audio/{filename}"
            ),
        }

    except Exception as exc:

        filepath.unlink(
            missing_ok=True
        )

        print(
            f"TTS ERROR: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "TTS generation failed: "
                f"{str(exc)}"
            ),
        ) from exc


# =========================================================
# CREATE DUBBING
# =========================================================

@app.post("/create-dubbing")
async def create_dubbing(
    data: DubbingRequest,
):

    cleanup_old_files()

    safe_filename = safe_name(
        data.filename
    )

    video_file = (
        UPLOAD_DIR / safe_filename
    )

    if not video_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Video file not found",
        )

    if not data.segments:
        raise HTTPException(
            status_code=400,
            detail="No dubbing segments",
        )

    job_id = uuid.uuid4().hex

    work_dir = (
        BASE_DIR
        / f"dubbing_{job_id}"
    )

    work_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:

        # -----------------------------------------
        # Get video duration
        # -----------------------------------------

        probe = run_command(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_file),
            ],
            timeout=60,
        )

        duration = float(
            probe.stdout.strip()
        )

        if duration <= 0:
            raise RuntimeError(
                "Invalid video duration"
            )

        # -----------------------------------------
        # Generate TTS
        # -----------------------------------------

        audio_files = []

        voice = (
            data.voice.strip()
            if data.voice
            else DEFAULT_VOICE
        )

        for index, segment in enumerate(
            data.segments
        ):

            if not isinstance(
                segment,
                dict,
            ):
                continue

            text = str(
                segment.get(
                    "translation",
                    segment.get(
                        "text",
                        "",
                    ),
                )
            ).strip()

            if not text:
                continue

            try:
                start = float(
                    segment.get(
                        "start",
                        0,
                    )
                )
            except Exception:
                start = 0

            try:
                end = float(
                    segment.get(
                        "end",
                        start + 1,
                    )
                )
            except Exception:
                end = start + 1

            start = max(
                0,
                start,
            )

            end = max(
                start + 0.1,
                end,
            )

            # Do not put audio outside video
            if start >= duration:
                continue

            end = min(
                end,
                duration,
            )

            tts_file = (
                work_dir
                / f"tts_{index}.mp3"
            )

            await generate_tts_with_retry(
                text=text,
                output_file=tts_file,
                voice=voice,
                retries=3,
            )

            audio_files.append(
                {
                    "file": tts_file,
                    "start": start,
                    "end": end,
                }
            )

        if not audio_files:
            raise RuntimeError(
                "No valid TTS segments"
            )

        # -----------------------------------------
        # Base silent audio
        # -----------------------------------------

        base_audio = (
            work_dir
            / "base_audio.wav"
        )

        run_command(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=stereo",
                "-t",
                str(duration),
                "-c:a",
                "pcm_s16le",
                str(base_audio),
            ],
            timeout=300,
        )

        # -----------------------------------------
        # Build inputs
        # -----------------------------------------

        inputs = [
            "-i",
            str(base_audio),
        ]

        for item in audio_files:

            inputs.extend(
                [
                    "-i",
                    str(item["file"]),
                ]
            )

        # -----------------------------------------
        # Build filters
        # -----------------------------------------

        filters = [
            "[0:a]anull[a0]"
        ]

        mix_inputs = [
            "[a0]"
        ]

        for index, item in enumerate(
            audio_files,
            start=1,
        ):

            delay_ms = max(
                0,
                int(
                    item["start"] * 1000
                ),
            )

            filters.append(
                f"[{index}:a]"
                f"adelay={delay_ms}:all=1,"
                f"aresample=44100,"
                f"volume=1.0"
                f"[a{index}]"
            )

            mix_inputs.append(
                f"[a{index}]"
            )

        filter_complex = (
            ";".join(filters)
            + ";"
            + "".join(mix_inputs)
            + f"amix=inputs={len(mix_inputs)}:"
              "duration=longest:"
              "dropout_transition=0,"
              "aresample=44100"
              "[mixed]"
        )

        # -----------------------------------------
        # Output
        # -----------------------------------------

        output_filename = (
            f"khmer_dubbed_{job_id}.mp4"
        )

        output_file = (
            OUTPUT_DIR
            / output_filename
        )

        command = [
            "ffmpeg",
            "-y",

            "-i",
            str(video_file),

            *inputs,

            "-filter_complex",
            filter_complex,

            "-map",
            "0:v:0",

            "-map",
            "[mixed]",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "23",

            "-c:a",
            "aac",

            "-b:a",
            "128k",

            "-t",
            str(duration),

            "-movflags",
            "+faststart",

            str(output_file),
        ]

        run_command(
            command,
            timeout=1200,
        )

        if (
            not output_file.exists()
            or output_file.stat().st_size <= 0
        ):
            raise RuntimeError(
                "FFmpeg did not create output video"
            )

        return {
            "success": True,
            "filename": output_filename,
            "video_url": (
                f"/video/{output_filename}"
            ),
            "message": (
                "Khmer dubbed video "
                "created successfully"
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:

        print(
            f"DUBBING ERROR: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Dubbing failed: "
                f"{str(exc)}"
            ),
        ) from exc

    finally:

        # IMPORTANT:
        # This now ALWAYS runs.
        shutil.rmtree(
            work_dir,
            ignore_errors=True,
        )


# =========================================================
# AUDIO
# =========================================================

@app.get("/audio/{filename}")
async def get_audio(
    filename: str,
):

    safe_filename = safe_name(
        filename
    )

    filepath = (
        AUDIO_DIR / safe_filename
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
# VIDEO
# =========================================================

@app.get("/video/{filename}")
async def get_video(
    filename: str,
):

    safe_filename = safe_name(
        filename
    )

    filepath = (
        OUTPUT_DIR / safe_filename
    )

    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail="Video file not found",
        )

    return FileResponse(
        path=str(filepath),
        media_type="video/mp4",
        filename=safe_filename,
    )


# =========================================================
# SERVER
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
