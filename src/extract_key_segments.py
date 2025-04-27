#!/usr/bin/env python3
"""
Script para extraer segmentos clave de las transcripciones para crear reels.
Fase 2.1 del proyecto NuevoPactoStudio.

Este script:
1. Analiza los archivos JSON de transcripción
2. Identifica segmentos impactantes para reels
3. Extrae los tiempos de inicio/fin y el texto original
4. Guarda los segmentos seleccionados para su uso posterior
"""
import os
import sys
import json
import glob
import re
import time
from datetime import datetime

# Añadir la ruta del proyecto para importaciones
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

# Configuración
MIN_SEGMENT_DURATION = 5  # Duración mínima en segundos
MAX_SEGMENT_DURATION = 60  # Duración máxima en segundos
MIN_WORDS = 10  # Mínimo número de palabras para considerar un segmento

class KeySegmentExtractor:
    """
    Clase para extraer segmentos clave de transcripciones para crear reels.
    """
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = os.path.join(self.base_dir, "data", "output")
        self.segments_dir = os.path.join(self.base_dir, "data", "segments")
        
        # Crear directorio para segmentos si no existe
        os.makedirs(self.segments_dir, exist_ok=True)
        
        # Palabras y frases clave que indican contenido importante
        self.key_phrases = [
            "dios", "señor", "jesús", "cristo", "espíritu", "biblia", "palabra", 
            "fe", "amor", "esperanza", "reino", "iglesia", "oración", "gracia",
            "gloria", "salvación", "verdad", "paz", "vida eterna", "promesa",
            "recuerda", "imagina", "piensa", "pregunto", "considera",
            "importante", "fundamental", "esencial", "clave", "vital",
            "nunca olvides", "siempre recuerda", "te invito", "te animo",
            "quiero decirte", "escucha", "entiende", "comprende",
            "¿qué significa?", "¿por qué?", "¿cómo?", "¿cuándo?",
            "amén", "aleluya", "gloria a dios", "bendito sea",
            "primera de", "segunda de", "salmo", "evangelio", "proverbio"
        ]
        
        # Expresiones que indican conclusiones o puntos importantes
        self.conclusion_phrases = [
            "en conclusión", "finalmente", "para terminar", "en resumen",
            "recordemos", "no olvides", "te invito", "mi desafío", "mi reto",
            "lo más importante", "el punto clave", "la verdad es", "la realidad es",
            "como cristianos", "como hijos de dios", "como creyentes",
            "debemos", "tenemos que", "es necesario", "es fundamental"
        ]
        
        # Patrones para identificar citas bíblicas
        self.bible_reference_pattern = re.compile(r'(\d*\s*[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ]+\s+\d+[:|,]\s*\d+)', re.IGNORECASE)
    
    def find_transcription_files(self):
        """Busca archivos JSON de transcripción."""
        sermon_folders = glob.glob(os.path.join(self.output_dir, "sermon_*"))
        
        if not sermon_folders:
            print(f"No se encontraron carpetas de transcripción en {self.output_dir}")
            return []
        
        # Ordenar por más reciente
        sermon_folders.sort(reverse=True)
        
        json_files = []
        for folder in sermon_folders:
            json_dir = os.path.join(folder, "json")
            if os.path.exists(json_dir):
                json_files.extend(glob.glob(os.path.join(json_dir, "*_transcription.json")))
        
        return json_files
    
    def load_transcription(self, json_file):
        """Carga un archivo JSON de transcripción."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error al cargar {json_file}: {e}")
            return None
    
    def get_word_level_segments(self, transcription_data):
        """Extraer segmentos a nivel de palabra si están disponibles."""
        if 'words' in transcription_data and transcription_data['words']:
            words = transcription_data['words']
            return words
        return None
    
    def analyze_text_for_keywords(self, text):
        """
        Analiza el texto buscando palabras/frases clave y asigna una puntuación.
        """
        text_lower = text.lower()
        score = 0
        
        # Buscar palabras y frases clave
        for phrase in self.key_phrases:
            if phrase in text_lower:
                score += 1
        
        # Buscar frases de conclusión (más importantes)
        for phrase in self.conclusion_phrases:
            if phrase in text_lower:
                score += 2
        
        # Buscar referencias bíblicas (muy importantes)
        bible_refs = self.bible_reference_pattern.findall(text)
        score += len(bible_refs) * 3
        
        # Analizar otras características del texto
        sentences = re.split(r'[.!?]', text)
        if len(sentences) > 1:  # Textos con varias oraciones completas
            score += 1
        
        # Comprobar si hay preguntas (suelen ser retóricas y potentes)
        if '?' in text:
            score += 2
        
        # Comprobar longitud - preferir segmentos de duración media, ni muy cortos ni muy largos
        word_count = len(text.split())
        if 15 <= word_count <= 40:  # Longitud ideal para un reel
            score += 2
        elif word_count > 40:  # Demasiado largo
            score -= 1
        
        return score
    
    def create_segments_from_words(self, words, max_duration=30):
        """
        Crea segmentos a partir de palabras individuales.
        Busca puntos naturales de ruptura como puntuación.
        """
        segments = []
        current_segment = []
        current_start = None
        
        for i, word in enumerate(words):
            # Asegurarse de que la palabra tiene los campos necesarios
            if not all(key in word for key in ['text', 'start', 'end']):
                continue
            
            # Si es la primera palabra, establecer tiempo de inicio
            if not current_segment:
                current_start = word['start']
            
            # Añadir la palabra al segmento actual
            current_segment.append(word)
            
            # Comprobar si deberíamos cerrar el segmento actual
            end_segment = False
            
            # 1. Si hay un punto natural (puntuación fuerte)
            if word['text'].rstrip().endswith(('.', '!', '?')):
                end_segment = True
            
            # 2. Si alcanzamos la duración máxima
            current_duration = float(word['end']) - float(current_start)
            if current_duration >= max_duration * 1000:  # convertir a ms
                end_segment = True
            
            # 3. Si es la última palabra
            if i == len(words) - 1:
                end_segment = True
            
            # Si debemos cerrar el segmento, procesarlo y añadirlo a la lista
            if end_segment and len(current_segment) >= MIN_WORDS:
                segment_text = ' '.join(w['text'] for w in current_segment)
                segment_start = float(current_start) / 1000  # convertir a segundos
                segment_end = float(word['end']) / 1000
                
                # Evaluar la importancia del segmento
                importance_score = self.analyze_text_for_keywords(segment_text)
                
                segments.append({
                    'start_time': segment_start,
                    'end_time': segment_end,
                    'duration': segment_end - segment_start,
                    'text': segment_text,
                    'importance_score': importance_score
                })
                
                # Preparar para el próximo segmento
                current_segment = []
                current_start = None
        
        return segments
    
    def create_segments_from_transcript_segments(self, transcript_segments):
        """
        Crea segmentos a partir de los segmentos de transcripción.
        Usa cuando no hay marcas de tiempo a nivel de palabra.
        """
        segments = []
        
        for segment in transcript_segments:
            # Validar que el segmento tenga los campos necesarios
            if not all(key in segment for key in ['start', 'end', 'text']):
                continue
            
            text = segment['text'].strip()
            if not text or len(text.split()) < MIN_WORDS:
                continue
            
            # Calcular duración
            start_time = float(segment.get('start', 0))
            end_time = float(segment.get('end', 0))
            duration = end_time - start_time
            
            # Verificar duración mínima y máxima
            if duration < MIN_SEGMENT_DURATION or duration > MAX_SEGMENT_DURATION:
                continue
            
            # Evaluar la importancia del segmento
            importance_score = self.analyze_text_for_keywords(text)
            
            segments.append({
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'text': text,
                'importance_score': importance_score
            })
        
        return segments
    
    def format_time(self, seconds):
        """Formatea los segundos a formato HH:MM:SS."""
        return time.strftime('%H:%M:%S', time.gmtime(seconds))
    
    def save_segments(self, segments, source_file, audio_file=None):
        """
        Guarda los segmentos extraídos en un archivo JSON y en un archivo TXT para fácil lectura.
        """
        if not segments:
            print("No hay segmentos para guardar")
            return None
        
        # Ordenar segmentos por puntuación (descendente)
        segments.sort(key=lambda s: s['importance_score'], reverse=True)
        
        # Crear estructura del archivo de salida
        output_data = {
            'source_file': source_file,
            'audio_file': audio_file,
            'extraction_date': datetime.now().isoformat(),
            'total_segments': len(segments),
            'segments': segments
        }
        
        # Generar nombre de archivo
        source_basename = os.path.basename(source_file)
        output_filename = f"segments_{os.path.splitext(source_basename)[0]}"
        json_path = os.path.join(self.segments_dir, output_filename + ".json")
        txt_path = os.path.join(self.segments_dir, output_filename + ".txt")
        
        # Guardar archivo JSON
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"Segmentos guardados en: {json_path}")
        except Exception as e:
            print(f"Error al guardar segmentos JSON: {e}")
            return None
        
        # Guardar archivo TXT para fácil lectura
        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                # Encabezado
                f.write(f"SEGMENTOS POTENCIALES PARA REELS\n")
                f.write(f"Archivo fuente: {source_basename}\n")
                f.write(f"Fecha de extracción: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write(f"Total de segmentos: {len(segments)}\n\n")
                
                # Escribir cada segmento
                for i, segment in enumerate(segments, 1):
                    f.write(f"#{i} - PUNTUACIÓN: {segment['importance_score']} - ")
                    start_time = self.format_time(segment['start_time'])
                    end_time = self.format_time(segment['end_time'])
                    f.write(f"TIEMPO: {start_time} a {end_time} - ")
                    f.write(f"DURACIÓN: {segment['duration']:.2f}s\n")
                    f.write(f"TEXTO: \"{segment['text']}\"\n\n")
                    f.write("-" * 80 + "\n\n")
                
            print(f"Versión de texto guardada en: {txt_path}")
        except Exception as e:
            print(f"Error al guardar versión de texto: {e}")
        
        return json_path
    
    def display_top_segments(self, segments, n=10):
        """
        Muestra los N segmentos más importantes.
        """
        if not segments:
            print("No hay segmentos para mostrar")
            return
        
        # Ordenar por puntuación de importancia
        sorted_segments = sorted(segments, key=lambda s: s['importance_score'], reverse=True)
        top_segments = sorted_segments[:n]
        
        print(f"\n=== TOP {min(n, len(top_segments))} SEGMENTOS MÁS IMPORTANTES ===")
        for i, segment in enumerate(top_segments, 1):
            print(f"\n{i}. PUNTUACIÓN: {segment['importance_score']} | DURACIÓN: {segment['duration']:.2f}s")
            print(f"   TIEMPO: {self.format_time(segment['start_time'])} - {self.format_time(segment['end_time'])}")
            print(f"   TEXTO: \"{segment['text']}\"")
            print("-" * 80)
    
    def process_transcription(self, json_file):
        """
        Procesa un archivo de transcripción y extrae segmentos importantes.
        """
        print(f"\nProcesando: {os.path.basename(json_file)}")
        
        # Cargar transcripción
        transcription_data = self.load_transcription(json_file)
        if not transcription_data:
            return None, None
        
        audio_file = transcription_data.get('audio_file', None)
        
        # Intentar usar datos a nivel de palabra si están disponibles
        words = self.get_word_level_segments(transcription_data)
        
        if words:
            print("Generando segmentos a partir de datos a nivel de palabra...")
            segments = self.create_segments_from_words(words)
        else:
            print("Generando segmentos a partir de segmentos de transcripción...")
            segments = self.create_segments_from_transcript_segments(transcription_data.get('segments', []))
        
        # Mostrar segmentos encontrados
        print(f"Se encontraron {len(segments)} segmentos potenciales para reels")
        
        # Mostrar los mejores segmentos
        self.display_top_segments(segments)
        
        # Guardar segmentos
        json_path = self.save_segments(segments, json_file, audio_file)
        
        if json_path:
            txt_path = json_path.replace(".json", ".txt")
            return json_path, txt_path
        else:
            return None, None

def main():
    extractor = KeySegmentExtractor()
    
    # Buscar archivos de transcripción
    json_files = extractor.find_transcription_files()
    
    if not json_files:
        print("No se encontraron archivos de transcripción")
        return
    
    # Mostrar archivos disponibles
    print("\n=== EXTRACTOR DE SEGMENTOS CLAVE PARA REELS ===")
    print("\nArchivos de transcripción disponibles:")
    for i, json_file in enumerate(json_files, 1):
        folder_name = os.path.basename(os.path.dirname(os.path.dirname(json_file)))
        file_name = os.path.basename(json_file)
        print(f"{i}. {folder_name}/{file_name}")
    
    # Pedir selección al usuario
    try:
        selection = int(input("\nSelecciona el número del archivo a analizar (0 para salir): "))
        if selection == 0:
            print("Operación cancelada")
            return
        
        selected_file = json_files[selection - 1]
    except (ValueError, IndexError):
        print("Selección inválida")
        return
    
    # Procesar el archivo seleccionado
    json_path, txt_path = extractor.process_transcription(selected_file)
    
    if json_path and txt_path:
        print("\n=== PROCESO COMPLETADO ===")
        print(f"El análisis ha identificado segmentos potenciales para reels")
        print(f"Los datos en formato JSON están disponibles en: {json_path}")
        print(f"Los datos en formato texto están disponibles en: {txt_path}")
        print("\nPuedes utilizar estos segmentos para crear reels que mantengan el audio y texto originales.")
    else:
        print("\n=== ERROR ===")
        print("No se pudo completar el análisis del archivo seleccionado.")

if __name__ == "__main__":
    main()
