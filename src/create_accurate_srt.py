#!/usr/bin/env python3
"""
Script para generar archivos SRT precisos a partir de transcripciones de AssemblyAI.
Este script utiliza las marcas de tiempo a nivel de palabra para crear subtítulos perfectamente sincronizados.
"""
import os
import sys
import json
import glob
import re
from datetime import datetime

# Añadir la ruta del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def format_time_srt(milliseconds):
    """Convierte milisegundos a formato HH:MM:SS,mmm para SRT"""
    seconds = milliseconds / 1000
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    millisecs = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{millisecs:03d}"

def format_subtitle_line(text, max_chars_per_line=40):
    """
    Formatea un texto para que quepa en máximo 2 líneas de subtítulos.
    """
    if len(text) <= max_chars_per_line:
        return text
    
    # Intentar dividir por puntos naturales cerca de la mitad
    words = text.split()
    half_len = len(text) // 2
    
    # Buscar espacios cerca del punto medio
    split_index = None
    for i in range(half_len - 15, half_len + 15):
        if i >= 0 and i < len(text) and text[i] == ' ':
            split_index = i
            break
    
    # Si no encontramos un buen punto de división, dividir entre palabras
    if split_index is None:
        current_len = 0
        for i, word in enumerate(words):
            current_len += len(word) + (1 if i > 0 else 0)
            if current_len > half_len and i > 0:
                split_index = len(' '.join(words[:i]))
                break
    
    # Si aún no hay punto de división, dividir exactamente por la mitad
    if split_index is None or split_index <= 0:
        split_index = half_len
    
    # Crear las dos líneas
    line1 = text[:split_index].strip()
    line2 = text[split_index:].strip()
    
    # Limitar cada línea a la longitud máxima sin truncar con puntos suspensivos
    if len(line1) > max_chars_per_line:
        last_space = line1.rfind(' ', 0, max_chars_per_line)
        if last_space != -1:
            line1 = line1[:last_space].strip()
    
    if len(line2) > max_chars_per_line:
        last_space = line2.rfind(' ', 0, max_chars_per_line)
        if last_space != -1:
            line2 = line2[:last_space].strip()
    
    return f"{line1}\n{line2}"

