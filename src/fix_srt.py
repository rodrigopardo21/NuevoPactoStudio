import os
import sys
import json
import subprocess
import time # Importar time para usarlo en _generate_srt...
from datetime import timedelta, datetime
from colorama import init, Fore, Style

# Inicializar colorama
init(autoreset=True)

def format_time_srt(seconds_float):
    """Convierte segundos (float) a formato HH:MM:SS,mmm para SRT"""
    try:
        if not isinstance(seconds_float, (int, float)):
            seconds_float = float(seconds_float)
        if seconds_float < 0: seconds_float = 0.0
        delta = timedelta(seconds=seconds_float)
        # Ajuste para obtener partes de tiempo
        total_seconds = int(delta.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = delta.microseconds // 1000 # Microsegundos de la parte fraccionaria
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    except (ValueError, TypeError) as e:
        print(f"{Fore.RED}Error formateando tiempo '{seconds_float}': {e}. Usando 00:00:00,000.")
        return "00:00:00,000"

def format_multi_line(text, max_chars_per_line=40):
    """
    Formatea texto en 1 o 2 líneas para SRT, sin truncar.
    """
    text = text.strip()
    if not text or len(text) <= max_chars_per_line:
        return text # Cabe en una línea o está vacío

    # Buscar el último espacio en o antes de la posición max_chars_per_line
    split_pos = text.rfind(' ', 0, max_chars_per_line + 1)

    # Si no hay espacio adecuado, forzar división (puede cortar palabra larga)
    if split_pos == -1 or split_pos == 0:
         split_pos = max_chars_per_line
         # Si el corte es justo antes de un espacio, mover el corte después del espacio
         if split_pos < len(text) and text[split_pos] == ' ':
              split_pos += 1

    line1 = text[:split_pos].strip()
    # La línea 2 contiene TODO el texto restante
    line2 = text[split_pos:].strip()

    # Devolver en 1 o 2 líneas
    return f"{line1}\n{line2}" if line2 else line1

# --- FUNCIÓN CLAVE: Genera SRT desde la lista 'words' ---
def generate_srt_entries_from_words(words_list):
    """
    Genera entradas SRT precisas usando una lista de palabras (dict)
    con claves 'text', 'start' (ms), 'end' (ms).
    Agrupa palabras en bloques lógicos.
    """
    if not words_list:
        print(f"{Fore.YELLOW}Advertencia: La lista 'words' está vacía. No se puede generar SRT.")
        return []

    # Usar Fore.CYAN que sí existe en colorama
    print(f"{Fore.CYAN}Generando SRT usando marcas de tiempo de {len(words_list)} palabras...")

    # Parámetros para agrupar palabras
    max_chars_per_block = 80  # Objetivo ~2 líneas de 40
    max_duration_sec = 5.0    # Máx 5 seg por bloque
    min_duration_sec = 0.5    # Mín 0.5 seg (para evitar bloques muy cortos si hay pausa)
    pause_threshold_ms = 700  # Pausa > 700ms fuerza nuevo bloque

    srt_blocks = []
    current_block_words_text = [] # Lista de strings de palabras editadas
    current_block_start_ms = -1
    last_word_end_ms = -1
    entry_index = 1

    for i, word_data in enumerate(words_list):
        try:
            word_text = word_data.get('text', '').strip()
            start_ms_raw = word_data.get('start')
            end_ms_raw = word_data.get('end')

            if start_ms_raw is None or end_ms_raw is None: continue
            if not word_text: continue # Saltar palabra vacía

            try:
                 start_ms = int(start_ms_raw)
                 end_ms = int(end_ms_raw)
                 if start_ms >= end_ms or start_ms < 0: raise ValueError("Tiempo inválido")
            except (ValueError, TypeError):
                 print(f"{Fore.YELLOW}Adv: Palabra omitida (índice {i}) - Tiempos inválidos.")
                 continue

            # Inicio de un nuevo bloque
            if current_block_start_ms < 0:
                current_block_start_ms = start_ms
                current_block_words_text = [word_text]
                last_word_end_ms = end_ms
                continue

            # Calcular si hay pausa significativa
            pause_duration_ms = start_ms - last_word_end_ms if last_word_end_ms >= 0 else 0

            # Texto y duración si añadiéramos esta palabra
            potential_text = " ".join(current_block_words_text + [word_text])
            potential_duration_sec = (end_ms - current_block_start_ms) / 1000.0
            is_last_word = (i == len(words_list) - 1)

            # Condiciones para finalizar el bloque ANTES de añadir la palabra actual
            should_finalize_block = False
            if is_last_word: # Siempre finalizar si es la última palabra
                 should_finalize_block = True
                 # Añadir la última palabra antes de finalizar
                 current_block_words_text.append(word_text)
                 last_word_end_ms = end_ms
                 final_text_current = " ".join(current_block_words_text)
            else:
                 if potential_duration_sec > max_duration_sec: should_finalize_block = True
                 elif len(potential_text) > max_chars_per_block + 10: should_finalize_block = True
                 elif pause_duration_ms > pause_threshold_ms and potential_duration_sec > min_duration_sec: should_finalize_block = True

            if should_finalize_block:
                # Usar el texto acumulado ANTES de esta palabra (o incluyendo esta si es la última)
                final_text_to_format = final_text_current if is_last_word else " ".join(current_block_words_text)
                formatted_text_block = format_multi_line(final_text_to_format)
                start_time_str = format_time_srt(current_block_start_ms / 1000.0)
                # Usar el tiempo final de la *última palabra del bloque*
                end_time_str = format_time_srt(last_word_end_ms / 1000.0)

                if formatted_text_block:
                    srt_entry = f"{entry_index}\n{start_time_str} --> {end_time_str}\n{formatted_text_block}"
                    srt_blocks.append(srt_entry)
                    entry_index += 1

                # Si NO es la última palabra, iniciar nuevo bloque con la palabra actual
                if not is_last_word:
                     current_block_start_ms = start_ms
                     current_block_words_text = [word_text]
                     last_word_end_ms = end_ms
                else: # Si era la última, ya terminamos
                     current_block_words_text = []
                     current_block_start_ms = -1
            else:
                # Añadir palabra actual al bloque en curso
                current_block_words_text.append(word_text)
                last_word_end_ms = end_ms

        except Exception as word_e:
             print(f"{Fore.RED}Error procesando palabra índice {i}: {word_data}. Error: {word_e}")
             # Reiniciar bloque en caso de error
             current_block_words_text = []
             current_block_start_ms = -1
             last_word_end_ms = -1
             continue

    # Capturar el último bloque si no se finalizó en el bucle (esto no debería pasar con la lógica is_last_word)
    # Pero lo dejamos por si acaso
    if current_block_words_text:
        final_text_last = " ".join(current_block_words_text)
        formatted_text_last = format_multi_line(final_text_last)
        start_time_str = format_time_srt(current_block_start_ms / 1000.0)
        end_time_str = format_time_srt(last_word_end_ms / 1000.0)
        if formatted_text_last:
             srt_entry = f"{entry_index}\n{start_time_str} --> {end_time_str}\n{formatted_text_last}"
             srt_blocks.append(srt_entry)

    print(f"{Fore.CYAN}Se generaron {len(srt_blocks)} bloques SRT finales.")
    return srt_blocks
# --- FIN FUNCIÓN CLAVE ---

def main():
    # --- CONFIGURACIÓN ---
    # ¡¡ASEGÚRATE QUE ESTA RUTA ES CORRECTA!!
    base_path = "/Users/rodrigo/NuevoPactoStudio/data/output" 
    # --- FIN CONFIGURACIÓN ---
    
    if not os.path.isdir(base_path):
        print(f"{Fore.RED}Error: Ruta base '{base_path}' no existe.")
        return

    # Listar sermones
    try:
        sermon_dirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d)) and d.startswith('sermon_')]
        sermon_dirs.sort()
    except Exception as e: print(f"{Fore.RED}Error listando sermones: {e}"); return
    if not sermon_dirs: print(f"{Fore.RED}No se encontraron directorios 'sermon_...' en '{base_path}'"); return

    print(f"\n{Fore.CYAN}Sermones disponibles:")
    for i, d in enumerate(sermon_dirs, 1): print(f"{Fore.GREEN}{i}.{Style.RESET_ALL} {d}")

    # Seleccionar Sermón
    selected_dir = None
    while selected_dir is None:
        try:
            selection_input = input(f"\n{Fore.YELLOW}Seleccione número del sermón: {Style.RESET_ALL}")
            if not selection_input.isdigit(): print(f"{Fore.RED}Entrada inválida."); continue
            selection = int(selection_input) - 1
            if 0 <= selection < len(sermon_dirs): selected_dir = sermon_dirs[selection]
            else: print(f"{Fore.RED}Número fuera de rango.")
        except ValueError: print(f"{Fore.RED}Entrada inválida.")

    full_path = os.path.join(base_path, selected_dir)
    json_path = os.path.join(full_path, "json")
    text_path = os.path.join(full_path, "text")

    if not os.path.isdir(json_path): print(f"{Fore.RED}Error: Dir JSON '{json_path}' no existe."); return
    os.makedirs(text_path, exist_ok=True)

    # Listar JSONs
    try:
        json_files = [f for f in os.listdir(json_path) if f.endswith('.json')]
        json_files.sort()
    except Exception as e: print(f"{Fore.RED}Error listando JSONs: {e}"); return
    if not json_files: print(f"{Fore.RED}No se encontraron JSONs en '{json_path}'"); return

    print(f"\n{Fore.CYAN}Archivos JSON en '{selected_dir}/json':")
    for i, f in enumerate(json_files, 1): print(f"{Fore.GREEN}{i}.{Style.RESET_ALL} {f}")

    # Seleccionar JSON
    selected_json = None
    while selected_json is None:
        try:
            json_selection_input = input(f"\n{Fore.YELLOW}Seleccione número del JSON a editar: {Style.RESET_ALL}")
            if not json_selection_input.isdigit(): print(f"{Fore.RED}Entrada inválida."); continue
            json_selection = int(json_selection_input) - 1
            if 0 <= json_selection < len(json_files): selected_json = json_files[json_selection]
            else: print(f"{Fore.RED}Número fuera de rango.")
        except ValueError: print(f"{Fore.RED}Entrada inválida.")

    json_full_path = os.path.join(json_path, selected_json)

    # --- INSTRUCCIONES DE EDICIÓN ACTUALIZADAS ---
    print(f"\n{Fore.CYAN}Abriendo '{selected_json}' en VS Code...")
    print(f"{Fore.YELLOW}IMPORTANTE:{Style.RESET_ALL} Edita {Fore.GREEN}SOLAMENTE{Style.RESET_ALL} el campo {Fore.MAGENTA}'text'{Style.RESET_ALL} dentro de {Fore.MAGENTA}CADA OBJETO EN LA LISTA 'words'{Style.RESET_ALL} (al final del archivo).")
    print(f"{Fore.YELLOW}Puede ser largo, pero asegura la sincronización.")
    print(f"{Fore.YELLOW}NO modifiques 'start', 'end' ni la estructura JSON.")
    print(f"{Fore.YELLOW}Guarda (Ctrl+S o Cmd+S) y cierra VS Code para continuar.\n")
    # --- FIN INSTRUCCIONES DE EDICIÓN ACTUALIZADAS ---

    code_command = "code"
    if sys.platform == "darwin":
        common_paths = ["/usr/local/bin/code", "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"]
        found = False
        for path in common_paths:
            if os.path.exists(path): code_command = f'"{path}"'; found = True; break
        if not found: print(f"{Fore.YELLOW}Adv: 'code' no encontrado. Intentando comando 'code'.")
    use_shell = True

    try:
        process = subprocess.run(f'{code_command} --wait "{json_full_path}"', check=True, shell=True, text=True, capture_output=True, encoding='utf-8', errors='ignore')
        print(f"{Fore.GREEN}VS Code cerrado.")
    except FileNotFoundError: print(f"{Fore.RED}Error: Comando 'code' no encontrado."); return
    except subprocess.CalledProcessError as e: print(f"{Fore.RED}Error VS Code. Stderr: {e.stderr}"); return
    except Exception as e: print(f"{Fore.RED}Error abriendo VS Code: {e}"); return

    print(f"\n{Fore.CYAN}Cargando JSON editado: {json_full_path}")
    try:
        with open(json_full_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            if not raw_content.strip(): print(f"{Fore.RED}Error: JSON '{selected_json}' está vacío."); return
            f.seek(0)
            data = json.load(f)
    except json.JSONDecodeError as e: print(f"{Fore.RED}Error en formato JSON: {e}\n{Fore.YELLOW}Revisa '{selected_json}'."); return
    except FileNotFoundError: print(f"{Fore.RED}Error: No se encontró '{json_full_path}'."); return
    except Exception as e: print(f"{Fore.RED}Error leyendo JSON: {e}"); return

    # --- LÓGICA DE GENERACIÓN ACTUALIZADA ---
    words_edited = data.get('words')
    if not words_edited or not isinstance(words_edited, list):
        print(f"{Fore.RED}Error: No se encontró la lista 'words' o está vacía/inválida en el JSON.")
        return

    print(f"\n{Fore.CYAN}Generando SRT desde la lista 'words' editada...")
    # Usar la función que agrupa palabras editadas en bloques SRT cortos y sincronizados
    srt_content = generate_srt_entries_from_words(words_edited)
    # --- FIN LÓGICA DE GENERACIÓN ACTUALIZADA ---

    if not srt_content:
        print(f"{Fore.RED}No se generó contenido SRT. Verifica la lista 'words' editada."); return

    # Nombre de archivo final
    video_name_base = os.path.splitext(selected_json)[0] # Base inicial
    if data.get('video_filename'): video_name_base = os.path.splitext(os.path.basename(data['video_filename']))[0]
    elif data.get('audio_file'): video_name_base = os.path.splitext(os.path.basename(data['audio_file']))[0]

    # Sufijo claro para indicar el método
    srt_name = f"{video_name_base}_subtitles_edit.srt" 
    srt_path = os.path.join(text_path, srt_name)

    try:
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(srt_content) + '\n\n')
        print(f"\n{Fore.GREEN}{Style.BRIGHT}¡Éxito! Archivo SRT sincronizado y editado guardado como: {srt_path}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error al guardar SRT '{srt_path}': {e}")

if __name__ == "__main__":
    main()
