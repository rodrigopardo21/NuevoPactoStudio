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
    
    # Log para depuración - número de segmentos
    print(f"{Fore.YELLOW}Número de segmentos encontrados: {len(json_data['segments'])}")
    
    # Mostrar ejemplo de los primeros segmentos
    for i, segment in enumerate(json_data['segments'][:3], 1):
        print(f"{Fore.CYAN}Segmento {i}: {segment['text'][:50]}...")
    
    # 1. Actualizar el texto principal basado en los segmentos
    original_text = json_data.get('text', '')
    updated_text = " ".join(segment["text"] for segment in json_data['segments'])
    json_data['text'] = updated_text
    
    # Log para mostrar diferencias
    print(f"{Fore.GREEN}Texto principal actualizado basado en los segmentos")
    print(f"{Fore.YELLOW}Longitud del texto original: {len(original_text)} caracteres")
    print(f"{Fore.YELLOW}Longitud del texto actualizado: {len(updated_text)} caracteres")
    
    # Verificar si hay diferencias reales
    if original_text == updated_text:
        print(f"{Fore.YELLOW}ADVERTENCIA: No se detectaron cambios en el texto.")
        print(f"{Fore.YELLOW}Asegúrate de editar los segmentos en el JSON y guardar los cambios.")
    else:
        # Calcular un porcentaje aproximado de diferencia
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, original_text, updated_text).ratio()
        diff_percent = (1 - similarity) * 100
        print(f"{Fore.GREEN}Se detectaron cambios en el texto: {diff_percent:.2f}% de diferencia")
    
    # 2. Si hay palabras, intentar actualizarlas basadas en los segmentos
    if 'words' in json_data and json_data['words']:
        print(f"{Fore.YELLOW}Número de palabras encontradas: {len(json_data['words'])}")
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
    
    # Agregar log para depuración
    print(f"{Fore.YELLOW}Ruta del archivo SRT: {srt_file}")
    
    # Verificar si tenemos palabras para hacer subtítulos más precisos
    if 'words' in json_data and json_data['words']:
        segments = create_sentence_segments(json_data['words'])
        print(f"{Fore.CYAN}Generando SRT usando marcas de tiempo a nivel de palabra (mayor precisión)")
        print(f"{Fore.YELLOW}Segmentos generados: {len(segments)}")
    else:
        segments = json_data.get('segments', [])
        print(f"{Fore.YELLOW}Generando SRT usando segmentos (menos preciso)")
        print(f"{Fore.YELLOW}Segmentos disponibles: {len(segments)}")
    
    # Log para depuración - mostrar algunos segmentos
    if segments:
        print(f"{Fore.YELLOW}Ejemplo de segmentos:")
        for i, segment in enumerate(segments[:3], 1):
            print(f"{Fore.CYAN}Segmento {i}: {segment['text'][:50]}...")
    
    # Generar entradas SRT
    srt_entries = []
    for i, segment in enumerate(segments, 1):
        # Validar que el segmento tenga los campos necesarios
        if not all(k in segment for k in ['start', 'end', 'text']):
            print(f"{Fore.RED}Segmento {i} incompleto, falta alguno de los campos requeridos")
            continue
        
        # Formatear texto y tiempos
        text = segment['text'].strip()
        if not text:
            print(f"{Fore.RED}Segmento {i} tiene texto vacío")
            continue
        
        formatted_text = format_subtitle_line(text)
        
        # Convertir a formato SRT
        start_ms = segment['start'] if isinstance(segment['start'], int) else int(segment['start'] * 1000)
        end_ms = segment['end'] if isinstance(segment['end'], int) else int(segment['end'] * 1000)
        
        # Garantizar una duración mínima y máxima adecuada para los subtítulos
        duration = end_ms - start_ms
        if duration < 500:  # Duración mínima de 500ms
            end_ms = start_ms + 500
        elif duration > 5000:  # Duración máxima de 5 segundos
            end_ms = start_ms + 5000
        
        # Generar el formato SRT (HH:MM:SS,mmm)
        start_time = format_time_srt(start_ms)
        end_time = format_time_srt(end_ms)
        
        # Crear entrada SRT con formato estándar
        srt_entry = f"{i}\n{start_time} --> {end_time}\n{formatted_text}"
        srt_entries.append(srt_entry)
    
    print(f"{Fore.YELLOW}Total de entradas SRT generadas: {len(srt_entries)}")
    
    # Guardar archivo SRT
    try:
        # Asegurarnos de que las entradas estén bien formateadas
        srt_content = "\n\n".join(srt_entries)
        if not srt_content.endswith("\n"):
            srt_content += "\n"  # Asegurar que el archivo termina con una línea en blanco
        
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        print(f"{Fore.GREEN}Archivo SRT actualizado: {Fore.CYAN}{srt_file}")
        
        # Verificar que el archivo se creó correctamente
        if os.path.exists(srt_file):
            file_size = os.path.getsize(srt_file)
            print(f"{Fore.GREEN}Archivo SRT creado correctamente. Tamaño: {file_size} bytes")
            
            # Leer las primeras líneas para verificar
            try:
                with open(srt_file, 'r', encoding='utf-8') as f:
                    lines = [line for _, line in zip(range(10), f)]
                    first_lines = ''.join(lines)
                print(f"{Fore.YELLOW}Primeras líneas del SRT:\n{first_lines}")
            except Exception as e:
                print(f"{Fore.RED}Error al leer el archivo SRT para verificación: {e}")
        else:
            print(f"{Fore.RED}El archivo SRT no existe después de intentar guardarlo")
            
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
    
    # Log para depuración - Directorio de trabajo actual
    print(f"{Fore.YELLOW}Directorio de trabajo actual: {os.getcwd()}")
    
    # Encontrar el archivo JSON
    file_info = find_json_file()
    if not file_info:
        print(f"{Fore.RED}No se pudo encontrar un archivo JSON para procesar")
        return
    
    json_file = file_info["json_file"]
    folder = file_info["folder"]
    
    # Log para depuración - Ruta completa del JSON
    print(f"{Fore.YELLOW}Ruta completa del JSON: {json_file}")
    print(f"{Fore.YELLOW}Carpeta de salida: {folder}")
    
    # Extraer el nombre base
    basename = os.path.basename(json_file).replace("_transcription.json", "")
    print(f"{Fore.YELLOW}Nombre base: {basename}")
    
    # Verificar que el archivo existe
    if not os.path.exists(json_file):
        print(f"{Fore.RED}El archivo JSON no existe en la ruta especificada")
        return
    
    # Cargar el JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        print(f"{Fore.GREEN}JSON cargado correctamente")
        
        # Log para depuración - Tamaño y estructura del JSON
        print(f"{Fore.YELLOW}Tamaño del JSON: {len(json.dumps(json_data))} bytes")
        print(f"{Fore.YELLOW}Claves principales: {', '.join(json_data.keys())}")
        
    except Exception as e:
        print(f"{Fore.RED}Error al cargar el JSON: {e}")
        return
    
    # Sincronizar las secciones del JSON
    original_text = json_data.get('text', '')
    json_data = sync_json_sections(json_data)
    updated_text = json_data.get('text', '')
    
    # Verificar si hubo cambios reales
    if original_text == updated_text:
        print()
        print(f"{Fore.RED}{Style.BRIGHT}=== ADVERTENCIA: NO SE DETECTARON CAMBIOS ===")
        print(f"{Fore.YELLOW}Posibles causas:")
        print(f"  1. No editaste el archivo JSON antes de ejecutar este script")
        print(f"  2. Guardaste el archivo JSON sin hacer cambios")
        print(f"  3. Los cambios no se aplicaron correctamente en los segmentos")
        print()
        print(f"{Fore.YELLOW}Sugerencias:")
        print(f"  1. Verifica que has editado el archivo correcto: {json_file}")
        print(f"  2. Asegúrate de editar la sección 'segments' en el JSON")
        print(f"  3. Guarda el archivo JSON después de editarlo")
        
        continuar = input(f"\n{Fore.YELLOW}¿Deseas continuar de todos modos? (s/n): {Style.RESET_ALL}").lower().strip()
        if continuar != 's':
            print(f"{Fore.CYAN}Operación cancelada por el usuario")
            return
    
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