def process_assemblyai_json(json_file):
    """Procesa el JSON de AssemblyAI para extraer palabras con sus marcas de tiempo"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"JSON cargado: {os.path.basename(json_file)}")
        
        # Intentar obtener palabras con marcas de tiempo
        words = []
        
        # AssemblyAI proporciona información a nivel de palabra
        if 'words' in data and data['words']:
            print(f"Encontradas {len(data['words'])} palabras con marcas de tiempo")
            words = data['words']
        else:
            # Intentar extraer directamente de la respuesta de la API
            transcript_id = data.get('transcript_id')
            
            if transcript_id:
                try:
                    import assemblyai as aai
                    from dotenv import load_dotenv
                    load_dotenv()
                    import os
                    
                    # Verificar API key
                    api_key = os.getenv("ASSEMBLYAI_API_KEY")
                    if not api_key:
                        raise ValueError("No se encontró la API key de AssemblyAI")
                    
                    # Configurar cliente
                    aai.settings.api_key = api_key
                    transcriber = aai.Transcriber()
                    
                    # Obtener transcripción completa con palabras
                    transcript = transcriber.get_transcript(transcript_id)
                    if transcript.words:
                        words = [
                            {
                                'text': word.text,
                                'start': word.start,
                                'end': word.end,
                                'confidence': word.confidence
                            }
                            for word in transcript.words
                        ]
                        print(f"Recuperadas {len(words)} palabras desde la API de AssemblyAI")
                except Exception as e:
                    print(f"Error al recuperar palabras de la API: {e}")
        
        # Si no hay palabras, intentar usar los segmentos
        if not words and 'segments' in data and data['segments']:
            print("No se encontraron palabras. Usando segmentos en su lugar.")
            return data['segments']
        
        return words
    
    except Exception as e:
        print(f"Error al procesar el archivo JSON: {e}")
        return []

def create_sentence_segments(words, max_words_per_segment=8, max_segment_duration=2500):
    """
    Crea segmentos de subtítulos a partir de palabras individuales.
    Agrupa palabras en frases naturales con puntuación o por cantidad máxima.
    """
    if not words:
        return []
    
    segments = []
    current_words = []
    current_start = None
    
    for i, word in enumerate(words):
        # Validar que la palabra tenga los campos necesarios
        if not all(k in word for k in ['text', 'start', 'end']):
            continue
        
        # Si es la primera palabra del segmento, marcar tiempo de inicio
        if not current_words:
            current_start = word['start']
        
        current_words.append(word)
        
        # Decidir si cerrar el segmento actual:
        # 1. Si la palabra termina con puntuación fuerte (.!?)
        # 2. Si la palabra termina con puntuación débil (,;:) Y hay suficientes palabras
        # 3. Si alcanzamos el máximo de palabras por segmento
        # 4. Si la duración del segmento actual supera el máximo
        # 5. Si es la última palabra
        
        create_segment = False
        
        # Verificar puntuación
        ends_with_strong_punct = word['text'].rstrip().endswith(('.', '!', '?'))
        ends_with_weak_punct = word['text'].rstrip().endswith((',', ';', ':'))
        
        # Calcular duración actual
        current_duration = word['end'] - current_start
        
        if (ends_with_strong_punct or
            (ends_with_weak_punct and len(current_words) >= 3) or
            len(current_words) >= max_words_per_segment or
            current_duration >= max_segment_duration or
            i == len(words) - 1):
            create_segment = True
        
        if create_segment:
            # Combinar las palabras en un texto
            text = ' '.join(w['text'] for w in current_words)
            
            # Crear segmento
            segments.append({
                'start': current_start,
                'end': word['end'],
                'text': text,
                'speaker': word.get('speaker', 'A')
            })
            
            # Reiniciar para el siguiente segmento
            current_words = []
            current_start = None
    
    # Eliminar duplicados y combinar segmentos muy cortos
    optimized_segments = optimize_segments(segments)
    return optimized_segments

def optimize_segments(segments, min_segment_duration=800):
    """
    Optimiza los segmentos:
    1. Elimina segmentos duplicados
    2. Combina segmentos muy cortos con el siguiente
    """
    if not segments:
        return []
    
    # Eliminar duplicados (misma marca de tiempo y texto)
    unique_segments = []
    for segment in segments:
        if not unique_segments or not (
            abs(segment['start'] - unique_segments[-1]['start']) < 100 and
            segment['text'] == unique_segments[-1]['text']
        ):
            unique_segments.append(segment)
    
    # Combinar segmentos muy cortos
    merged_segments = []
    i = 0
    while i < len(unique_segments):
        segment = unique_segments[i]
        
        # Si no es el último segmento y es muy corto
        if i < len(unique_segments) - 1 and (segment['end'] - segment['start']) < min_segment_duration:
            next_segment = unique_segments[i + 1]
            
            # Combinar con el siguiente segmento
            merged_segments.append({
                'start': segment['start'],
                'end': next_segment['end'],
                'text': f"{segment['text']} {next_segment['text']}",
                'speaker': segment['speaker']
            })
            
            # Saltar el siguiente segmento
            i += 2
        else:
            merged_segments.append(segment)
            i += 1
    
    return merged_segments

def create_srt_file(segments, output_file, max_chars_per_line=40):
    """
    Crea un archivo SRT a partir de segmentos.
    """
    if not segments:
        print("No hay segmentos para generar el archivo SRT")
        return False
    
    # Crear copia de respaldo si existe el archivo
    if os.path.exists(output_file):
        backup_dir = os.path.dirname(output_file)
        base_name = os.path.basename(output_file)
        backup_name = f"{os.path.splitext(base_name)[0]}_bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.srt"
        backup_path = os.path.join(backup_dir, backup_name)
        
        try:
            with open(output_file, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            print(f"Copia de respaldo creada en: {backup_path}")
        except Exception as e:
            print(f"Error al crear copia de respaldo: {e}")
    
    # Generar entradas SRT
    srt_entries = []
    for i, segment in enumerate(segments, 1):
        # Validar que el segmento tenga los campos necesarios
        if not all(k in segment for k in ['start', 'end', 'text']):
            continue
        
        # Formatear texto y tiempos
        text = segment['text'].strip()
        if not text:
            continue
        
        formatted_text = format_subtitle_line(text, max_chars_per_line)
        start_time = format_time_srt(segment['start'])
        end_time = format_time_srt(segment['end'])
        
        # Crear entrada SRT
        srt_entry = f"{i}\n{start_time} --> {end_time}\n{formatted_text}"
        srt_entries.append(srt_entry)
    
    # Asegurarse de que la ruta de salida tiene extensión .srt
    if not output_file.lower().endswith('.srt'):
        output_file = os.path.splitext(output_file)[0] + '.srt'
    
    # Guardar archivo SRT
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(srt_entries))
        print(f"Archivo SRT generado con {len(srt_entries)} subtítulos en: {output_file}")
        return True
    except Exception as e:
        print(f"Error al guardar el archivo SRT: {e}")
        return False

def main():
    # Configurar rutas
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "data", "output")
    
    # Buscar carpetas en output_dir automáticamente (la más reciente)
    output_folders = glob.glob(os.path.join(output_dir, "sermon_*"))
    
    if not output_folders:
        print("No se encontraron carpetas de salida en", output_dir)
        return
    
    # Seleccionar la carpeta más reciente
    selected_folder = sorted(output_folders)[-1]
    print(f"Usando carpeta: {os.path.basename(selected_folder)}")
    
    # Buscar archivos JSON en la carpeta seleccionada
    json_dir = os.path.join(selected_folder, "json")
    json_files = glob.glob(os.path.join(json_dir, "*_transcription.json"))
    
    if not json_files:
        print(f"No se encontraron archivos JSON en {json_dir}")
        return
    
    # Seleccionar el archivo JSON más reciente
    selected_json = sorted(json_files, key=os.path.getmtime)[-1]
    print(f"Usando archivo JSON: {os.path.basename(selected_json)}")
    
    # Definir ruta de salida para el archivo SRT
    text_dir = os.path.join(selected_folder, "text")
    base_name = os.path.basename(selected_json).replace("_transcription.json", "")
    srt_output_path = os.path.join(text_dir, f"{base_name}_subtitles.srt")
    
    # Procesar JSON y obtener palabras con marcas de tiempo
    words_or_segments = process_assemblyai_json(selected_json)
    
    if not words_or_segments:
        print("No se pudieron obtener palabras o segmentos del archivo JSON")
        return
    
    # Verificar si estamos trabajando con palabras o segmentos
    if 'text' in words_or_segments[0]:
        # Estamos trabajando con segmentos, usarlos directamente
        print("Usando segmentos en lugar de palabras individuales")
        segments = words_or_segments
    else:
        # Estamos trabajando con palabras, crear segmentos
        print(f"Creando segmentos a partir de {len(words_or_segments)} palabras...")
        segments = create_sentence_segments(words_or_segments)
    
    # Crear archivo SRT
    if create_srt_file(segments, srt_output_path):
        print("¡Archivo SRT creado con éxito!")
    else:
        print("Error al crear el archivo SRT")

if __name__ == "__main__":
    main()
