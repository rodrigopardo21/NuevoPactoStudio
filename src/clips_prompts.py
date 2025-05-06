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

def create_clip_prompt(segment, count=None):
    """
    Crea un prompt para enviar a Claude para generar ideas de clips visuales.
    
    Args:
        segment (dict): Datos del segmento de reel
        count (int, optional): Número de ideas de prompts a generar.
                              Si es None, se calcula automáticamente según la duración.
    
    Returns:
        str: Prompt para Claude
        int: Número de prompts solicitados
    """
    text = segment["text"]
    duration = segment["duration"]
    score = segment.get("score", 0)
    reasons = segment.get("reasons", "")
    
    # Si no se especifica count, calcularlo basado en la duración
    # Asumiendo clips de 8 segundos para Google AI Studio Veo2
    if count is None:
        # Calcular cuántos clips de 8 segundos caben en la duración del reel
        # y reducir un 20% para dar espacio
        clip_duration = 8  # segundos por clip
        count = max(1, min(7, int((duration / clip_duration) * 0.8)))
    
    prompt = f"""
    Eres un experto creativo en generación de ideas visuales para contenido religioso cristiano.
    
    Necesito que generes exactamente {count} ideas de prompts visuales para crear clips de video con Google AI Studio Veo2.
    Cada prompt debe poder ilustrar/visualizar una parte específica del mensaje y ser útil para crear clips
    de video generativo que acompañen el audio.
    
    IMPORTANTE: 
    1. Cada clip de video tendrá una duración de aproximadamente 8 segundos
    2. En total necesito cubrir un audio de {duration:.1f} segundos con {count} clips
    3. Los clips DEBEN CONTAR UNA HISTORIA FLUIDA cuando se pongan en secuencia
    4. Utiliza movimiento y progresión en las escenas - ESTOS SON VIDEOS, NO IMÁGENES ESTÁTICAS
    5. Diseña cada prompt pensando en cómo fluye desde el clip anterior y hacia el siguiente
    6. Mantener consistencia visual (estilo, personajes, tono) entre todos los clips
    
    SEGMENTO DE SERMÓN (duración: {duration:.1f} segundos):
    "{text}"
    
    RELEVANCIA TEOLÓGICA (Puntuación: {score}/50):
    {reasons}
    
    FORMATO REQUERIDO - SÓLO PROMPTS NUMERADOS:
    Prompt 1: [Descripción concisa de la primera escena visual EN MOVIMIENTO - MAX 400 caracteres]
    
    Prompt 2: [Descripción concisa de la segunda escena visual EN MOVIMIENTO que CONTINUA LA NARRATIVA - MAX 400 caracteres]
    
    Y así sucesivamente hasta completar exactamente {count} prompts, asegurando una narrativa visual FLUIDA y COHERENTE.
    
    CONSIDERACIONES IMPORTANTES:
    - Diseña una NARRATIVA VISUAL COHESIVA que fluya a través de los {count} clips
    - Especifica MOVIMIENTO y ACCIÓN en cada prompt (cámara en movimiento, personas realizando acciones, etc.)
    - Indica TRANSICIONES sugeridas entre cada clip para mantener continuidad
    - Mantener consistencia en elementos visuales (personajes, locaciones, colores, etc.) entre clips
    - Asegúrate que cada escena propuesta sea adecuada para contenido religioso cristiano y respetuosa
    - Evita escenas que requieran representaciones directas de deidad o figuras bíblicas sagradas
    - Prefiere escenas con ambientación contemporánea o metafórica que ilustre principios bíblicos
    - Piensa en escenas que funcionen bien en formatos verticales para redes sociales
    - Varía entre escenas con personas, naturaleza, símbolos, y metáforas visuales pero MANTENER COHERENCIA
    - Asegúrate de que las escenas fluyan naturalmente en secuencia para contar una historia coherente
    - Recuerda que estos prompts se usarán para generar clips de video de 8 segundos cada uno
    - Utiliza lenguaje rico y descriptivo que Google AI Studio Veo2 pueda interpretar correctamente
    - Incluye detalles sobre iluminación, estilo artístico, ángulo y composición en los prompts
    - NO INCLUYAS "Descripción:", "Frase del Audio:" u otros elementos - SÓLO LOS PROMPTS NUMERADOS
    """
    
    
    return prompt, count

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
        # Crear prompt para Claude con número de clips basado en duración
        prompt, prompt_count = create_clip_prompt(segment)
        
        print(f"{Fore.CYAN}Generando {prompt_count} ideas para clips de 8 segundos (segmento {index})...")
        print(f"{Fore.CYAN}Extracto del texto: \"{segment['text'][:100]}...\"")
        print(f"{Fore.CYAN}Duración total del reel: {segment['duration']:.1f} segundos")
        
        # Llamar a la API de Claude
        try:
            # Intentar con el modelo claude-3-5-sonnet primero
            try:
                response = claude_client.messages.create(
                    model="claude-3-5-sonnet-20240620",  # Modelo reciente con capacidades creativas
                    max_tokens=4000,
                    system="Eres un experto creativo en contenido religioso cristiano que genera ideas visuales para clips de video.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                response_text = response.content[0].text
            except Exception as model_e:
                # Si falla, intentar con claude-3-opus como respaldo
                print(f"{Fore.YELLOW}Advertencia: Error con modelo sonnet, probando con opus: {model_e}")
                try:
                    response = claude_client.messages.create(
                        model="claude-3-opus-20240229",  # Modelo alternativo
                        max_tokens=4000,
                        system="Eres un experto creativo en contenido religioso cristiano que genera ideas visuales para clips de video.",
                        messages=[
                            {"role": "user", "content": prompt}
                        ]
                    )
                    response_text = response.content[0].text
                except Exception as backup_e:
                    print(f"{Fore.RED}Error al llamar a la API de Claude con ambos modelos: {backup_e}")
                    return False
        except Exception as e:
            print(f"{Fore.RED}Error al llamar a la API de Claude: {e}")
            return False
        
        # Procesar y simplificar la respuesta
        processed_response = response_text
        
        # Limpiar la respuesta para que sólo tenga las líneas de "Prompt X:" 
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        prompt_lines = [line for line in lines if line.startswith("Prompt ") or line.startswith("**Prompt ")]
        
        if prompt_lines:
            # Limpiar formato extra que pueda haber añadido Claude
            clean_prompts = []
            for line in prompt_lines:
                # Eliminar cualquier formato markdown como **
                line = line.replace("**", "")
                # Asegurarse de que comienza con "Prompt X:"
                if not line.startswith("Prompt "):
                    if ":" in line:
                        parts = line.split(":", 1)
                        line = f"Prompt {parts[0].strip().split()[-1]}: {parts[1].strip()}"
                clean_prompts.append(line)
            
            # Unir las líneas con doble salto de línea para mejor legibilidad
            processed_response = "PROMPTS PARA VEO2 (8 SEGUNDOS POR CLIP):\n\n"
            processed_response += "\n\n".join(clean_prompts)
        else:
            # Si no encontramos líneas de prompts, intentar extraerlas con otro método
            print(f"{Fore.YELLOW}Formato inesperado en la respuesta. Intentando extracción alternativa...")
            # Buscar patrones como "Prompt 1:", "1:" o similares
            import re
            pattern = r"(?:Prompt\s*)?\d+:.*?"
            matches = re.findall(pattern, response_text)
            if matches:
                processed_response = "PROMPTS PARA VEO2 (8 SEGUNDOS POR CLIP):\n\n"
                processed_response += "\n\n".join([f"Prompt {i+1}: {m.split(':', 1)[1].strip()}" 
                                                for i, m in enumerate(matches)])
        
        # Guardar respuesta procesada
        file_path = save_prompt_file(
            output_path, 
            f"prompts.txt",
            processed_response
        )
                
        if file_path:
            print(f"{Fore.GREEN}Prompts generados y guardados en: {file_path}")
            print(f"{Fore.GREEN}Se solicitaron {prompt_count} prompts para clips de 8 segundos")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"{Fore.RED}Error al generar prompts para clips: {str(e)}")
        # Guardar un archivo de error para diagnóstico
        error_info = f"ERROR AL PROCESAR SEGMENTO #{index}\n" + \
                    f"===========================================\n" + \
                    f"Error: {str(e)}\n\n" + \
                    f"Texto del segmento:\n{segment.get('text', 'No disponible')}\n"
        error_path = save_prompt_file(
            output_path,
            f"error.txt",
            error_info
        )
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
        
        # Crear carpeta principal para prompts si no existe
        base_dir = os.path.dirname(segments_json_path)
        prompts_dir = os.path.join(base_dir, "prompts")
        os.makedirs(prompts_dir, exist_ok=True)
        
        # Generar prompts para cada segmento
        print(f"{Fore.GREEN}Procesando {len(segments)} segmentos...")
        
        successful_count = 0
        for i, segment in enumerate(segments, 1):
            print(f"\n{Fore.CYAN}Procesando segmento {i}/{len(segments)}...")
            
            # Crear una subcarpeta específica para este reel
            reel_prompts_dir = os.path.join(prompts_dir, f"reel_{i:02d}")
            os.makedirs(reel_prompts_dir, exist_ok=True)
            
            success = generate_clip_prompts(
                segment,
                claude_client,
                reel_prompts_dir,
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
        
    # Verificar que existen los archivos de audio y texto de los reels
    reels_audio_dir = os.path.join(reels_dir, "audio")
    reels_text_dir = os.path.join(reels_dir, "text")
    
    if not os.path.isdir(reels_audio_dir) or not os.path.isdir(reels_text_dir):
        print(f"{Fore.YELLOW}Advertencia: No se encontraron las carpetas de audio o texto de reels")
        print(f"{Fore.YELLOW}Es posible que los reels no se hayan extraído correctamente")
    
    # Procesar segmentos
    success = process_reel_segments(segments_json_path, claude_client)
    
    if success:
        print(f"\n{Fore.GREEN}{Style.BRIGHT}¡Generación de prompts para clips completada con éxito!")
        # Mostrar instrucciones de uso
        print(f"\n{Fore.CYAN}Los prompts se han guardado con un formato simplificado para Google AI Studio Veo2:")
        print(f"{Fore.CYAN}  {reels_dir}/prompts/reel_XX/prompts.txt - Secuencia de clips de 8 segundos")
        
        print(f"\n{Fore.YELLOW}INSTRUCCIONES PARA USAR CON GOOGLE AI STUDIO VEO2:")
        print(f"{Fore.YELLOW}1. Abre los archivos 'prompts.txt' en cada carpeta de reel")
        print(f"{Fore.YELLOW}2. Copia cada prompt individualmente a Google AI Studio Veo2")
        print(f"{Fore.YELLOW}3. Genera cada clip de 8 segundos con Veo2 en orden secuencial")
        print(f"{Fore.YELLOW}4. Descarga los clips generados manteniendo el orden de la narrativa")
        print(f"{Fore.YELLOW}5. Combina los clips en secuencia (1->2->3...) para mantener la historia visual")
        print(f"{Fore.YELLOW}6. Sincroniza el audio original del reel con la secuencia de clips")
        
        print(f"\n{Fore.GREEN}NOTA: Los prompts han sido diseñados para crear una narrativa visual FLUIDA")
        print(f"{Fore.GREEN}con clips de 8 segundos que se conectan entre sí para contar una historia")
        print(f"{Fore.GREEN}que complementa el audio del reel. Asegúrate de mantener el orden.")
    else:
        print(f"\n{Fore.RED}{Style.BRIGHT}La generación de prompts para clips ha fallado")

if __name__ == "__main__":
    main()
