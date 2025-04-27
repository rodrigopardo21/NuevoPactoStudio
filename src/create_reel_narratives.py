#!/usr/bin/env python3
"""
Script para crear narrativas de reels a partir de segmentos extraídos.
Fase 2.1 del proyecto NuevoPactoStudio.

Este script:
1. Carga los segmentos analizados previamente
2. Construye narrativas coherentes combinando varios segmentos
3. Crea "mini-historias" evangelizadoras con estructura de trailer
4. Optimiza la duración para reels (30s-90s)
"""
import os
import sys
import json
import glob
import time
from datetime import datetime
import random

# Añadir la ruta del proyecto para importaciones
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ReelNarrativeCreator:
    """
    Clase para crear narrativas de reels a partir de segmentos.
    """
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.segments_dir = os.path.join(self.base_dir, "data", "segments")
        self.narratives_dir = os.path.join(self.base_dir, "data", "narratives")
        
        # Crear directorio para narrativas si no existe
        os.makedirs(self.narratives_dir, exist_ok=True)
        
        # Patrones narrativos basados en el análisis del reel de ejemplo
        self.narrative_patterns = [
            {
                "name": "Reflexión y Desafío",
                "structure": [
                    {"type": "introducción_reflexiva", "min_score": 4},
                    {"type": "contraste", "min_score": 4},
                    {"type": "desafío", "min_score": 6},
                    {"type": "solución", "min_score": 5}
                ],
                "target_duration": 45  # segundos
            },
            {
                "name": "Llamado a la Acción",
                "structure": [
                    {"type": "pregunta_retórica", "min_score": 5},
                    {"type": "problema", "min_score": 4},
                    {"type": "llamado", "min_score": 7},
                    {"type": "cierre_empoderador", "min_score": 6}
                ],
                "target_duration": 60  # segundos
            },
            {
                "name": "Contraste Esperanza-Mundo",
                "structure": [
                    {"type": "problema_mundial", "min_score": 4},
                    {"type": "verdad_bíblica", "min_score": 6},
                    {"type": "contraste", "min_score": 5},
                    {"type": "esperanza", "min_score": 7}
                ],
                "target_duration": 50  # segundos
            }
        ]
        
        # Palabras clave para clasificar los segmentos según su tipo narrativo
        self.narrative_keywords = {
            "introducción_reflexiva": ["imagina", "piensa", "considera", "¿sabes?", "¿alguna vez", "¿has sentido"],
            "contraste": ["pero", "sin embargo", "no obstante", "en cambio", "a diferencia", "al contrario"],
            "desafío": ["te invito", "te animo", "te reto", "mi desafío", "desafío", "reto"],
            "solución": ["la solución", "la respuesta", "la clave", "el secreto", "la verdad es"],
            "pregunta_retórica": ["¿por qué?", "¿cómo?", "¿cuándo?", "¿dónde?", "¿quién?", "¿qué pasaría?"],
            "problema": ["problema", "dificultad", "obstáculo", "lucha", "batalla", "crisis"],
            "llamado": ["necesitas", "debes", "tienes que", "es necesario", "es importante", "urgente"],
            "cierre_empoderador": ["puedes", "eres capaz", "tienes el poder", "es posible", "está en ti"],
            "problema_mundial": ["mundo", "sociedad", "cultura", "actualidad", "hoy en día", "tiempos"],
            "verdad_bíblica": ["biblia dice", "palabra dice", "escritura", "jesús dijo", "dios dice"],
            "esperanza": ["esperanza", "promesa", "futuro", "eternidad", "gloria", "salvación"]
        }
    
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
    
    def classify_segment(self, segment):
        """
        Clasifica un segmento según su tipo narrativo basado en palabras clave.
        """
        text = segment['text'].lower()
        segment_types = []
        
        # Verificar cada tipo narrativo
        for narrative_type, keywords in self.narrative_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    segment_types.append(narrative_type)
                    break
        
        # Si no se identifica ningún tipo específico, clasificar según otras características
        if not segment_types:
            # Si es una pregunta, probablemente es una pregunta retórica
            if '?' in segment['text']:
                segment_types.append('pregunta_retórica')
            
            # Si tiene una puntuación alta, podría ser una solución o cierre
            if segment['importance_score'] >= 7:
                segment_types.append('cierre_empoderador')
                segment_types.append('solución')
            
            # Si menciona a Dios, Jesús, etc., probablemente sea una verdad bíblica
            if any(word in text for word in ['dios', 'jesús', 'cristo', 'señor', 'biblia']):
                segment_types.append('verdad_bíblica')
                segment_types.append('esperanza')
        
        return segment_types
    
    def create_narrative(self, segments_data, pattern):
        """
        Crea una narrativa según el patrón especificado.
        """
        if not segments_data or 'segments' not in segments_data:
            return None
        
        segments = segments_data['segments']
        audio_file = segments_data.get('audio_file')
        
        # Clasificar todos los segmentos
        for segment in segments:
            segment['narrative_types'] = self.classify_segment(segment)
        
        # Construir la narrativa según la estructura del patrón
        narrative_segments = []
        total_duration = 0
        target_duration = pattern['target_duration']
        
        for step in pattern['structure']:
            step_type = step['type']
            min_score = step['min_score']
            
            # Encontrar segmentos que coincidan con el tipo y puntuación mínima
            matching_segments = [
                s for s in segments 
                if step_type in s.get('narrative_types', []) 
                and s['importance_score'] >= min_score
                and s not in narrative_segments  # Evitar duplicados
            ]
            
            if not matching_segments:
                # Si no hay coincidencias exactas, buscar alternativas
                matching_segments = [
                    s for s in segments
                    if s['importance_score'] >= min_score
                    and s not in narrative_segments  # Evitar duplicados
                ]
            
            if matching_segments:
                # Ordenar por puntuación (mayor primero) y seleccionar
                matching_segments.sort(key=lambda s: s['importance_score'], reverse=True)
                
                # Seleccionar un segmento que no exceda demasiado la duración objetivo
                selected = None
                for segment in matching_segments[:5]:  # Considerar los 5 mejores
                    new_duration = total_duration + segment['duration']
                    if new_duration <= target_duration * 1.2:  # Permitir hasta un 20% extra
                        selected = segment
                        break
                
                # Si todos son muy largos, elegir el más corto de los mejores
                if not selected and matching_segments:
                    selected = min(matching_segments[:3], key=lambda s: s['duration'])
                
                if selected:
                    narrative_segments.append(selected)
                    total_duration += selected['duration']
        
        # Si la narrativa es demasiado corta, añadir segmentos adicionales
        if total_duration < target_duration * 0.8 and segments:  # Al menos 80% de la duración objetivo
            # Ordenar por puntuación descartando los ya usados
            remaining = [s for s in segments if s not in narrative_segments]
            remaining.sort(key=lambda s: s['importance_score'], reverse=True)
            
            # Añadir segmentos hasta alcanzar la duración objetivo
            for segment in remaining:
                if total_duration >= target_duration * 0.8:
                    break
                
                # Evitar que se exceda demasiado
                if total_duration + segment['duration'] > target_duration * 1.2:
                    continue
                
                narrative_segments.append(segment)
                total_duration += segment['duration']
        
        # Ordenar los segmentos por tiempo de inicio para mantener la coherencia del audio
        narrative_segments.sort(key=lambda s: s['start_time'])
        
        # Crear la estructura de narrativa
        narrative = {
            'name': pattern['name'],
            'pattern': pattern,
            'source_file': segments_data.get('source_file'),
            'audio_file': audio_file,
            'creation_date': datetime.now().isoformat(),
            'total_duration': total_duration,
            'segments': narrative_segments
        }
        
        return narrative
    
    def create_all_narratives(self, segments_data):
        """
        Crea narrativas para todos los patrones disponibles.
        """
        narratives = []
        
        for pattern in self.narrative_patterns:
            narrative = self.create_narrative(segments_data, pattern)
            if narrative and narrative['segments']:
                narratives.append(narrative)
        
        return narratives
    
    def save_narratives(self, narratives, source_file):
        """
        Guarda las narrativas en archivos JSON y TXT.
        """
        if not narratives:
            print("No hay narrativas para guardar")
            return None
        
        results = []
        
        # Crear un archivo para cada narrativa
        for narrative in narratives:
            # Generar nombre de archivo
            source_basename = os.path.basename(source_file)
            narrative_name = narrative['name'].lower().replace(' ', '_')
            output_filename = f"narrative_{narrative_name}_{os.path.splitext(source_basename)[0].replace('segments_', '')}"
            json_path = os.path.join(self.narratives_dir, output_filename + ".json")
            txt_path = os.path.join(self.narratives_dir, output_filename + ".txt")
            
            # Guardar archivo JSON
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(narrative, f, ensure_ascii=False, indent=2)
                print(f"Narrativa '{narrative['name']}' guardada en: {json_path}")
            except Exception as e:
                print(f"Error al guardar narrativa JSON: {e}")
                continue
            
            # Guardar archivo TXT para fácil lectura
            try:
                with open(txt_path, 'w', encoding='utf-8') as f:
                    # Encabezado
                    f.write(f"NARRATIVA PARA REEL: {narrative['name']}\n")
                    f.write(f"Archivo fuente: {os.path.basename(source_file)}\n")
                    f.write(f"Fecha de creación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                    f.write(f"Duración total: {narrative['total_duration']:.2f} segundos\n\n")
                    
                    # Explicación de la estructura narrativa
                    f.write(f"ESTRUCTURA NARRATIVA:\n")
                    for i, step in enumerate(narrative['pattern']['structure'], 1):
                        f.write(f"{i}. {step['type'].replace('_', ' ').title()}\n")
                    f.write("\n")
                    
                    # Escribir cada segmento
                    f.write("SECUENCIA DE SEGMENTOS:\n")
                    for i, segment in enumerate(narrative['segments'], 1):
                        f.write(f"SEGMENTO {i} - TIEMPO: {self.format_time(segment['start_time'])} a {self.format_time(segment['end_time'])}\n")
                        f.write(f"DURACIÓN: {segment['duration']:.2f}s - PUNTUACIÓN: {segment['importance_score']}\n")
                        f.write(f"TIPO: {', '.join(segment.get('narrative_types', ['No clasificado']))}\n")
                        f.write(f"TEXTO: \"{segment['text']}\"\n\n")
                    
                    # Agregar instrucciones para uso
                    f.write("=" * 80 + "\n\n")
                    f.write("INSTRUCCIONES DE USO:\n")
                    f.write("1. Esta narrativa está diseñada para crear un reel impactante de estilo 'trailer'\n")
                    f.write("2. Sigue la secuencia de segmentos en el orden indicado\n")
                    f.write("3. Utiliza el archivo de audio original para mantener la voz auténtica\n")
                    f.write("4. Cada segmento debe tener un estilo visual acorde a su tipo narrativo\n")
                    f.write("5. Mantén la coherencia visual y narrativa entre segmentos\n")
                
                print(f"Versión de texto guardada en: {txt_path}")
                results.append((json_path, txt_path))
            except Exception as e:
                print(f"Error al guardar versión de texto: {e}")
        
        return results
    
    def display_narrative_preview(self, narrative):
        """
        Muestra una vista previa de la narrativa.
        """
        if not narrative or 'segments' not in narrative:
            print("No hay narrativa para mostrar")
            return
        
        print(f"\n=== VISTA PREVIA: {narrative['name']} ===")
        print(f"Duración total: {narrative['total_duration']:.2f} segundos")
        
        for i, segment in enumerate(narrative['segments'], 1):
            start = self.format_time(segment['start_time'])
            end = self.format_time(segment['end_time'])
            duration = segment['duration']
            
            print(f"\nSEGMENTO {i} - {start} a {end} ({duration:.2f}s)")
            print(f"TEXTO: \"{segment['text']}\"")
        
        print("\nNota: Los segmentos están ordenados por tiempo para mantener la coherencia del audio original")
    
    def process_segments(self, segment_file):
        """
        Procesa un archivo de segmentos y crea narrativas.
        """
        print(f"\nCargando: {os.path.basename(segment_file)}")
        
        # Cargar segmentos
        segments_data = self.load_segments(segment_file)
        if not segments_data:
            return None
        
        # Crear narrativas
        print("Creando narrativas basadas en patrones...")
        narratives = self.create_all_narratives(segments_data)
        
        if not narratives:
            print("No se pudieron crear narrativas con los segmentos disponibles")
            return None
        
        # Mostrar vista previa de cada narrativa
        for narrative in narratives:
            self.display_narrative_preview(narrative)
        
        # Guardar narrativas
        results = self.save_narratives(narratives, segment_file)
        
        return results

def main():
    creator = ReelNarrativeCreator()
    
    # Buscar archivos de segmentos
    segment_files = creator.find_segment_files()
    
    if not segment_files:
        print("No se encontraron archivos de segmentos")
        print("Primero ejecuta extract_key_segments.py para generar estos archivos")
        return
    
    # Mostrar archivos disponibles
    print("\n=== CREADOR DE NARRATIVAS PARA REELS ===")
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
    results = creator.process_segments(selected_file)
    
    if results:
        print("\n=== PROCESO COMPLETADO ===")
        print(f"Se han creado {len(results)} narrativas para reels")
        print("\nRevisa los archivos generados para ver las narrativas completas.")
        print("Cada narrativa sigue una estructura tipo 'trailer' para captar la atención y evangelizar.")
    else:
        print("\n=== ERROR ===")
        print("No se pudieron crear narrativas para reels.")

if __name__ == "__main__":
    main()
