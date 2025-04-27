#!/usr/bin/env python3
"""
Script para generar archivos de audio y SRT a partir de narrativas para reels.
Fase 2.1 del proyecto NuevoPactoStudio.

Este script:
1. Carga narrativas generadas por create_reel_narratives.py
2. Extrae segmentos de audio del archivo original
3. Los concatena con silencios naturales entre ellos
4. Genera archivos SRT sincronizados con el nuevo audio
5. Permite previsualizar las narrativas antes de producir los reels
"""
import os
import sys
import json
import glob
import time
import subprocess
from datetime import datetime

# Añadir la ruta del proyecto para importaciones
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class NarrativeMediaGenerator:
    """
    Clase para generar archivos de audio y SRT a partir de narrativas.
    """
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.narratives_dir = os.path.join(self.base_dir, "data", "narratives")
        self.media_dir = os.path.join(self.base_dir, "data", "narrative_media")
        
        # Crear directorio para medios si no existe
        os.makedirs(self.media_dir, exist_ok=True)
        
        # Duración del silencio entre segmentos (en segundos)
        self.silence_duration = 0.5  # Medio segundo de silencio
    
    def find_narrative_files(self):
        """Busca archivos JSON de narrativas generadas."""
        if not os.path.exists(self.narratives_dir):
            print(f"No se encontró el directorio de narrativas: {self.narratives_dir}")
            return []
        
        narrative_files = glob.glob(os.path.join(self.narratives_dir, "narrative_*.json"))
        
        if not narrative_files:
            print(f"No se encontraron archivos de narrativas en {self.narratives_dir}")
            print("Primero ejecuta create_reel_narratives.py para generar estos archivos")
            return []
        
        # Ordenar por más reciente
        narrative_files.sort(key=os.path.getmtime, reverse=True)
        return narrative_files
    
    def load_narrative(self, narrative_file):
        """Carga un archivo JSON de narrativa."""
        try:
            with open(narrative_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error al cargar {narrative_file}: {e}")
            return None
    
    def format_time_srt(self, seconds):
        """Convierte segundos a formato HH:MM:SS,mmm para SRT"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def format_time_ffmpeg(self, seconds):
        """Formatea los segundos a formato HH:MM:SS.mmm para ffmpeg."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}.{milliseconds:03d}"
    
    def extract_audio_segment(self, audio_file, start_time, end_time, output_file):
        """
        Extrae un segmento de audio del archivo original.
        """
        if not audio_file or not os.path.exists(audio_file):
            print(f"Archivo de audio no encontrado: {audio_file}")
            return False
        
        try:
            # Formatear tiempos para ffmpeg
            start_formatted = self.format_time_ffmpeg(start_time)
            duration = end_time - start_time
            
            # Construir comando ffmpeg
            cmd = [
                "ffmpeg",
                "-i", audio_file,              # Archivo de entrada
                "-ss", start_formatted,        # Tiempo de inicio
                "-t", str(duration),           # Duración
                "-c:a", "libmp3lame",          # Codec de audio
                "-q:a", "2",                   # Calidad
                "-y",                          # Sobrescribir si existe
                output_file                    # Archivo de salida
            ]
            
            # Ejecutar ffmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Error al extraer segmento de audio: {result.stderr}")
                return False
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error al extraer audio: {e}")
            return False
        except Exception as e:
            print(f"Error inesperado: {e}")
            return False
    
    def create_silence(self, duration, output_file):
        """
        Crea un archivo de audio con silencio de la duración especificada.
        """
        try:
            cmd = [
                "ffmpeg",
                "-f", "lavfi",                # Formato de entrada filtro
                "-i", f"anullsrc=r=44100:cl=mono",  # Generador de silencio
                "-t", str(duration),          # Duración
                "-c:a", "libmp3lame",         # Codec de audio
                "-q:a", "2",                  # Calidad
                "-y",                         # Sobrescribir si existe
                output_file                   # Archivo de salida
            ]
            
            # Ejecutar ffmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Error al crear silencio: {result.stderr}")
                return False
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error al crear silencio: {e}")
            return False
        except Exception as e:
            print(f"Error inesperado: {e}")
            return False
    
    def concatenate_audio_files(self, audio_files, output_file):
        """
        Concatena múltiples archivos de audio en uno solo.
        """
        if not audio_files:
            print("No hay archivos de audio para concatenar")
            return False
        
        try:
            # Crear archivo de lista para ffmpeg
            list_file = os.path.join(self.media_dir, "concat_list.txt")
            with open(list_file, "w", encoding="utf-8") as f:
                for audio_file in audio_files:
                    f.write(f"file '{audio_file}'\n")
            
            # Construir comando ffmpeg
            cmd = [
                "ffmpeg",
                "-f", "concat",              # Formato de entrada concatenación
                "-safe", "0",                # Permitir rutas absolutas
                "-i", list_file,             # Archivo de lista
                "-c:a", "libmp3lame",        # Codec de audio
                "-q:a", "2",                 # Calidad
                "-y",                        # Sobrescribir si existe
                output_file                  # Archivo de salida
            ]
            
            # Ejecutar ffmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Eliminar archivo de lista temporal
            if os.path.exists(list_file):
                os.remove(list_file)
            
            if result.returncode != 0:
                print(f"Error al concatenar audio: {result.stderr}")
                return False
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error al concatenar audio: {e}")
            return False
        except Exception as e:
            print(f"Error inesperado: {e}")
            return False
    
    def generate_srt(self, segments, output_srt):
        """
        Genera un archivo SRT para los segmentos concatenados.
        """
        if not segments:
            print("No hay segmentos para generar SRT")
            return False
        
        try:
            srt_entries = []
            current_time = 0
            
            for i, segment in enumerate(segments, 1):
                segment_text = segment.get('text', '')
                segment_duration = segment.get('duration', 0)
                
                # Tiempos para el subtítulo
                start_time = current_time
                end_time = current_time + segment_duration
                
                # Formatear tiempos para SRT
                start_formatted = self.format_time_srt(start_time)
                end_formatted = self.format_time_srt(end_time)
                
                # Formatear texto (dividir en dos líneas si es necesario)
                if len(segment_text) > 40:
                    # Dividir por palabras cerca del punto medio
                    words = segment_text.split()
                    half_len = len(segment_text) // 2
                    
                    current_len = 0
                    split_index = 0
                    
                    for j, word in enumerate(words):
                        current_len += len(word) + (1 if j > 0 else 0)
                        if current_len >= half_len:
                            split_index = j
                            break
                    
                    first_part = ' '.join(words[:split_index])
                    second_part = ' '.join(words[split_index:])
                    
                    formatted_text = f"{first_part}\n{second_part}"
                else:
                    formatted_text = segment_text
                
                # Crear entrada SRT
                srt_entry = f"{i}\n{start_formatted} --> {end_formatted}\n{formatted_text}"
                srt_entries.append(srt_entry)
                
                # Actualizar tiempo actual (incluyendo silencio después del segmento)
                current_time = end_time + self.silence_duration
            
            # Guardar archivo SRT
            with open(output_srt, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(srt_entries))
            
            return True
            
        except Exception as e:
            print(f"Error al generar archivo SRT: {e}")
            return False
    
    def process_narrative(self, narrative_file):
        """
        Procesa un archivo de narrativa para generar audio y SRT.
        """
        print(f"\nProcesando: {os.path.basename(narrative_file)}")
        
        # Cargar narrativa
        narrative_data = self.load_narrative(narrative_file)
        if not narrative_data:
            return None
        
        # Verificar que haya un archivo de audio fuente
        audio_file = narrative_data.get('audio_file')
        if not audio_file or not os.path.exists(audio_file):
            print(f"Archivo de audio no encontrado: {audio_file}")
            return None
        
        # Obtener segmentos
        segments = narrative_data.get('segments', [])
        if not segments:
            print("No hay segmentos en la narrativa")
            return None
        
        # Crear directorio temporal para archivos intermedios
        temp_dir = os.path.join(self.media_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generar nombre base para archivos de salida
        base_name = os.path.splitext(os.path.basename(narrative_file))[0]
        output_audio = os.path.join(self.media_dir, f"{base_name}.mp3")
        output_srt = os.path.join(self.media_dir, f"{base_name}.srt")
        
        try:
            # Lista para archivos de audio a concatenar
            audio_files = []
            
            # Extraer cada segmento de audio
            print("Extrayendo segmentos de audio...")
            for i, segment in enumerate(segments):
                # Extraer audio del segmento
                segment_audio = os.path.join(temp_dir, f"segment_{i:03d}.mp3")
                success = self.extract_audio_segment(
                    audio_file,
                    segment['start_time'],
                    segment['end_time'],
                    segment_audio
                )
                
                if not success:
                    print(f"Error al extraer segmento de audio {i}")
                    continue
                
                audio_files.append(segment_audio)
                
                # Agregar silencio después de cada segmento (excepto el último)
                if i < len(segments) - 1:
                    silence_audio = os.path.join(temp_dir, f"silence_{i:03d}.mp3")
                    success = self.create_silence(self.silence_duration, silence_audio)
                    
                    if not success:
                        print(f"Error al crear silencio después del segmento {i}")
                        continue
                    
                    audio_files.append(silence_audio)
            
            # Concatenar todos los archivos de audio
            print("Concatenando segmentos de audio...")
            success = self.concatenate_audio_files(audio_files, output_audio)
            
            if not success:
                print("Error al concatenar archivos de audio")
                return None
            
            # Generar archivo SRT
            print("Generando archivo SRT...")
            success = self.generate_srt(segments, output_srt)
            
            if not success:
                print("Error al generar archivo SRT")
                return None
            
            # Limpiar archivos temporales
            for file in audio_files:
                if os.path.exists(file):
                    os.remove(file)
            
            if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                os.rmdir(temp_dir)
            
            return {
                'narrative_file': narrative_file,
                'audio_file': output_audio,
                'srt_file': output_srt
            }
            
        except Exception as e:
            print(f"Error al procesar narrativa: {e}")
            return None
        finally:
            # Asegurar limpieza de archivos temporales en caso de error
            try:
                for file in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, file))
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass
    
    def play_preview(self, audio_file, srt_file):
        """
        Reproduce una vista previa del audio con subtítulos (si está disponible).
        """
        if not audio_file or not os.path.exists(audio_file):
            print("Archivo de audio no disponible para reproducir")
            return False
        
        try:
            # Construir comando ffplay
            cmd = [
                "ffplay",
                "-autoexit",                # Cerrar después de reproducir
                "-loglevel", "quiet",       # Silenciar logs
                audio_file                  # Archivo de audio
            ]
            
            # Agregar subtítulos si están disponibles
            if srt_file and os.path.exists(srt_file):
                cmd.extend(["-vf", f"subtitles={srt_file}"])
            
            print(f"\nReproduciendo vista previa... (cierra la ventana para detener)")
            
            # Ejecutar ffplay
            subprocess.run(cmd)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error al reproducir vista previa: {e}")
            return False
        except Exception as e:
            print(f"Error inesperado: {e}")
            return False

