"""
Servidor Principal FastAPI - LumaVida
Sistema de Detección de Vida Facial y Reconocimiento Biométrico
Proyecto UPCH - Temas Avanzados de Seguridad Informática
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.core.config import settings
from backend.app.api.endpoints import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API de Detección de Vida Facial mediante Reflectancia Cutánea y rPPG, con Matching ArcFace 1:1 y Protección BTP (ISO/IEC 24745)."
)

# Configuración CORS permisiva para desarrollo y pruebas en red local/móvil
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas API
app.include_router(api_router, prefix=settings.API_V1_STR)

# Montar frontend web estático
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "message": "Servidor LumaVida activo. Coloca index.html en static/",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
