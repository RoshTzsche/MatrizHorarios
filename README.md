# Gestor de Horarios Modular 

Sistema de orquestación de horarios universitarios mediante algoritmos de resolución combinatoria.

## Instalación y Ejecución

### 1. Linux (Distribuciones basadas en Arch / CachyOS)

Python en Arch Linux no incluye los binarios de Tcl/Tk por defecto. 

1. Instala el compilador gráfico del sistema:
```bash
sudo pacman -S tk
```

2. Navega al directorio del proyecto y crea un entorno virtual para aislar las dependencias:
```bash
python -m venv .venv
```

3. Activa el entorno virtual:
```bash
source .venv/bin/activate
```

4. Instala los paquetes requeridos:
```bash
pip install pandas Pillow openpyxl xlsxwriter
```

5. Ejecuta el sistema:
```bash
python main.py
```
*Nota técnica para Wayland/Hyprland: Si el escalado DPI falla y el texto es difuso, fuerza la variable de entorno del motor gráfico ejecutando `GDK_SCALE=1.5 python main.py`.*

### 2. Windows 10/11

Tkinter viene incluido por defecto en los instaladores oficiales de Python para arquitecturas Windows.

1. Asegúrate de tener Python 3.10 o superior instalado. Durante la instalación, es obligatorio marcar la casilla "Add Python to PATH".
2. Abre la terminal (PowerShell o CMD) en la carpeta del proyecto.
3. Crea el entorno virtual:
```cmd
python -m venv .venv
```
4. Activa el entorno virtual:
```cmd
.venv\Scripts\activate
```
5. Instala los dependencias requeridas:
```cmd
pip install pandas Pillow openpyxl xlsxwriter
```
6. Ejecuta el sistema:
```cmd
python main.py
```

## Arquitectura del Código

* `main.py`: Punto de entrada e inicialización de las llamadas al sistema para el escalado DPI.
* `gui.py`: Renderizado matricial. Implementa el cálculo matemático de luminancia para la legibilidad (L = 0.299R + 0.587G + 0.114B).
* `scheduler.py`: Motor de validación espacial y temporal mediante algoritmos de ramificación y poda (Backtracking).
