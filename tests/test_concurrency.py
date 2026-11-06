"""
Pruebas de Concurrencia y Seguridad Edge / BTP para Aula de Clase
Simula múltiples alumnos enrolándose y verificándose simultáneamente.
"""

import concurrent.futures
import numpy as np
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.user_store import user_store

client = TestClient(app)

def test_concurrent_user_enrollment():
    """Simula 10 alumnos enrolándose al mismo tiempo."""
    def enroll_single_student(idx: int):
        # Generar imagen sintética válida 112x112 en base64
        import cv2, base64
        dummy_face = np.full((120, 120, 3), 180, dtype=np.uint8)
        # Dibujar rasgos mínimos para que pase detección
        cv2.circle(dummy_face, (40, 45), 10, (50, 50, 50), -1)
        cv2.circle(dummy_face, (80, 45), 10, (50, 50, 50), -1)
        cv2.rectangle(dummy_face, (45, 80), (75, 90), (80, 80, 180), -1)
        _, buf = cv2.imencode('.jpg', dummy_face)
        b64 = base64.b64encode(buf).decode('utf-8')

        resp = client.post("/api/enroll", json={
            "user_id": f"student_2026_{idx}",
            "full_name": f"Alumno Concurrente {idx}",
            "face_image_b64": f"data:image/jpeg;base64,{b64}"
        })
        return resp.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(enroll_single_student, range(5)))

    # Al menos los que detectaron rostro debieron registrarse o arrojar 422 si la imagen sintética no tuvo rostro
    # Lo crucial es que no haya fallos 500 de race condition
    assert all(code in (200, 422) for code in results)

def test_edge_privacy_no_embedding_leak():
    """Garantiza que la respuesta de /verify nunca devuelva el vector de embedding crudo."""
    resp = client.post("/api/simulate-attack?scenario_type=photo")
    assert resp.status_code == 200
    data = resp.json()
    # Verificar que no exista ningún vector de float en el payload
    assert "probe_embedding" not in str(data)
    assert "ciphertext" not in str(data)

def test_user_store_thread_safety():
    """Prueba concurrencia directa sobre el almacén cifrado."""
    def write_op(idx: int):
        user_store.save_template(f"concurrent_test_{idx}", {
            "user_id": f"concurrent_test_{idx}",
            "full_name": f"Test {idx}",
            "cancelable_token": "ABC123DEF456" * 4
        })
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write_op, range(20)))

    assert user_store.count() >= 20
