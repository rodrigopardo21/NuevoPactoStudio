"""
Script para recortar videos usando ffmpeg.
"""
import os
import sys
import subprocess
from datetime import datetime
import time

def main():
    # Configurar rutas
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_dir = os.path.join(base_dir, "source_video")
    output_dir = os.path.join(base_dir, "data", "input")
    
    # Verificar que existen las carpetas
    os.makedirs(source_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # Verificar archivos de video disponibles
    videos = [f for f in os.listdir(source_dir) if f.endswith((".mp4", ".MP4"))]
    
    if not videos:
        print(f"No se encontraron archivos de video en {source_dir}")
        print(f"Por favor, coloca tus videos originales en {source_dir}")
        sys.exit(1)
    
    # Mostrar videos disponibles
    print("\n=== RECORTADOR DE VIDEOS ===")
    print(f"\nVideos disponibles en: {source_dir}")
    print("-" * 50)
    for i, video in enumerate(videos, 1):
        print(f"{i}. {video}")
    print("-" * 50)
    
    # Pedir selección al usuario
    try:
        selection = int(input("\nSelecciona el número del video a recortar (0 para salir): "))
        if selection == 0:
            print("Operación cancelada")
            sys.exit(0)
        
        if selection < 1 or selection > len(videos):
            print("Selección inválida")
            sys.exit(1)
            
        selected_video = videos[selection - 1]
        print(f"\nVideo seleccionado: {selected_video}")
    except (ValueError, IndexError):
        print("Selección inválida")
        sys.exit(1)
    
    # Pedir tiempos de inicio y fin
    try:
        print("\nIntroduce los tiempos en formato HH:MM:SS")
        start_time = input("Tiempo de inicio: ")
        end_time = input("Tiempo de fin (dejar vacío para cortar hasta el final): ")
        
        # Nombre del archivo de salida
        default_name = f"sermon_recortado_{datetime.now().strftime('%d%m%y')}"
        print(f"\nNombre sugerido: {default_name}")
        output_name = input(f"Nombre para el archivo recortado (Enter para usar el sugerido): ")
        
        if not output_name:
            output_name = default_name
        
        output_file = os.path.join(output_dir, f"{output_name}.mp4")
    except KeyboardInterrupt:
        print("\nOperación cancelada")
        sys.exit(0)
    
    # Preparar el comando ffmpeg
    input_file = os.path.join(source_dir, selected_video)
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", input_file,
        "-ss", start_time
    ]
    
    # Añadir tiempo de fin si se especificó
    if end_time:
        ffmpeg_cmd.extend(["-to", end_time])
    
    # Opciones de codificación - MODIFICADO PARA ASEGURAR KEYFRAMES
    ffmpeg_cmd.extend([
        "-c:v", "libx264",  # Recodificar video en lugar de copiar
        "-preset", "fast",  # Preset de codificación
        "-crf", "22",       # Calidad del video
        "-c:a", "aac",      # Codec de audio
        "-b:a", "128k",     # Bitrate de audio
        "-force_key_frames", "expr:gte(t,0)",  # Forzar keyframe al inicio
        output_file
    ])
    
    # Ejecutar el comando
    try:
        print("\n=== COMENZANDO RECORTE ===")
        print(f"Video: {selected_video}")
        print(f"Desde: {start_time}")
        if end_time:
            print(f"Hasta: {end_time}")
        print(f"Guardando como: {output_name}.mp4")
        print("-" * 50)
        print("Procesando...")
        
        # Mostrar un contador simple para indicar progreso
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Mostrar un indicador de progreso simple
        spinner = ['-', '\\', '|', '/']
        i = 0
        while process.poll() is None:
            print(f"\rProcesando {spinner[i % len(spinner)]}", end='')
            i += 1
            time.sleep(0.2)
        
        # Verificar si el proceso terminó correctamente
        if process.returncode == 0:
            print("\r¡Video recortado con éxito!          ")
            print(f"\nGuardado en: {output_file}")
        else:
            print("\rError al recortar el video          ")
            stderr = process.stderr.read().decode('utf-8', errors='ignore')
            print(f"Error: {stderr}")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"\nError al recortar el video: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario")
        # Intentar matar el proceso si está en ejecución
        if 'process' in locals() and process.poll() is None:
            process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()
