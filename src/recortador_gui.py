"""
Interfaz gráfica para recortar videos usando ffmpeg.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
from datetime import datetime

class RecortadorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Recortador de Videos - NuevoPactoStudio")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        
        # Configurar rutas
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.source_dir = os.path.join(self.base_dir, "source_videos")
        self.output_dir = os.path.join(self.base_dir, "data", "input")
        
        # Asegurar que las carpetas existan
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Variables
        self.videos = self.get_videos()
        self.selected_video = tk.StringVar()
        self.start_time = tk.StringVar(value="00:00:00")
        self.end_time = tk.StringVar(value="")
        self.output_name = tk.StringVar()
        
        # Crear la interfaz
        self.create_widgets()
        
        # Actualizar lista de videos al inicio
        self.refresh_videos()
    
    def get_videos(self):
        """Obtener lista de videos disponibles"""
        return [f for f in os.listdir(self.source_dir) if f.endswith((".mp4", ".MP4"))]
    
    def refresh_videos(self):
        """Actualizar lista de videos"""
        self.videos = self.get_videos()
        self.video_listbox.delete(0, tk.END)
        
        if not self.videos:
            self.video_listbox.insert(tk.END, "No hay videos disponibles")
            self.process_button.config(state=tk.DISABLED)
        else:
            for video in self.videos:
                self.video_listbox.insert(tk.END, video)
            self.process_button.config(state=tk.NORMAL)
    
    def select_video(self, event):
        """Gestionar la selección de un video"""
        if not self.videos:
            return
            
        selection = self.video_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.videos):
                self.selected_video.set(self.videos[index])
                # Sugerir nombre de salida basado en el video
                base_name = os.path.splitext(self.videos[index])[0]
                self.output_name.set(f"{base_name}_recortado")
    
    def browse_source(self):
        """Abrir explorador para seleccionar un video"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar Video",
            filetypes=[("Archivos MP4", "*.mp4 *.MP4")]
        )
        if file_path:
            # Copiar el archivo a la carpeta source_videos
            filename = os.path.basename(file_path)
            dest_path = os.path.join(self.source_dir, filename)
            
            try:
                # Si el archivo no está ya en la carpeta, copiarlo
                if file_path != dest_path:
                    import shutil
                    shutil.copy2(file_path, dest_path)
                    messagebox.showinfo("Éxito", f"Video {filename} copiado a la carpeta source_videos")
                
                # Actualizar lista
                self.refresh_videos()
                
                # Seleccionar el video en la lista
                for i, video in enumerate(self.videos):
                    if video == filename:
                        self.video_listbox.selection_clear(0, tk.END)
                        self.video_listbox.selection_set(i)
                        self.video_listbox.see(i)
                        self.selected_video.set(video)
                        # Sugerir nombre de salida
                        base_name = os.path.splitext(video)[0]
                        self.output_name.set(f"{base_name}_recortado")
                        break
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo copiar el video: {e}")
    
    def process_video(self):
        """Iniciar el proceso de recorte"""
        if not self.selected_video.get():
            messagebox.showerror("Error", "Selecciona un video primero")
            return
        
        start = self.start_time.get().strip()
        end = self.end_time.get().strip()
        output = self.output_name.get().strip()
        
        # Validaciones
        if not start or not self.is_valid_time(start):
            messagebox.showerror("Error", "Tiempo de inicio inválido. Formato: HH:MM:SS")
            return
            
        if end and not self.is_valid_time(end):
            messagebox.showerror("Error", "Tiempo de fin inválido. Formato: HH:MM:SS")
            return
            
        if not output:
            # Usar fecha actual como nombre
            output = f"sermon_recortado_{datetime.now().strftime('%d%m%y')}"
        
        # Preparar rutas
        input_file = os.path.join(self.source_dir, self.selected_video.get())
        output_file = os.path.join(self.output_dir, f"{output}.mp4")
        
        # Deshabilitar botones
        self.process_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        self.browse_button.config(state=tk.DISABLED)
        
        # Iniciar en un hilo para no bloquear la interfaz
        thread = threading.Thread(target=self.run_ffmpeg, args=(input_file, output_file, start, end))
        thread.daemon = True
        thread.start()
    
    def run_ffmpeg(self, input_file, output_file, start_time, end_time):
        """Ejecutar ffmpeg en un hilo separado"""
        try:
            # Actualizar estado
            self.status_label.config(text="Estado: Recortando video...")
            self.progress_bar.start(10)
            
            # Preparar comando
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", input_file,
                "-ss", start_time
            ]
            
            # Añadir tiempo de fin si se especificó
            if end_time:
                ffmpeg_cmd.extend(["-to", end_time])
                
            # Opciones de codificación
            ffmpeg_cmd.extend([
                "-c:v", "copy",
                "-c:a", "copy",
                output_file
            ])
            
            # Ejecutar comando
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            
            # Verificar resultado
            if process.returncode == 0:
                self.root.after(0, lambda: self.status_label.config(text="Estado: ¡Recorte completado con éxito!"))
                self.root.after(0, lambda: messagebox.showinfo("Éxito", f"Video recortado guardado en:\n{output_file}"))
            else:
                self.root.after(0, lambda: self.status_label.config(text="Estado: Error en el recorte"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"No se pudo recortar el video:\n{stderr}"))
                
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text="Estado: Error en el recorte"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error inesperado: {e}"))
            
        finally:
            # Detener barra de progreso
            self.root.after(0, self.progress_bar.stop)
            # Habilitar botones
            self.root.after(0, lambda: self.process_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.refresh_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.browse_button.config(state=tk.NORMAL))
    
    def is_valid_time(self, time_str):
        """Validar formato de tiempo HH:MM:SS"""
        parts = time_str.split(":")
        if len(parts) != 3:
            return False
            
        try:
            h, m, s = parts
            if not (h.isdigit() and m.isdigit() and s.isdigit()):
                return False
                
            h, m, s = int(h), int(m), int(s)
            if not (0 <= h and 0 <= m < 60 and 0 <= s < 60):
                return False
                
            return True
        except:
            return False
    
    def create_widgets(self):
        """Crear todos los widgets de la interfaz"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sección de selección de video
        video_frame = ttk.LabelFrame(main_frame, text="Seleccionar Video", padding=10)
        video_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Lista de videos
        list_frame = ttk.Frame(video_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.video_listbox = tk.Listbox(list_frame, height=10, width=50)
        self.video_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.video_listbox.bind('<<ListboxSelect>>', self.select_video)
        
        # Scrollbar para la lista
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.video_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.video_listbox.config(yscrollcommand=scrollbar.set)
        
        # Botones para videos
        btn_frame = ttk.Frame(video_frame)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        self.refresh_button = ttk.Button(btn_frame, text="Actualizar", command=self.refresh_videos)
        self.refresh_button.pack(fill=tk.X, pady=5)
        
        self.browse_button = ttk.Button(btn_frame, text="Buscar...", command=self.browse_source)
        self.browse_button.pack(fill=tk.X, pady=5)
        
        # Sección de configuración
        config_frame = ttk.LabelFrame(main_frame, text="Configuración de Recorte", padding=10)
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Tiempo de inicio
        ttk.Label(config_frame, text="Tiempo de inicio (HH:MM:SS):").grid(column=0, row=0, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.start_time, width=20).grid(column=1, row=0, padx=5, pady=5)
        
        # Tiempo de fin
        ttk.Label(config_frame, text="Tiempo de fin (HH:MM:SS):").grid(column=0, row=1, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.end_time, width=20).grid(column=1, row=1, padx=5, pady=5)
        ttk.Label(config_frame, text="(Opcional)").grid(column=2, row=1, sticky=tk.W)
        
        # Nombre de salida
        ttk.Label(config_frame, text="Nombre del archivo de salida:").grid(column=0, row=2, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.output_name, width=30).grid(column=1, row=2, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Sección de proceso
        process_frame = ttk.Frame(main_frame, padding=10)
        process_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Barra de progreso
        self.progress_bar = ttk.Progressbar(process_frame, mode="indeterminate", length=400)
        self.progress_bar.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        # Estado
        self.status_label = ttk.Label(process_frame, text="Estado: Listo")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Botón de proceso
        self.process_button = ttk.Button(process_frame, text="Recortar Video", command=self.process_video, width=20)
        self.process_button.pack(side=tk.RIGHT, padx=5)
        if not self.videos:
            self.process_button.config(state=tk.DISABLED)

# Función principal
def main():
    root = tk.Tk()
    app = RecortadorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
