import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, Toplevel, colorchooser
import pandas as pd
import json
import ctypes
import platform
import os
from scheduler import AutoScheduler 
from functools import partial
from PIL import Image, ImageTk


class SchoolSchedulerApp:
    def __init__(self, root):
        self.root = root

        self.scale_factor = self._configurar_dpi()

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
            
        w = int(screen_w * 0.8)
        h = int(screen_h * 0.8)
        
        self.root.geometry(f"{w}x{h}")
        self._configurar_estilos() # Definir colores
        self._crear_header()       # Poner la barra superior
        
        self.root.title("Gestor de Horarios Modular - UJED _ Escuela de Psicología")
        self.db_file = "database.json"
        self.data = {
            "Salones": [], "Maestros": [], "Grupos": [], "Materias": []
        }
        self.subject_colors = {} 
        self.requirements = [] 
        self.listboxes = {}

        # --- MENU SUPERIOR ---
        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="💾 Guardar Cambios (Ctrl+S)", command=self.save_state)
        file_menu.add_separator()
        file_menu.add_command(label="📥 Importar Excel", command=self.import_catalogs)
        file_menu.add_command(label="❓ Ayuda", command=self.show_format_help)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        root.config(menu=menubar)
        root.bind('<Control-s>', lambda e: self.save_state())

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # 1. PESTAÑA UNIFICADA "AGREGAR DATOS"
        self.create_data_input_tab()
        
        self.scheduler_engine = None
        
        # 2. DEMÁS PESTAÑAS
        self.create_requirements_tab()
        self.create_visual_tab()

        self.load_state()

    def _configurar_estilos(self):
        style = ttk.Style()
        
        # 'clam' es un tema versátil que obedece bien a los colores personalizados en Linux/Windows
        style.theme_use('clam')
        
        # --- PALETA DE COLORES (Professional Dark/Light Mix) ---
        primary_dark = "#2c3e50"    # Azul pizarra oscuro (Encabezados)
        accent_color = "#27ae60"    # Verde esmeralda (Botones acción)
        bg_light = "#ecf0f1"        # Gris muy claro (Fondos)
        text_dark = "#2c3e50"       # Texto principal
        
        # --- CONFIGURACIÓN GENERAL ---
        # Configuramos todos los Frames y Labels para que tengan el fondo claro homogéneo
        style.configure("TFrame", background=bg_light)
        style.configure("TLabel", background=bg_light, foreground=text_dark, font=("Segoe UI", 10))
        style.configure("TLabelframe", background=bg_light, foreground=text_dark)
        style.configure("TLabelframe.Label", background=bg_light, foreground=primary_dark, font=("Segoe UI", 10, "bold"))
        
        # --- BOTONES ---
        # Botón Normal
        style.configure("TButton", 
                        font=("Segoe UI", 9), 
                        padding=6, 
                        relief="flat",
                        background="#bdc3c7",
                        foreground="black")
        
        # Efecto Hover (cuando pasas el mouse)
        style.map("TButton", background=[("active", "#95a5a6")])

        # Botón de Acción (Guardar/Calcular) - Estilo Personalizado
        style.configure("Accent.TButton", 
                        font=("Segoe UI", 10, "bold"), 
                        background=accent_color, 
                        foreground="white")
        style.map("Accent.TButton", background=[("active", "#219150")])

        # --- TREEVIEW (Tablas) ---
        style.configure("Treeview", 
                        background="white",
                        foreground="black", 
                        rowheight=25,
                        fieldbackground="white")
        style.map("Treeview", background=[("selected", primary_dark)])
        
        # Encabezados de la tabla
        style.configure("Treeview.Heading", 
                        font=("Segoe UI", 9, "bold"), 
                        background="#bdc3c7", 
                        foreground="black")

        # --- PESTAÑAS (Notebook) ---
        style.configure("TNotebook", background=bg_light)
        style.configure("TNotebook.Tab", padding=[10, 5], font=("Segoe UI", 10))
        
        # Guardamos colores en self para usarlos en widgets no-ttk (como Canvas o tk.Frame)
        self.colors = {
            "primary": primary_dark,
            "bg": bg_light,
            "accent": accent_color,
            "text": text_dark
        }
        
        # Configurar el fondo de la ventana raíz
        self.root.configure(bg=bg_light)


    def _crear_header(self):
        # Frame superior oscuro (Tkinter nativo para controlar el color de fondo exacto sin bordes)
        header = tk.Frame(self.root, bg=self.colors["primary"], height=80)
        header.pack(side="top", fill="x")
        
        # --- LOGO (Izquierda) ---
        # Asegúrate de tener una imagen 'logo.png' en tu carpeta o usa un try/except
        try:
            # Cargar y redimensionar imagen con alta calidad
            load = Image.open("logo.png") 
            # Redimensionar proporcionalmente (ej. 60px de alto)
            aspect = load.width / load.height
            load = load.resize((int(60 * aspect), 60), Image.Resampling.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(load) # Guardar referencia en self para que no la borre el recolector de basura
            
            lbl_logo = tk.Label(header, image=self.logo_img, bg=self.colors["primary"])
            lbl_logo.pack(side="left", padx=20, pady=10)
        except Exception as e:
            # Si no hay imagen, ponemos un texto placeholder
            tk.Label(header, text="🏛️ UDLAP", font=("Arial", 20, "bold"), 
                     bg=self.colors["primary"], fg="white").pack(side="left", padx=20)

        # --- TÍTULO (Centro/Izquierda) ---
        title_frame = tk.Frame(header, bg=self.colors["primary"])
        title_frame.pack(side="left", padx=10)
        
        tk.Label(title_frame, text="Sistema de Gestión de Horarios", 
                 font=("Segoe UI", 18, "bold"), bg=self.colors["primary"], fg="white").pack(anchor="w")
        
        tk.Label(title_frame, text="Optimización Inteligente de Recursos", 
                 font=("Segoe UI", 10, "italic"), bg=self.colors["primary"], fg="#bdc3c7").pack(anchor="w")

        # --- TU FIRMA (Derecha) ---
        # Frame para alinear a la derecha
        right_frame = tk.Frame(header, bg=self.colors["primary"])
        right_frame.pack(side="right", padx=20)
        
        tk.Label(right_frame, text="Desarrollado por:", 
                 font=("Segoe UI", 8), bg=self.colors["primary"], fg="#bdc3c7").pack(anchor="e")
        
        tk.Label(right_frame, text="Rosh", 
                 font=("Segoe UI", 14, "bold"), bg=self.colors["primary"], fg=self.colors["accent"]).pack(anchor="e")


    def _configurar_dpi(self):
        """
        Ajusta la escala de la UI basándose en el sistema operativo y la densidad del monitor.
        Objetivo: S_factor = DPI_real / 96.0
        """
        sistema = platform.system()
        scale_factor = 1.0
        
        if sistema == "Windows":
            try:
                # Windows 10/11: SetProcessDpiAwareness(1)
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
                scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
            except:
                try:
                    # Windows 7/8
                    ctypes.windll.user32.SetProcessDPIAware()
                except:
                    pass # Fallback silencioso
                    
        elif sistema == "Linux":
            # Para tu Hyprland/CachyOS
            dpi = self.root.winfo_fpixels('1i')
            scale_factor = dpi / 96.0
            
            # Corrección heurística para pantallas HiDPI en Linux si Tkinter se queda corto
            if scale_factor < 1.2 and self.root.winfo_screenwidth() > 1920:
                 scale_factor = 1.5 
        
        # Aplicamos el factor al motor gráfico Tcl
        # Esto reescala fuentes y grosores de widgets
        self.root.tk.call('tk', 'scaling', scale_factor)
        
        # Opcional: Retornar el factor por si quieres ajustar tamaños de fuente manualmente
        return scale_factor 


    # --- PESTAÑAS DE DATOS ---
    def create_data_input_tab(self):
        main_data_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_data_frame, text="📂 Agregar Datos")
        self.catalogs_notebook = ttk.Notebook(main_data_frame)
        self.catalogs_notebook.pack(expand=True, fill='both', padx=10, pady=10)
        for var_name in ["Salones", "Maestros", "Grupos", "Materias"]:
            self.create_crud_tab(var_name, parent=self.catalogs_notebook)


    def create_crud_tab(self, category, parent):
        frame = ttk.Frame(parent)
        parent.add(frame, text=category)
        
        # Panel de entrada
        input_frame = ttk.LabelFrame(frame, text=f"Nuevo {category[:-1]}") # Truco: Materias -> Materia
        input_frame.pack(fill='x', padx=20, pady=10)
        
        # Entrada de texto (Nombre)
        ttk.Label(input_frame, text="Nombre:").pack(side='left', padx=5)
        entry = ttk.Entry(input_frame, width=25)
        entry.pack(side='left', padx=5)
        
        # --- LÓGICA ESPECIAL PARA MATERIAS ---
        self.current_color = "#3498db" # Azul por defecto
        btn_color = None # Variable placeholder
        
        if category == "Materias":
            # Función para abrir el selector
            def pick_color():
                # colorchooser devuelve ((r,g,b), "#hex")
                color = colorchooser.askcolor(title="Color de Materia", color=self.current_color)
                if color[1]: # Si no canceló
                    self.current_color = color[1]
                    btn_color.config(bg=self.current_color) # Actualizar visualmente el botón

            ttk.Label(input_frame, text="Color:").pack(side='left', padx=5)
            # Usamos tk.Button normal para poder cambiar el background
            btn_color = tk.Button(input_frame, text="🎨", width=3, bg=self.current_color, command=pick_color)
            btn_color.pack(side='left', padx=5)

        # Listbox para ver los existentes
        lb = tk.Listbox(frame, height=12)
        lb.pack(expand=True, fill='both', padx=20, pady=10)
        self.listboxes[category] = lb
        
        # --- FUNCIÓN AGREGAR MEJORADA ---
        def add():
            v = entry.get().strip()
            if v and v not in self.data[category]:
                self.data[category].append(v)
                lb.insert(tk.END, v)
                
                # Si es Materia, guardamos su color y pintamos la lista
                if category == "Materias":
                    self.subject_colors[v] = self.current_color
                    
                    text_col = self._get_contrast_text_color(self.current_color)
                    # Pintar el item en el Listbox para feedback visual inmediato
                    idx = lb.size() - 1
                    lb.itemconfig(idx, {'bg': self.current_color, 'fg':text_col, 'selectbackground': self.current_color, 'selectforeground': text_col})
                    # Resetear color al default para la siguiente
                    self.current_color = "#3498db" 
                    btn_color.config(bg=self.current_color)

                entry.delete(0, tk.END)

        def delete():
            sel = lb.curselection()
            if sel:
                val = lb.get(sel[0])
                self.data[category].remove(val)
                lb.delete(sel[0])
                # Limpiar también del diccionario de colores si es materia
                if category == "Materias" and val in self.subject_colors:
                    del self.subject_colors[val]

        # Botonera de acción
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="➕ Agregar", command=add).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="🗑️ Eliminar Seleccionado", command=delete).pack(side='left', padx=10)

    # --- PERSISTENCIA ---
    def save_state(self):
        # 1. Capturar asignaciones actuales si existe el motor
        allocated_classes = []
        if self.scheduler_engine:
            for day in self.scheduler_engine.days:
                df = self.scheduler_engine.grid[day]
                for time in self.scheduler_engine.hours:
                    for room in self.scheduler_engine.rooms:
                        cell = df.at[time, room]
                        if cell:
                            # Guardamos la 'foto' de esta asignación
                            allocated_classes.append({
                                'day': day,
                                'time': time,
                                'room': room,
                                'data': cell # El objeto clase (maestro, materia, etc.)
                            })
        # 2. Estructura de guardado completa
        state = {
            "catalogs": self.data,
            "subject_colors": self.subject_colors,
            "requirements": self.requirements,
            "allocations": allocated_classes 
        }
        
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Guardado", "Cambios y Horario actual guardados.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_state(self):

        if not os.path.exists(self.db_file): return
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self.data = state.get("catalogs", self.data)
            self.subject_colors = state.get("sunject_colors", {})
            self.requirements = state.get("requirements", [])
            self.refresh_crud_views()
            
            # Limpiar y repoblar árbol
            for item in self.tree_req.get_children(): self.tree_req.delete(item)
            
            for req in self.requirements:
                # Usar .get() para compatibilidad con archivos viejos
                sat_rule = req.get('saturday_rule', 'Puede') 
                self.tree_req.insert("", tk.END, values=(
                    req['subject'], req['teacher'], req['group'], 
                    req['sessions'], req['duration'], sat_rule
                ))

            # --- RECUPERACIÓN DE LA MATRIZ (HORARIO) ---
            allocations = state.get("allocations", [])
            if allocations and self.data['Salones']:
                # 1. Inicializar el motor silenciosamente
                if not self.scheduler_engine:
                    self.scheduler_engine = AutoScheduler(self.data['Salones'])
                
                # 2. Re-inyectar las clases guardadas
                # Es vital usar _place_class para que se marquen ocupados los maestros/grupos
                count = 0
                for alloc in allocations:
                    day = alloc['day']
                    time = alloc['time']
                    room = alloc['room']
                    cell_data = alloc['data']
                    
                    # Generamos una llave única para el rastreo interno
                    subj_key = f"{cell_data['subject']}_{cell_data['group']}"
                    
                    # Intentamos colocarla (sin validación estricta para asegurar restauración)
                    # O usamos _place_class directamente confiando en que el guardado era válido
                    try:
                        self.scheduler_engine._place_class(day, time, room, cell_data, subj_key)
                        count += 1
                    except Exception:
                        pass # Si falla una, seguimos con las demás
                
                if count > 0:
                    print(f"Horario restaurado: {count} bloques recuperados.")
                    # Habilitar la pestaña visual si hay datos
                    self.notebook.select(self.visual_frame)
                    self.render_visual_notebook()

        except Exception as e:
            print(f"Error cargando estado: {e}")
    # --- UTILS ---
    def show_format_help(self):
        messagebox.showinfo("Ayuda", "Hojas Excel:\n'Salones', 'Maestros', 'Grupos', 'Materias'.")

    def import_catalogs(self):
        filename = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if not filename: return
        try:
            xls = pd.read_excel(filename, sheet_name=None)
            count = 0
            for cat in self.data.keys():
                if cat in xls:
                    vals = xls[cat].iloc[:, 0].dropna().astype(str).unique().tolist()
                    for v in vals:
                        if v not in self.data[cat]:
                            self.data[cat].append(v)
                            count += 1
            self.refresh_crud_views()
            messagebox.showinfo("Éxito", f"Importados {count} registros.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh_crud_views(self):
        for cat, lb in self.listboxes.items():
            lb.delete(0, tk.END)
            for i, item in enumerate(self.data[cat]):
                lb.insert(tk.END, item)
                
                # Si es materia, recuperamos su color y calculamos contraste
                if cat == "Materias" and item in self.subject_colors:
                    bg_c = self.subject_colors[item]
                    fg_c = self._get_contrast_text_color(bg_c) # <--- CALCULO
                    
                    try:
                        lb.itemconfig(i, {
                            'bg': bg_c, 
                            'fg': fg_c, # <--- APLICACION
                            'selectbackground': bg_c,
                            'selectforeground': fg_c
                        })
                    except: pass 

    def on_tab_change(self, event):
        tab_text = event.widget.tab(event.widget.select(), "text")
        if "Horario Interactivo" in tab_text:
            self.render_visual_notebook()
        elif "Clases" in tab_text:
            if hasattr(self, 'combos'):
                for k, cb in self.combos.items(): cb['values'] = self.data[k]

    # --- PESTAÑA CLASES ---
    def create_requirements_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📝 Clases")
        
        ctrl_frame = ttk.LabelFrame(frame, text="Nueva Clase")
        ctrl_frame.pack(fill='x', padx=10, pady=10)

        self.cb_vars = {k: tk.StringVar() for k in ["Maestros", "Materias", "Grupos"]}
        self.combos = {}
        
        # Agregamos columnas extras para Sábado
        for i, k in enumerate(["Materias", "Maestros", "Grupos"]):
            ttk.Label(ctrl_frame, text=k).grid(row=0, column=i, padx=5, sticky='w')
            cb = ttk.Combobox(ctrl_frame, textvariable=self.cb_vars[k], state="readonly", width=15)
            cb.grid(row=1, column=i, padx=5)
            self.combos[k] = cb

        ttk.Label(ctrl_frame, text="Sesiones").grid(row=0, column=3, padx=5)
        spin_sess = ttk.Spinbox(ctrl_frame, from_=1, to=5, width=5)
        spin_sess.set(1)
        spin_sess.grid(row=1, column=3, padx=5)
        
        ttk.Label(ctrl_frame, text="Duración (h)").grid(row=0, column=4, padx=5)
        spin_dur = ttk.Spinbox(ctrl_frame, values=(1, 2, 3, 4), width=5)
        spin_dur.set(2) # [CHANGE] Default cambiado a 2
        spin_dur.grid(row=1, column=4, padx=5)

        # [NEW] Selector de Sábado
        ttk.Label(ctrl_frame, text="¿Sábado?").grid(row=0, column=5, padx=5)
        self.var_sat = tk.StringVar(value="Puede")
        cb_sat = ttk.Combobox(ctrl_frame, textvariable=self.var_sat, values=["Puede", "No", "Sí o sí"], state="readonly", width=8)
        cb_sat.grid(row=1, column=5, padx=5)

        # [CHANGE] Agregamos columna "Sab" al Treeview
        columns = ("Mat", "Prof", "Gpo", "Ses", "Dur", "Sab")
        self.tree_req = ttk.Treeview(frame, columns=columns, show='headings', height=10)
        
        widths = [100, 100, 100, 50, 50, 70]
        for c, w in zip(columns, widths): 
            self.tree_req.heading(c, text=c)
            self.tree_req.column(c, width=w)
        
        self.tree_req.pack(expand=True, fill='both', padx=10)

        def add_req():
            vals = {k: var.get() for k, var in self.cb_vars.items()}
            if all(vals.values()):
                try:
                    s = int(spin_sess.get())
                    d = int(spin_dur.get())
                    sat_rule = self.var_sat.get() # Capturar regla
                    
                    self.requirements.append({
                        'subject': vals['Materias'], 
                        'teacher': vals['Maestros'],
                        'group': vals['Grupos'], 
                        'sessions': s, 
                        'duration': d,
                        'saturday_rule': sat_rule # Guardar regla
                    })
                    # Actualizar vista
                    self.tree_req.insert("", tk.END, values=(
                        vals['Materias'], vals['Maestros'], vals['Grupos'], s, d, sat_rule
                    ))
                except ValueError: pass

        def del_req():
            sel = self.tree_req.selection()
            if sel:
                idx = self.tree_req.index(sel[0])
                del self.requirements[idx]
                self.tree_req.delete(sel[0])

        btn_frame = ttk.Frame(ctrl_frame)
        btn_frame.grid(row=2, column=0, columnspan=6, pady=10)
        ttk.Button(btn_frame, text="➕ Agregar", command=add_req).pack(side='left', padx=10)
        ttk.Button(frame, text="🗑️ Eliminar", command=del_req).pack(pady=5)
        
        
    def get_weekly_grid_for_entity(self, entity_type, entity_name):
        """
        Genera un DataFrame donde:
        - Filas: Horas
        - Columnas: Días de la semana (Lunes, Martes...)
        - Celdas: La clase correspondiente a la entidad seleccionada.
        """
        days = self.scheduler_engine.days
        hours = self.scheduler_engine.hours
        
        # Creamos una matriz vacía [Horas x Días]
        df_view = pd.DataFrame(index=hours, columns=days)
        df_view[:] = None # Inicializar con None
        
        for day in days:
            # Grid original del día: [Horas x Salones]
            day_grid = self.scheduler_engine.grid[day]
            
            for h in hours:
                cell = None
                
                if entity_type == "Por Salón":
                    # Acceso directo: Dame lo que pasa en este salón a esta hora
                    if entity_name in day_grid.columns:
                        cell = day_grid.at[h, entity_name]
                        
                elif entity_type == "Por Maestro":
                    # Búsqueda: Buscar en todos los salones dónde está este maestro
                    # (Iteramos la fila de esa hora)
                    row_data = day_grid.loc[h]
                    for room_col in day_grid.columns:
                        c = row_data[room_col]
                        if c and c['teacher'] == entity_name:
                            cell = c
                            # Guardamos el salón original para referencia visual
                            # Hacemos una copia superficial para no alterar el objeto real
                            cell = cell.copy() 
                            cell['display_room'] = room_col 
                            break
                
                # Asignamos a nuestra nueva matriz visual
                df_view.at[h, day] = cell
                
        return df_view
    
    def get_data_by_teacher_view(self, day):
        """
        Transforma la matriz [Horas x Salones] a [Horas x Maestros].
        Retorna un DataFrame temporal para visualización.
        """
        # 1. Obtener lista de todos los maestros
        teachers = sorted(self.data.get("Maestros", []))
        hours = self.scheduler_engine.hours
        
        # 2. Crear DataFrame vacío: Filas=Horas, Cols=Maestros
        df_teachers = pd.DataFrame(index=hours, columns=teachers)
        df_teachers[:] = None
        
        # 3. Llenar datos iterando sobre la grilla original de salones
        original_df = self.scheduler_engine.grid[day]
        
        for h in hours:
            for room in original_df.columns:
                cell = original_df.at[h, room]
                if cell:
                    # Si hay clase, colocamos la info en la columna del maestro correspondiente
                    teacher_name = cell['teacher']
                    if teacher_name in df_teachers.columns:
                        # Clonamos la celda para agregarle el dato del SALÓN (que ahora es el dato variable)
                        cell_view = cell.copy()
                        cell_view['display_text'] = f"{cell['subject']}\n({cell['group']})\n📍 {room}"
                        # Guardamos la referencia original para poder eliminarla si es necesario
                        cell_view['_original_room'] = room 
                        
                        df_teachers.at[h, teacher_name] = cell_view
                        
        return df_teachers
    # --- PESTAÑA GENERAR ---

    def run_logic(self):
        # ... validaciones iniciales ...
        if not self.data['Salones'] or not self.requirements:
             messagebox.showerror("Error", "Faltan datos.")
             return

        self.scheduler_engine = AutoScheduler(self.data['Salones'])
        flat_reqs = []
        for r in self.requirements:
            sat_rule = r.get('saturday_rule', 'Puede')
            for _ in range(r['sessions']):
                flat_reqs.append({
                    'subject': r['subject'], 
                    'teacher': r['teacher'],
                    'group': r['group'], 
                    'duration': r['duration'],
                    'saturday_rule': sat_rule # <--- PASAMOS LA REGLA AQUÍ
                })
        
        success = self.scheduler_engine.generate_schedule(flat_reqs)
        # ... resto de la función ...
        if success:
            messagebox.showinfo("Éxito", "Horario generado.")
            self.notebook.select(self.visual_frame)
            self.render_visual_notebook()
        else:
            messagebox.showwarning("Fallo", "No se pudo generar el horario con esas restricciones.")
    
    def execute_generation_sequence(self):
        # Primero calcula (bloqueante)
        self.run_logic()
        # Solo cuando termine, repinta
        self.render_visual_notebook()
    
    def create_visual_tab(self):
        self.visual_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.visual_frame, text="👁️ Horario Interactivo")
        
        # --- BARRA DE CONTROL ---
        tool = ttk.Frame(self.visual_frame)
        tool.pack(fill='x', padx=5, pady=5)
        ttk.Button(tool, text="CALCULAR HORARIO", command=self.execute_generation_sequence, style="Accent.TButton").pack(expand=True, ipadx=20, ipady=10)

        # Selector 1: MODO (¿Qué dimensión manda?)
        ttk.Label(tool, text="Modo:").pack(side='left', padx=2)
        self.viz_mode = tk.StringVar(value="General (Días)")
        cb_mode = ttk.Combobox(tool, textvariable=self.viz_mode, state="readonly", width=15,
                       values=["General (Días)", "Por Salón", "Por Maestro"])
        ttk.Button(tool, text="🔄 Actualizar", command=self.render_visual_notebook).pack(side='left', padx=5)
        cb_mode.pack(side='left', padx=5)
        
        # Selector 2: OBJETO (¿Cuál salón o cuál maestro?)
        ttk.Label(tool, text="Ver:").pack(side='left', padx=2)
        self.viz_target = tk.StringVar()
        self.cb_target = ttk.Combobox(tool, textvariable=self.viz_target, state="readonly", width=20)
        self.cb_target.pack(side='left', padx=5)
        
        # Eventos: Cuando cambia el modo, actualizamos la lista de objetos
        cb_mode.bind("<<ComboboxSelected>>", self.on_viz_mode_change)
        self.cb_target.bind("<<ComboboxSelected>>", lambda e: self.render_visual_notebook())
        
        ttk.Button(tool, text="Exportar Excel", command=self.export_excel).pack(side='right')
        
        # Contenedor de la grilla (Notebook o Frame simple)
        self.days_notebook = ttk.Notebook(self.visual_frame)
        self.days_notebook.pack(expand=True, fill='both', padx=5, pady=5)

    def on_viz_mode_change(self, event):
        mode = self.viz_mode.get()
        if mode == "General (Días)":
            self.cb_target.set("")
            self.cb_target['values'] = []
            self.render_visual_notebook()
        elif mode == "Por Salón":
            self.cb_target['values'] = self.data['Salones']
            if self.data['Salones']: self.cb_target.current(0)
            self.render_visual_notebook()
        elif mode == "Por Maestro":
            self.cb_target['values'] = self.data['Maestros']
            if self.data['Maestros']: self.cb_target.current(0)
            self.render_visual_notebook()

    def render_visual_notebook(self):
        # Limpiar todo
        for tab in self.days_notebook.tabs(): 
            self.days_notebook.forget(tab)
            
        if not self.scheduler_engine: return

        mode = self.viz_mode.get()
        target = self.viz_target.get()

        # ESTRATEGIA A: VISTA GENERAL (Días en las pestañas)
        if mode == "General (Días)":
            for day in self.scheduler_engine.days:
                # [CHANGE] Pasamos 'day' como contexto explícito (tab_context)
                self.create_tab_grid(day, self.scheduler_engine.grid[day], is_weekly_view=False, tab_context=day)

        # ESTRATEGIA B: VISTA FILTRADA (Entidad en la pestaña, Días en columnas)
        else:
            if not target: return
            df_weekly = self.get_weekly_grid_for_entity(mode, target)
            # [CHANGE] tab_context es la entidad (ej. nombre del maestro), pero las columnas serán los días
            self.create_tab_grid(f"Horario: {target}", df_weekly, is_weekly_view=True, tab_context=target)

    def create_tab_grid(self, tab_title, data_frame, is_weekly_view, tab_context):
        f_tab = ttk.Frame(self.days_notebook)
        self.days_notebook.add(f_tab, text=tab_title)
        
        canvas = tk.Canvas(f_tab)
        scroll_v = ttk.Scrollbar(f_tab, orient="vertical", command=canvas.yview)
        scroll_h = ttk.Scrollbar(f_tab, orient="horizontal", command=canvas.xview)
        content = ttk.Frame(canvas)
        
        content.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
        canvas.create_window((0,0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scroll_v.set, xscrollcommand=scroll_h.set)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll_v.grid(row=0, column=1, sticky="ns")
        scroll_h.grid(row=1, column=0, sticky="ew")
        f_tab.grid_rowconfigure(0, weight=1); f_tab.grid_columnconfigure(0, weight=1)

        # Llamamos al renderizador pasando el contexto
        self.render_generic_grid(content, data_frame, is_weekly_view, tab_context)

    def render_generic_grid(self, parent, df, is_weekly_view, tab_context):
        hours = list(df.index)
        cols = list(df.columns) 

        # --- PALETA DE COLORES LOCAL (Para control total) ---
        COLOR_HEADER_BG = "#34495e"  # Azul oscuro profesional
        COLOR_HEADER_FG = "white"
        
        COLOR_TIME_BG   = "#ecf0f1"  # Gris muy claro para las horas
        COLOR_TIME_FG   = "#2c3e50"
        
        COLOR_FREE_BG   = "white"
        COLOR_FREE_FG   = "#95a5a6"  # Gris para el signo '+'
        
        COLOR_BUSY_BG   = "#27ae60"  # Verde esmeralda (Buen contraste con blanco)
        COLOR_BUSY_FG   = "white"    # Texto blanco puro
        
        # ----------------------------------------------------

        # Encabezados (Días o Salones)
        # Usamos tk.Label estándar para poder forzar el background exacto
        tk.Label(parent, text="Hora", font=('Segoe UI', 9, 'bold'), 
                 bg=COLOR_HEADER_BG, fg=COLOR_HEADER_FG, width=8).grid(row=0, column=0, padx=1, pady=1, sticky="nsew")
        
        for j, c in enumerate(cols):
            # Escalado del ancho
            w_col = int(20 * getattr(self, 'scale_factor', 1.0)) 
            tk.Label(parent, text=c, font=('Segoe UI', 9, 'bold'), 
                     bg=COLOR_HEADER_BG, fg=COLOR_HEADER_FG, width=w_col).grid(row=0, column=j+1, padx=1, pady=1, sticky="nsew")

        # Celdas del Grid
        for i, h in enumerate(hours):
            # Columna de Hora (Izquierda)
            tk.Label(parent, text=f"{h}:00", font=('Segoe UI', 8, 'bold'), 
                     bg=COLOR_TIME_BG, fg=COLOR_TIME_FG).grid(row=i+1, column=0, sticky="nsew", padx=1, pady=1)
            
            for j, col in enumerate(cols):
                cell = df.at[h, col]
                
                # Cálculo de coordenadas (Igual que antes)
                target_day = None
                target_room = None
                if is_weekly_view:
                    target_day = col
                    if cell and 'display_room' in cell: target_room = cell['display_room']
                    else: target_room = tab_context 
                else:
                    target_day = tab_context
                    target_room = col

                # --- LÓGICA VISUAL DE ALTO CONTRASTE ---
                if cell:
                    # CASO OCUPADO
                    subject_name = cell['subject']

                    bg_color = self.subject_colors.get(subject_name, "#26ae60")
                    fg_color = self._get_contrast_text_color(bg_color)
                    relief = "raised"
                    cursor = "hand2" # Manita al pasar el mouse
                    
                    if is_weekly_view and 'display_room' in cell:
                        # Usamos emojis para guiar el ojo rápidamente
                        txt = f"{cell['subject']}\nGroup: {cell['group']}\n📍 {cell['display_room']}"
                    else:
                        txt = f"{cell['subject']}\n{cell['group']}"
                        if not is_weekly_view:
                            # En vista general, añadimos el profe para referencia rápida
                            txt += f"\n {cell['teacher']}"

                    cmd = partial(self.on_cell_click, target_day, h, target_room)
                    
                else:
                    # CASO VACÍO
                    bg_color = COLOR_FREE_BG
                    fg_color = COLOR_FREE_FG
                    relief = "flat"
                    cursor = "arrow"
                    txt = "+" 
                    cmd = partial(self.on_cell_click, target_day, h, target_room)

                # Renderizamos el BOTÓN
                # Nota: Usamos 'wraplength' para que el texto largo no ensanche la celda infinitamente
                btn = tk.Button(
                    parent, 
                    text=txt, 
                    bg=bg_color, 
                    fg=fg_color,        # <--- AQUÍ ESTÁ LA CLAVE DEL CONTRASTE
                    font=('Segoe UI', 9), 
                    relief=relief,
                    cursor=cursor,
                    borderwidth=0 if not cell else 2,
                    wraplength=120,      # Auto-ajuste de texto si es muy largo
                    activebackground="#2ecc71" if cell else "#f1f2f6", # Color al hacer click
                    command=cmd
                )
                btn.grid(row=i+1, column=j+1, padx=1, pady=1, sticky="nsew")
    def on_cell_click(self, day, time, room):
        if not self.scheduler_engine: return
        try:
            cell = self.scheduler_engine.grid[day].at[time, room]
        except:
            cell = None
        if not cell:
            self.open_add_menu(day, time, room)

        # --- VENTANA EMERGENTE (EDITOR) ---
        edit_win = tk.Toplevel(self.root)
        edit_win.title(f"Editar: {cell['subject']}")
        edit_win.geometry("650x650")
        
        # Estilos visuales rápidos
        pad_opts = {'padx': 15, 'pady': 8}
        
        # 1. INFORMACIÓN ACTUAL
        info_frame = ttk.LabelFrame(edit_win, text="Información Actual")
        info_frame.pack(fill='x', **pad_opts)
        
        lbl_text = f"Materia: {cell['subject']}\nGrupo: {cell['group']}\nMaestro: {cell['teacher']}\nDuración: {cell['duration']}h"
        ttk.Label(info_frame, text=lbl_text, font=('Arial', 10)).pack(anchor='w', padx=10)

        # 2. ÁREA DE MODIFICACIÓN MANUAL
        mod_frame = ttk.LabelFrame(edit_win, text="Mover / Cambiar")
        mod_frame.pack(fill='x', **pad_opts)

        # Selectores
        vars_mod = {}
        # Días
        ttk.Label(mod_frame, text="Nuevo Día:").grid(row=0, column=0)
        vars_mod['day'] = tk.StringVar(value=day)
        cb_day = ttk.Combobox(mod_frame, textvariable=vars_mod['day'], values=self.scheduler_engine.days, state="readonly")
        cb_day.grid(row=0, column=1)

        # Horas
        ttk.Label(mod_frame, text="Nueva Hora:").grid(row=1, column=0)
        vars_mod['time'] = tk.IntVar(value=time)
        cb_time = ttk.Combobox(mod_frame, textvariable=vars_mod['time'], values=self.scheduler_engine.hours, state="readonly")
        cb_time.grid(row=1, column=1)

        # Salones
        ttk.Label(mod_frame, text="Nuevo Salón:").grid(row=2, column=0)
        vars_mod['room'] = tk.StringVar(value=room)
        cb_room = ttk.Combobox(mod_frame, textvariable=vars_mod['room'], values=self.data['Salones'], state="readonly")
        cb_room.grid(row=2, column=1)
        
        # Maestro (Permitir cambio)
        ttk.Label(mod_frame, text="Cambiar Maestro:").grid(row=3, column=0)
        vars_mod['teacher'] = tk.StringVar(value=cell['teacher'])
        cb_prof = ttk.Combobox(mod_frame, textvariable=vars_mod['teacher'], values=self.data['Maestros'], state="readonly")
        cb_prof.grid(row=3, column=1)

        # 3. SUGERENCIAS (Listbox)
        sugg_frame = ttk.LabelFrame(edit_win, text="Sugerencias (Espacios Libres)")
        sugg_frame.pack(fill='both', expand=True, **pad_opts)
        
        lb_sugg = tk.Listbox(sugg_frame, height=6)
        lb_sugg.pack(fill='both', expand=True, side='left')
        sb_sugg = ttk.Scrollbar(sugg_frame, orient="vertical", command=lb_sugg.yview)
        sb_sugg.pack(fill='y', side='right')
        lb_sugg.config(yscrollcommand=sb_sugg.set)

        # Función para poblar sugerencias
        def load_suggestions():
            lb_sugg.delete(0, tk.END)
            # Obtenemos alternativas para la configuración ACTUAL (sin cambios manuales aun)
            alts = self.scheduler_engine.suggest_alternatives(
                cell['duration'], vars_mod['teacher'].get(), cell['group'], f"{cell['subject']}_{cell['group']}"
            )
            if not alts:
                lb_sugg.insert(tk.END, "No hay alternativas directas.")
            for a in alts:
                lb_sugg.insert(tk.END, a)

        ttk.Button(sugg_frame, text="↻ Actualizar Sugerencias", command=load_suggestions).pack(anchor='n')
        
        # Si seleccionan una sugerencia, llenar los combos
        def on_sugg_select(evt):
            sel = lb_sugg.curselection()
            if not sel: return
            val = lb_sugg.get(sel[0]) # Ej: "Lunes 7:00 - Salón 101"
            parts = val.split()
            if len(parts) >= 4:
                vars_mod['day'].set(parts[0])     # Lunes
                vars_mod['time'].set(parts[1].split(':')[0]) # 7
                # El salón es el resto del string después del guión
                # "Lunes 7:00 - Salón 101" -> split " - " -> [part1, part2]
                try:
                    r_val = val.split(" - ")[1]
                    vars_mod['room'].set(r_val)
                except: pass

        lb_sugg.bind('<<ListboxSelect>>', on_sugg_select)

        # 4. BOTONES DE ACCIÓN
        btn_frame = ttk.Frame(edit_win)
        btn_frame.pack(fill='x', **pad_opts)

        def apply_changes():
            target_d = vars_mod['day'].get()
            target_t = vars_mod['time'].get()
            target_r = vars_mod['room'].get()
            target_p = vars_mod['teacher'].get()
            
            # Caso 1: No hubo cambios
            if target_d == day and target_t == time and target_r == room and target_p == cell['teacher']:
                messagebox.showinfo("Info", "No realizaste cambios.", parent=edit_win)
                return

            # Caso 2: Intento de movimiento
            # Primero quitamos la clase ORIGINAL para evaluar si cabe en el destino
            subj_key = f"{cell['subject']}_{cell['group']}"
            
            # Hack: Creamos una copia del objeto clase con el nuevo maestro (si cambió)
            new_class_obj = cell.copy()
            new_class_obj['teacher'] = target_p
            
            # Borramos temporalmente
            self.scheduler_engine._remove_class(day, time, room, cell, subj_key)
            
            # Verificamos si es seguro ponerla en el destino
            if self.scheduler_engine._is_safe(target_d, target_t, target_r, target_p, cell['group'], cell['duration'], subj_key):
                # Es seguro -> Colocar
                self.scheduler_engine._place_class(target_d, target_t, target_r, new_class_obj, subj_key)
                messagebox.showinfo("Éxito", "Clase movida correctamente.", parent=edit_win)
                edit_win.destroy()
                self.render_visual_notebook()

            else:
                # --- ANÁLISIS FORENSE DEL ERROR ---
                conflict_type, conf_cell, conf_room = self.scheduler_engine.get_conflict_details(
                    target_d, target_t, target_p, cell['group']
                )
                
                # Rollback (Regresamos la clase original a su lugar por seguridad visual)
                self.scheduler_engine._place_class(day, time, room, cell, subj_key)
                
                # --- AQUÍ CONSTRUYES TU MENSAJE DETALLADO ---
                msg = f"⛔ CONFLICTO DE {conflict_type.upper()}\n\n"
                
                if conflict_type == "Maestro":
                    # Reto para ti: Usa f-strings para acceder a conf_cell['subject'] y conf_cell['group']
                    msg += f"El maestro {target_p} no puede estar en dos lugares.\n"
                    msg += f"ACTUALMENTE: Está dando '{conf_cell['subject']}'\n"
                    msg += f"A QUIÉN: Grupo {conf_cell['group']}\n"
                    msg += f"DÓNDE: Salón {conf_room}"
                    
                    # Tu lógica de sugerencia existente...
                    if messagebox.askyesno("Conflicto de Maestro", msg + "\n\n¿Quieres ir al choque para intentar mover LA OTRA clase?"):
                        edit_win.destroy()
                        self.on_cell_click(target_d, target_t, conf_room)
                    return # Importante retornar aquí para no mostrar el error genérico abajo

                elif conflict_type == "Grupo":
                    msg += f"El grupo {cell['group']} ya está ocupado a esta hora.\n"
                    msg += f"MATERIA: {conf_cell['subject']}\n"
                    msg += f"MAESTRO: {conf_cell['teacher']}\n"
                    msg += f"SALÓN: {conf_room}"
                    
                elif conflict_type == "Salón":
                    msg += f"El salón {target_r} ya está ocupado.\n"
                    msg += f"POR: {conf_cell['subject']} ({conf_cell['group']})\n"
                    msg += f"PROF: {conf_cell['teacher']}"

                else:
                    msg += "Conflicto desconocido o capacidad excedida."

                # Mostramos el mensaje final detallado
                messagebox.showerror("No se pudo mover", msg, parent=edit_win)


        def delete_class():
            if messagebox.askyesno("Confirmar", "¿Eliminar clase permanentemente?", parent=edit_win):
                subj_key = f"{cell['subject']}_{cell['group']}"
                self.scheduler_engine._remove_class(day, time, room, cell, subj_key)
                edit_win.destroy()
                self.render_visual_notebook()

        ttk.Button(btn_frame, text="💾 Aplicar Cambios", command=apply_changes).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="🗑️ Eliminar Clase", command=delete_class).pack(side='left', padx=5)
        
        # Cargar sugerencias iniciales
        load_suggestions()


    def open_add_menu(self, day, time, room):
        # Ventana modal pequeña
        win = Toplevel(self.root)
        win.title(f"Agregar: {day} {time}:00 - {room}")
        win.geometry("650x650")
        
        pad_opts = {'padx':15, 'pady':8}

        main_frame = ttk.LabelFrame(win, text="Detalles de Asignación")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        main_frame.columnconfigure(1, weight=1)

        ttk.Label(main_frame, text="Materia:").grid(row=0, column=0, sticky='w', **pad_opts)
        v_mat = ttk.Combobox(main_frame, values=self.data['Materias'], state="readonly")
        v_mat.grid(row=0, column=1, sticky='ew', padx=(0, 10)) # sticky='ew' estira este-oeste

        # Fila 1: Maestro
        ttk.Label(main_frame, text="Maestro:").grid(row=1, column=0, sticky='w', **pad_opts)
        v_prof = ttk.Combobox(main_frame, values=self.data['Maestros'], state="readonly")
        v_prof.grid(row=1, column=1, sticky='ew', padx=(0, 10))

        # Fila 2: Grupo
        ttk.Label(main_frame, text="Grupo:").grid(row=2, column=0, sticky='w', **pad_opts)
        v_gpo = ttk.Combobox(main_frame, values=self.data['Grupos'], state="readonly")
        v_gpo.grid(row=2, column=1, sticky='ew', padx=(0, 10))

        # Fila 3: Duración
        ttk.Label(main_frame, text="Duración (h):").grid(row=3, column=0, sticky='w', **pad_opts)
        v_dur = ttk.Spinbox(main_frame, from_=1, to=4, width=5)
        v_dur.set(1)
        v_dur.grid(row=3, column=1, sticky='w', padx=(0, 10)) # sticky='w' para que no sea gigante

        # 4. ÁREA DE BOTONES (Fuera del grid de datos, abajo)
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill='x', padx=15, pady=10)
        def confirm():
            # 1. Capturamos lo que el usuario quiere crear
            cls = {
                'subject': v_mat.get(), 
                'teacher': v_prof.get(),
                'group': v_gpo.get(), 
                'duration': int(v_dur.get())
            }
            
            # Validación básica de campos vacíos
            if not all([cls['subject'], cls['teacher'], cls['group']]): 
                messagebox.showwarning("Faltan datos", "Por favor llena todos los campos.", parent=win)
                return
            
            subj_key = f"{cls['subject']}_{cls['group']}"
            
            # 2. INTENTO DE COLOCACIÓN
            # Verificamos si es seguro agregar la clase
            if self.scheduler_engine._is_safe(day, time, room, cls['teacher'], cls['group'], cls['duration'], subj_key):
                # ES SEGURO -> Procedemos
                self.scheduler_engine._place_class(day, time, room, cls, subj_key)
                self.render_visual_notebook()
                win.destroy() # Cerramos la ventanita
            else:
                # NO ES SEGURO -> DIAGNÓSTICO
                # Aquí invocamos al mismo método que usaste en 'on_cell_click'
                conflict_type, conf_cell, conf_room = self.scheduler_engine.get_conflict_details(
                    day, time, cls['teacher'], cls['group']
                )
                
                # Construcción del reporte de error
                msg = f"NO SE PUEDE AGREGAR ({conflict_type})\n\n"
                
                if conflict_type == "Maestro":
                    msg += f"El maestro {cls['teacher']} ya está ocupado.\n"
                    if conf_cell:
                        msg += f"DANDO: {conf_cell.get('subject', '?')} al grupo {conf_cell.get('group', '?')}\n"
                        msg += f"UBICACIÓN: Salón {conf_room}"
                    else:
                        msg += "Razón: Restricción de horario o bloqueo manual."

                elif conflict_type == "Grupo":
                    msg += f"El grupo {cls['group']} no está disponible.\n"
                    if conf_cell:
                        msg += f"YA TIENE CLASE DE: {conf_cell.get('subject', '?')}\n"
                        msg += f"CON EL PROFE: {conf_cell.get('teacher', '?')}\n"
                        msg += f"EN EL SALÓN: {conf_room}"
                
                elif conflict_type == "Salón":
                    # Este caso es raro si diste click en una celda vacía, 
                    # pero puede pasar si intentas meter un bloque de 2 horas 
                    # y la SEGUNDA hora está ocupada.
                    msg += f"El salón {room} se ocupa durante el bloque de {cls['duration']}h.\n"
                    if conf_cell:
                        msg += f"CHOCA CON: {conf_cell.get('subject', '?')} ({conf_cell.get('group', '?')})"

                else:
                    msg += "Conflicto desconocido (posible choque de duración múltiple o restricción externa)."
                
                messagebox.showerror("Choque de Horario", msg, parent=win)
        ttk.Button(btn_frame, text="Guardar Asignación", command=confirm).pack(side='right', fill='x', expand=True)
        ttk.Button(btn_frame, text="Cancelar", command=win.destroy).pack(side='left', padx=5)
    # --- MENÚ DE ACCIONES (Celda Llena) ---
    def open_action_menu(self, day, time, room, cell_data):
        win = Toplevel(self.root)
        win.title(f"Gestión: {cell_data['subject']}")
        win.geometry("350x300")
        
        lbl_info = f"{cell_data['subject']}\n{cell_data['teacher']}\n{cell_data['group']}"
        tk.Label(win, text=lbl_info, font=("Arial", 10, "bold"), bg="#ddd", padx=10, pady=5).pack(fill='x', pady=5)

        # 1. MODIFICAR (Simple: Borra y abre Add Menu)
        def action_edit():
            self.action_delete(day, time, room, cell_data, ask=False) # Borrar sin preguntar
            win.destroy()
            self.open_add_menu(day, time, room) # Abrir menú de agregar
            
        # 2. BORRAR
        def action_delete_wrapper():
            if messagebox.askyesno("Confirmar", "¿Eliminar esta clase?"):
                self.action_delete(day, time, room, cell_data)
                win.destroy()

        # 3. SMART MOVE (El Cerebro)
        def action_smart_move():
            suggestions = self.scheduler_engine.suggest_alternatives(cell_data, day, time, room)
            
            if not suggestions:
                messagebox.showinfo("Turing Analysis", "No hay movimientos eficientes disponibles.")
                return
            
            # UI para seleccionar vector
            move_win = Toplevel(win)
            move_win.title("Vectores de Optimización")
            
            tk.Label(move_win, text="Selecciona la mejor opción:").pack()
            
            lb = tk.Listbox(move_win, width=50, height=5)
            lb.pack(padx=10, pady=10)
            
            for s in suggestions:
                score_desc = "⭐" * int(s['score']/10)
                lb.insert(tk.END, f"{s['day']} {s['time']}:00 en {s['room']} (Efic.: {s['score']})")
                
            def execute_move():
                sel = lb.curselection()
                if not sel: return
                target = suggestions[sel[0]]
                
                # Ejecutar movimiento: Borrar origen -> Poner destino
                self.action_delete(day, time, room, cell_data, ask=False)
                
                subj_key = f"{cell_data['subject']}_{cell_data['group']}"
                self.scheduler_engine._place_class(target['day'], target['time'], target['room'], cell_data, subj_key)
                
                self.render_visual_notebook()
                move_win.destroy()
                win.destroy()
                messagebox.showinfo("Éxito", "Clase reubicada estratégicamente.")

            ttk.Button(move_win, text="Proceder", command=execute_move).pack(pady=5)

        # Botonera
        ttk.Button(win, text="Modificar Datos", command=action_edit).pack(fill='x', padx=20, pady=2)
        ttk.Button(win, text="Desplazamiento Inteligente", command=action_smart_move).pack(fill='x', padx=20, pady=2)
        ttk.Button(win, text="Eliminar Clase", command=action_delete_wrapper).pack(fill='x', padx=20, pady=15)

    def action_delete(self, day, time, room, cell_data, ask=True):
        # Wrapper auxiliar para la lógica de borrado
        subj_key = f"{cell_data['subject']}_{cell_data['group']}"
        self.scheduler_engine._remove_class(day, time, room, cell_data, subj_key)
        self.render_visual_notebook()
        
    def export_excel(self):
        if not self.scheduler_engine: return
        fname = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if fname:
            ok, msg = self.scheduler_engine.export_excel(fname)
            messagebox.showinfo("Exportar", msg)




    def _get_contrast_text_color(self, hex_color):
        """
        Calcula si el texto debe ser blanco o negro basado en la luminancia del fondo.
        Fórmula: L = 0.299R + 0.587G + 0.114B
        """
        if not hex_color or not hex_color.startswith('#'):
            return "black" # Fallback por seguridad
        
        # 1. Convertir Hex (#RRGGBB) a decimales (R, G, B)
        h = hex_color.lstrip('#')
        try:
            r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            
            # 2. Calcular Luminancia
            luminance = (0.299 * r + 0.587 * g + 0.114 * b)
            
            # 3. Decisión (Umbral estándar 128)
            return "black" if luminance > 128 else "white"
        except ValueError:
            return "black"
