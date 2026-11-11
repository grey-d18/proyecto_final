#!/usr/bin/env bash
# Enciende la versión de PRUEBA en vivo: la API corre en esta laptop y un túnel gratuito de
# Cloudflare la conecta a internet, sin cuenta ni tarjeta. La página (GitHub Pages) le habla
# a la API por ese túnel. Mientras esta terminal esté abierta, la app funciona desde cualquier
# celular; al cerrarla (Ctrl+C) se apaga todo.
#
# Uso, desde la carpeta del proyecto:   bash scripts/demo_en_vivo.sh
# Necesita: brew install cloudflared   (y la API instalada, ver README «Cómo correrlo»)
set -euo pipefail
cd "$(dirname "$0")/.."

PAGINA="${PAGINA:-https://grey-d18.github.io/proyecto_final/}"
PUERTO=8000

command -v cloudflared >/dev/null || { echo "Falta cloudflared. Instálalo con: brew install cloudflared"; exit 1; }

PROCESOS=()
REGISTRO_TUNEL=$(mktemp)
apagar() { kill "${PROCESOS[@]}" 2>/dev/null || true; rm -f "$REGISTRO_TUNEL"; }
trap apagar EXIT

# 1. La API (si ya estaba encendida en otra terminal, se usa esa)
if curl -s "http://localhost:$PUERTO/salud" >/dev/null; then
  echo "La API ya estaba encendida en el puerto $PUERTO."
else
  echo "Encendiendo la API (Whisper tarda unos segundos en cargar)…"
  .venv/bin/uvicorn api.main:app --port "$PUERTO" --log-level warning &
  PROCESOS+=($!)
fi

# 2. El túnel: Cloudflare da una dirección pública temporal (https://…trycloudflare.com)
echo "Abriendo el túnel…"
cloudflared tunnel --url "http://localhost:$PUERTO" --no-autoupdate 2>"$REGISTRO_TUNEL" &
PROCESOS+=($!)

TUNEL=""
for _ in $(seq 1 60); do
  TUNEL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$REGISTRO_TUNEL" | head -1 || true)
  [ -n "$TUNEL" ] && break
  sleep 1
done
[ -n "$TUNEL" ] || { echo "No se pudo abrir el túnel. Revisa tu internet e inténtalo otra vez."; exit 1; }

ENLACE="${PAGINA}?api=${TUNEL}"
echo
echo "Listo. Comparte este enlace (o el código QR) mientras dure la prueba:"
echo
echo "    $ENLACE"
echo
uvx --quiet --from "qrcode==8.2" qr "$ENLACE" 2>/dev/null || true
echo "Para apagar todo: Ctrl+C"
wait
