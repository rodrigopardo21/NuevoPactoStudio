"""
Módulo de transcripción de audio/video usando AssemblyAI.

Este módulo proporciona funcionalidades para la transcripción de audio y video
utilizando la API de AssemblyAI.
"""

import os
import subprocess
import json
from datetime import datetime
import glob
import assemblyai as aai
import time

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
        aai.settings.api_key = api_key
        
    def _create_output_dir(self, video_filename):
        """
        Crea una carpeta de salida con formato sermon_DDMMAA_XX_assemblyai
        """
        # Generar formato de fecha DDMMAA
        today = datetime.now().strftime("%d%m%y")
        base_name = os.path.splitext(video_filename)[0]
        output_prefix = f"sermon_{today}_"
        
        # Buscar carpetas existentes con el mismo prefijo de fecha y _assemblyai
        existing_dirs = glob.glob(os.path.join(self.output_base_dir, f"{output_prefix}*_assemblyai"))
        
        # Determinar el número de contador
        counter = 1
        if existing_dirs:
            counters = []
            for dir_path in existing_dirs:
                dir_name = os.path.basename(dir_path)
                try:
                    counter_part = dir_name.replace(output_prefix, "").split("_")[0]
                    counters.append(int(counter_part))
                except (ValueError, IndexError):
                    continue
            
            if counters:
                counter = max(counters) + 1
        
        # Crear la carpeta principal con el formato correcto
        main_output_dir = os.path.join(self.output_base_dir, f"{output_prefix}{counter:02d}_assemblyai")
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
            subprocess.run(cmd, check=True, capture_output=True)
            
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
        try:
            print(f"Iniciando transcripción de {os.path.basename(audio_path)} con AssemblyAI...")
            
            # Configurar transcripción
            config = aai.TranscriptionConfig(
                language_code="es",  # Español
                speech_model=aai.SpeechModel.best  # Mejor modelo disponible
            )
            
            # Iniciar transcripción
            transcript = aai.Transcriber().transcribe(audio_path, config=config)
            
            # Verificar si hubo error
            if transcript.status == "error":
                raise Exception(f"Error en la transcripción: {transcript.error}")
            
            # Crear diccionario de transcripción
            transcription_data = {
                'text': transcript.text,
                'timestamp': datetime.now().isoformat(),
                'audio_file': audio_path,
                'transcript_id': transcript.id
            }
            
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
            
            # Guardamos la transcripción en formato JSON
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(transcription_data, f, ensure_ascii=False, indent=4)
                print(f"Transcripción guardada en: {output_path}")
                
                # Exportamos también como texto plano
                text_output_filename = os.path.splitext(video_filename)[0] + "_transcript.txt"
                text_output_path = os.path.join(output_dirs["text"], text_output_filename)
                
                # Contenido para el archivo de texto
                content = []
                content.append(f"TRANSCRIPCIÓN (AssemblyAI): {video_filename}")
                content.append(f"Fecha de procesamiento: {datetime.now().isoformat()}")
                content.append("")  # Línea en blanco
                content.append("=" * 80)  # Separador
                content.append("")  # Línea en blanco
                
                # Añadir el texto principal
                content.append(transcription_data.get('text', '').strip())
                
                # Guardar el texto
                with open(text_output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(content))
                print(f"Transcripción en texto plano guardada en: {text_output_path}")
                
            except Exception as e:
                print(f"Error al guardar archivos finales: {str(e)}")
            
            return transcription_data
            
        except Exception as e:
            error_message = f"Error procesando el video {video_filename}: {str(e)}"
            print(error_message)
            raise Exception(error_message)
