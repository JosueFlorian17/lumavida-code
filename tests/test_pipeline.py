"""
Pruebas Unitarias del Pipeline de Seguridad Biométrica LumaVida
Verifica que cada componente cumpla con las especificaciones del documento UPCH.
"""

import numpy as np
import pytest
from backend.app.services.reflectance import SkinReflectanceAnalyzer
from backend.app.services.rppg import RPPGAnalyzer
from backend.app.services.liveness_fusion import LivenessDecisionEngine
from backend.app.services.arcface_matcher import ArcFaceMatcher
from backend.app.services.btp_security import BiometricTemplateProtector

def test_skin_reflectance_analyzer_bona_fide():
    analyzer = SkinReflectanceAnalyzer()
    n = 30
    # Simular estímulo de color variante
    t = np.linspace(0, 2, n)
    proj = [{"r": 200 + 40 * np.sin(2 * np.pi * 1.5 * ti),
             "g": 120 + 30 * np.sin(2 * np.pi * 1.5 * ti),
             "b": 100 + 20 * np.sin(2 * np.pi * 1.5 * ti),
             "timestamp": ti * 1000} for ti in t]
    
    # Simular piel reactiva con correlación y ligera atenuación difusa
    obs = [{"r": p["r"] * 0.8 + np.random.normal(0, 1),
            "g": p["g"] * 0.75 + np.random.normal(0, 1),
            "b": p["b"] * 0.7 + np.random.normal(0, 1),
            "timestamp": p["timestamp"]} for p in proj]
    
    res = analyzer.analyze_reflectance(proj, obs)
    assert res["correlation"] > 0.35
    assert res["specular_ratio"] < 0.30
    assert res["is_live"] is True

def test_skin_reflectance_analyzer_static_photo():
    analyzer = SkinReflectanceAnalyzer()
    n = 30
    proj = [{"r": 255 if i % 2 == 0 else 0, "g": 100, "b": 150, "timestamp": i * 66} for i in range(n)]
    # Imagen de papel fotográfico mate no reactivo (brillo fijo constante)
    obs = [{"r": 120.0, "g": 110.0, "b": 95.0, "timestamp": i * 66} for i in range(n)]

    res = analyzer.analyze_reflectance(proj, obs)
    assert res["is_live"] is False
    assert res["correlation"] < 0.20

def test_rppg_pulse_extraction_bona_fide():
    analyzer = RPPGAnalyzer(fps=30.0)
    # Generar señal con pulso cardíaco real a ~72 BPM (1.2 Hz)
    fs = 30.0
    duration = 2.0
    t = np.linspace(0, duration, int(fs * duration))
    hr_freq = 1.2 # 72 BPM
    
    # Onda pulsátil hemodinámica con absorción microvascular diferencial (mayor en verde/rojo que en azul)
    pulse_g = 1.8 * np.sin(2 * np.pi * hr_freq * t)
    pulse_r = 0.8 * np.sin(2 * np.pi * hr_freq * t)
    pulse_b = 0.1 * np.sin(2 * np.pi * hr_freq * t)
    
    rgb_series = []
    for i in range(len(t)):
        r = 160.0 + pulse_r[i] + np.random.normal(0, 0.05)
        g = 130.0 + pulse_g[i] + np.random.normal(0, 0.05)
        b = 100.0 + pulse_b[i] + np.random.normal(0, 0.05)
        rgb_series.append((r, g, b))

    res = analyzer.analyze_rppg(rgb_series, sampling_rate=fs)
    assert res["is_live"] is True
    assert 60.0 <= res["bpm"] <= 85.0
    assert res["snr"] >= 0.38

def test_rppg_pulse_extraction_spoof_flat():
    analyzer = RPPGAnalyzer(fps=30.0)
    rng = np.random.default_rng(42)
    # Foto estática sin modulación pulsátil (solo ruido residual de sensor)
    rgb_series = [(150.0 + rng.normal(0, 0.005),
                   120.0 + rng.normal(0, 0.005),
                   90.0 + rng.normal(0, 0.005)) for _ in range(60)]

    res = analyzer.analyze_rppg(rgb_series, sampling_rate=30.0)
    assert res["is_live"] is False

def test_btp_template_encryption_and_biohash():
    protector = BiometricTemplateProtector()
    user_id = "test_user_72849102"
    
    # Generar vector aleatorio 512-D
    original_embedding = np.random.randn(512).astype(np.float32)
    original_embedding /= np.linalg.norm(original_embedding)

    # 1. Proteger plantilla
    protected = protector.protect_template(original_embedding, user_id)
    assert "ciphertext_b64" in protected
    assert "cancelable_token" in protected
    assert len(protected["cancelable_token"]) > 32

    # 2. Desproteger en TEE simulation
    decrypted_embedding = protector.unprotect_template(protected)
    np.testing.assert_allclose(original_embedding, decrypted_embedding, atol=1e-5)

def test_arcface_matcher_cosine_similarity():
    matcher = ArcFaceMatcher(threshold=0.62)
    # Probar que vectores idénticos dan similitud 1.0
    v1 = np.random.randn(512).astype(np.float32)
    v1 /= np.linalg.norm(v1)

    sim = matcher.cosine_similarity(v1, v1)
    assert pytest.approx(sim, 0.001) == 1.0

    # Vectores ortogonales deben dar ~0.0
    v2 = np.random.randn(512).astype(np.float32)
    v2 -= np.dot(v2, v1) * v1
    v2 /= np.linalg.norm(v2)
    sim_ortho = matcher.cosine_similarity(v1, v2)
    assert abs(sim_ortho) < 0.05

def test_liveness_decision_engine():
    engine = LivenessDecisionEngine()
    
    # Caso 1: Vivo
    ref_bona = {"is_live": True, "reflectance_score": 0.8, "specular_ratio": 0.05, "correlation": 0.65}
    rppg_bona = {"is_live": True, "confidence": 0.85, "snr": 1.8, "bpm": 75.0}
    dec_bona = engine.evaluate(ref_bona, rppg_bona)
    assert dec_bona["is_bona_fide"] is True
    assert dec_bona["attack_type"] == "NONE"

    # Caso 2: Pantalla
    ref_screen = {"is_live": False, "reflectance_score": 0.2, "specular_ratio": 0.45, "correlation": 0.50}
    rppg_screen = {"is_live": False, "confidence": 0.2, "snr": 0.6, "bpm": 120.0}
    dec_screen = engine.evaluate(ref_screen, rppg_screen)
    assert dec_screen["is_bona_fide"] is False
    assert dec_screen["attack_type"] == "SPOOF_SCREEN_REPLAY"
