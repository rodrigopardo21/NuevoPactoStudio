#!/usr/bin/env python3
"""
Script para seleccionar y refinar manualmente segmentos para crear reels.
Fase 2.1 del proyecto NuevoPactoStudio.

Este script:
1. Carga los segmentos extraídos por extract_key_segments.py
2. Permite al usuario seleccionar y ajustar los segmentos deseados
3. Genera un archivo JSON con los segmentos finales a usar para reels
4. Opcionalmente permite reproducir fragmentos de audio para verificar
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

class ReelSegmentSelector:
    """
    Clase para seleccionar y refinar manualmente segmentos para reels.
    """
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.segments_dir = os.path.join(self.base_dir, "data", "segments")
        self.reels_dir = os.path.join(self.base_dir, "data", "reels")
        
        # Crear directorio para reels si no existe
        os.makedirs(self.reels_dir, exist_ok=True)
    
    def find_segment_files(self):
        """Busca archivos JSON de segmentos extraídos."""
        if not os.path.exists(self.segments_dir):
            print(f"No se encontró el directorio de segmentos: {self.segments_dir}")
            return []
        
        segment_files = glob.glob(os.path.join(self.segments_dir, "segments_*.json"))
        
        if not segment_files:
            print(f"No se encontraron archivos de segmentos en {self.segments_dir}")
            print("Primero ejecuta extract_key_segments.py para generar estos archivos")
            return []
        
        # Ordenar por más reciente
        segment_files.sort(key=os.path.getmtime, reverse=True)
        return segment_files
    
    def load_segments(self, segment_file):
        """Carga un archivo JSON de segmentos."""
        try:
            with open(segment_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error al cargar {segment_file}: {e}")
            return None
    
    def format_time(self, seconds):
        """Formatea los segundos a formato HH:MM:SS."""
        return time.strftime('%H:%M:%S', time.gmtime(seconds))
    
    def format_time_ffmpeg(self, seconds):
        """Formatea los segundos a formato HH:MM:SS.mmm para ffmpeg."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}.{milliseconds:03d}"
    
    def play_audio_segment(self, audio_file, start_time, end_time):
        """
        Reproduce un segmento de audio usando ffplay (parte de ffmpeg).
        """
        if not audio_file or not os.path.exists(audio_file):
            print("Archivo de audio no encontrado")
            return False
        
        try:
            # Formatear tiempos para ffmpeg
            start_formatted = self.format_time_ffmpeg(start_time)
            duration = end_time - start_time
            
            # Construir comando ffplay
            cmd = [
                "ffplay",
                "-nodisp",                  # Sin interfaz gráfica
                "-autoexit",                # Cerrar después de reproducir
                "-loglevel", "quiet",       # Silenciar logs
                "-ss", start_formatted,     # Tiempo de inicio
                "-t", str(duration),        # Duración
                audio_file                  # Archivo de audio
            ]
            
            print(f"\nReproduciendo segmento: {start_formatted} a {self.format_time_ffmpeg(end_time)}")
            print("Presiona Ctrl+C para detener la reproducción...")
            
            # Ejecutar ffplay
            subprocess.run(cmd)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error al reproducir audio: {e}")
            return False
        except KeyboardInterrupt:
            print("\nReproducción detenida por el usuario")
            return False
    
    def display_segments(self, segments_data):
        """
        Muestra los segmentos disponibles para selección.
        """
        if not segments_data or 'segments' not in segments_data:
            print("No hay segmentos para mostrar")
            return
        
        segments = segments_data['segments']
        source_file = segments_data.get('source_file', 'Desconocido')
        audio_file = segments_data.get('audio_file', None)
        
        print(f"\n=== SEGMENTOS DE: {os.path.basename(source_file)} ===")
        print(f"Total de segmentos: {len(segments)}")
        
        # Mostrar los segmentos ordenados por puntuación
        sorted_segments = sorted(segments, key=lambda s: s['importance_score'], reverse=True)
        
        for i, segment in enumerate(sorted_segments, 1):
            start = self.format_time(segment['start_time'])
            end = self.format_time(segment['end_time'])
            duration = segment['duration']
            text = segment['text']
            score = segment['importance_score']
            
            # Limitar texto para visualización
            display_text = text[:100] + "..." if len(text) > 100 else text
            
            print(f"\n{i}. PUNTUACIÓN: {score} | DURACIÓN: {duration:.2f}s | TIEMPO: {start} - {end}")
            print(f"   TEXTO: \"{display_text}\"")
        
        return sorted_segments, audio_file
    
    def select_segment(self, segments, audio_file):
        """
        Permite al usuario seleccionar un segmento.
        """
        while True:
            try:
                selection = input("\nSelecciona un segmento (número), 'r' para reproducir, 'q' para salir: ")
                
                if selection.lower() == 'q':
                    return None
                
                if selection.lower() == 'r' and audio_file:
                    seg_num = int(input("¿Qué segmento quieres reproducir? "))
                    if 1 <= seg_num <= len(segments):
                        segment = segments[seg_num - 1]
                        self.play_audio_segment(audio_file, segment['start_time'], segment['end_time'])
                    else:
                        print("Número de segmento inválido")
                    continue
                
                seg_num = int(selection)
                if 1 <= seg_num <= len(segments):
                    return segments[seg_num - 1]
                else:
                    print("Número de segmento inválido")
            
            except ValueError:
                print("Entrada inválida")
            except KeyboardInterrupt:
                print("\nOperación cancelada")
                return None
    
    def adjust_segment(self, segment, audio_file):
        """
        Permite al usuario ajustar el inicio, fin o texto del segmento.
        """
        original_segment = segment.copy()
        
        while True:
            print("\n=== AJUSTE DE SEGMENTO ===")
            start = self.format_time(segment['start_time'])
            end = self.format_time(segment['end_time'])
            duration = segment['end_time'] - segment['start_time']
            
            print(f"Tiempo actual: {start} - {end} (Duración: {duration:.2f}s)")
            print(f"Texto actual: \"{segment['text']}\"")
            print("\nOpciones:")
            print("1. Ajustar tiempo de inicio")
            print("2. Ajustar tiempo de fin")
            print("3. Editar texto")
            print("4. Reproducir segmento actual")
            print("5. Aceptar y guardar este segmento")
            print("0. Cancelar y volver sin guardar")
            
            try:
                choice = int(input("\nSelecciona una opción: "))
                
                if choice == 0:
                    return None  # Cancelar
                
                elif choice == 1:  # Ajustar inicio
                    current = segment['start_time']
                    prompt = f"Tiempo de inicio actual: {start}. Ajuste en segundos (+/-): "
                    adjust = float(input(prompt))
                    segment['start_time'] = max(0, current + adjust)
                    segment['duration'] = segment['end_time'] - segment['start_time']
                
                elif choice == 2:  # Ajustar fin
                    current = segment['end_time']
                    prompt = f"Tiempo de fin actual: {end}. Ajuste en segundos (+/-): "
                    adjust = float(input(prompt))
                    segment['end_time'] = current + adjust
                    segment['duration'] = segment['end_time'] - segment['start_time']
                
                elif choice == 3:  # Editar texto
                    print(f"Texto actual: \"{segment['text']}\"")
                    new_text = input("Nuevo texto (Enter para mantener igual): ")
                    if new_text:
                        segment['text'] = new_text
                
                elif choice == 4:  # Reproducir
                    if audio_file:
                        self.play_audio_segment(audio_file, segment['start_time'], segment['end_time'])
                    else:
                        print("No hay archivo de audio disponible para reproducir")
                
                elif choice == 5:  # Aceptar
                    # Verificar que la duración es razonable
                    if segment['duration'] < 1:
                        print("¡Advertencia! La duración es demasiado corta (<1s)")
                        if input("¿Continuar de todos modos? (s/n): ").lower() != 's':
                            continue
                    elif segment['duration'] > 60:
                        print("¡Advertencia! La duración es demasiado larga (>60s)")
                        if input("¿Continuar de todos modos? (s/n): ").lower() != 's':
                            continue
                    
                    return segment
                
                else:
                    print("Opción inválida")
            
            except ValueError:
                print("Entrada inválida. Introduce un número.")
            except KeyboardInterrupt:
                print("\nOperación cancelada")
                return None
    
    def save_reel_segments(self, selected_segments, source_data):
        """
        Guarda los segmentos seleccionados para reels en un archivo JSON.
        """
        if not selected_segments:
            print("No hay segmentos para guardar")
            return None
        
        # Obtener información del archivo original
        source_file = source_data.get('source_file', 'Desconocido')
        audio_file = source_data.get('audio_file', None)
        
        # Crear estructura del archivo de salida
        output_data = {
            'source_file': source_file,
            'audio_file': audio_file,
            'selection_date': datetime.now().isoformat(),
            'total_segments': len(selected_segments),
            'segments': selected_segments
        }
        
        # Generar nombre de archivo
        source_basename = os.path.basename(source_file)
        base_name = os.path.splitext(source_basename)[0].replace('segments_', '')
        output_filename = f"reels_{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = os.path.join(self.reels_dir, output_filename)
        
        # Guardar archivo
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"\nSegmentos para reels guardados en: {output_path}")
            return output_path
        except Exception as e:
            print(f"\nError al guardar segmentos: {e}")
            return None
    
    def process_segments(self, segment_file):
        """
        Procesa un archivo de segmentos y permite seleccionar los mejores para reels.
        """
        print(f"\nCargando: {os.path.basename(segment_file)}")
        
        # Cargar segmentos
        segments_data = self.load_segments(segment_file)
        if not segments_data:
            return None
        
        # Mostrar segmentos disponibles
        sorted_segments, audio_file = self.display_segments(segments_data)
        if not sorted_segments:
            return None
        
        # Seleccionar segmentos para reels
        selected_segments = []
        while True:
            print(f"\n=== SELECCIÓN DE SEGMENTOS PARA REELS ===")
            print(f"Segmentos seleccionados: {len(selected_segments)}")
            print("\nOpciones:")
            print("1. Seleccionar otro segmento")
            print("2. Ver segmentos ya seleccionados")
            print("3. Guardar selección actual y terminar")
            print("0. Cancelar y salir sin guardar")
            
            try:
                choice = int(input("\nSelecciona una opción: "))
                
                if choice == 0:
                    if selected_segments and input("¿Seguro que quieres salir sin guardar? (s/n): ").lower() == 's':
                        return None
                    if not selected_segments:
                        return None
                
                elif choice == 1:  # Seleccionar segmento
                    segment = self.select_segment(sorted_segments, audio_file)
                    if segment:
                        # Permitir ajustes en el segmento seleccionado
                        adjusted_segment = self.adjust_segment(segment.copy(), audio_file)
                        if adjusted_segment:
                            selected_segments.append(adjusted_segment)
                            print(f"\nSegmento añadido. Total: {len(selected_segments)}")
                
                elif choice == 2:  # Ver seleccionados
                    if not selected_segments:
                        print("\nNo hay segmentos seleccionados aún")
                        continue
                    
                    print("\n=== SEGMENTOS SELECCIONADOS ===")
                    for i, segment in enumerate(selected_segments, 1):
                        start = self.format_time(segment['start_time'])
                        end = self.format_time(segment['end_time'])
                        print(f"{i}. {start} - {end} | \"{segment['text'][:50]}...\"")
                    
                    # Opción para reproducir o eliminar
                    sub_choice = input("\nOpciones: 'r' para reproducir, 'd' para eliminar, Enter para volver: ")
                    if sub_choice.lower().startswith('r'):
                        seg_num = int(input("¿Qué segmento quieres reproducir? "))
                        if 1 <= seg_num <= len(selected_segments):
                            seg = selected_segments[seg_num - 1]
                            self.play_audio_segment(audio_file, seg['start_time'], seg['end_time'])
                    elif sub_choice.lower().startswith('d'):
                        seg_num = int(input("¿Qué segmento quieres eliminar? "))
                        if 1 <= seg_num <= len(selected_segments):
                            del selected_segments[seg_num - 1]
                            print("Segmento eliminado")
                
                elif choice == 3:  # Guardar y terminar
                    if not selected_segments:
                        print("\nNo hay segmentos seleccionados para guardar")
                        continue
                    
                    return self.save_reel_segments(selected_segments, segments_data)
                
                else:
                    print("Opción inválida")
            
            except ValueError:
                print("Entrada inválida. Introduce un número.")
            except KeyboardInterrupt:
                print("\nOperación cancelada")
                if selected_segments:
                    if input("¿Guardar los segmentos seleccionados antes de salir? (s/n): ").lower() == 's':
                        return self.save_reel_segments(selected_segments, segments_data)
                return None

