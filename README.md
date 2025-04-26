# NuevoPactoStudio - Transcriptor y Subtitulador de Sermones

Este proyecto transcribe automáticamente sermones de video a texto utilizando la API de AssemblyAI.
Genera audio extraído, transcripciones detalladas con marcas de tiempo y subtítulos perfectamente sincronizados (SRT).

## Características

- Extracción de audio de videos
- Transcripción automática utilizando AssemblyAI
- Generación de subtítulos SRT con sincronización precisa a nivel de palabra
- Organización automática de archivos por fecha
- Múltiples formatos de salida (JSON, TXT, SRT)

## Estructura del Proyecto

- `source_video/`: Videos originales sin recortar
- `data/input/`: Videos recortados listos para transcribir
- `data/output/`: Transcripciones y archivos generados (organizados por fecha)
  - `sermon_DDMMAA_XX/`: Carpeta para cada transcripción
    - `audio/`: Archivo de audio extraído
    - `json/`: Transcripción completa en formato JSON con marcas de tiempo
    - `text/`: Archivos de texto y subtítulos
      - `*_transcript.txt`: Transcripción en texto plano
      - `*_transcript_detailed.txt`: Transcripción con marcas de tiempo
      - `*_subtitles.srt`: Archivo de subtítulos sincronizados
- `src/`: Scripts y código fuente
  - `transcribe_assemblyai.py`: Script principal de transcripción
  - `create_accurate_srt.py`: Generador de subtítulos preciso
  - `recortar_video.py`: Herramienta para recortar videos
  - `json_to_srt.py`: Conversor de JSON a SRT
  - `transcriber/`: Módulos de transcripción

## Requisitos

- Python 3.12.2 o superior
- ffmpeg (instalado en el sistema)
- Cuenta y API Key de AssemblyAI
- Dependencias de Python listadas en `requirements.txt`

## Instalación

1. Clona este repositorio
2. Crea un entorno virtual e instala las dependencias:

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Crea un archivo `.env` en la raíz del proyecto con tu API key:

```
ASSEMBLYAI_API_KEY=tu_clave_api_de_assemblyai
```

## Uso

### 1. Recortar un video para transcripción

```bash
python src/recortar_video.py
```

Este script te guiará para:
- Seleccionar un video desde `source_video/`
- Definir los tiempos de inicio y fin
- Recortar y guardar en `data/input/`

### 2. Transcribir un video y generar subtítulos

```bash
python src/transcribe_assemblyai.py
```

Este script te guiará para:
- Seleccionar un video desde `data/input/`
- Extraer el audio
- Enviar a AssemblyAI para transcripción
- Guardar todos los archivos generados

### 3. Regenerar subtítulos (opcional)

Si necesitas regenerar los subtítulos sin volver a transcribir:

```bash
python src/create_accurate_srt.py
```

## Resultados

Después de la transcripción, encontrarás los siguientes archivos en la carpeta `data/output/sermon_DDMMAA_XX/`:

- Audio extraído (MP3)
- Transcripción completa con marcas de tiempo (JSON)
- Texto plano para edición
- Transcripción detallada con marcas de tiempo
- Archivo de subtítulos SRT perfectamente sincronizado

## Notas

- La calidad de la transcripción depende de la claridad del audio
- El sistema puede manejar archivos de audio/video largos
- Se recomienda revisar y corregir manualmente las transcripciones para mayor precisión
