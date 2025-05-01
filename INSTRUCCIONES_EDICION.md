# Guía Detallada: Edición de Transcripciones

Este documento proporciona instrucciones paso a paso para editar transcripciones y regenerar todos los archivos derivados en NuevoPactoStudio.

## Visión general del proceso

El proceso de edición de transcripciones consiste en:

1. Localizar el archivo JSON que contiene la transcripción
2. Editar el texto de los segmentos que contienen errores
3. Ejecutar el script de actualización para sincronizar todos los archivos

## Instrucciones detalladas

### 1. Localizar el archivo JSON

- Navega a la carpeta del proyecto
- Entra en la carpeta `data/output`
- Encuentra la subcarpeta más reciente (formato `sermon_DDMMAA_XX`)
- Dentro de esa carpeta, entra en la subcarpeta `json`
- Abre el archivo que termina en `_transcription.json` con VS Code u otro editor

```bash
cd data/output/sermon_DDMMAA_XX/json
code nombre_del_video_transcription.json
```

### 2. Entender la estructura del JSON

El archivo JSON tiene varias secciones importantes:

- **`text`**: El texto completo de la transcripción
- **`segments`**: Array de objetos que representan fragmentos de texto con marcas de tiempo
- **`words`**: Array de objetos que representan palabras individuales con marcas de tiempo

**¡IMPORTANTE!** Solo necesitas editar la sección `segments`. El script de actualización se encargará de sincronizar el resto.

### 3. Editar los segmentos

Cada segmento tiene esta estructura:

```json
{
  "start": 125000,
  "end": 129500,
  "text": "Este es el texto del segmento",
  "speaker": "A"
}
```

Para editar:
1. Localiza el segmento que contiene el error
2. Modifica solo el valor del campo `"text"`
3. NO modifiques los valores de `start`, `end` o `speaker`
4. Guarda el archivo cuando termines

### 4. Ejecutar el script de actualización

Desde la carpeta raíz del proyecto:

```bash
python src/actualizar_transcripcion.py
```

Este script:
- Detecta automáticamente el JSON más reciente
- Crea copias de respaldo de todos los archivos
- Sincroniza todas las secciones del JSON
- Regenera los archivos TXT y SRT con tus correcciones

### 5. Verificar los resultados

Después de ejecutar el script, verifica los archivos actualizados en:
```
data/output/sermon_DDMMAA_XX/text/
```

Deberías encontrar:
- `nombre_video_transcript.txt`: Transcripción en texto plano
- `nombre_video_transcript_detailed.txt`: Transcripción con marcas de tiempo
- `nombre_video_subtitles.srt`: Archivo de subtítulos

## Consejos para la edición

### Consejos generales
- Haz correcciones pequeñas y ejecuta el actualizador con frecuencia
- El script sobrescribe los archivos existentes sin crear copias de respaldo
- Mantén la puntuación original cuando sea posible

### Errores comunes al editar JSON
- No olvides las comillas dobles alrededor de los valores de texto
- No elimines las comas que separan los segmentos
- No añadas comas después del último elemento de un array
- Asegúrate de que las llaves `{` y `}` estén correctamente emparejadas

### Ejemplo de edición correcta

**Original:**
```json
{
  "start": 125000,
  "end": 129500,
  "text": "El Señor nos invita a la oración",
  "speaker": "A"
}
```

**Corregido:**
```json
{
  "start": 125000,
  "end": 129500,
  "text": "El Señor nos invita a la adoración",
  "speaker": "A"
}
```

## Solución de problemas

### El script muestra un error relacionado con JSON
- Verifica que el JSON sea válido (no falten comillas, comas, etc.)
- Prueba con un validador de JSON en línea

### Las correcciones no aparecen en los archivos
- Asegúrate de que estás editando el archivo JSON correcto (el más reciente)
- Verifica que guardaste el archivo antes de ejecutar el script

### Deseas volver a una versión anterior
- Si necesitas volver a una versión anterior, considera usar el control de versiones (git)
- Se recomienda hacer commits frecuentes para tener puntos de recuperación

## Preguntas frecuentes

**P: ¿Tengo que editar las secciones `text` y `words` también?**
R: No, solo necesitas editar la sección `segments`. El script actualiza automáticamente las demás secciones.

**P: ¿Puedo editar las marcas de tiempo?**
R: No se recomienda. Editar las marcas de tiempo puede desincronizar los subtítulos.

**P: ¿Qué pasa si hay muchos errores en la transcripción?**
R: Para transcripciones con muchos errores, considera mejorar la calidad del audio o ajustar el entorno de grabación para futuras transcripciones.

**P: ¿Es posible regenerar solo los subtítulos?**
R: El script actualiza todos los archivos. Si necesitas regenerar solo un tipo específico, deberías modificar el script.