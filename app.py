import os, uuid, subprocess
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).parent
UPLOADS = ROOT / "uploads"
OUTPUTS = ROOT / "outputs"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

app = FastAPI(title="NEXUS CLIPS AI")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")

@app.get("/api/status")
def status():
    return {"status": "online", "message": "NEXUS CLIPS AI está no ar"}

@app.post("/api/clips")
async def create_clips(video: UploadFile = File(...), duration: int = 60):
    if duration not in (60, 75, 90):
        raise HTTPException(400, "Duração inválida")
    ext = Path(video.filename or "video.mp4").suffix.lower()
    if ext not in (".mp4", ".mov", ".mkv", ".webm"):
        raise HTTPException(400, "Formato não suportado")
    name = f"{uuid.uuid4().hex}{ext}"
    source = UPLOADS / name
    source.write_bytes(await video.read())
    # Creates up to five consecutive segments; this is not AI viral-moment detection.
    results = []
    for i in range(5):
        out = OUTPUTS / f"{source.stem}_corte_{i+1}.mp4"
        start = i * duration
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-i", str(source),
            "-t", str(duration), "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", str(out)
        ]
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode == 0 and out.exists() and out.stat().st_size:
            results.append({"name": out.name, "url": f"/api/download/{out.name}"})
        else:
            break
    if not results:
        raise HTTPException(500, "Não foi possível gerar cortes. Verifique se o vídeo tem duração suficiente.")
    return {"clips": results, "note": "Cortes sequenciais; ainda não há seleção automática de momentos virais."}

@app.get("/api/download/{filename}")
def download(filename: str):
    path = OUTPUTS / Path(filename).name
    if not path.exists():
        raise HTTPException(404, "Arquivo não encontrado")
    return FileResponse(path, filename=path.name, media_type="video/mp4")
