"""
Módulo de transcripción de audio/video.

Este módulo proporciona funcionalidades para la transcripción de audio y video
utilizando el modelo Whisper de OpenAI con detección inteligente de silencios.
"""

import os
import ffmpeg
from openai import OpenAI
from datetime import datetime
import json
from pydub import AudioSegment
from pydub.silence import split_on_silence
import glob

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
        self.client = OpenAI(api_key=api_key)
        
        # La carpeta específica de salida se creará con la fecha al transcribir

    def _create_output_dir(self, video_filename):
        """
        Crea una carpeta de salida con formato sermon_DDMMAA_XX.
        
        Args:
            video_filename (str): Nombre del archivo de video
            
        Returns:
            str: Ruta a la carpeta de salida creada
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
        
        # Crear la carpeta con el formato correcto
        output_dir = os.path.join(self.output_base_dir, f"{output_prefix}{counter:02d}")
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Carpeta de salida creada: {output_dir}")
        return output_dir

    def extract_audio(self, video_path, output_dir):
        """
        Extrae el audio de un archivo de video.
        
        Args:
            video_path (str): Ruta completa al archivo de video
            output_dir (str): Directorio donde guardar el audio
            
        Returns:
            str: Ruta al archivo de audio extraído
        """
        # Construir el nombre del archivo de audio basado en el video original
        video_filename = os.path.basename(video_path)
        audio_filename = os.path.splitext(video_filename)[0] + "_audio.wav"
        audio_path = os.path.join(output_dir, audio_filename)
        
        try:
            # Configurar el proceso de FFmpeg para extraer audio
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(stream, audio_path,
                                 acodec='pcm_s16le',  # Codec de audio sin pérdida
                                 ac=1,                 # Mono (1 canal)
                                 ar='16k')            # Frecuencia de muestreo de 16kHz
            
            # Ejecutar el proceso de FFmpeg
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            return audio_path
            
        except ffmpeg.Error as e:
            error_message = f"Error al extraer audio de {video_path}: {str(e)}"
            raise Exception(error_message)

    def split_audio_hybrid(self, audio_path, output_dir, segment_duration=600):
        """
        Divide un archivo de audio usando un enfoque híbrido:
        1. Divide en segmentos grandes de duración fija
        2. Refina los puntos de corte buscando silencios cercanos
        
        Args:
            audio_path (str): Ruta al archivo de audio
            output_dir (str): Directorio donde guardar los segmentos
            segment_duration (int): Duración objetivo de cada segmento en segundos
            
        Returns:
            list: Lista de rutas a los segmentos de audio generados
        """
        try:
            # Obtenemos la duración del audio usando ffprobe
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['format']['duration'])
            print(f"Duración total del audio: {duration} segundos")

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
                segment_path = os.path.join(output_dir, segment_filename)
                
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
                
                # Exportar el segmento
                basename = os.path.splitext(os.path.basename(audio_path))[0]
                segment_filename = f"{basename}_segment_{i+1}.mp3"
                segment_path = os.path.join(output_dir, segment_filename)
                
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
            return self.split_audio_by_time(audio_path, output_dir)
                
    def split_audio_by_time(self, audio_path, output_dir, segment_duration=600):
        """
        Método de respaldo: divide un archivo de audio en segmentos de duración fija.
        
        Args:
            audio_path (str): Ruta al archivo de audio completo
            output_dir (str): Directorio donde guardar los segmentos
            segment_duration (int): Duración de cada segmento en segundos
            
        Returns:
            list: Lista de rutas a los segmentos de audio generados
        """
        try:
            # Obtenemos la duración del audio usando ffprobe
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['format']['duration'])
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
                        output_dir,
                        f"{os.path.splitext(os.path.basename(audio_path))[0]}_segment_{i+1}.mp3"
                    )
                    # Usamos el formato mp3 para reducir tamaño
                    ffmpeg.input(audio_path, ss=start_time).output(
                        output_segment,
                        acodec='libmp3lame',
                        ac=1,
                        ar='16k',
                        ab='32k'
                    ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
                else:
                    output_segment = os.path.join(
                        output_dir,
                        f"{os.path.splitext(os.path.basename(audio_path))[0]}_segment_{i+1}.mp3"
                    )
                    ffmpeg.input(audio_path, ss=start_time, t=segment_duration).output(
                        output_segment,
                        acodec='libmp3lame',
                        ac=1,
                        ar='16k',
                        ab='32k'
                    ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)

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
                # Realizamos la transcripción usando la API de OpenAI
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="es",
                    response_format="verbose_json"
                )
            
            # Procesamos la respuesta para extraer información útil
            segments_list = []
            if hasattr(response, 'segments'):
                for seg in response.segments:
                    segment_dict = {
                        'start': float(seg.start),
                        'end': float(seg.end),
                        'text': seg.text
                    }
                    segments_list.append(segment_dict)
            
            transcription_data = {
                'text': response.text,  # Texto completo de la transcripción
                'segments': segments_list,  # Lista de diccionarios con segmentos
                'timestamp': datetime.now().isoformat(),  # Cuándo se realizó
                'audio_file': audio_path  # Referencia al archivo original
            }
            
            # Agregamos texto a la transcripción
            all_text = response.text.strip()
            print(f"Transcripción: \"{all_text[:100]}...\"")
            
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
            output_dir = self._create_output_dir(video_filename)
            
            # Paso 1: Extraer el audio del video
            print(f"Extrayendo audio de {video_filename}...")
            audio_path = self.extract_audio(video_path, output_dir)
            
            # Paso 2: Dividir el audio usando enfoque híbrido
            print(f"Dividiendo el audio usando enfoque híbrido...")
            audio_segments = self.split_audio_hybrid(audio_path, output_dir)
            
            # Paso 3: Transcribir cada segmento
            print(f"Transcribiendo {len(audio_segments)} segmentos...")
            
            all_transcription_data = {
                'text': '',
                'segments': [],
                'audio_file': audio_path,
                'timestamp': datetime.now().isoformat()
            }
            
            # Procesamos cada segmento
            offset = 0  # Para ajustar las marcas de tiempo
            
            for i, segment_path in enumerate(audio_segments):
                print(f"Transcribiendo segmento {i+1}/{len(audio_segments)}...")
                try:
                    segment_data = self.transcribe_audio(segment_path)
                    
                    # Calcular offset para este segmento
                    if i > 0:
                        # Obtener duración del segmento anterior
                        probe = ffmpeg.probe(audio_segments[i-1])
                        prev_duration = float(probe['format']['duration'])
                        offset += prev_duration
                    
                    # Ajustamos las marcas de tiempo
                    for segment in segment_data['segments']:
                        segment['start'] += offset
                        segment['end'] += offset
                        
                    # Añadimos el texto a la transcripción completa
                    all_transcription_data['text'] += ' ' + segment_data['text']
                    # Añadimos los segmentos a la lista completa
                    all_transcription_data['segments'].extend(segment_data['segments'])
                    
                except Exception as e:
                    print(f"Error transcribiendo segmento {i+1}: {str(e)}")
                    # Continuamos con el siguiente segmento incluso si este falla
            
            # Paso 4: Guardar los resultados
            output_filename = os.path.splitext(video_filename)[0] + "_transcription.json"
            output_path = os.path.join(output_dir, output_filename)
            
            # Añadimos información adicional útil
            all_transcription_data.update({
                'video_filename': video_filename,
                'processing_date': datetime.now().isoformat(),
                'video_path': video_path,
                'total_segments': len(audio_segments)
            })
            
            # Guardamos la transcripción en formato JSON
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(all_transcription_data, f, ensure_ascii=False, indent=4)
                print(f"Transcripción completada y guardada en: {output_path}")
                
                # Exportamos también como texto plano para revisión humana
                self.export_plain_text(all_transcription_data, output_dir)
            except Exception as e:
                print(f"Error al guardar el archivo JSON: {str(e)}")
            
            return all_transcription_data
            
        except Exception as e:
            error_message = f"Error procesando el video {video_filename}: {str(e)}"
            print(error_message)
            raise Exception(error_message)

    def export_plain_text(self, transcription_data, output_dir, output_filename=None):
        """
        Exporta la transcripción a un archivo de texto plano para revisión humana.
        
        Args:
            transcription_data (dict): Datos de la transcripción
            output_dir (str): Directorio donde guardar el archivo de texto
            output_filename (str, optional): Nombre del archivo de salida
                                            
        Returns:
            str: Ruta al archivo de texto creado
        """
        if not output_filename:
            # Si no se proporciona un nombre, derivamos uno del nombre del archivo de audio
            video_name = os.path.basename(transcription_data.get('video_path', ''))
            base_name = os.path.splitext(video_name)[0]
            output_filename = f"{base_name}_transcript.txt"
        
        output_path = os.path.join(output_dir, output_filename)
        
        # Contenido para el archivo de texto
        content = []
        
        # Añadimos un encabezado
        content.append(f"TRANSCRIPCIÓN: {transcription_data.get('video_filename', 'Archivo')}")
        content.append(f"Fecha de procesamiento: {transcription_data.get('processing_date', 'Desconocida')}")
        content.append("")  # Línea en blanco
        content.append("=" * 80)  # Separador
        content.append("")  # Línea en blanco
        
        # Añadimos el texto principal
        content.append(transcription_data.get('text', '').strip())
        
        # Guardamos el contenido en el archivo
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        print(f"Transcripción en texto plano guardada en: {output_path}")
        return output_path
