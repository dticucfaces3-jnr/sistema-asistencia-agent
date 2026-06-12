import asyncio
import sys
import os
import webbrowser

# Cargar variables de entorno desde .env si existe antes de importar módulos de la app
def load_dotenv(dotenv_path=".env"):
    if os.path.exists(dotenv_path):
        try:
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().strip('"').strip("'")
                        os.environ[key] = val
        except Exception as e:
            print(f"⚠️ Error al leer archivo .env: {e}")

# Cargar desde la carpeta de ejecución actual y desde la carpeta raíz del agente
load_dotenv()
agent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(agent_dir, ".env"))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database.sqlite import init_db
from app.api.routes.biomini import router as biomini_router, sync_huellas_from_backend
from app.services.biomini import biomini_service, hardware_status

def get_resource_path(relative_path):
    """Obtiene la ruta absoluta para los recursos incluidos en el ejecutable de PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    # Busca relativo a la raíz del agente (padre del directorio 'app')
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)

async def hardware_checker():
    """Tarea en segundo plano para verificar periódicamente el estado del hardware."""
    while True:
        try:
            hardware_status["connected"] = biomini_service.is_connected()
        except Exception:
            hardware_status["connected"] = False
        await asyncio.sleep(0.5)

def abrir_navegador():
    try:
        webbrowser.open("http://localhost:8000")
    except Exception as e:
        print(f"⚠️ No se pudo abrir el navegador automáticamente: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lógica de startup
    init_db()
    sync_huellas_from_backend()
    # Iniciar la tarea en background
    asyncio.create_task(hardware_checker())
    # Abrir el navegador en diferido
    asyncio.get_event_loop().call_later(1.5, abrir_navegador)
    yield

app = FastAPI(
    title="Agente Local Suprema BioMini",
    version="1.0.0",
    lifespan=lifespan
)

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(biomini_router)

# Servir Frontend en la raíz
dist_path = get_resource_path("dist")
if os.path.exists(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")
else:
    print(f"⚠️ Advertencia: No se encontró la carpeta estática del frontend en '{dist_path}'. El frontend no estará disponible de forma unificada.")

if __name__ == "__main__":
    import uvicorn
    # Al pasar la instancia directa 'app', uvicorn no necesita importar el módulo de forma dinámica
    uvicorn.run(app, host="localhost", port=8000)
