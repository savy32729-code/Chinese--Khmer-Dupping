import os

import shutil

import uuid

import subprocess

from pathlib import Path

from deep_translator import GoogleTranslator

from fastapi import FastAPI, HTTPException, File, UploadFile

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import FileResponse

from faster_whisper import WhisperModel

import edge_tts

from pydantic import BaseModel

app = FastAPI(

    title="Chinese-Khmer Dubbing API",

    version="2.0.0",

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

AUDIO_DIR = Path("/tmp/audio")

AUDIO_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path("/tmp/output")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================

# Allowed Video

# =========================================================

ALLOWED_VIDEO_EXTENSIONS = {

    ".mp4",

    ".mov",

    ".mkv",

    ".avi",

    ".webm",

}

# =========================================================

# Whisper

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

class DubbingRequest(BaseModel):

    filename: str

    segments: list

# =========================================================

# Home

# =========================================================

@app.get("/")

def home():

    return {

        "status": "ok",

        "message": "Chinese-Khmer Dubbing API is running",

        "version": "2.0.0",

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

# Upload

# =========================================================

@app.post("/upload")

async def upload_video(

    file: UploadFile = File(...)

):

    if not file.filename:

        raise HTTPException(

            status_code=400,

            detail="No file selected",

        )

    extension = Path(

        file.filename

    ).suffix.lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:

        raise HTTPException(

            status_code=400,

            detail=(

                "Unsupported video format. "

                f"Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}"

            ),

        )

    original_name = Path(

        file.filename

    ).name

    stem = (

        Path(original_name).stem

        or "video"

    )

    filename = (

        f"{stem}_"

        f"{uuid.uuid4().hex[:8]}"

        f"{extension}"

    )

    output_file = (

        UPLOAD_DIR / filename

    )

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

# Transcribe

# =========================================================

@app.post("/transcribe")

async def transcribe_video(

    filename: str

):

    safe_filename = Path(

        filename

    ).name

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

            text = segment.text.strip()

            if not text:

                continue

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

                    "text": text,

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

# Translate

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

    try:

        translated = GoogleTranslator(

            source=data.source or "auto",

            target=data.target or "km",

        ).translate(text)

        return {

            "success": True,

            "original": text,

            "translation": translated,

            "source": data.source,

            "target": data.target,

        }

    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail=f"Translation failed: {exc}",

        ) from exc

# =========================================================

# TTS

# =========================================================

@app.post("/tts")

async def text_to_speech(data: TTSRequest):

    if not data.text or not data.text.strip():

        raise HTTPException(

            status_code=400,

            detail="Text cannot be empty"

        )

    try:

        filename = f"{uuid.uuid4()}.mp3"

        filepath = AUDIO_DIR / filename

        voice = "km-KH-PisethNeural"

        communicate = edge_tts.Communicate(

            data.text,

            voice

        )

        await communicate.save(str(filepath))

        return {

            "success": True,

            "filename": filename,

            "voice": voice,

            "audio_url": f"/audio/{filename}"

        }

    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=f"TTS generation failed: {str(e)}"

        )

    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail=f"TTS failed: {exc}",

        ) from exc

# =========================================================

# Create Final Dubbing Video

# =========================================================

@app.post("/create-dubbing")

async def create_dubbing(

    data: DubbingRequest

):

    safe_filename = Path(

        data.filename

    ).name

    video_file = (

        UPLOAD_DIR /

        safe_filename

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

        Path("/tmp") /

        f"dubbing_{job_id}"

    )

    work_dir.mkdir(

        parents=True,

        exist_ok=True,

    )

    try:

        # ---------------------------------------------

        # Get video duration

        # ---------------------------------------------

        probe = subprocess.run(

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

            capture_output=True,

            text=True,

            check=True,

        )

        duration = float(

            probe.stdout.strip()

        )

        # ---------------------------------------------

        # Generate TTS for each segment

        # ---------------------------------------------

        audio_files = []

        for index, segment in enumerate(

            data.segments

        ):

            text = str(

                segment.get(

                    "translation",

                    ""

                )

            ).strip()

            if not text:

                continue

            start = float(

                segment.get(

                    "start",

                    0

                )

            )

            end = float(

                segment.get(

                    "end",

                    start + 1

                )

            )

            if end <= start:

                end = start + 1

            tts_file = (

                work_dir /

                f"tts_{index}.mp3"

            )

            voice = "km-KH-PisethNeural"

communicate = edge_tts.Communicate(
    text,
    voice
)

await communicate.save(
    str(tts_file)
)

            audio_files.append(

                {

                    "file": tts_file,

                    "start": start,

                    "end": end,

                }

            )

        if not audio_files:

            raise HTTPException(

                status_code=400,

                detail="Could not create Khmer audio",

            )

        # ---------------------------------------------

        # Create silent base audio

        # ---------------------------------------------

        base_audio = (

            work_dir /

            "base_audio.wav"

        )

        subprocess.run(

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

            capture_output=True,

            check=True,

        )

        # ---------------------------------------------

        # Prepare audio inputs

        # ---------------------------------------------

        inputs = [

            "-i",

            str(base_audio)

        ]

        for item in audio_files:

            inputs.extend(

                [

                    "-i",

                    str(item["file"])

                ]

            )

        # ---------------------------------------------

        # Build FFmpeg filter

        # ---------------------------------------------

        filters = []

        filters.append(

            "[0:a]anull[a0]"

        )

        mix_inputs = [

            "[a0]"

        ]

        for index, item in enumerate(

            audio_files,

            start=1

        ):

            delay_ms = max(

                0,

                int(

                    item["start"] * 1000

                )

            )

            filters.append(

                f"[{index}:a]"

                f"adelay={delay_ms}:all=1,"

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

              "dropout_transition=0"

              "[mixed]"

        )

        output_filename = (

            f"khmer_dubbed_"

            f"{job_id}.mp4"

        )

        output_file = (

            OUTPUT_DIR /

            output_filename

        )

        # ---------------------------------------------

        # Merge video + Khmer audio

        # ---------------------------------------------

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

            "-shortest",

            "-movflags",

            "+faststart",

            str(output_file),

        ]

        result = subprocess.run(

            command,

            capture_output=True,

            text=True,

        )

        if result.returncode != 0:

            raise RuntimeError(

                result.stderr[-4000:]

            )

        return {

            "success": True,

            "filename": output_filename,

            "video_url":

                f"/video/{output_filename}",

            "message":

                "Khmer dubbed video created successfully",

        }

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(

            status_code=500,

            detail=(

                "Dubbing video failed: "

                f"{exc}"

            ),

        ) from exc

    finally:

        # ---------------------------------------------

        # Cleanup temporary files

        # ---------------------------------------------

        shutil.rmtree(

            work_dir,

            ignore_errors=True,

        )

# =========================================================

# Audio

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

# Final Video

# =========================================================

@app.get("/video/{filename}")

async def get_video(

    filename: str

):

    safe_filename = Path(

        filename

    ).name

    filepath = (

        OUTPUT_DIR /

        safe_filename

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

# Start Server

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
