"""
Script para extraer segmentos impactantes de sermones para crear reels usando la API de Claude.
"""
import os
import sys
import json
import time
import subprocess
import re
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
init(autoreset=True)  # autoreset=True hace que cada impresión vuelva al color normal

# Constantes
MIN_DURATION_SECONDS = 15  # Duración mínima recomendada (15 segundos)
MAX_DURATION_SECONDS = 180  # Duración máxima (3 minutos)

def load_json_transcription(json_path):
    """Carga el archivo JSON de transcripción y verifica su estructura."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Verificar estructura mínima necesaria
        if "words" not in data or not isinstance(data["words"], list) or not data["words"]:
            raise ValueError("El JSON no contiene la sección 'words' o está vacía")
            
        return data
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}Error al decodificar el JSON: {e}")
        return None
    except Exception as e:
        print(f"{Fore.RED}Error al cargar el archivo: {e}")
        return None

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

def create_claude_prompt(transcription_text):
    """Crea el prompt especializado para enviar a Claude."""
    
    prompt = f"""
    Tu tarea es analizar un sermón transcrito e identificar IDEAS COMPLETAS Y AUTÓNOMAS que serían efectivas para crear reels religiosos. Estas ideas deben ser GRAMATICALMENTE COMPLETAS, con principio, desarrollo y cierre claro.
    
    REGLAS CRUCIALES PARA DELIMITAR LAS IDEAS CORRECTAMENTE:
    1. NUNCA inicies un segmento en mitad de una frase o idea - SIEMPRE inicia en el comienzo EXACTO de una oración completa
    2. NUNCA termines un segmento en mitad de una frase o idea - SIEMPRE termina en un punto final o cierre lógico del pensamiento
    3. NUNCA agregues palabras adicionales después del final natural de un pensamiento o párrafo
    4. NUNCA incluyas conectores o palabras que queden "colgando" al final (como "y", "pero", "entonces", "en", "hay", "el", etc.)
    5. SIEMPRE verifica que la primera y última palabra del segmento formen parte de oraciones completas y con sentido
    6. SIEMPRE incluye unidades completas de pensamiento, nunca parciales
    7. Si hay una cita bíblica, incluye el versículo completo, desde su introducción ("dice así...") hasta su conclusión
    8. Si hay una pregunta retórica, incluye la pregunta completa con su contexto
    
    CRITERIOS DE SELECCIÓN DE IDEAS:
    1. Declaraciones directas y poderosas sobre verdades espirituales
    2. Contrastes claros entre perspectivas mundanas y verdades bíblicas
    3. Preguntas retóricas impactantes que inviten a la reflexión
    4. Metáforas o ilustraciones memorables que clarifiquen verdades profundas
    5. Verdades espirituales con aplicación práctica inmediata
    6. Unidades autónomas y comprensibles sin necesitar contexto adicional
    7. Tono inspirador, motivador o revelador (similar a sermones virales)
    
    INSTRUCCIONES ADICIONALES:
    - Evita incluir bromas, comentarios informales o ejemplos que puedan malinterpretarse sin contexto
    - Los segmentos NO DEBEN repetir contenido entre sí - cada segmento debe ser totalmente independiente
    - Puedes extraer ideas antes o después de lo que dice otro segmento, pero sin compartir ninguna parte
    - Prioriza la coherencia y completitud de la idea sobre cualquier restricción de duración
    - Asegúrate de que cada idea sea teológicamente sólida y edificante por sí misma
    
    Por cada idea identificada, proporciona:
    - El texto EXACTO y COMPLETO del segmento (comprueba que inicie y termine en puntos gramaticalmente correctos)
    - Una puntuación de 1-50 basada en su impacto y relevancia teológica
    - Las razones específicas por las que esta idea sería efectiva como reel
    - Una frase única dentro del segmento que sea distintiva y fácil de localizar
    
    Identifica 8-12 ideas potenciales independientes. Proporciona tu respuesta en formato JSON:
    
    ```json
    [
      {{
        "text": "Texto COMPLETO del segmento con inicio y cierre gramatical perfecto. Verifica que la primera y última palabra formen parte de oraciones completas...",
        "score": 42,
        "reasons": "Razones por las que esta idea es teológicamente impactante y autónoma...",
        "marker_phrase": "frase única y distintiva dentro del segmento"
      }},
      // Más segmentos...
    ]
    ```
    
    SERMÓN TRANSCRITO:
    {transcription_text}
    """
    
    return prompt

def extract_json_from_response(response_text):
    """Extrae el JSON de la respuesta de Claude con mejor manejo de errores."""
    try:
        # Primero buscamos el formato más común: JSON entre marcadores de código
        start_marker = "```json"
        end_marker = "```"
        
        if start_marker in response_text:
            start_idx = response_text.find(start_marker) + len(start_marker)
            end_idx = response_text.find(end_marker, start_idx)
            if end_idx > start_idx:
                json_text = response_text[start_idx:end_idx].strip()
                # Intento de análisis con este método
                try:
                    segments = json.loads(json_text)
                    return segments
                except Exception as e:
                    print(f"{Fore.YELLOW}Error en el primer método de extracción: {e}")
        
        # Segundo intento: buscar corchetes de apertura y cierre de un array JSON
        start_idx = response_text.find("[")
        end_idx = response_text.rfind("]") + 1
        if start_idx != -1 and end_idx > start_idx:
            json_text = response_text[start_idx:end_idx].strip()
            try:
                # Limpiar posibles comentarios de estilo JavaScript
                # Encontrar y eliminar líneas que comiencen con //
                lines = json_text.split('\n')
                filtered_lines = [line for line in lines if not line.strip().startswith('//')]
                cleaned_json = '\n'.join(filtered_lines)
                
                # Intento de análisis después de limpieza
                segments = json.loads(cleaned_json)
                return segments
            except Exception as e:
                print(f"{Fore.YELLOW}Error en el segundo método de extracción: {e}")
                
                # Intento avanzado: buscar y corregir errores comunes de formato
                try:
                    # Intento de corrección manual del JSON
                    # 1. Eliminar comas extras al final de objetos JSON
                    corrected_json = re.sub(r',\s*}', '}', cleaned_json)
                    corrected_json = re.sub(r',\s*\]', ']', corrected_json)
                    
                    # 2. Asegurar que las propiedades tengan el formato correcto
                    corrected_json = re.sub(r'([\w]+)\s*:', r'"\1":', corrected_json)
                    
                    # Intento final con el JSON corregido
                    segments = json.loads(corrected_json)
                    print(f"{Fore.GREEN}Corrección automática del JSON exitosa")
                    return segments
                except Exception as e:
                    print(f"{Fore.YELLOW}Error en la corrección automática: {e}")
        
        # Guardar la respuesta para depuración
        debug_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 "debug_claude_response.txt")
        with open(debug_path, 'w', encoding='utf-8') as f:
            f.write(response_text)
        print(f"{Fore.YELLOW}Respuesta guardada en {debug_path} para depuración")
        
        # Último recurso: procesar manualmente la respuesta
        print(f"{Fore.RED}No se pudo extraer JSON automáticamente. Intentando extracción manual...")
        
        # Buscar segmentos de texto que parezcan objetos JSON
        segments = []
        pattern = r'\{[^\{\}]*"text"\s*:\s*"[^"]*"[^\{\}]*\}'
        matches = re.finditer(pattern, response_text)
        
        for match in matches:
            try:
                obj_text = match.group(0)
                # Intentar extraer los valores clave
                text_match = re.search(r'"text"\s*:\s*"([^"]*)"', obj_text)
                score_match = re.search(r'"score"\s*:\s*(\d+)', obj_text)
                reasons_match = re.search(r'"reasons"\s*:\s*"([^"]*)"', obj_text)
                marker_match = re.search(r'"marker_phrase"\s*:\s*"([^"]*)"', obj_text)
                
                if text_match and score_match and marker_match:
                    segment = {
                        "text": text_match.group(1),
                        "score": int(score_match.group(1)),
                        "reasons": reasons_match.group(1) if reasons_match else "Razones no especificadas",
                        "marker_phrase": marker_match.group(1)
                    }
                    segments.append(segment)
            except Exception as e:
                print(f"{Fore.RED}Error al procesar segmento individual: {e}")
        
        if segments:
            print(f"{Fore.GREEN}Extracción manual exitosa: {len(segments)} segmentos encontrados")
            return segments
            
        print(f"{Fore.RED}No se pudo extraer JSON válido de la respuesta.")
        return None
    except Exception as e:
        print(f"{Fore.RED}Error general al extraer JSON: {e}")
        return None

def find_segment_in_words(segment, words_data):
    """Encuentra un segmento en la lista de palabras y obtiene las marcas de tiempo."""
    try:
        # Obtener la frase marcadora y el texto completo del segmento
        marker_phrase = segment["marker_phrase"]
        segment_text = segment["text"]
        
        # Construir texto completo para búsqueda
        full_text = " ".join(word["text"] for word in words_data)
        
        # Verificar si la frase marcadora exacta está en el texto (case-insensitive)
        marker_found = False
        if marker_phrase.lower() in full_text.lower():
            marker_found = True
            print(f"{Fore.GREEN}Frase marcadora encontrada: '{marker_phrase}'")
        else:
            print(f"{Fore.YELLOW}Advertencia: Frase exacta '{marker_phrase}' no encontrada. Intentando búsqueda flexible...")
            
            # Intentar encontrar coincidencias parciales
            # 1. Dividir la frase marcadora en palabras y buscar secuencias de palabras
            marker_words = marker_phrase.lower().split()
            if len(marker_words) >= 3:
                # Intentar con diferentes subconjuntos de palabras (al menos 3 palabras consecutivas)
                for i in range(len(marker_words) - 2):
                    partial_marker = " ".join(marker_words[i:i+3])
                    if partial_marker.lower() in full_text.lower():
                        print(f"{Fore.GREEN}Coincidencia parcial encontrada: '{partial_marker}'")
                        marker_phrase = partial_marker
                        marker_found = True
                        break
            
            # 2. Si aún no hay coincidencia, buscar las primeras palabras del segmento
            if not marker_found and len(segment_text.split()) >= 5:
                start_words = " ".join(segment_text.split()[:5])
                if start_words.lower() in full_text.lower():
                    print(f"{Fore.GREEN}Usando primeras palabras del segmento como marcador: '{start_words[:30]}...'")
                    marker_phrase = start_words
                    marker_found = True
                else:
                    # 3. Intentar con combinaciones de palabras aleatorias del segmento
                    segment_unique_words = [w.lower() for w in segment_text.split() if len(w) > 5]
                    for word in segment_unique_words[:10]:  # Probar con las primeras 10 palabras distintivas
                        if word.lower() in full_text.lower() and len(word) > 5:  # Solo palabras significativas
                            surrounding_text = full_text.lower()[max(0, full_text.lower().find(word.lower())-40):full_text.lower().find(word.lower())+40]
                            print(f"{Fore.GREEN}Palabra clave encontrada: '{word}' en contexto: '...{surrounding_text}...'")
                            marker_phrase = word
                            marker_found = True
                            break
            
            # Si aún no hay coincidencia, no podemos proceder
            if not marker_found:
                print(f"{Fore.RED}No se pudo encontrar ningún marcador adecuado en el texto")
                return None
        
        # Buscar dónde empieza y termina el segmento completo
        segment_start = None
        segment_end = None
        
        # Preprocesar el texto del segmento para asegurarnos de que es gramaticalmente correcto
        # Encontrar el último punto, interrogación o exclamación
        last_punctuation = max(segment_text.rfind('.'), segment_text.rfind('!'), segment_text.rfind('?'))
        if last_punctuation > 0 and last_punctuation < len(segment_text) - 1:
            # Si hay contenido después del último punto, recortar hasta el punto
            clean_segment_text = segment_text[:last_punctuation+1]
            print(f"{Fore.YELLOW}Recortando texto después del último punto: '{segment_text[last_punctuation+1:]}' (eliminado)")
        else:
            clean_segment_text = segment_text
        
        # Obtener las primeras y últimas palabras del segmento limpio para búsqueda
        segment_words = clean_segment_text.split()
        first_words = segment_words[:min(10, len(segment_words))]  # Primeras 10 palabras o menos
        first_phrase = " ".join(first_words).lower()
        
        last_words = segment_words[-min(10, len(segment_words)):] if len(segment_words) >= 10 else segment_words
        last_phrase = " ".join(last_words).lower()
        
        # Buscar el inicio del segmento con mejor tolerancia a pequeñas diferencias
        best_match_score = 0
        for i in range(len(words_data) - len(first_words) + 1):
            window = " ".join(words_data[j]["text"].lower() for j in range(i, min(i + len(first_words), len(words_data))))
            
            # Calcular similitud usando una métrica simple de palabras coincidentes
            phrase_words = set(first_phrase.split())
            window_words = set(window.split())
            common_words = phrase_words.intersection(window_words)
            match_score = len(common_words) / max(len(phrase_words), 1)
            
            if match_score > 0.7:  # Al menos 70% de palabras coincidentes
                segment_start = i
                print(f"{Fore.GREEN}Inicio encontrado en palabra {i} (coincidencia {match_score:.2f}): '{words_data[i]['text']}...'")
                break
            elif match_score > best_match_score:
                best_match_score = match_score
        
        # Si no encontramos el inicio exacto, intentar con la frase marcadora
        if segment_start is None:
            if best_match_score > 0.5:  # Usar el mejor match si tiene al menos 50% de coincidencia
                for i in range(len(words_data) - len(first_words) + 1):
                    window = " ".join(words_data[j]["text"].lower() for j in range(i, min(i + len(first_words), len(words_data))))
                    phrase_words = set(first_phrase.split())
                    window_words = set(window.split())
                    common_words = phrase_words.intersection(window_words)
                    match_score = len(common_words) / max(len(phrase_words), 1)
                    
                    if match_score == best_match_score:
                        segment_start = i
                        print(f"{Fore.YELLOW}Usando mejor coincidencia aproximada ({match_score:.2f}): '{words_data[i]['text']}...'")
                        break
            else:  # Buscar por la frase marcadora
                # Buscar la frase marcadora en el texto
                for i in range(len(words_data) - 5):
                    text_window = " ".join(words_data[j]["text"].lower() for j in range(i, min(i+10, len(words_data))))
                    if marker_phrase.lower() in text_window:
                        # Retroceder para encontrar el inicio de una oración
                        for j in range(i, max(0, i-50), -1):
                            if j > 0 and words_data[j-1]["text"].strip().endswith(('.', '!', '?')):
                                segment_start = j  # Comenzar después del punto
                                print(f"{Fore.GREEN}Inicio alternativo encontrado después de punto: '{words_data[segment_start]['text']}...'")
                                break
                        
                        if segment_start is None:  # Si no encontramos un punto, usar un offset fijo
                            segment_start = max(0, i - 20)
                            print(f"{Fore.YELLOW}Usando inicio aproximado: '{words_data[segment_start]['text']}...'")
                        
                        break
        
        # Si aún no hay inicio, no podemos proceder
        if segment_start is None:
            print(f"{Fore.RED}No se pudo encontrar un punto de inicio confiable para el segmento")
            return None
        
        # Buscar el final del segmento con mejor tolerancia a diferencias
        best_match_score = 0
        for i in range(segment_start + len(first_words), len(words_data) - len(last_words) + 1):
            window = " ".join(words_data[j]["text"].lower() for j in range(i, min(i + len(last_words), len(words_data))))
            
            # Calcular similitud usando una métrica simple de palabras coincidentes
            phrase_words = set(last_phrase.split())
            window_words = set(window.split())
            common_words = phrase_words.intersection(window_words)
            match_score = len(common_words) / max(len(phrase_words), 1)
            
            if match_score > 0.7:  # Al menos 70% de palabras coincidentes
                # Buscar un punto final después de este match
                for j in range(i + len(last_words) - 1, min(i + len(last_words) + 15, len(words_data))):
                    if words_data[j]["text"].strip().endswith(('.', '!', '?')):
                        segment_end = j
                        print(f"{Fore.GREEN}Final encontrado en palabra {j} (coincidencia {match_score:.2f}): '...{words_data[j]['text']}'")
                        break
                
                if segment_end is not None:
                    break
                else:  # Si no encontramos un punto final claro, usar una aproximación
                    segment_end = min(i + len(last_words) + 10, len(words_data) - 1)
                    print(f"{Fore.YELLOW}Final aproximado sin punto encontrado: '...{words_data[segment_end]['text']}'")
                    break
            elif match_score > best_match_score:
                best_match_score = match_score
        
        # Si no encontramos el final exacto, intentar estrategias alternativas
        if segment_end is None:
            if best_match_score > 0.5:  # Usar el mejor match si tiene al menos 50% de coincidencia
                for i in range(segment_start + len(first_words), len(words_data) - len(last_words) + 1):
                    window = " ".join(words_data[j]["text"].lower() for j in range(i, min(i + len(last_words), len(words_data))))
                    phrase_words = set(last_phrase.split())
                    window_words = set(window.split())
                    common_words = phrase_words.intersection(window_words)
                    match_score = len(common_words) / max(len(phrase_words), 1)
                    
                    if match_score == best_match_score:
                        # Buscar un punto final después de este match
                        for j in range(i + len(last_words) - 1, min(i + len(last_words) + 15, len(words_data))):
                            if words_data[j]["text"].strip().endswith(('.', '!', '?')):
                                segment_end = j
                                print(f"{Fore.YELLOW}Usando mejor coincidencia aproximada para final ({match_score:.2f}): '...{words_data[j]['text']}'")
                                break
                        
                        if segment_end is None:  # Si no encontramos punto, aproximar
                            segment_end = min(i + len(last_words) + 5, len(words_data) - 1)
                            print(f"{Fore.YELLOW}Usando final aproximado sin punto: '...{words_data[segment_end]['text']}'")
                        
                        break
            else:  # Buscar por la frase marcadora y localizar un punto después
                # Encontrar la ubicación aproximada de la frase marcadora
                marker_index = None
                for i in range(segment_start, len(words_data) - 5):
                    text_window = " ".join(words_data[j]["text"].lower() for j in range(i, min(i+10, len(words_data))))
                    if marker_phrase.lower() in text_window:
                        marker_index = i
                        break
                
                if marker_index is not None:
                    # Buscar un punto después del marcador hasta un máximo de 100 palabras
                    for i in range(marker_index, min(marker_index + 100, len(words_data))):
                        if words_data[i]["text"].strip().endswith(('.', '!', '?')):
                            segment_end = i
                            print(f"{Fore.GREEN}Final alternativo encontrado después de marcador: '...{words_data[i]['text']}'")
                            break
                
                # Si aún no hay final, estimar basado en el inicio y la longitud típica
                if segment_end is None:
                    # Estimación basada en duración esperada (aprox. 30-60 segundos de audio)
                    estimated_word_count = min(70, max(40, len(segment_text.split())))  # ~40-70 palabras
                    segment_end = min(len(words_data) - 1, segment_start + estimated_word_count)
                    
                    # Buscar el siguiente punto después de esta posición estimada
                    for i in range(segment_end, max(segment_start, segment_end - 20), -1):
                        if i < len(words_data) and words_data[i]["text"].strip().endswith(('.', '!', '?')):
                            segment_end = i
                            print(f"{Fore.YELLOW}Final estimado por longitud: '...{words_data[i]['text']}'")
                            break
                    
                    if segment_end >= len(words_data) or not words_data[segment_end]["text"].strip().endswith(('.', '!', '?')):
                        print(f"{Fore.YELLOW}No se encontró punto al final - usando aproximación")
                        segment_end = min(len(words_data) - 1, segment_start + 60)
        
        # Asegurar que el segmento termina en un punto gramatical completo
        # Retroceder hasta encontrar un punto, signo de exclamación o interrogación
        original_end = segment_end
        while segment_end > segment_start:
            if words_data[segment_end]["text"].strip().endswith(('.', '!', '?')):
                break
            segment_end -= 1
        
        if original_end != segment_end:
            print(f"{Fore.YELLOW}Ajustado final para terminar en punto gramatical: de palabra {original_end} a {segment_end}")
        
        # Limitar la duración máxima (3 minutos)
        max_allowed_duration = MAX_DURATION_SECONDS  # 3 minutos máximo
        current_duration = (words_data[segment_end]["end"] - words_data[segment_start]["start"]) / 1000
        if current_duration > max_allowed_duration:
            print(f"{Fore.YELLOW}Duración {current_duration:.1f}s excede el límite. Ajustando...")
            # Buscar un punto anterior que mantenga la duración dentro del límite
            for i in range(segment_end, segment_start, -1):
                if words_data[i]["text"].strip().endswith(('.', '!', '?')):
                    new_duration = (words_data[i]["end"] - words_data[segment_start]["start"]) / 1000
                    if new_duration <= max_allowed_duration:
                        segment_end = i
                        print(f"{Fore.GREEN}Nuevo final encontrado: '...{words_data[i]['text']}'")
                        break
        
        # Calcular duración mínima recomendada (15 segundos)
        min_preferred_duration = MIN_DURATION_SECONDS  # 15 segundos como mínimo recomendado
        current_duration = (words_data[segment_end]["end"] - words_data[segment_start]["start"]) / 1000
        if current_duration < min_preferred_duration:
            print(f"{Fore.YELLOW}Duración {current_duration:.1f}s es muy corta. Intentando extender...")
            # Buscar un punto posterior para extender la duración si es posible
            original_end = segment_end
            for i in range(segment_end + 1, min(segment_end + 50, len(words_data))):
                if words_data[i]["text"].strip().endswith(('.', '!', '?')):
                    new_duration = (words_data[i]["end"] - words_data[segment_start]["start"]) / 1000
                    if new_duration >= min_preferred_duration:
                        segment_end = i
                        print(f"{Fore.GREEN}Segmento extendido para duración mínima: '...{words_data[i]['text']}'")
                        current_duration = new_duration
                        break
        
        # Calcular tiempos y texto final
        start_time = words_data[segment_start]["start"] / 1000  # convertir a segundos
        end_time = words_data[segment_end]["end"] / 1000  # convertir a segundos
        exact_text = " ".join(word["text"] for word in words_data[segment_start:segment_end+1])
        
        # Verificar que el texto termine en un punto gramatical correcto
        if not exact_text.strip().endswith(('.', '!', '?')):
            print(f"{Fore.YELLOW}Advertencia: El segmento no termina con punto. Buscando un mejor final...")
            # Encontrar el último punto dentro del texto
            last_punct = max(exact_text.rfind('.'), exact_text.rfind('!'), exact_text.rfind('?'))
            if last_punct > 0:
                exact_text = exact_text[:last_punct + 1]
                print(f"{Fore.GREEN}Texto recortado para terminar en punto gramatical")
        
        # Realizar una limpieza final del texto para evitar problemas comunes
        exact_text = exact_text.strip()
        
        # Verificar que el texto no comience con una palabra incompleta o conector suelto
        skip_start_words = ['y', 'pero', 'mas', 'e', 'o', 'u', 'aunque', 'sin embargo', 'por lo tanto', 'así que', 'entonces']
        first_word = exact_text.split()[0].lower() if exact_text.split() else ''
        
        if first_word in skip_start_words:
            words = exact_text.split()
            # Eliminar la primera palabra si es un conector
            exact_text = ' '.join(words[1:]) if len(words) > 1 else exact_text
            print(f"{Fore.YELLOW}Eliminado conector inicial: '{first_word}'")
        
        # Verificar que el texto no termine con una palabra incompleta o conector suelto
        if not exact_text.endswith(('.', '!', '?')):
            # Buscar el último punto
            last_punct = max(exact_text.rfind('.'), exact_text.rfind('!'), exact_text.rfind('?'))
            if last_punct > 0:
                exact_text = exact_text[:last_punct + 1]

        # Verificar que el texto no termine con una palabra incompleta o conector suelto
            if not exact_text.endswith(('.', '!', '?')):
                # Buscar el último punto
                last_punct = max(exact_text.rfind('.'), exact_text.rfind('!'), exact_text.rfind('?'))
                if last_punct > 0:
                    exact_text = exact_text[:last_punct + 1]
                    print(f"{Fore.GREEN}Texto ajustado para terminar en punto gramatical")
                else:
                    # Si no hay punto, agregar uno
                    exact_text += '.'
                    print(f"{Fore.YELLOW}Añadido punto final")

        # Realizar análisis final de calidad del segmento
        sentence_count = exact_text.count('.') + exact_text.count('!') + exact_text.count('?')
        word_count = len(exact_text.split())

        print(f"{Fore.CYAN}Segmento final: {word_count} palabras, {sentence_count} oraciones, {current_duration:.1f} segundos")

        # Si el segmento es de buena calidad (al menos 1 oración completa y suficientes palabras)
        if sentence_count >= 1 and word_count >= 10:
            return {
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "text": exact_text,
                "score": segment["score"],
                "reasons": segment["reasons"],
                "start_word_index": segment_start,
                "end_word_index": segment_end,
                "word_count": word_count,
                "sentence_count": sentence_count
            }
        else:
            print(f"{Fore.RED}Segmento rechazado por baja calidad: {sentence_count} oraciones, {word_count} palabras")
            return None
    except Exception as e:
        print(f"{Fore.RED}Error al buscar segmento en palabras: {e}")
        print(f"{Fore.RED}Detalles: {str(e)}")
        return None

def process_claude_response(response_text, transcription_data):
    """Procesa la respuesta de Claude y mapea los segmentos a marcas de tiempo."""
    try:
        # Extraer segmentos de la respuesta
        segments = extract_json_from_response(response_text)
        if not segments:
            return []

        # Obtener lista de palabras
        words_data = transcription_data["words"]

        # Mapear cada segmento a marcas de tiempo
        timed_segments = []

        for segment in segments:
            print(f"{Fore.CYAN}Procesando segmento con puntuación {segment['score']}...")
            print(f"{Fore.CYAN}Inicio del texto: \"{segment['text'][:100]}...\"")

            timed_segment = find_segment_in_words(segment, words_data)
            if timed_segment:
                # Aceptamos segmentos de cualquier duración, pero informamos
                duration = timed_segment["duration"]
                if duration < 15:  # menos de 15 segundos es muy corto
                    print(f"{Fore.YELLOW}  Segmento muy corto: {duration:.1f}s")
                elif duration > 180:  # más de 3 minutos puede ser demasiado largo
                    print(f"{Fore.YELLOW}  Segmento muy largo: {duration:.1f}s")
                else:
                    print(f"{Fore.GREEN}  Segmento encontrado: {duration:.1f}s - Idea completa identificada")

                # Mostrar una muestra del texto extraído para verificación
                excerpt = timed_segment["text"]
                if len(excerpt) > 150:
                    excerpt = excerpt[:75] + "..." + excerpt[-75:]
                print(f"{Fore.WHITE}  Texto extraído: \"{excerpt}\"")

                # Añadimos todos los segmentos sin importar su duración
                timed_segments.append(timed_segment)
            else:
                print(f"{Fore.YELLOW}  No se pudo mapear este segmento a marcas de tiempo")

        return timed_segments
    except Exception as e:
        print(f"{Fore.RED}Error al procesar la respuesta de Claude: {e}")
        return []

def format_time_srt(seconds):
    """Convierte segundos a formato HH:MM:SS,mmm para SRT"""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

def generate_srt_file(segment, output_path, index):
    """Genera un archivo SRT para un segmento."""
    try:
        # Crear contenido SRT
        start_srt = format_time_srt(segment["start_time"])
        end_srt = format_time_srt(segment["end_time"])

        # Dividir texto largo en líneas
        text = segment["text"]
        if len(text) > 40:
            words = text.split()
            half_length = len(text) // 2
            current_length = 0
            split_index = 0

            for i, word in enumerate(words):
                current_length += len(word) + (1 if i > 0 else 0)
                if current_length > half_length:
                    split_index = i
                    break

            if split_index > 0:
                line1 = " ".join(words[:split_index])
                line2 = " ".join(words[split_index:])
                text = f"{line1}\n{line2}"

        content = f"1\n{start_srt} --> {end_srt}\n{text}\n\n"

        # Guardar archivo
        file_path = os.path.join(output_path, f"reel_{index:02d}.srt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_path
    except Exception as e:
        print(f"{Fore.RED}Error al generar archivo SRT: {e}")
        return None

def generate_txt_file(segment, output_path, index):
    """Genera un archivo TXT para un segmento."""
    try:
        content = f"""SEGMENTO DE REEL #{index:02d}
