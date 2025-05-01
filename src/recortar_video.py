"""
Script para recortar videos usando ffmpeg.
"""
import os
import sys
import subprocess
from datetime import datetime
import time
from colorama import init, Fore, Back, Style

# Inicializar colorama
init(autoreset=True)  # autoreset=True hace que cada impresión vuelva al color normal

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
        print(f"{Fore.RED}{Style.BRIGHT}No se encontraron archivos de video en {source_dir}")
        print(f"{Fore.YELLOW}Por favor, coloca tus videos originales en {source_dir}")
        sys.exit(1)
    
    # Mostrar videos disponibles
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== RECORTADOR DE VIDEOS ===")
    print(f"\n{Fore.CYAN}Videos disponibles en: {source_dir}")
    print(f"{Fore.CYAN}{'-' * 50}")
    for i, video in enumerate(videos, 1):
        print(f"{Fore.GREEN}{i}.{Style.RESET_ALL} {video}")
    print(f"{Fore.CYAN}{'-' * 50}")
    
    # Pedir selección al usuario
    try:
        selection = int(input(f"\n{Fore.YELLOW}Selecciona el número del video a recortar (0 para salir): {Style.RESET_ALL}"))
        if selection == 0:
            print(f"{Fore.CYAN}Operación cancelada")
            sys.exit(0)
        
        if selection < 1 or selection > len(videos):
            print(f"{Fore.RED}{Style.BRIGHT}Selección inválida")
            sys.exit(1)
            
        selected_video = videos[selection - 1]
        print(f"\n{Fore.CYAN}Video seleccionado: {Fore.YELLOW}{selected_video}")
    except (ValueError, IndexError):
        print(f"{Fore.RED}{Style.BRIGHT}Selección inválida")
        sys.exit(1)
    
    # Pedir tiempos de inicio y fin
    try:
        print(f"\n{Fore.CYAN}Introduce los tiempos en formato HH:MM:SS")
        start_time = input(f"{Fore.YELLOW}Tiempo de inicio: {Style.RESET_ALL}")
        end_time = input(f"{Fore.YELLOW}Tiempo de fin (dejar vacío para cortar hasta el final): {Style.RESET_ALL}")
        
        # Nombre del archivo de salida
        default_name = f"sermon_recortado_{datetime.now().strftime('%d%m%y')}"
        print(f"\n{Fore.CYAN}Nombre sugerido: {Fore.GREEN}{default_name}")
        output_name = input(f"{Fore.YELLOW}Nombre para el archivo recortado (Enter para usar el sugerido): {Style.RESET_ALL}")
        
        if not output_name:
            output_name = default_name
        
        output_file = os.path.join(output_dir, f"{output_name}.mp4")
    except KeyboardInterrupt:
        print(f"\n{Fore.CYAN}Operación cancelada")
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
        print(f"\n{Fore.CYAN}{Style.BRIGHT}=== COMENZANDO RECORTE ===")
        print(f"{Fore.CYAN}Video: {Fore.YELLOW}{selected_video}")
        print(f"{Fore.CYAN}Desde: {Fore.GREEN}{start_time}")
        if end_time:
            print(f"{Fore.CYAN}Hasta: {Fore.GREEN}{end_time}")
        print(f"{Fore.CYAN}Guardando como: {Fore.GREEN}{output_name}.mp4")
        print(f"{Fore.CYAN}{'-' * 50}")
        print(f"{Fore.YELLOW}Procesando...")
        
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
            print(f"\r{Fore.GREEN}{Style.BRIGHT}¡Video recortado con éxito!          ")
            print(f"\n{Fore.CYAN}Guardado en: {Fore.GREEN}{output_file}")
        else:
            print(f"\r{Fore.RED}{Style.BRIGHT}Error al recortar el video          ")
            stderr = process.stderr.read().decode('utf-8', errors='ignore')
            print(f"{Fore.RED}Error: {stderr}")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"\n{Fore.RED}{Style.BRIGHT}Error al recortar el video: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operación cancelada por el usuario")
        # Intentar matar el proceso si está en ejecución
        if 'process' in locals() and process.poll() is None:
            process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()
