"""
Script principal para transcribir videos usando AssemblyAI.
"""
import os
import sys
from dotenv import load_dotenv
from transcriber_assemblyai.transcriber import AssemblyAITranscriber

def main():
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar API key
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("Error: No se encontró la API key de AssemblyAI en el archivo .env")
        print("Crea un archivo .env con el siguiente contenido:")
        print("ASSEMBLYAI_API_KEY=tu_clave_aqui")
        sys.exit(1)
    
    # Configurar rutas
    input_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "input")
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "output")
    
    # Verificar que existen las carpetas
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # Verificar archivos de video disponibles
    videos = [f for f in os.listdir(input_dir) if f.endswith((".mp4", ".MP4"))]
    
    if not videos:
        print(f"No se encontraron archivos de video en {input_dir}")
        print("Por favor, coloca tus videos recortados en esta carpeta")
        sys.exit(1)
    
    # Mostrar videos disponibles
    print("Videos disponibles para transcribir:")
    for i, video in enumerate(videos, 1):
        print(f"{i}. {video}")
    
    # Pedir selección al usuario
    try:
        selection = int(input("\nSelecciona el número del video a transcribir (0 para salir): "))
        if selection == 0:
            print("Operación cancelada")
            sys.exit(0)
        
        selected_video = videos[selection - 1]
    except (ValueError, IndexError):
        print("Selección inválida")
        sys.exit(1)
    
    # Iniciar transcripción
    print(f"\nIniciando transcripción de: {selected_video}")
    transcriber = AssemblyAITranscriber(input_dir, output_dir, api_key)
    
    try:
        transcriber.process_video(selected_video)
        print("\n¡Transcripción completada con éxito!")
    except Exception as e:
        print(f"\nError durante la transcripción: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
