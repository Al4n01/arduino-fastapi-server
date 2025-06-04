from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware # type: ignore
import os
import subprocess
import uuid

app = FastAPI()

# Habilitar CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "sketches"

@app.post("/upload")
async def upload_code(code: str = Form(...)):
    sketch_id = str(uuid.uuid4())[:8]
    sketch_path = os.path.join(UPLOAD_DIR, sketch_id)
    os.makedirs(sketch_path, exist_ok=True)
    
    ino_path = os.path.join(sketch_path, f"{sketch_id}.ino")
    
    with open(ino_path, "w") as f:
        f.write(code)
    
    try:
        compile_result = subprocess.run(
            ["arduino-cli", "compile", "--fqbn", "arduino:avr:uno", ino_path],
            capture_output=True,
            text=True
        )
        if compile_result.returncode != 0:
            return {"status": "error", "message": compile_result.stderr}
        
        upload_result = subprocess.run(
            ["arduino-cli", "upload", "-p", "/dev/ttyUSB0", "--fqbn", "arduino:avr:uno", ino_path],
            capture_output=True,
            text=True
        )
        if upload_result.returncode != 0:
            return {"status": "error", "message": upload_result.stderr}
        
        return {"status": "success", "message": "Código subido correctamente"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