================================================================================
PUNTUACIÓN: {segment['score']}
TIEMPO: {segment['start_time']:.2f} - {segment['end_time']:.2f} (Duración: {segment['duration']:.1f}s)
--------------------------------------------------------------------------------
{segment['text']}
--------------------------------------------------------------------------------
RAZONES PARA SELECCIÓN:
{segment['reasons']}
================================================================================
"""

        # Guardar archivo
        file_path = os.path.join(output_path, f"reel_{index:02d}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_path
    except Exception as e:
        print(f"{Fore.RED}Error al generar archivo TXT: {e}")
        return None

def extract_audio_segment(audio_path, segment, output_dir, index):
    """Extrae un segmento de audio usando ffmpeg."""
    try:
        start_time = segment["start_time"]
        duration = segment["duration"]

        output_file = os.path.join(output_dir, f"reel_{index:02d}.mp3")

        cmd = [
            "ffmpeg",
            "-i", audio_path,
            "-ss", str(start_time),
            "-t", str(duration),
            "-c:a", "libmp3lame",
            "-q:a", "2",
            "-y",  # Sobrescribir si existe
            output_file
        ]

        # Ejecutar ffmpeg sin mostrar salida
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if process.returncode != 0:
            print(f"{Fore.YELLOW}Advertencia en ffmpeg: {process.stderr[:150]}...")

        return output_file
    except Exception as e:
        print(f"{Fore.RED}Error al extraer segmento de audio: {e}")
        return None

def process_sermon(sermon_dir, claude_client):
    """Procesa un sermón completo para extraer segmentos para reels."""
    try:
        # Estructurar rutas
        json_dir = os.path.join(sermon_dir, "json")
        audio_dir = os.path.join(sermon_dir, "audio")
        text_dir = os.path.join(sermon_dir, "text")

        # Crear carpeta de reels si no existe
        reels_dir = os.path.join(sermon_dir, "reels")
        os.makedirs(reels_dir, exist_ok=True)
        reels_audio_dir = os.path.join(reels_dir, "audio")
        os.makedirs(reels_audio_dir, exist_ok=True)
        reels_text_dir = os.path.join(reels_dir, "text")
        os.makedirs(reels_text_dir, exist_ok=True)

        # Buscar archivo JSON
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
        if not json_files:
            print(f"{Fore.RED}No se encontraron archivos JSON en {json_dir}")
            return False

        # Seleccionar el primer archivo JSON (normalmente solo hay uno)
        json_file = json_files[0]
        json_path = os.path.join(json_dir, json_file)

        # Cargar transcripción
        print(f"{Fore.CYAN}Cargando transcripción desde {json_file}...")
        transcription_data = load_json_transcription(json_path)
        if not transcription_data:
            return False

        # Buscar archivo de audio
        audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
        if not audio_files:
            print(f"{Fore.RED}No se encontraron archivos de audio en {audio_dir}")
            return False

        audio_file = audio_files[0]
        audio_path = os.path.join(audio_dir, audio_file)

        # Preparar texto para Claude
        print(f"{Fore.CYAN}Preparando texto para análisis...")

        # Construir texto completo a partir de words
        full_text = " ".join(word["text"] for word in transcription_data["words"])

        # Crear prompt para Claude
        prompt = create_claude_prompt(full_text)

        # Llamar a la API de Claude
        print(f"{Fore.CYAN}Enviando a Claude para análisis (esto puede tomar un momento)...")
        try:
            response = claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",  # Usar un modelo más reciente con mejor soporte para JSON
                max_tokens=4000,
                system="Por favor, analízate el sermón y extrae segmentos siguiendo las instrucciones. Asegúrate de responder SOLO en formato JSON válido dentro de marcadores ```json. Es crucial que el JSON esté bien formateado sin comentarios ni caracteres adicionales.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = response.content[0].text
        except Exception as e:
            print(f"{Fore.RED}Error al llamar a la API de Claude: {e}")
            return False

        # Procesar respuesta
        print(f"{Fore.CYAN}Procesando respuesta de Claude...")
        segments = process_claude_response(response_text, transcription_data)

        if not segments:
            print(f"{Fore.RED}No se identificaron segmentos válidos")
            return False

        # Ordenar segmentos por puntuación
        segments.sort(key=lambda x: x["score"], reverse=True)

        # Guardar el JSON de segmentos
        segments_json_path = os.path.join(reels_dir, "reel_segments.json")
        with open(segments_json_path, 'w', encoding='utf-8') as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)

        print(f"{Fore.GREEN}JSON de segmentos guardado en: {segments_json_path}")

        # Generar archivos para cada segmento
        print(f"{Fore.GREEN}Generando archivos para {len(segments)} segmentos...")

        for i, segment in enumerate(segments, 1):
            print(f"{Fore.CYAN}Procesando segmento {i}/{len(segments)}...")

            # Generar SRT
            srt_path = generate_srt_file(segment, reels_text_dir, i)

            # Generar TXT
            txt_path = generate_txt_file(segment, reels_text_dir, i)

            # Extraer audio
            audio_segment_path = extract_audio_segment(audio_path, segment, reels_audio_dir, i)

            if srt_path and txt_path and audio_segment_path:
                print(f"{Fore.GREEN}  - Archivos generados: SRT, TXT y MP3")
            else:
                print(f"{Fore.YELLOW}  - Algunos archivos no se generaron correctamente")

        print(f"\n{Fore.GREEN}{Style.BRIGHT}¡Proceso completado con éxito!")
        print(f"{Fore.CYAN}Segmentos identificados: {len(segments)}")
        print(f"{Fore.CYAN}Archivos guardados en: {reels_dir}")

        return True
    except Exception as e:
        print(f"{Fore.RED}Error en el procesamiento del sermón: {e}")
        return False

def main():
    """Función principal del script."""
    # Mostrar encabezado
    print(f"{Fore.CYAN}{Style.BRIGHT}" + "="*60)
    print(f"{Fore.CYAN}{Style.BRIGHT}  NuevoPactoStudio - Extractor de Reels")
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

    success = process_sermon(sermon_path, claude_client)

    if success:
        print(f"\n{Fore.GREEN}{Style.BRIGHT}¡Extracción de reels completada con éxito!")
    else:
        print(f"\n{Fore.RED}{Style.BRIGHT}La extracción de reels ha fallado")

if __name__ == "__main__":
    main()
