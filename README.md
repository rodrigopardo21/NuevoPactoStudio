# NuevoPactoStudio - Transcriptor, Subtitulador y Extractor de Sermones

Este proyecto permite procesar sermones en video para generar transcripciones detalladas y extraer segmentos impactantes para la creación de reels. Utiliza la API de AssemblyAI para la transcripción automática y la API de Claude para el análisis inteligente del contenido.

## Características

- Extracción de audio de videos
- Transcripción automática utilizando AssemblyAI
- Generación de subtítulos SRT con sincronización precisa a nivel de palabra
- Organización automática de archivos por fecha
- Múltiples formatos de salida (JSON, TXT, SRT)
- Interfaz amigable con colores para mejor visualización
- Corrección de transcripciones mediante edición del JSON original
- **NUEVO**: Extracción inteligente de segmentos para reels con la API de Claude
  - Análisis avanzado del contenido para identificar ideas impactantes
  - Generación automática de clips de audio para cada segmento
  - Puntuación y clasificación de segmentos por impacto teológico

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
    - `reels/`: **NUEVO** - Segmentos extraídos para reels
      - `audio/`: Clips de audio extraídos para cada segmento
      - `text/`: Archivos de texto y subtítulos para cada segmento
      - `reel_segments.json`: Datos detallados de todos los segmentos extraídos
- `src/`: Scripts y código fuente
  - `recortar_video.py`: Herramienta para recortar videos originales
  - `transcribe.py`: Script principal de transcripción
  - `fix_srt.py`: Script para corregir errores en las transcripciones y generar nuevos SRT
  - `extract_reels.py`: **NUEVO** - Script para extraer segmentos impactantes para reels
- `backup/`: Copias de seguridad de archivos importantes

## Requisitos

- Python 3.12.2 o superior
- ffmpeg (instalado en el sistema)
- Cuenta y API Key de AssemblyAI
- Cuenta y API Key de Anthropic (Claude)
- Dependencias de Python listadas en `requirements.txt`

## Instalación

1. Clona este repositorio
2. Crea un entorno virtual e instala las dependencias:

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Crea un archivo `.env` en la raíz del proyecto con tus API keys:

```
ASSEMBLYAI_API_KEY=tu_clave_api_de_assemblyai
ANTHROPIC_API_KEY=tu_clave_api_de_claude
```

## Flujo de trabajo

### 1. Recortar el video original

```bash
python src/recortar_video.py
```

Este script te guiará para:
- Seleccionar un video desde `source_video/`
- Definir los tiempos de inicio y fin
- Recortar y guardar en `data/input/`

### 2. Transcribir el video recortado

```bash
python src/transcribe.py
```

Este script te guiará para:
- Seleccionar un video desde `data/input/`
- Extraer el audio
- Enviar a AssemblyAI para transcripción
- Guardar todos los archivos generados (audio, JSON, TXT y SRT)

### 3. Corregir errores en la transcripción

```bash
python src/fix_srt.py
```

Este script te permite:
- Seleccionar el archivo JSON de una transcripción existente
- Abrir el editor Code para corregir palabras mal transcritas en la sección "words"
- Generar automáticamente un nuevo archivo SRT una vez realizadas las correcciones
- Solucionar problemas con palabras incorrectas o mal interpretadas por el transcriptor

### 4. Extraer segmentos para reels (NUEVO)

```bash
python src/extract_reels.py
```

Este script te permite:
- Seleccionar un sermón transcrito de la lista disponible
- Analizar automáticamente el contenido usando la API de Claude
- Identificar segmentos impactantes y teológicamente relevantes
- Extraer clips de audio para cada segmento
- Generar archivos de texto y subtítulos para cada reel
- Ordenar los segmentos por puntuación de relevancia

## Resultados

### Después de la transcripción:

- Audio extraído (MP3)
- Transcripción completa con marcas de tiempo (JSON)
- Texto plano para edición (TXT)
- Transcripción detallada con marcas de tiempo (TXT)
- Archivo de subtítulos SRT perfectamente sincronizado

### Después de la extracción de reels:

- Clips de audio individuales para cada segmento (MP3)
- Archivos de texto explicativos para cada segmento (TXT)
- Archivos de subtítulos para cada segmento (SRT)
- JSON con datos detallados de todos los segmentos

## Notas

- La calidad de la transcripción depende de la claridad del audio
- El sistema puede manejar archivos de audio/video largos
- La API de AssemblyAI proporciona transcripciones precisas en español con detección de hablantes
- Los subtítulos SRT generados tienen sincronización precisa a nivel de palabra
- La API de Claude analiza el contenido teológico y extrae las ideas más impactantes
- Los segmentos extraídos son ideas completas que funcionan de manera autónoma