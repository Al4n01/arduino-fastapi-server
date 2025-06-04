from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware # type: ignore
import os
import subprocess
import uuid
import shutil # Importar shutil para limpiar directorios

app = FastAPI()

# Habilitar CORS para el frontend
# En producción, deberías restringir 'allow_origins' a la URL de tu frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# En entornos de nube como Render, /tmp es el lugar recomendado para archivos temporales.
# Los archivos guardados aquí no son persistentes entre reinicios del servicio.
UPLOAD_DIR = "/tmp/sketches" 

@app.post("/upload")
async def upload_code(code: str = Form(...)):
    # Genera un ID único para cada sketch para evitar colisiones
    sketch_id = str(uuid.uuid4())[:8]
    # Crea un directorio temporal para el sketch actual
    current_sketch_path = os.path.join(UPLOAD_DIR, sketch_id)
    
    try:
        # Crea el directorio si no existe
        os.makedirs(current_sketch_path, exist_ok=True)
        
        # Define la ruta completa del archivo .ino
        ino_path = os.path.join(current_sketch_path, f"{sketch_id}.ino")
        
        # Escribe el código recibido en el archivo .ino
        with open(ino_path, "w") as f:
            f.write(code)
        
        # --- Parte de compilación con arduino-cli ---
        # Este comando intenta compilar el sketch para la placa Arduino Uno.
        # Render debe tener 'arduino-cli' y el core 'arduino:avr' instalados en el entorno.
        
        # Define el directorio de datos para arduino-cli.
        # Usamos os.environ.get para leer la variable de entorno ARDUINO_DATA_DIR,
        # proporcionando un valor predeterminado si no está configurada (útil para desarrollo local).
        arduino_data_dir = os.environ.get("ARDUINO_DATA_DIR", "/tmp/.arduino15")

        compile_command = [
            "arduino-cli",
            "--config-dir", arduino_data_dir, # ¡CORREGIDO: Ahora usa --config-dir para el comando compile!
            "compile", 
            "--fqbn", "arduino:avr:uno", # Fully Qualified Board Name para Arduino Uno
            ino_path
        ]
        
        # Ejecuta el comando de compilación
        compile_result = subprocess.run(
            compile_command,
            capture_output=True, # Captura la salida estándar y de error
            text=True            # Decodifica la salida como texto
        )
        
        # Verifica si la compilación falló (código de retorno distinto de 0)
        if compile_result.returncode != 0:
            return {
                "status": "error",
                "message": "Compilation failed.",
                "stderr": compile_result.stderr, # Mensajes de error de la compilación
                "stdout": compile_result.stdout  # Salida estándar de la compilación
            }
        
        # ***** IMPORTANTE: LA PARTE DE 'UPLOAD' HA SIDO ELIMINADA/COMENTADA *****
        # Un servidor en la nube NO puede acceder a un puerto USB físico como /dev/ttyUSB0.
        # Si esta sección estuviera activa, el despliegue fallaría o la API daría un error.
        #
        # upload_result = subprocess.run(
        #     ["arduino-cli", "upload", "-p", "/dev/ttyUSB0", "--fqbn", "arduino:avr:uno", ino_path],
        #     capture_output=True,
        #     text=True
        # )
        # if upload_result.returncode != 0:
        #     return {"status": "error", "message": upload_result.stderr}
        
        # Si la compilación fue exitosa, devuelve un mensaje de éxito
        return {
            "status": "success", 
            "message": "Code compiled successfully. You can now copy the code to upload manually to your Arduino.",
            "stdout": compile_result.stdout # Incluye la salida de la compilación para el usuario
        }
    except FileNotFoundError as e:
        # Maneja el error si 'arduino-cli' no se encuentra en el servidor
        return {
            "status": "error", 
            "message": f"Server error: Command 'arduino-cli' not found. Ensure it's installed in the environment. ({e})",
            "stderr": str(e)
        }
    except Exception as e:
        # Captura cualquier otro error inesperado durante el procesamiento
        return {
            "status": "error", 
            "message": f"An unexpected server error occurred: {str(e)}",
            "stderr": str(e)
        }
    finally:
        # Asegura que el directorio temporal se limpie al finalizar,
        # independientemente de si hubo un error o no.
        if os.path.exists(current_sketch_path):
            shutil.rmtree(current_sketch_path)
