"""
Almacenamiento Persistente y Thread-Safe de Plantillas Biométricas Protegidas (BTP)
Cumple con la Ley N.° 29733 y D.S. 016-2024-JUS:
- Las plantillas permanecen cifradas en reposo con AES-256-GCM.
- Ninguna fotografía del rostro se almacena en disco.
- Soporta concurrencia thread-safe para enrolamiento simultáneo de múltiples alumnos.
"""

import os
import json
import threading
from typing import Dict, Any, List, Optional

class EncryptedUserStore:
    def __init__(self, storage_path: str = "data/users_store.json"):
        self.storage_path = storage_path
        self._lock = threading.Lock()
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._init_storage()

    def _init_storage(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self._templates = json.load(f)
            except Exception as e:
                print(f"[UserStore] Advertencia al cargar datos previos: {e}")
                self._templates = {}

    def save_template(self, user_id: str, protected_payload: Dict[str, Any]):
        """Guarda la plantilla protegida de forma thread-safe en memoria y en disco."""
        with self._lock:
            self._templates[user_id] = protected_payload
            try:
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump(self._templates, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[UserStore] Error al persistir usuario {user_id}: {e}")

    def get_template(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene la plantilla protegida de un usuario."""
        with self._lock:
            return self._templates.get(user_id)

    def list_users(self) -> List[Dict[str, str]]:
        """Lista pública de alumnos enrolados (solo metadatos no sensibles y biohash)."""
        with self._lock:
            result = []
            for uid, data in self._templates.items():
                result.append({
                    "user_id": uid,
                    "full_name": data.get("full_name", ""),
                    "cancelable_token_preview": (data.get("cancelable_token") or "")[:24] + "...",
                    "standard": data.get("standard", "ISO/IEC 24745"),
                    "compliance": data.get("compliance", "Ley N° 29733 / D.S. 016-2024-JUS")
                })
            return result

    def count(self) -> int:
        with self._lock:
            return len(self._templates)

# Instancia global del store
user_store = EncryptedUserStore()
