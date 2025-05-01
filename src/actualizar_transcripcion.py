#!/usr/bin/env python3
"""
Script para actualizar la transcripción y regenerar todos los archivos.
Este script sincroniza las ediciones del JSON y regenera tanto el SRT como el TXT.
"""
import os
import sys
import json
import glob
import re
from datetime import datetime
from colorama import init, Fore, Style

# Inicializar colorama
init(autoreset=True)

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
    """Formatea un texto para que quepa en máximo 2 líneas de subtítulos."""
    if len(text) <= max_chars_per_line:
        return text
    
    # Buscar un punto natural para dividir cerca del centro
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
    
    return f"{line1}\n{line2}"

def find_json_file():
    """Encuentra el archivo JSON de transcripción más reciente."""
    # Configurar rutas
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "data", "output")
    
    # Buscar carpetas en output_dir (la más reciente)
    output_folders = glob.glob(os.path.join(output_dir, "sermon_*"))
    
    if not output_folders:
        print(f"{Fore.RED}{Style.BRIGHT}No se encontraron carpetas de salida en {output_dir}")
        return None
    
    # Seleccionar la carpeta más reciente
    selected_folder = sorted(output_folders)[-1]
    print(f"{Fore.CYAN}Usando carpeta: {Fore.GREEN}{os.path.basename(selected_folder)}")
    
    # Buscar archivos JSON en la carpeta seleccionada
    json_dir = os.path.join(selected_folder, "json")
    json_files = glob.glob(os.path.join(json_dir, "*_transcription.json"))
    
    if not json_files:
        print(f"{Fore.RED}{Style.BRIGHT}No se encontraron archivos JSON en {json_dir}")
        return None
    
    # Seleccionar el archivo JSON más reciente
    selected_json = sorted(json_files, key=os.path.getmtime)[-1]
    print(f"{Fore.CYAN}Archivo JSON encontrado: {Fore.GREEN}{os.path.basename(selected_json)}")
    
    return {
        "json_file": selected_json,
        "folder": selected_folder
    }

def sync_json_sections(json_data):
    """
    Sincroniza las secciones del JSON (text, segments, words) basándose en los segmentos.
    Los segmentos son considerados la fuente de verdad para las ediciones.
    """
    print(f"{Fore.YELLOW}Sincronizando secciones del JSON...")
    
    # Verificar que tenemos segmentos
    if 'segments' not in json_data or not json_data['segments']:
        print(f"{Fore.RED}No se encontraron segmentos en el JSON")
        return json_data
    
    # 1. Actualizar el texto principal basado en los segmentos
    updated_text = " ".join(segment["text"] for segment in json_data['segments'])
    json_data['text'] = updated_text
    print(f"{Fore.GREEN}Texto principal actualizado basado en los segmentos")
    
    # 2. Si hay palabras, intentar actualizarlas basadas en los segmentos
    if 'words' in json_data and json_data['words']:
        # Esto es más complejo y requiere una aproximación heurística
        # porque los tiempos de las palabras deben mantenerse
        print(f"{Fore.YELLOW}Manteniendo las palabras originales por ahora")
    
    return json_data

def save_plain_text(json_data, folder_path, basename):
    """Guarda la transcripción como texto plano."""
    text_dir = os.path.join(folder_path, "text")
    text_file = os.path.join(text_dir, f"{basename}_transcript.txt")
    
    # Crear contenido del archivo de texto
    content = []
    content.append(f"TRANSCRIPCIÓN: {basename}")
    content.append(f"Fecha de actualización: {datetime.now().isoformat()}")
    if 'confidence' in json_data:
        content.append(f"Nivel de confianza: {json_data.get('confidence', 'N/A')}")
    content.append("")  # Línea en blanco
    content.append("=" * 80)  # Separador
    content.append("")  # Línea en blanco
    
    # Añadir el texto principal
    content.append(json_data.get('text', '').strip())
    
    # Guardar el texto
    try:
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        print(f"{Fore.GREEN}Archivo de texto actualizado: {Fore.CYAN}{text_file}")
        
        # También crear versión detallada con marcas de tiempo
        detailed_file = os.path.join(text_dir, f"{basename}_transcript_detailed.txt")
        
        # Contenido detallado
        detailed_content = []
        detailed_content.append(f"TRANSCRIPCIÓN DETALLADA: {basename}")
        detailed_content.append(f"Fecha de actualización: {datetime.now().isoformat()}")
        detailed_content.append("")  # Línea en blanco
        detailed_content.append("=" * 80)  # Separador
        detailed_content.append("")  # Línea en blanco
        
        # Añadir segmentos con marcas de tiempo
        for segment in json_data.get('segments', []):
            start_time = format_time_srt(segment['start'])
            speaker = segment.get('speaker', 'unknown')
            detailed_content.append(f"[{start_time}] {speaker}: {segment['text']}")
        
        # Guardar el texto detallado
        with open(detailed_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(detailed_content))
        print(f"{Fore.GREEN}Archivo de texto detallado actualizado: {Fore.CYAN}{detailed_file}")
        
        return True
    except Exception as e:
        print(f"{Fore.RED}Error al guardar el archivo de texto: {e}")
        return False

