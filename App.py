import os
import uuid
import subprocess
from pathlib import Path
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

BASE = Path(__file__).parent
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"

UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/api/status")
def status():
    return {"status": "online"}

@app.post("/api/clips")
async def create_clips(video: UploadFile, duration: int = 60):

    if duration not in [60, 75, 90]:
        raise HTTPException(400, "Duração inválida")

    ext = Path(video.filename).suffix.lower()

    if ext not in [".mp4", ".mov", ".mkv", ".webm"]:
        raise HTTPException(400, "Formato não suportado")

    filename = str(uuid.uuid4()) + ext
    source = UPLOADS / filename

    source.write_bytes(await video.read())

    clips = []

    for i in range(5):

        output = OUTPUTS / f"corte_{i+1}_{uuid.uuid4().hex[:6]}.mp4"

        command = [
            "ffmpeg", "-y",
            "-ss", str(i * duration),
            "-i", str(source),
            "-t", str(duration),
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-c:a", "aac",
            str(output)
        ]

        result = subprocess.run(command, capture_output=True)

        if result.returncode != 0:
            break

        clips.append({
            "name": output.name,
            "url": "/api/download/" + output.name
        })

    if not clips:
        raise HTTPException(500, "Não foi possível criar os cortes.")

    return {"clips": clips}

@app.get("/api/download/{filename}")
def download(filename: str):

    file = OUTPUTS / Path(filename).name

    if not file.exists():
        raise HTTPException(404, "Arquivo não encontrado")

    return FileResponse(file, filename=file.name)
