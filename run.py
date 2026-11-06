"""
Punto de Entrada para Despliegue en Red Local e Internet (Acceso desde Cualquier Red)
LumaVida - UPCH (Temas Avanzados de Seguridad Informática)

Crea un túnel público seguro HTTPS (Cloudflare Tunnel) para que alumnos y evaluadores
puedan acceder desde cualquier red externa o celular con cámara habilitada al instante,
mientras todo el procesamiento biométrico pesado se ejecuta 100% en esta PC.
"""

import sys
import os
import atexit
import signal
import uvicorn
from backend.app.core.tunnel import CloudflareTunnelManager

tunnel_manager = None

def cleanup():
    global tunnel_manager
    if tunnel_manager:
        print("\n[+] Cerrando túnel público de forma segura...")
        tunnel_manager.stop()
        tunnel_manager = None

def print_qr_code(url: str):
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        print("\n  📲 ESCANEA ESTE CÓDIGO QR CON LA CÁMARA DE TU CELULAR:\n")
        qr.print_ascii(invert=True)
    except Exception:
        pass

def main():
    global tunnel_manager
    port = 8000
    enable_tunnel = "--no-tunnel" not in sys.argv

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: (cleanup(), sys.exit(0)))

    public_url = None
    if enable_tunnel:
        print("\n[+] Iniciando túnel público HTTPS seguro hacia Internet...")
        tunnel_manager = CloudflareTunnelManager(port=port)
        public_url = tunnel_manager.start(timeout_sec=12)

    print("\n" + "=" * 76)
    print("🎓 SISTEMA LUMAVIDA - ACCESO GLOBAL MULTI-RED (INTERNET + LAN)")
    print("   Universidad Peruana Cayetano Heredia (UPCH)")
    print("   Detección de Vida Facial (Reflectancia + rPPG) + ArcFace 1:1 + BTP ISO 24745")
    print("   * Todo el procesamiento de IA y biometría se ejecuta en tu PC anfitriona *")
    print("=" * 76)

    print(f"\n[+] Servidor Host Local (Tu PC):        http://localhost:{port}")

    if public_url:
        print("\n" + "★" * 76)
        print(f"  🌐 ENLACE PÚBLICO PARA OTRAS REDES / CUALQUIER LUGAR (HTTPS Oficial):")
        print(f"     👉  {public_url}")
        print("★" * 76)
        print("  ✓ Certificado SSL oficial reconocido por Android e iOS.")
        print("  ✓ Habilita la cámara frontal de cualquier celular sin advertencias.")
        print_qr_code(public_url)
    else:
        print("[!] Modo túnel no activo. Para habilitarlo, ejecuta sin flag --no-tunnel.")

    print(f"\n[+] Documentación Swagger API:          http://localhost:{port}/docs")
    print("-" * 76)
    print("⚡ Concurrencia activa: Múltiples alumnos pueden conectarse simultáneamente.")
    print("🛡️ Seguridad Edge & BTP: Embeddings cifrados con AES-256-GCM. Fotos nunca guardadas.")
    print("=" * 76 + "\n")

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

if __name__ == "__main__":
    main()
