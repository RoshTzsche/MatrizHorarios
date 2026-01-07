import tkinter as tk
from tkinter import ttk
import ctypes

# Importamos la clase de la interfaz desde gui.py
from gui import SchoolSchedulerApp 

if __name__ == "__main__":
    # Configuración para Windows (DPI High Awareness)
    # Esto hace que las fuentes se vean nítidas en monitores modernos
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass # Si estamos en Linux, esto se ignora

    root = tk.Tk()
    
    # Intentar usar tema 'clam' para que se vea mejor en Linux/Windows
    try:
        style = ttk.Style()
        style.theme_use('clam')
    except:
        pass

    app = SchoolSchedulerApp(root)
    root.mainloop()