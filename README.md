# NuevoPactoStudio - Transcriptor de Sermones

Este proyecto transcribe automáticamente sermones de video a texto utilizando la API de Whisper de OpenAI. Genera archivos de audio segmentados, transcripciones en formato JSON (con marcas de tiempo) y texto plano para revisar y crear contenido para RRSS.

## Estructura del Proyecto

- `source_videos/`: Videos originales sin recortar
- `data/input/`: Videos recortados listos para transcribir
- `data/output/`: Transcripciones generadas (organizadas por fecha)
- `src/transcriber/`: Código fuente del transcriptor
- `venv/`: Entorno virtual de Python

## Requisitos

- Python 3.12.2
- ffmpeg
- OpenAI API Key

## Uso

1. Coloca el video original en `source_videos/`
2. Recorta el sermón usando ffmpeg
3. Ejecuta el script de transcripción
4. Los resultados se guardan en `data/output/sermon_DDMMAA_XX/` (donde XX es un contador incremental)