def main():
    generator = NarrativeMediaGenerator()
    
    # Buscar archivos de narrativas
    narrative_files = generator.find_narrative_files()
    
    if not narrative_files:
        print("No se encontraron archivos de narrativas")
        print("Primero ejecuta create_reel_narratives.py para generar estos archivos")
        return
    
    # Mostrar archivos disponibles
    print("\n=== GENERADOR DE MEDIOS PARA NARRATIVAS ===")
    print("\nArchivos de narrativas disponibles:")
    for i, narrative_file in enumerate(narrative_files, 1):
        file_name = os.path.basename(narrative_file)
        print(f"{i}. {file_name}")
    
    # Pedir selección al usuario
    try:
        selection = int(input("\nSelecciona el número del archivo a procesar (0 para salir): "))
        if selection == 0:
            print("Operación cancelada")
            return
        
        selected_file = narrative_files[selection - 1]
    except (ValueError, IndexError):
        print("Selección inválida")
        return
    
    # Procesar el archivo seleccionado
    result = generator.process_narrative(selected_file)
    
    if result:
        print("\n=== PROCESO COMPLETADO ===")
        print("Archivos generados:")
        print(f"- Audio: {result['audio_file']}")
        print(f"- Subtítulos: {result['srt_file']}")
        
        # Preguntar si quiere reproducir una vista previa
        preview = input("\n¿Quieres reproducir una vista previa? (s/n): ")
        if preview.lower() == 's':
            generator.play_preview(result['audio_file'], result['srt_file'])
        
        print("\nEstos archivos pueden ser utilizados para crear reels con el audio y subtítulos extraídos.")
    else:
        print("\n=== ERROR ===")
        print("No se pudieron generar los archivos de medios.")

if __name__ == "__main__":
    main()