def main():
    selector = ReelSegmentSelector()
    
    # Buscar archivos de segmentos
    segment_files = selector.find_segment_files()
    
    if not segment_files:
        print("No se encontraron archivos de segmentos")
        print("Primero ejecuta extract_key_segments.py para generar estos archivos")
        return
    
    # Mostrar archivos disponibles
    print("\n=== SELECTOR DE SEGMENTOS PARA REELS ===")
    print("\nArchivos de segmentos disponibles:")
    for i, segment_file in enumerate(segment_files, 1):
        file_name = os.path.basename(segment_file)
        print(f"{i}. {file_name}")
    
    # Pedir selección al usuario
    try:
        selection = int(input("\nSelecciona el número del archivo a procesar (0 para salir): "))
        if selection == 0:
            print("Operación cancelada")
            return
        
        selected_file = segment_files[selection - 1]
    except (ValueError, IndexError):
        print("Selección inválida")
        return
    
    # Procesar el archivo seleccionado
    output_path = selector.process_segments(selected_file)
    
    if output_path:
        print("\n=== PROCESO COMPLETADO ===")
        print(f"Los segmentos para reels han sido guardados en: {output_path}")
        print("\nPuedes usar estos segmentos para generar reels que mantengan el audio y texto originales.")
    else:
        print("\n=== PROCESO CANCELADO ===")
        print("No se guardaron segmentos para reels.")

if __name__ == "__main__":
    main()