def create_srt_file(json_data, folder_path, basename):
    """Crea un archivo SRT a partir de los segmentos del JSON."""
    text_dir = os.path.join(folder_path, "text")
    srt_file = os.path.join(text_dir, f"{basename}_subtitles.srt")
    
    # Verificar si tenemos palabras para hacer subtítulos más precisos
    if 'words' in json_data and json_data['words']:
        segments = create_sentence_segments(json_data['words'])
        print(f"{Fore.CYAN}Generando SRT usando marcas de tiempo a nivel de palabra (mayor precisión)")
    else:
        segments = json_data.get('segments', [])
        print(f"{Fore.YELLOW}Generando SRT usando segmentos (menos preciso)")
    
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
        
        formatted_text = format_subtitle_line(text)
        
        # Convertir a formato SRT
        start_time = format_time_srt(segment['start'] if isinstance(segment['start'], int) else segment['start'] * 1000)
        end_time = format_time_srt(segment['end'] if isinstance(segment['end'], int) else segment['end'] * 1000)
        
        # Crear entrada SRT
        srt_entry = f"{i}\n{start_time} --> {end_time}\n{formatted_text}"
        srt_entries.append(srt_entry)
    
    # Guardar archivo SRT
    try:
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(srt_entries))
        print(f"{Fore.GREEN}Archivo SRT actualizado: {Fore.CYAN}{srt_file}")
        return True
    except Exception as e:
        print(f"{Fore.RED}Error al guardar el archivo SRT: {e}")
        return False

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
        word_text = word['text'].rstrip()
        ends_with_strong_punct = any(word_text.endswith(p) for p in ('.', '!', '?'))
        ends_with_weak_punct = any(word_text.endswith(p) for p in (',', ';', ':'))
        
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
    
    return segments

def save_updated_json(json_data, json_file):
    """Guarda el JSON actualizado."""
    try:
        # Guardar el JSON actualizado
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            
        print(f"{Fore.GREEN}JSON actualizado y guardado con éxito")
        return True
    except Exception as e:
        print(f"{Fore.RED}Error al guardar el JSON: {e}")
        return False

def main():
    # Mostrar encabezado
    print(f"{Fore.CYAN}{Style.BRIGHT}" + "="*60)
    print(f"{Fore.CYAN}{Style.BRIGHT}  NuevoPactoStudio - Actualizador de Transcripción")
    print(f"{Fore.CYAN}{Style.BRIGHT}  Actualiza todos los archivos desde el JSON editado")
    print(f"{Fore.CYAN}{Style.BRIGHT}" + "="*60)
    print()
    
    # Encontrar el archivo JSON
    file_info = find_json_file()
    if not file_info:
        print(f"{Fore.RED}No se pudo encontrar un archivo JSON para procesar")
        return
    
    json_file = file_info["json_file"]
    folder = file_info["folder"]
    
    # Extraer el nombre base
    basename = os.path.basename(json_file).replace("_transcription.json", "")
    
    # Cargar el JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        print(f"{Fore.GREEN}JSON cargado correctamente")
    except Exception as e:
        print(f"{Fore.RED}Error al cargar el JSON: {e}")
        return
    
    # Sincronizar las secciones del JSON
    json_data = sync_json_sections(json_data)
    
    # Guardar el JSON actualizado
    if not save_updated_json(json_data, json_file):
        return
    
    # Actualizar el archivo de texto plano
    save_plain_text(json_data, folder, basename)
    
    # Crear/actualizar el archivo SRT
    create_srt_file(json_data, folder, basename)
    
    print(f"\n{Fore.GREEN}{Style.BRIGHT}¡Actualización completa!")
    print(f"{Fore.CYAN}Se han actualizado todos los archivos basados en el JSON editado")

if __name__ == "__main__":
    main()
