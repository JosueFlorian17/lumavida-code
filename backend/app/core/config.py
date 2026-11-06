# Configuración del Sistema LumaVida
# Basado en la propuesta UPCH: Temas Avanzados de Seguridad Informática

import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True)

    PROJECT_NAME: str = "LumaVida - Verificación de Vida Facial (rPPG & Reflectancia)"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Parámetros de captura y latencia (Meta ISO: < 2.0 s)
    TARGET_FPS: float = 30.0
    CHALLENGE_DURATION_SEC: float = 2.0
    MIN_FRAMES_REQUIRED: int = 30
    
    # Parámetros rPPG (Filtro fisiológico 42 - 210 BPM)
    # En ventanas ultracortas (~2s / 60 frames) con webcam RGB, el ensanchamiento espectral (leakage)
    # sitúa el SNR fisiológico típico de humanos vivos entre 0.38 y 0.75.
    RPPG_MIN_FREQ_HZ: float = 0.7   # ~42 bpm
    RPPG_MAX_FREQ_HZ: float = 3.5   # ~210 bpm
    RPPG_SNR_THRESHOLD: float = 0.38 # Umbral calibrado para ventanas cortas (< 2.5s)
    RPPG_PEAK_PROMINENCE_MIN: float = 1.8 # Relación pico / ruido medio del espectro
    
    # Parámetros de Reflectancia Cutánea (Flash Liveness)
    # Calibrado para luz ambiental de aula/habitación con compensación de latencia de cámara
    REFLECTANCE_CORRELATION_MIN: float = 0.22
    SPECULAR_SATURATION_MAX: float = 0.35
    
    # ArcFace Matching 1:1
    ARCFACE_SIMILARITY_THRESHOLD: float = 0.62 # Umbral para FMR < 0.01%
    EMBEDDING_DIM: int = 512
    
    # Biometric Template Protection (BTP - ISO/IEC 24745 & Ley 29733)
    MASTER_KEY_SECRET: str = os.getenv("LUMAVIDA_SECRET", "lumavida_upch_master_btp_key_2026_aes256")

settings = Settings()
