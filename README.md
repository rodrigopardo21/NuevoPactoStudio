# NuevoPactoStudio - Transcriptor y Subtitulador de Sermones

Este proyecto transcribe automáticamente sermones de video a texto utilizando la API de AssemblyAI.
Genera audio extraído, transcripciones detalladas con marcas de tiempo y subtítulos perfectamente sincronizados (SRT).

## Características

- Extracción de audio de videos
- Transcripción automática utilizando AssemblyAI
- Generación de subtítulos SRT con sincronización precisa a nivel de palabra
- Organización automática de archivos por fecha
- Múltiples formatos de salida (JSON, TXT, SRT)
- Interfaz amigable con colores para mejor visualización
- Sistema de edición y actualización de transcripciones

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
  - `recortar_video.py`: Herramienta para recortar videos originales
  - `transcribe.py`: Script principal de transcripción
  - `actualizar_transcripcion.py`: Actualiza todos los archivos tras editar el JSON

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

## Flujo de trabajo completo

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

### 3. Editar la transcripción (cuando hay errores)

1. Localiza el archivo JSON en la carpeta `data/output/sermon_DDMMAA_XX/json/`
2. Ábrelo con un editor como VS Code
3. Busca la sección `segments` y edita el texto de los segmentos que contienen errores
4. Guarda el archivo JSON

### 4. Actualizar todos los archivos tras la edición

```bash
python src/actualizar_transcripcion.py
```

Este script:
- Detecta automáticamente la transcripción más reciente
- Sincroniza las secciones del JSON basándose en tus ediciones
- Crea copias de respaldo de los archivos originales
- Actualiza todos los archivos (JSON, TXT y SRT) con tus correcciones

## Resultados

Después de la transcripción, encontrarás los siguientes archivos en la carpeta `data/output/sermon_DDMMAA_XX/`:

- Audio extraído (MP3)
- Transcripción completa con marcas de tiempo (JSON)
- Texto plano para edición (TXT)
- Transcripción detallada con marcas de tiempo (TXT)
- Archivo de subtítulos SRT perfectamente sincronizado

## Guía para editar transcripciones

### 1. Estructura del JSON

El archivo JSON contiene:
- `text`: Texto completo de la transcripción
- `segments`: Fragmentos de texto con marcas de tiempo
- `words`: Palabras individuales con marcas de tiempo precisas

### 2. Cómo editar correctamente

- Abre el archivo JSON en VS Code (u otro editor)
- Localiza la sección `segments`
- Encuentra y corrige el texto en los segmentos donde hay errores
- Guarda el archivo
- Ejecuta `python src/actualizar_transcripcion.py`

### 3. Ejemplo de edición

Si la transcripción dice "enmendadme de mis pecados" pero debería ser "arrepentidme de mis pecados":

1. Localiza ese segmento en el JSON:
```json
{
  "start": 125000,
  "end": 129500,
  "text": "enmendadme de mis pecados",
  "speaker": "A"
}
```

2. Corrige el texto:
```json
{
  "start": 125000,
  "end": 129500,
  "text": "arrepentidme de mis pecados",
  "speaker": "A"
}
```

3. Guarda el archivo y ejecuta el actualizador

## Notas

- La calidad de la transcripción depende de la claridad del audio
- El sistema puede manejar archivos de audio/video largos
- Se recomienda revisar y corregir manualmente las transcripciones para mayor precisión
- Las ediciones solo deben hacerse en los textos, no en las marcas de tiempo
- El script de actualización sobrescribe los archivos existentes sin crear copias de respaldo