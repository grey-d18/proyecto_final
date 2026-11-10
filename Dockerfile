# Receta para publicar la API en Hugging Face Spaces (tipo «Docker», plan gratuito con CPU).
# Hugging Face la construye solo; también sirve para probarla con Docker en tu laptop:
#     docker build -t reciclavoz-api . && docker run -p 7860:7860 reciclavoz-api
FROM python:3.12-slim

# Hugging Face corre la app con un usuario sin permisos de administrador (número 1000).
RUN useradd -m -u 1000 usuario
WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

# Descargamos Whisper al construir, no cuando llega la primera persona.
USER usuario
ENV HOME=/home/usuario
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

# Solo lo que usa la API (el .dockerignore deja fuera secretos, la voz privada y la base local).
COPY --chown=usuario api/ api/
COPY --chown=usuario nucleo/ nucleo/
COPY --chown=usuario datos/ datos/

EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
