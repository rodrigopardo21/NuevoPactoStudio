"""
Script para generar prompts creativos para clips visuales basados en los reels extraídos.
Utiliza la API de Claude para analizar el contenido de los reels y generar ideas visuales.
"""
import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Verificar dependencias requeridas
try:
    import anthropic
except ImportError:
    print("Error: Biblioteca anthropic no encontrada.")
    print("Por favor, instálala ejecutando: pip install anthropic")
    sys.exit(1)

# Inicializar colorama
init(autoreset=True)

def setup_claude_client():
    """Configura el cliente de API de Claude usando la clave en .env."""
    try:
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            print(f"{Fore.RED}Error: No se encontró la clave API de Claude en el archivo .env")
            sys.exit(1)
            
        client = anthropic.Anthropic(api_key=api_key)
        return client
    except Exception as e:
        print(f"{Fore.RED}Error al configurar el cliente de Claude: {e}")
        sys.exit(1)

def create_clip_prompt(segment, count=7):
    """
    Crea un prompt para enviar a Claude para generar ideas de clips visuales.
    
    Args:
        segment (dict): Datos del segmento de reel
        count (int): Número de ideas de prompts a generar
    
    Returns:
        str: Prompt para Claude
    """
    text = segment["text"]
    duration = segment["duration"]
    score = segment.get("score", 0)
    reasons = segment.get("reasons", "")
    
    prompt = f"""
    Eres un experto creativo en generación de ideas visuales para contenido religioso cristiano.
    
    Necesito que generes {count} ideas de prompts visuales (escenas) basados en el siguiente segmento de sermón.
    Cada prompt debe poder ilustrar/visualizar una parte específica del mensaje y ser útil para crear
    imágenes o videos generativos que acompañen el audio.
    
    SEGMENTO DE SERMÓN (duración: {duration:.1f} segundos):
    "{text}"
    
    RELEVANCIA TEOLÓGICA (Puntuación: {score}/50):
    {reasons}
    
    Para cada idea, proporciona:
    1. Un título conciso
    2. Una descripción detallada de la escena visual (ambientación, iluminación, personas, acciones, etc.)
    3. Una frase específica del audio que esta escena ilustraría (cita exacta del texto)
    4. Un prompt de generación de imagen conciso (1-2 líneas) que capture la esencia
    
    Formato para cada idea:
    **Prompt {num}: [Título]**
    **Descripción: **[Descripción detallada de la escena visual]
    **Frase del Audio: **"[Cita textual del segmento]"
    **Prompt: **"[Prompt de generación de imagen]"
    
    CONSIDERACIONES IMPORTANTES:
    - Asegúrate que cada escena propuesta sea adecuada para contenido religioso cristiano y respetuosa
    - Evita escenas que requieran representaciones directas de deidad o figuras bíblicas sagradas
    - Prefiere escenas con ambientación contemporánea o metafórica que ilustre principios bíblicos
    - Piensa en escenas que funcionen bien en formatos verticales para redes sociales
    - Varía entre escenas con personas, naturaleza, símbolos, y metáforas visuales
    - No repitas conceptos visuales entre los diferentes prompts
    """
    
    return prompt

