"""
Script principal para transcribir videos usando AssemblyAI.
"""
import os
import sys
import glob
import json
import time
from datetime import datetime

# Añadir la ruta del proyecto para importaciones
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class AssemblyAITranscriber:
    """
    Clase para manejar la transcripción de audio y video usando AssemblyAI.
    """

    def __init__(self, input_dir, output_dir, api_key):
        """
        Inicializa el transcriptor con las configuraciones necesarias.
        """
        self.input_dir = input_dir
        self.output_base_dir = output_dir
        
        # Configurar cliente de AssemblyAI
        import assemblyai as aai
        aai.settings.api_key = api_key
        self.transcriber = aai.Transcriber()
        
    def _format_time_srt(self, seconds):
        """Convierte segundos a formato HH:MM:SS,mmm para SRT"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

    def _generate_srt_entries(self, transcription_data):
        """
        Genera entradas SRT a partir de los datos de transcripción.
        Prioriza usar las marcas de tiempo a nivel de palabra para mayor precisión.
        """
        # Verificar si hay palabras con marcas de tiempo precisas
        if 'words' in transcription_data and transcription_data['words']:
            print("Generando SRT usando marcas de tiempo a nivel de palabra para mayor precisión...")
            words = transcription_data['words']
            
            # Crear segmentos a partir de palabras
            segments = []
            current_words = []
            current_start = None
            
            # Parámetros de segmentación
            max_words_per_segment = 8
            max_segment_duration = 3000  # 3 segundos en ms
            
            for i, word in enumerate(words):
                # Si es la primera palabra del segmento, marcar tiempo de inicio
                if not current_words:
                    current_start = word['start']
                
                current_words.append(word)
                
                # Verificar si debemos cerrar el segmento actual
                ends_with_strong_punct = word['text'].rstrip().endswith(('.', '!', '?'))
                ends_with_weak_punct = word['text'].rstrip().endswith((',', ';', ':'))
                current_duration = word['end'] - current_start
                
                if (ends_with_strong_punct or
                    (ends_with_weak_punct and len(current_words) >= 3) or
                    len(current_words) >= max_words_per_segment or
                    current_duration >= max_segment_duration or
                    i == len(words) - 1):
                    
                    # Combinar las palabras en un texto
                    text = ' '.join(w['text'] for w in current_words)
                    
                    # Añadir segmento
                    segments.append({
                        'index': len(segments) + 1,
                        'start': current_start / 1000,  # Convertir a segundos
                        'end': word['end'] / 1000,      # Convertir a segundos
                        'text': text
                    })
                    
                    # Reiniciar para el siguiente segmento
                    current_words = []
                    current_start = None
            
            # Generar entradas SRT a partir de los segmentos
            srt_content = []
            for segment in segments:
                # Formatear tiempos
                start_formatted = self._format_time_srt(segment['start'])
                end_formatted = self._format_time_srt(segment['end'])
                
                # Formatear texto (máximo 2 líneas)
                text = segment['text']
                if len(text) > 40:
                    text = self._format_multi_line(text)
                
                # Crear entrada SRT
                srt_entry = f"{segment['index']}\n{start_formatted} --> {end_formatted}\n{text}"
                srt_content.append(srt_entry)
            
            return srt_content
        
        # Si no hay marcas de tiempo a nivel de palabra, usar segmentos
        print("Generando SRT usando segmentos (menos preciso)...")
        return self._generate_srt_from_segments(transcription_data)
    
    def _format_multi_line(self, text, max_chars_per_line=40):
        """
        Formatea un texto en máximo 2 líneas para subtitulado.
        """
        if len(text) <= max_chars_per_line:
            return text
        
        # Intentar dividir por puntos naturales cerca de la mitad
        words = text.split()
        half_len = len(text) // 2
        
        # Buscar espacios cerca del punto medio
        split_index = None
        for i in range(half_len - 15, half_len + 15):
            if i >= 0 and i < len(text) and text[i] == ' ':
                split_index = i
                break
        
        # Si no encontramos un buen punto de división, dividir entre palabras
        if split_index is None:
            current_len = 0
            for i, word in enumerate(words):
                current_len += len(word) + (1 if i > 0 else 0)
                if current_len > half_len and i > 0:
                    split_index = len(' '.join(words[:i]))
                    break
        
        # Si aún no hay punto de división, dividir exactamente por la mitad
        if split_index is None or split_index <= 0:
            split_index = half_len
        
        # Crear las dos líneas
        line1 = text[:split_index].strip()
        line2 = text[split_index:].strip()
        
        # Limitar cada línea al máximo permitido
        if len(line1) > max_chars_per_line:
            last_space = line1.rfind(' ', 0, max_chars_per_line)
            if last_space != -1:
                line1 = line1[:last_space].strip()
        
        if len(line2) > max_chars_per_line:
            last_space = line2.rfind(' ', 0, max_chars_per_line)
            if last_space != -1:
                line2 = line2[:last_space].strip()
        
        return f"{line1}\n{line2}"
    
    def _generate_srt_from_segments(self, transcription_data):
        """
        Método antiguo para generar SRT a partir de segmentos (menos preciso).
        """
        # Verificar que hay segmentos
        segments = transcription_data.get('segments', [])
        if not segments:
            print("Advertencia: No se encontraron segmentos para generar SRT")
            return []

        srt_content = []
        for i, segment in enumerate(segments, 1):
            try:
                # Validar que los segmentos tengan los campos necesarios
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                text = segment.get('text', '').strip()

                # Validar que el texto no esté vacío
                if not text:
                    continue

                # Formatear tiempos
                start_formatted = self._format_time_srt(start)
                end_formatted = self._format_time_srt(end)

                # Dividir texto en máximo 2 líneas
                if len(text) > 40:
                    text = self._format_multi_line(text)

                # Verificar la duración del segmento
                duration = end - start
                
                # Si la duración es muy larga, acortarla para mejor sincronización
                if duration > 3.0:  # máximo 3 segundos
                    end = start + 3.0
                    end_formatted = self._format_time_srt(end)
                
                # Crear entrada SRT con los tiempos ajustados
                srt_entry = f"{i}\n{start_formatted} --> {end_formatted}\n{text}"
                srt_content.append(srt_entry)

            except Exception as e:
                print(f"Error procesando segmento {i}: {e}")
                continue

        return srt_content

    def _create_output_dir(self, video_filename):
        """
        Crea una carpeta de salida con formato sermon_DDMMAA_XX
        y subcarpetas para cada tipo de archivo.
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
                    # Extraer el número del formato sermon_DDMMAA_XX
                    counter_part = dir_name.replace(output_prefix, "")
                    counters.append(int(counter_part))
                except (ValueError, IndexError):
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
        
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(json_dir, exist_ok=True)
        os.makedirs(text_dir, exist_ok=True)
        
        print(f"Carpeta de salida creada: {main_output_dir}")
        print(f"  - Audio: {audio_dir}")
        print(f"  - JSON: {json_dir}")
        print(f"  - Texto: {text_dir}")
        
        # Devolver un diccionario con las rutas
        return {
            "main": main_output_dir,
            "audio": audio_dir,
            "json": json_dir,
            "text": text_dir
        }

    def extract_audio(self, video_path, output_dirs):
        """
        Extrae el audio de un archivo de video.
        """
        import subprocess
        
        # Construir el nombre del archivo de audio basado en el video original
        video_filename = os.path.basename(video_path)
        audio_filename = os.path.splitext(video_filename)[0] + "_audio.mp3"
        audio_path = os.path.join(output_dirs["audio"], audio_filename)
        
        try:
            # Usar subprocess directamente para extraer audio
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # Sin video
                '-acodec', 'libmp3lame',
                '-ac', '1',  # Mono
                '-ar', '44100',  # 44.1kHz
                '-ab', '128k',  # 128kbps
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

    def transcribe_audio(self, audio_path):
        """
        Transcribe un archivo de audio usando AssemblyAI.
        """
        import assemblyai as aai
        import time
        from datetime import datetime
        
        try:
            print(f"Iniciando transcripción de {os.path.basename(audio_path)} con AssemblyAI...")
            
            # Configurar opciones de transcripción
            config = aai.TranscriptionConfig(
                language_code="es",  # Español
                speaker_labels=True,  # Identificar hablantes
                punctuate=True,       # Incluir puntuación
                format_text=True,     # Formatear texto
                dual_channel=False,   # Un solo canal
                webhook_url=None,     # Sin webhook
                webhook_auth_header_name=None,
                webhook_auth_header_value=None,
                word_boost=["Dios", "Señor", "Jesús", "Cristo", "Espíritu", "fe", "amor", "esperanza", "iglesia"]  # Boost para palabras religiosas
            )
            
            # Iniciar transcripción
            transcript = self.transcriber.transcribe(
                audio_path,
                config=config
            )
            
            # Esperar a que la transcripción se complete
            while transcript.status != aai.TranscriptStatus.completed:
                if transcript.status == aai.TranscriptStatus.error:
                    raise Exception(f"Error en la transcripción: {transcript.error}")
                
                print(f"Estado de la transcripción: {transcript.status}. Esperando 10 segundos...")
                time.sleep(10)
                transcript = self.transcriber.get_transcript(transcript.id)
            
            # Procesar la transcripción completada
            segments_list = []
            
            # Obtener segmentos (utterances)
            if transcript.utterances:
                print("Procesando segmentos de utterances (habla detectada)...")
                for utterance in transcript.utterances:
                    # Dividir utterances largos en fragmentos más pequeños para mejorar sincronización
                    text = utterance.text.strip()
                    start_time = float(utterance.start) / 1000  # Convertir ms a segundos
                    end_time = float(utterance.end) / 1000      # Convertir ms a segundos
                    duration = end_time - start_time
                    
                    # Si el segmento es muy largo (más de 6 segundos), dividirlo
                    if duration > 6 and len(text) > 80:
                        # Dividir por puntuación fuerte
                        sentences = []
                        current = ""
                        for char in text:
                            current += char
                            if char in ['.', '!', '?'] and len(current.strip()) > 0:
                                sentences.append(current.strip())
                                current = ""
                        
                        # Añadir la última parte si quedó algo
                        if current.strip():
                            sentences.append(current.strip())
                        
                        # Si se logró dividir, crear múltiples segmentos
                        if len(sentences) > 1:
                            # Calcular tiempo aproximado por segmento
                            time_per_segment = duration / len(sentences)
                            
                            for i, sentence in enumerate(sentences):
                                segment_start = start_time + (i * time_per_segment)
                                segment_end = segment_start + time_per_segment
                                
                                segments_list.append({
                                    'start': segment_start,
                                    'end': segment_end,
                                    'text': sentence,
                                    'speaker': utterance.speaker
                                })
                        else:
                            # Si no se pudo dividir, usar el segmento completo
                            segments_list.append({
                                'start': start_time,
                                'end': end_time,
                                'text': text,
                                'speaker': utterance.speaker
                            })
                    else:
                        # Usar el segmento como viene si no es muy largo
                        segments_list.append({
                            'start': start_time,
                            'end': end_time,
                            'text': text,
                            'speaker': utterance.speaker
                        })
            
            # Si no hay utterances, intentar con palabras
            elif transcript.words:
                print("No se detectaron utterances, procesando por palabras...")
                # Agrupar palabras en frases (cuando hay puntuación)
                current_sentence = []
                current_start = None
                
                for word in transcript.words:
                    if current_start is None:
                        current_start = float(word.start) / 1000
                    
                    current_sentence.append(word.text)
                    
                    # Si termina con puntuación o es la última palabra, crear un segmento
                    if (word.text.endswith(('.', '!', '?', ':', ';')) or 
                        word == transcript.words[-1]):
                        
                        segments_list.append({
                            'start': current_start,
                            'end': float(word.end) / 1000,
                            'text': ' '.join(current_sentence),
                            'speaker': 'unknown'
                        })
                        
                        current_sentence = []
                        current_start = None
            
            # Crear diccionario de transcripción
            transcription_data = {
                'text': transcript.text,
                'segments': segments_list,
                'timestamp': datetime.now().isoformat(),
                'audio_file': audio_path,
                'transcript_id': transcript.id,
                'confidence': transcript.confidence
            }
            
            # Guardar también las palabras individuales con marcas de tiempo para subtitulado preciso
            if transcript.words:
                words_list = []
                for word in transcript.words:
                    words_list.append({
                        'text': word.text,
                        'start': word.start,
                        'end': word.end,
                        'confidence': word.confidence,
                        'speaker': word.speaker if hasattr(word, 'speaker') else 'A'
                    })
                transcription_data['words'] = words_list
                print(f"Se guardaron {len(words_list)} palabras con marcas de tiempo precisas")
            
            # Mostrar un extracto de la transcripción
            all_text = transcript.text.strip()
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
        """
        try:
            # Construimos la ruta completa al archivo de video
            video_path = os.path.join(self.input_dir, video_filename)
            
            # Verificamos que el archivo existe
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"No se encontró el archivo: {video_path}")
            
            # Crear directorio de salida
            output_dirs = self._create_output_dir(video_filename)
            
            # Paso 1: Extraer el audio del video
            print(f"Extrayendo audio de {video_filename}...")
            audio_path = self.extract_audio(video_path, output_dirs)
            
            # Paso 2: Transcribir el audio completo (AssemblyAI maneja archivos grandes)
            print(f"Transcribiendo audio con AssemblyAI (esto puede tomar tiempo)...")
            transcription_data = self.transcribe_audio(audio_path)
            
            # Paso 3: Guardar los resultados
            output_filename = os.path.splitext(video_filename)[0] + "_transcription.json"
            output_path = os.path.join(output_dirs["json"], output_filename)
            
            # Añadimos información adicional útil
            transcription_data.update({
                'video_filename': video_filename,
                'processing_date': datetime.now().isoformat(),
                'video_path': video_path,
                'processor': 'AssemblyAI'
            })
            
            # Guardar la transcripción en formato JSON
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(transcription_data, f, ensure_ascii=False, indent=4)
                print(f"Transcripción guardada en: {output_path}")
                
                # Exportar como texto plano
                text_output_filename = os.path.splitext(video_filename)[0] + "_transcript.txt"
                text_output_path = os.path.join(output_dirs["text"], text_output_filename)
                
                # Contenido para el archivo de texto
                content = []
                content.append(f"TRANSCRIPCIÓN: {video_filename}")
                content.append(f"Fecha de procesamiento: {datetime.now().isoformat()}")
                content.append(f"Nivel de confianza: {transcription_data.get('confidence', 'N/A')}")
                content.append("")  # Línea en blanco
                content.append("=" * 80)  # Separador
                content.append("")  # Línea en blanco
                
                # Añadir el texto principal
                content.append(transcription_data.get('text', '').strip())
                
                # Guardar el texto
                with open(text_output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(content))
                print(f"Transcripción en texto plano guardada en: {text_output_path}")
                
                # Versión formateada con marcas de tiempo
                detailed_output_filename = os.path.splitext(video_filename)[0] + "_transcript_detailed.txt"
                detailed_output_path = os.path.join(output_dirs["text"], detailed_output_filename)

                # Contenido detallado
                detailed_content = []
                detailed_content.append(f"TRANSCRIPCIÓN DETALLADA: {video_filename}")
                detailed_content.append(f"Fecha de procesamiento: {datetime.now().isoformat()}")
                detailed_content.append("")  # Línea en blanco
                detailed_content.append("=" * 80)  # Separador
                detailed_content.append("")  # Línea en blanco

                # Añadir segmentos con marcas de tiempo
                for segment in transcription_data.get('segments', []):
                    start_time = time.strftime('%H:%M:%S', time.gmtime(segment['start']))
                    speaker = segment.get('speaker', 'unknown')
                    detailed_content.append(f"[{start_time}] {speaker}: {segment['text']}")

                # Guardar el texto detallado
                with open(detailed_output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(detailed_content))
                print(f"Transcripción detallada guardada en: {detailed_output_path}")

                # Guardar también como archivo SRT para subtítulos
                srt_output_filename = os.path.splitext(video_filename)[0] + "_subtitles.srt"
                srt_output_path = os.path.join(output_dirs["text"], srt_output_filename)

                # Generar entradas SRT usando el nuevo método
                srt_content = self._generate_srt_entries(transcription_data)

                # Guardar archivo SRT con verificación adicional
                if srt_content:
                    with open(srt_output_path, 'w', encoding='utf-8') as f:
                        f.write('\n\n'.join(srt_content))
                    print(f"Archivo de subtítulos SRT guardado en: {srt_output_path}")
                else:
                    print("No se generaron entradas SRT. El archivo quedará vacío.")

            except Exception as e:
                print(f"Error al guardar archivos de salida: {e}")

            return transcription_data

        except Exception as e:
            error_message = f"Error procesando el video {video_filename}: {str(e)}"
            print(error_message)
            raise Exception(error_message)

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
