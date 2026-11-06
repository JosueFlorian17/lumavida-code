"""
Gestor de Túnel Público Seguro (Cloudflare Tunnel)
Permite compartir el servidor local a cualquier red externa / Internet con HTTPS válido,
procesando toda la computación biométrica en la PC anfitriona.
"""

import os
import re
import sys
import time
import subprocess
import threading
from typing import Optional

class CloudflareTunnelManager:
    def __init__(self, port: int = 8000, binary_path: str = None):
        self.port = port
        self.binary_path = binary_path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "tools", "cloudflared.exe")
        self.process: Optional[subprocess.Popen] = None
        self.public_url: Optional[str] = None
        self._url_event = threading.Event()

    def start(self, timeout_sec: int = 15) -> Optional[str]:
        """
        Inicia cloudflared en segundo plano y extrae la URL pública HTTPS asignada.
        Si el binario no existe, lo descarga automáticamente de los releases oficiales de Cloudflare.
        """
        if not os.path.exists(self.binary_path):
            print(f"[Tunnel] Descargando binario oficial portable cloudflared en: {self.binary_path}...")
            try:
                import urllib.request
                os.makedirs(os.path.dirname(self.binary_path), exist_ok=True)
                download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
                urllib.request.urlretrieve(download_url, self.binary_path)
                print("[Tunnel] Descarga completada exitosamente.")
            except Exception as e:
                print(f"[Tunnel] Error al descargar cloudflared: {e}")
                return None

        cmd = [
            self.binary_path,
            "tunnel",
            "--url", f"http://127.0.0.1:{self.port}",
            "--no-autoupdate"
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace"
            )

            # Cloudflared escribe sus logs de conexión y la URL en stderr
            t = threading.Thread(target=self._monitor_output, daemon=True)
            t.start()

            # Esperar a que la URL esté disponible
            if self._url_event.wait(timeout=timeout_sec):
                return self.public_url
            else:
                print("[Tunnel] Tiempo de espera agotado para obtener URL de Cloudflare.")
                return None

        except Exception as e:
            print(f"[Tunnel] Error al iniciar túnel: {e}")
            return None

    def _monitor_output(self):
        url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        for line in self.process.stderr:
            match = url_pattern.search(line)
            if match and not self.public_url:
                self.public_url = match.group(0)
                self._url_event.set()
                break

    def stop(self):
        """Detiene el proceso del túnel de forma limpia."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