def save_prompt_file(output_path, filename, content):
    """Guarda un archivo de prompt en disco."""
    try:
        file_path = os.path.join(output_path, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    except Exception as e:
        print(f"{Fore.RED}Error al guardar archivo: {e}")
        return None

def generate_clip_prompts(segment, claude_client, output_path, index):
    """
    Genera prompts para clips visuales para un segmento usando Claude.
    
    Args:
        segment (dict): Datos del segmento de reel
        claude_client: Cliente de API de Claude
        output_path (str): Carpeta donde guardar los prompts
        index (int): Índice del segmento para nombrar archivos
    
    Returns:
        bool: True si se generó con éxito, False en caso contrario
    """
    try:
        # Crear prompt para Claude
        prompt = create_clip_prompt(segment)
        
        print(f"{Fore.CYAN}Generando ideas visuales para el segmento {index}...")
        print(f"{Fore.CYAN}Extracto del texto: \"{segment['text'][:100]}...\"")
        
        # Llamar a la API de Claude
        try:
            response = claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",  # Modelo reciente con capacidades creativas
                max_tokens=4000,
                system="Eres un experto creativo en contenido religioso cristiano que genera ideas visuales y prompts detallados.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = response.content[0].text
        except Exception as e:
            print(f"{Fore.RED}Error al llamar a la API de Claude: {e}")
            return False
        
        # Guardar respuesta completa
        file_path = save_prompt_file(
            output_path, 
            f"reel_{index:02d}_prompts.txt",
            response_text
        )
        
        if file_path:
            print(f"{Fore.GREEN}Prompts generados y guardados en: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"{Fore.RED}Error al generar prompts para clips: {e}")
        return False

def process_reel_segments(segments_json_path, claude_client):
    """
    Procesa todos los segmentos de reels y genera prompts para cada uno.
    
    Args:
        segments_json_path (str): Ruta al archivo JSON con segmentos de reels
        claude_client: Cliente de API de Claude
    
    Returns:
        bool: True si el proceso fue exitoso, False en caso contrario
    """
    try:
        # Cargar JSON de segmentos
        print(f"{Fore.CYAN}Cargando segmentos desde {segments_json_path}...")
        with open(segments_json_path, 'r', encoding='utf-8') as f:
            segments = json.load(f)
        
        if not segments:
            print(f"{Fore.RED}No se encontraron segmentos en el archivo JSON")
            return False
        
        # Crear carpeta para prompts si no existe
        base_dir = os.path.dirname(segments_json_path)
        prompts_dir = os.path.join(base_dir, "prompts")
        os.makedirs(prompts_dir, exist_ok=True)
        
        # Generar prompts para cada segmento
        print(f"{Fore.GREEN}Procesando {len(segments)} segmentos...")
        
        successful_count = 0
        for i, segment in enumerate(segments, 1):
            print(f"\n{Fore.CYAN}Procesando segmento {i}/{len(segments)}...")
            
            success = generate_clip_prompts(
                segment,
                claude_client,
                prompts_dir,
                i
            )
            
            if success:
                successful_count += 1
            
            # Pequeña pausa para evitar límites de rate en la API
            if i < len(segments):
                time.sleep(1)
        
        print(f"\n{Fore.GREEN}{Style.BRIGHT}Proceso completado: {successful_count}/{len(segments)} prompts generados")
        print(f"{Fore.CYAN}Prompts guardados en: {prompts_dir}")
        
        return successful_count > 0
        
    except Exception as e:
        print(f"{Fore.RED}Error al procesar segmentos: {e}")
        return False

def main():
    """Función principal del script."""
    # Mostrar encabezado
    print(f"{Fore.CYAN}{Style.BRIGHT}" + "="*60)
    print(f"{Fore.CYAN}{Style.BRIGHT}  NuevoPactoStudio - Generador de Prompts para Clips")
    print(f"{Fore.CYAN}{Style.BRIGHT}" + "="*60)
    print()
    
    # Configurar cliente de Claude
    claude_client = setup_claude_client()
    
    # Configurar rutas
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "data", "output")
    
    # Verificar que existe la carpeta
    if not os.path.isdir(output_dir):
        print(f"{Fore.RED}Error: No se encontró la carpeta de salida: {output_dir}")
        sys.exit(1)
    
    # Listar sermones disponibles
    try:
        sermon_dirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d)) and d.startswith('sermon_')]
        sermon_dirs.sort()
    except Exception as e:
        print(f"{Fore.RED}Error al listar sermones: {e}")
        sys.exit(1)
    
    if not sermon_dirs:
        print(f"{Fore.RED}No se encontraron sermones en {output_dir}")
        sys.exit(1)
    
    # Mostrar sermones disponibles
    print(f"{Fore.CYAN}{Style.BRIGHT}Sermones disponibles:")
    for i, d in enumerate(sermon_dirs, 1):
        print(f"{Fore.GREEN}{i}.{Style.RESET_ALL} {d}")
    
    # Pedir selección al usuario
    selected_sermon = None
    while selected_sermon is None:
        try:
            selection = int(input(f"\n{Fore.YELLOW}Selecciona el número del sermón a procesar (0 para salir): {Style.RESET_ALL}"))
            if selection == 0:
                print(f"{Fore.CYAN}Operación cancelada")
                sys.exit(0)
            
            if 1 <= selection <= len(sermon_dirs):
                selected_sermon = sermon_dirs[selection - 1]
            else:
                print(f"{Fore.RED}Selección fuera de rango. Intenta de nuevo.")
        except ValueError:
            print(f"{Fore.RED}Por favor ingresa un número válido")
    
    # Procesar el sermón seleccionado
    sermon_path = os.path.join(output_dir, selected_sermon)
    print(f"\n{Fore.CYAN}{Style.BRIGHT}Procesando: {selected_sermon}")
    
    # Buscar archivo JSON de segmentos
    reels_dir = os.path.join(sermon_path, "reels")
    segments_json_path = os.path.join(reels_dir, "reel_segments.json")
    
    if not os.path.isfile(segments_json_path):
        print(f"{Fore.RED}Error: No se encontró el archivo JSON de segmentos: {segments_json_path}")
        print(f"{Fore.RED}Ejecuta primero 'extract_reels.py' para este sermón")
        sys.exit(1)
    
    # Procesar segmentos
    success = process_reel_segments(segments_json_path, claude_client)
    
    if success:
        print(f"\n{Fore.GREEN}{Style.BRIGHT}¡Generación de prompts para clips completada con éxito!")
    else:
        print(f"\n{Fore.RED}{Style.BRIGHT}La generación de prompts para clips ha fallado")

if __name__ == "__main__":
    main()
