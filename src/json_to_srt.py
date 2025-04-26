"""
Script para convertir transcripciones JSON de AssemblyAI a formato SRT.
"""
import os
import json
import sys
import argparse
from datetime import timedelta

def format_time(seconds):
    """Convierte segundos a formato HH:MM:SS,mmm para SRT"""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def json_to_srt(json_file, output_file=None):
    """Convierte un archivo JSON de transcripción a formato SRT"""
    # Determinar el nombre del archivo de salida si no se proporciona
    if not output_file:
        output_file = os.path.splitext(json_file)[0] + ".srt"
    
    # Leer el archivo JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error al leer el archivo JSON: {e}")
        return False
    
    # Crear el contenido SRT
    srt_content = []
    
    # Verificar si hay segmentos en el JSON
    if 'segments' not in data or not data['segments']:
        print("No se encontraron segmentos en el archivo JSON")
        return False
    
    # Procesar cada segmento
    for i, segment in enumerate(data['segments'], 1):
        # Obtener tiempos de inicio y fin
        start_time = segment.get('start', 0)
        end_time = segment.get('end', 0)
        
        # Formatear tiempos para SRT
        start_formatted = format_time(start_time)
        end_formatted = format_time(end_time)
        
        # Obtener el texto
        text = segment.get('text', '').strip()
        
        # Añadir el hablante si está disponible
        if 'speaker' in segment and segment['speaker'] != 'unknown':
            text = f"[{segment['speaker']}] {text}"
        
        # Crear entrada SRT
        srt_entry = f"{i}\n{start_formatted} --> {end_formatted}\n{text}\n"
        srt_content.append(srt_entry)
    
    # Escribir el archivo SRT
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(srt_content))
        print(f"Archivo SRT creado exitosamente: {output_file}")
        return True
    except Exception as e:
        print(f"Error al escribir el archivo SRT: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Convierte transcripciones JSON a formato SRT')
    parser.add_argument('json_file', help='Ruta al archivo JSON de transcripción')
    parser.add_argument('-o', '--output', help='Ruta del archivo SRT de salida (opcional)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.json_file):
        print(f"Error: El archivo {args.json_file} no existe")
        sys.exit(1)
    
    success = json_to_srt(args.json_file, args.output)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
