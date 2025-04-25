"""
Módulo de transcripción de audio/video.

Este módulo proporciona funcionalidades para la transcripción de audio y video
utilizando el modelo Whisper de OpenAI con detección inteligente de silencios.
"""

import os
import subprocess
import openai
from datetime import datetime
import json
from pydub import AudioSegment
from pydub.silence import split_on_silence
import glob
import shutil

class AudioTranscriber:
    """
    Clase para manejar la transcripción de audio y video.
    
    Proporciona funcionalidades para:
    1. Procesar archivos de video
    2. Extraer y segmentar audio usando detección híbrida
    3. Realizar transcripción con Whisper API
    4. Generar archivos de salida en JSON y texto plano
    """

    def __init__(self, input_dir, output_dir, api_key):
        """
        Inicializa el transcriptor con las configuraciones necesarias.

        Args:
            input_dir (str): Ruta al directorio de videos de entrada
            output_dir (str): Ruta al directorio base donde se guardarán las transcripciones
            api_key (str): Clave de API de OpenAI
        """
        self.input_dir = input_dir
        self.output_base_dir = output_dir
        # Configurar con la versión antigua de OpenAI
        openai.api_key = api_key
        self.client = openai
        
        # La carpeta específica de salida se creará con la fecha al transcribir

    def _create_output_dir(self, video_filename):
        """
        Crea una carpeta de salida con formato sermon_DDMMAA_XX y subcarpetas para cada tipo de archivo.
        
        Args:
            video_filename (str): Nombre del archivo de video
            
        Returns:
            dict: Diccionario con las rutas a las diferentes carpetas
        """
        # Generar formato de fecha DDMMAA
        today = datetime.now().strftime("%d%m%y")
        base_name = os.path.splitext(video_filename)[0]
        output_prefix = f"sermon_{today}_"
        
        # Buscar carpetas existentes con el mismo prefijo de fecha
        existing_dirs = glob.glob(os.path.join(self.output_base_dir, f"{output_prefix}*"))
        
        # Determinar el número de contador
        if not existing_dirs:
            counter = 1
        else:
            # Extraer los números de contador existentes
            counters = []
            for dir_path in existing_dirs:
                dir_name = os.path.basename(dir_path)
                try:
                    counter_str = dir_name.replace(output_prefix, "")
                    counters.append(int(counter_str))
                except ValueError:
                    continue
            
            if counters:
                counter = max(counters) + 1
            else:
                counter = 1
        
        # Crear la carpeta principal con el formato correcto
        main_output_dir = os.path.join(self.output_base_dir, f"{output_prefix}{counter:02d}")
        os.makedirs(main_output_dir, exist_ok=True)
        
        # Crear subcarpetas para cada tipo de archivo
        audio_dir = os.path.join(main_output_dir, "audio")
        json_dir = os.path.join(main_output_dir, "json")
        text_dir = os.path.join(main_output_dir, "text")
        temp_dir = os.path.join(main_output_dir, "temp")
        
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(json_dir, exist_ok=True)
        os.makedirs(text_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        print(f"Carpeta de salida creada: {main_output_dir}")
        print(f"  - Audio: {audio_dir}")
        print(f"  - JSON: {json_dir}")
        print(f"  - Texto: {text_dir}")
        print(f"  - Temp: {temp_dir}")
        
        # Devolver un diccionario con las rutas
        return {
            "main": main_output_dir,
            "audio": audio_dir,
            "json": json_dir,
            "text": text_dir,
            "temp": temp_dir
        }

    def extract_audio(self, video_path, output_dirs):
        """
        Extrae el audio de un archivo de video.
        
        Args:
            video_path (str): Ruta completa al archivo de video
            output_dirs (dict): Diccionario con las rutas de salida
            
        Returns:
            str: Ruta al archivo de audio extraído
        """
        # Construir el nombre del archivo de audio basado en el video original
        video_filename = os.path.basename(video_path)
        audio_filename = os.path.splitext(video_filename)[0] + "_audio.wav"
        audio_path = os.path.join(output_dirs["audio"], audio_filename)
        
        try:
            # Usar subprocess directamente en lugar de ffmpeg-python
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-acodec', 'pcm_s16le',
                '-ac', '1',
                '-ar', '16k',
                '-y',  # Sobrescribir si existe
                audio_path
            ]
            
            # Ejecutar el proceso
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            return audio_path
            
        except subprocess.CalledProcessError as e:
            error_message = f"Error al extraer audio de {video_path}: {e.stderr}"
            raise Exception(error_message)
        except Exception as e:
            error_message = f"Error inesperado al extraer audio: {str(e)}"
            raise Exception(error_message)

    def split_audio_hybrid(self, audio_path, output_dirs, segment_duration=600):
        """
        Divide un archivo de audio usando un enfoque híbrido:
        1. Divide en segmentos grandes de duración fija
        2. Refina los puntos de corte buscando silencios cercanos
        
        Args:
            audio_path (str): Ruta al archivo de audio
            output_dirs (dict): Diccionario con las rutas de salida
            segment_duration (int): Duración objetivo de cada segmento en segundos
            
        Returns:
            list: Lista de rutas a los segmentos de audio generados
        """
        try:
            # Obtenemos la duración del audio usando ffprobe
            try:
                cmd = [
                    'ffprobe', 
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    audio_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                duration = float(result.stdout.strip())
                print(f"Duración total del audio: {duration} segundos")
            except subprocess.CalledProcessError as e:
                print(f"Error al obtener duración: {e.stderr}")
                raise

            # Cargamos el audio con pydub para buscar silencios
            audio = AudioSegment.from_wav(audio_path)
            
            # Calculamos cuántos segmentos necesitamos
            num_segments = int(duration / segment_duration) + 1
            print(f"Planificando {num_segments} segmentos de aproximadamente {segment_duration} segundos")
            
            # Lista para almacenar las rutas de los segmentos
            segment_paths = []
            
            # Si el audio es corto, no lo segmentamos
            if duration <= segment_duration:
                basename = os.path.splitext(os.path.basename(audio_path))[0]
                segment_filename = f"{basename}_segment_1.mp3"
                segment_path = os.path.join(output_dirs["temp"], segment_filename)
                
                # Convertir el audio completo a mp3 para reducir tamaño
                audio.export(
                    segment_path,
                    format="mp3",
                    parameters=["-ac", "1", "-ar", "16000", "-b:a", "32k"]
                )
                segment_paths.append(segment_path)
                print(f"Audio corto: se creó un solo segmento: {segment_path}")
                return segment_paths
            
            # Para cada punto de corte teórico, buscamos un silencio cercano
            for i in range(num_segments):
                # Punto de corte teórico (tiempo)
                target_time_ms = i * segment_duration * 1000  # Convertir a milisegundos
                
                # Si es el último segmento o estamos más allá del final, terminamos
                if target_time_ms >= len(audio):
                    break
                
                # Definir el rango de búsqueda de silencio (± 30 segundos)
                silence_search_range = 30 * 1000  # 30 segundos en ms
                
                # Ajustar el rango para no salir de los límites del audio
                start_search = max(0, target_time_ms - silence_search_range)
                end_search = min(len(audio), target_time_ms + silence_search_range)
                
                # Si es el primer segmento, lo tomamos desde el principio
                if i == 0:
                    start_time = 0
                else:
                    # Buscar silencios en el rango
                    silences = split_on_silence(
                        audio[start_search:end_search],
                        min_silence_len=700,        # Mínimo 700ms de silencio
                        silence_thresh=-40,         # Umbral de silencio (dB)
                        keep_silence=300            # Mantener 300ms de silencio
                    )
                    
                    # Si no encontramos silencios, usamos el punto teórico
                    if not silences:
                        start_time = target_time_ms
                        print(f"No se encontraron silencios cerca de {target_time_ms/1000}s, usando punto fijo")
                    else:
                        # Elegimos el silencio más cercano al punto teórico
                        silence_positions = []
                        current_pos = start_search
                        
                        for silence in silences:
                            silence_start = current_pos + len(silence) / 2  # Punto medio del silencio
                            silence_positions.append(silence_start)
                            current_pos += len(silence)
                        
                        # Encontrar el silencio más cercano al punto teórico
                        closest_silence = min(silence_positions, key=lambda x: abs(x - target_time_ms))
                        start_time = closest_silence
                        print(f"Silencio encontrado a {start_time/1000}s (cercano a {target_time_ms/1000}s)")
                
                # Definir el fin del segmento (inicio del siguiente o fin del audio)
                if i == num_segments - 1:
                    end_time = len(audio)
                else:
                    next_target = (i + 1) * segment_duration * 1000
                    end_search_next = min(len(audio), next_target + silence_search_range)
                    
                    # Buscar silencios para el siguiente punto de corte
                    next_start_search = max(0, next_target - silence_search_range)
                    silences_next = split_on_silence(
                        audio[next_start_search:end_search_next],
                        min_silence_len=700,
                        silence_thresh=-40,
                        keep_silence=300
                    )
                    
                    if not silences_next:
                        end_time = next_target
                    else:
                        # Elegimos el silencio más cercano al siguiente punto teórico
                        silence_positions = []
                        current_pos = next_start_search
                        
                        for silence in silences_next:
                            silence_start = current_pos + len(silence) / 2
                            silence_positions.append(silence_start)
                            current_pos += len(silence)
                        
                        closest_silence = min(silence_positions, key=lambda x: abs(x - next_target))
                        end_time = closest_silence
                
                # Asegurarse de que el segmento no sea vacío o demasiado corto
                if end_time <= start_time or end_time - start_time < 5000:  # menos de 5 segundos
                    continue
                
                # Exportar el segmento a la carpeta temporal
                basename = os.path.splitext(os.path.basename(audio_path))[0]
                segment_filename = f"{basename}_segment_{i+1}.mp3"
                segment_path = os.path.join(output_dirs["temp"], segment_filename)
                
                segment_audio = audio[start_time:end_time]
                segment_audio.export(
                    segment_path,
                    format="mp3",
                    parameters=["-ac", "1", "-ar", "16000", "-b:a", "32k"]
                )
                
                segment_paths.append(segment_path)
                print(f"Creado segmento {i+1} ({(end_time-start_time)/1000}s): {segment_path}")
                
            return segment_paths

        except Exception as e:
            error_message = f"Error al dividir el audio {audio_path}: {str(e)}"
            print(error_message)
            # En caso de error, intentamos la división básica por tiempo
            print("Recurriendo a división por tiempo estándar...")
            return self.split_audio_by_time(audio_path, output_dirs)
                
    def split_audio_by_time(self, audio_path, output_dirs, segment_duration=600):
        """
        Método de respaldo: divide un archivo de audio en segmentos de duración fija.
        
        Args:
            audio_path (str): Ruta al archivo de audio completo
            output_dirs (dict): Diccionario con las rutas de salida
            segment_duration (int): Duración de cada segmento en segundos
            
        Returns:
            list: Lista de rutas a los segmentos de audio generados
        """
        try:
            # Obtenemos la duración del audio usando ffprobe
            cmd = [
                'ffprobe', 
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            print(f"Duración total del audio: {duration} segundos")

            # Calculamos cuántos segmentos necesitamos
            num_segments = int(duration / segment_duration) + 1
            print(f"Dividiendo en {num_segments} segmentos de {segment_duration} segundos")

            # Creamos cada segmento
            segments = []
            for i in range(num_segments):
                start_time = i * segment_duration
                # Si es el último segmento, ajustamos la duración
                if i == num_segments - 1:
                    # No especificamos duración para el último segmento
                    output_segment = os.path.join(
                        output_dirs["temp"],
                        f"{os.path.splitext(os.path.basename(audio_path))[0]}_segment_{i+1}.mp3"
                    )
                    
                    # Usar ffmpeg con subprocess
                    cmd = [
                        'ffmpeg',
                        '-i', audio_path,
                        '-ss', str(start_time),
                        '-acodec', 'libmp3lame',
                        '-ac', '1',
                        '-ar', '16k',
                        '-ab', '32k',
                        '-y',
                        output_segment
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)
                else:
                    output_segment = os.path.join(
                        output_dirs["temp"],
                        f"{os.path.splitext(os.path.basename(audio_path))[0]}_segment_{i+1}.mp3"
                    )
                    
                    # Usar ffmpeg con subprocess
                    cmd = [
                        'ffmpeg',
                        '-i', audio_path,
                        '-ss', str(start_time),
                        '-t', str(segment_duration),
                        '-acodec', 'libmp3lame',
                        '-ac', '1',
                        '-ar', '16k',
                        '-ab', '32k',
                        '-y',
                        output_segment
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)

                segments.append(output_segment)
                print(f"Creado segmento {i+1}/{num_segments}: {output_segment}")

            return segments

        except Exception as e:
            error_message = f"Error al dividir el audio {audio_path}: {str(e)}"
            print(error_message)
            raise Exception(error_message)

    def transcribe_audio(self, audio_path):
        """
        Transcribe un archivo de audio usando el modelo Whisper de OpenAI.
        
        Args:
            audio_path (str): Ruta al archivo de audio a transcribir
            
        Returns:
            dict: Diccionario con la transcripción y metadatos asociados
        """
        try:
            # Abrimos el archivo de audio en modo binario
            with open(audio_path, 'rb') as audio_file:
                # Usar la API antigua de OpenAI
                response = self.client.Audio.transcribe(
                    "whisper-1",
                    audio_file,
                    language="es",
                    response_format="verbose_json"
                )
            
            # Procesamos la respuesta para extraer información útil
            segments_list = []
            if 'segments' in response:
                for seg in response['segments']:
                    segment_dict = {
                        'start': float(seg['start']),
                        'end': float(seg['end']),
                        'text': seg['text']
                    }
                    segments_list.append(segment_dict)
            
            transcription_data = {
                'text': response['text'],  # Texto completo de la transcripción
                'segments': segments_list,  # Lista de diccionarios con segmentos
                'timestamp': datetime.now().isoformat(),  # Cuándo se realizó
                'audio_file': audio_path  # Referencia al archivo original
            }
            
            # Mostramos parte de la transcripción
            all_text = response['text'].strip()
            if all_text:
                print(f"Transcripción: \"{all_text[:100]}...\"")
            else:
                print("No se obtuvo texto en la transcripción")
            
            return transcription_data
            
        except Exception as e:
            error_message = f"Error durante la transcripción de {audio_path}: {str(e)}"
            raise Exception(error_message)

    def process_video(self, video_filename):
        """
        Procesa un video completo, desde la extracción de audio hasta la transcripción.
        
        Args:
            video_filename (str): Nombre del archivo de video a procesar
            
        Returns:
            dict: Diccionario con la transcripción y toda la información asociada
        """
        try:
            # Construimos la ruta completa al archivo de video
            video_path = os.path.join(self.input_dir, video_filename)
            
            # Verificamos que el archivo existe
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"No se encontró el archivo: {video_path}")
            
            # Crear directorio de salida con formato sermon_DDMMAA_XX
            output_dirs = self._create_output_dir(video_filename)
            
            # Paso 1: Extraer el audio del video
            print(f"Extrayendo audio de {video_filename}...")
            audio_path = self.extract_audio(video_path, output_dirs)
            
            # Paso 2: Dividir el audio usando enfoque híbrido
            print(f"Dividiendo el audio usando enfoque híbrido...")
            audio_segments = self.split_audio_hybrid(audio_path, output_dirs)
            
            # Paso 3: Transcribir cada segmento
            print(f"Transcribiendo {len(audio_segments)} segmentos...")
            
            all_transcription_data = {
                'text': '',
                'segments': [],
                'audio_file': audio_path,
                'timestamp': datetime.now().isoformat()
            }
            
            # Crear archivos parciales para cada segmento
            for i, segment_path in enumerate(audio_segments):
                print(f"Transcribiendo segmento {i+1}/{len(audio_segments)}...")
                try:
                    segment_data = self.transcribe_audio(segment_path)
                    
                    # Guardar transcripción parcial en JSON
                    segment_json_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_segment_{i+1}.json"
                    segment_json_path = os.path.join(output_dirs["json"], segment_json_filename)
                    with open(segment_json_path, 'w', encoding='utf-8') as f:
                        json.dump(segment_data, f, ensure_ascii=False, indent=4)
                    
                    # Guardar transcripción parcial en texto
                    segment_text_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_segment_{i+1}.txt"
                    segment_text_path = os.path.join(output_dirs["text"], segment_text_filename)
                    with open(segment_text_path, 'w', encoding='utf-8') as f:
                        f.write(segment_data['text'])
                    
                    # Copiar segmento de audio a la carpeta final
                    segment_audio_filename = os.path.basename(segment_path)
                    segment_audio_path = os.path.join(output_dirs["audio"], segment_audio_filename)
                    shutil.copy2(segment_path, segment_audio_path)
                    
                    # Agregar a la transcripción completa
                    all_transcription_data['text'] += ' ' + segment_data['text']
                    
                    # Calcular offset para ajustar tiempos
                    offset = 0
                    if i > 0:
                        for j in range(i):
                            # Obtener duración del segmento anterior
                            prev_json_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_segment_{j+1}.json"
                            prev_json_path = os.path.join(output_dirs["json"], prev_json_filename)
                            with open(prev_json_path, 'r', encoding='utf-8') as f:
                                prev_data = json.load(f)
                            if prev_data['segments']:
                                offset += prev_data['segments'][-1]['end']
                    
                    # Ajustar tiempos y añadir segmentos
                    for segment in segment_data['segments']:
                        segment['start'] += offset
                        segment['end'] += offset
                        all_transcription_data['segments'].append(segment)
                    
                except Exception as e:
                    print(f"Error transcribiendo segmento {i+1}: {str(e)}")
                    # Continuamos con el siguiente segmento incluso si este falla
            
            # Paso 4: Guardar los resultados completos
            output_filename = os.path.splitext(video_filename)[0] + "_transcription_completa.json"
            output_path = os.path.join(output_dirs["json"], output_filename)
            
            # Añadimos información adicional útil
            all_transcription_data.update({
                'video_filename': video_filename,
                'processing_date': datetime.now().isoformat(),
                'video_path': video_path,
                'total_segments': len(audio_segments)
            })
            
            # Guardamos la transcripción completa en formato JSON
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(all_transcription_data, f, ensure_ascii=False, indent=4)
                print(f"Transcripción completa guardada en: {output_path}")
                
                # Exportamos también como texto plano completo
                text_output_filename = os.path.splitext(video_filename)[0] + "_transcription_completa.txt"
                text_output_path = os.path.join(output_dirs["text"], text_output_filename)
                
                # Contenido para el archivo de texto
                content = []
                content.append(f"TRANSCRIPCIÓN COMPLETA: {video_filename}")
                content.append(f"Fecha de procesamiento: {datetime.now().isoformat()}")
                content.append("")  # Línea en blanco
                content.append("=" * 80)  # Separador
                content.append("")  # Línea en blanco
                content.append(all_transcription_data['text'].strip())
                
                with open(text_output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(content))
                print(f"Transcripción completa en texto guardada en: {text_output_path}")
                
                # Crear versión MP3 completa
                complete_audio_filename = os.path.splitext(video_filename)[0] + "_audio_completo.mp3"
                complete_audio_path = os.path.join(output_dirs["audio"], complete_audio_filename)
                
                # Copiar el archivo WAV original como MP3
                cmd = [
                    'ffmpeg',
                    '-i', audio_path,
                    '-acodec', 'libmp3lame',
                    '-ac', '1',
                    '-ar', '16k',
                    '-ab', '64k',
                    '-y',
                    complete_audio_path
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                print(f"Audio completo guardado en: {complete_audio_path}")
                
            except Exception as e:
                print(f"Error al guardar archivos finales: {str(e)}")
            
            return all_transcription_data
            
        except Exception as e:
            error_message = f"Error procesando el video {video_filename}: {str(e)}"
            print(error_message)
            raise Exception(error_message)
