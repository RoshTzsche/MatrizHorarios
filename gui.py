import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import json
import os
# IMPORTANTE: Importamos la lógica desde scheduler.py
from scheduler import AutoScheduler 

class SchoolSchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Horarios Modular")
        self.root.geometry("1100x850")

        self.db_file = "database.json"
        self.data = {
            "Salones": [], "Maestros": [], "Grupos": [], "Materias": []
        }
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
        self.create_run_tab()
        self.create_visual_tab()

        self.load_state()

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
        
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill='x', padx=20, pady=10)
        entry = ttk.Entry(input_frame)
        entry.pack(side='left', expand=True, fill='x')
        
        lb = tk.Listbox(frame, height=15)
        lb.pack(expand=True, fill='both', padx=20, pady=5)
        self.listboxes[category] = lb
        
        def add():
            v = entry.get().strip()
            if v and v not in self.data[category]:
                self.data[category].append(v)
                lb.insert(tk.END, v)
                entry.delete(0, tk.END)
        def delete():
            sel = lb.curselection()
            if sel:
                val = lb.get(sel[0])
                self.data[category].remove(val)
                lb.delete(sel[0])

        ttk.Button(input_frame, text="Agregar", command=add).pack(side='right', padx=5)
        ttk.Button(frame, text="Eliminar Seleccionado", command=delete).pack(pady=5)

    # --- PERSISTENCIA ---
    def save_state(self):
        state = {"catalogs": self.data, "requirements": self.requirements}
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Guardado", "Cambios guardados localmente.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_state(self):
        if not os.path.exists(self.db_file): return
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self.data = state.get("catalogs", self.data)
            self.requirements = state.get("requirements", [])
            self.refresh_crud_views()
            for item in self.tree_req.get_children(): self.tree_req.delete(item)
            for req in self.requirements:
                self.tree_req.insert("", tk.END, values=(
                    req['subject'], req['teacher'], req['group'], 
                    req['sessions'], req['duration']
                ))
        except Exception: pass

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
            for item in self.data[cat]: lb.insert(tk.END, item)
        if hasattr(self, 'combos'):
            for k, cb in self.combos.items(): cb['values'] = self.data[k]

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
        spin_dur = ttk.Spinbox(ctrl_frame, values=(1, 2), width=5)
        spin_dur.set(1)
        spin_dur.grid(row=1, column=4, padx=5)

        self.tree_req = ttk.Treeview(frame, columns=("Mat", "Prof", "Gpo", "Ses", "Dur"), show='headings', height=10)
        for c in ("Mat", "Prof", "Gpo", "Ses", "Dur"): 
            self.tree_req.heading(c, text=c); self.tree_req.column(c, width=100)
        self.tree_req.pack(expand=True, fill='both', padx=10)

        def add_req():
            vals = {k: var.get() for k, var in self.cb_vars.items()}
            if all(vals.values()):
                try:
                    s = int(spin_sess.get()); d = int(spin_dur.get())
                    self.requirements.append({
                        'subject': vals['Materias'], 'teacher': vals['Maestros'],
                        'group': vals['Grupos'], 'sessions': s, 'duration': d
                    })
                    self.tree_req.insert("", tk.END, values=(vals['Materias'], vals['Maestros'], vals['Grupos'], s, d))
                except ValueError: pass

        def del_req():
            sel = self.tree_req.selection()
            if sel:
                idx = self.tree_req.index(sel[0])
                del self.requirements[idx]
                self.tree_req.delete(sel[0])

        btn_frame = ttk.Frame(ctrl_frame)
        btn_frame.grid(row=2, column=0, columnspan=5, pady=10)
        ttk.Button(btn_frame, text="➕ Agregar", command=add_req).pack(side='left', padx=10)
        ttk.Button(frame, text="🗑️ Eliminar", command=del_req).pack(pady=5)

# En gui.py -> SchoolSchedulerApp
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
    def create_run_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🚀 Generar")
        ttk.Button(frame, text="CALCULAR HORARIO", command=self.run_logic).pack(expand=True, ipadx=20, ipady=20)

    def run_logic(self):
        if not self.data['Salones'] or not self.requirements:
            messagebox.showerror("Error", "Faltan datos.")
            return

        self.scheduler_engine = AutoScheduler(self.data['Salones'])
        flat_reqs = []
        for r in self.requirements:
            for _ in range(r['sessions']):
                flat_reqs.append({
                    'subject': r['subject'], 'teacher': r['teacher'],
                    'group': r['group'], 'duration': r['duration']
                })
        
        success = self.scheduler_engine.generate_schedule(flat_reqs)
        if success:
            messagebox.showinfo("Éxito", "Horario generado.")
            self.notebook.select(self.visual_frame)
        else:
            messagebox.showwarning("Fallo", "No se pudo generar el horario.")

    # --- PESTAÑA VISUAL ---
# En gui.py -> SchoolSchedulerApp

    def create_visual_tab(self):
        self.visual_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.visual_frame, text="👁️ Horario Interactivo")
        
        # --- BARRA DE CONTROL ---
        tool = ttk.Frame(self.visual_frame)
        tool.pack(fill='x', padx=5, pady=5)
        
        # Selector 1: MODO (¿Qué dimensión manda?)
        ttk.Label(tool, text="Modo:").pack(side='left', padx=2)
        self.viz_mode = tk.StringVar(value="General (Días)")
        cb_mode = ttk.Combobox(tool, textvariable=self.viz_mode, state="readonly", width=15,
                               values=["General (Días)", "Por Salón", "Por Maestro"])
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

        # ESTRATEGIA A: VISTA GENERAL (Lo que ya tenías)
        if mode == "General (Días)":
            for day in self.scheduler_engine.days:
                self.create_tab_grid(day, self.scheduler_engine.grid[day], is_weekly_view=False)

        # ESTRATEGIA B: VISTA FILTRADA (La inversión)
        else:
            if not target: return
            # 1. Obtenemos la data pivotada (Cols=Días, Rows=Horas)
            df_weekly = self.get_weekly_grid_for_entity(mode, target)
            
            # 2. Renderizamos una sola pestaña llamada como la entidad
            self.create_tab_grid(f"Horario: {target}", df_weekly, is_weekly_view=True)

    # Función auxiliar para no repetir código de creación de canvas
    def create_tab_grid(self, tab_title, data_frame, is_weekly_view):
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

        # Llamamos al renderizador de celdas
        self.render_generic_grid(content, data_frame, is_weekly_view)

    def render_generic_grid(self, parent, df, is_weekly_view):
        hours = list(df.index)
        cols = list(df.columns) # Pueden ser Salones (modo general) o Días (modo semanal)

        # Encabezados
        tk.Label(parent, text="Hora", font=('Arial', 9, 'bold'), bg="#ccc", width=8).grid(row=0, column=0, padx=1, pady=1)
        for j, c in enumerate(cols):
            tk.Label(parent, text=c, font=('Arial', 9, 'bold'), bg="#ddd", width=18).grid(row=0, column=j+1, padx=1, pady=1)

        # Celdas
        for i, h in enumerate(hours):
            tk.Label(parent, text=f"{h}:00", font=('Arial', 8, 'bold'), bg="#eee").grid(row=i+1, column=0, sticky="nsew", padx=1, pady=1)
            for j, col in enumerate(cols):
                cell = df.at[h, col]
                bg = "#c3e6cb" if cell else "white"
                txt = "---"
                
                if cell:
                    # Lógica de texto según la vista
                    if is_weekly_view:
                        # Si veo Días en columnas, quiero saber Salón (si veo maestro) o Materia/Grupo
                        if 'display_room' in cell: # Es vista Maestro
                            txt = f"{cell['subject']}\n{cell['group']}\n📍 {cell['display_room']}"
                        else: # Es vista Salón
                            txt = f"{cell['subject']}\n({cell['teacher']})\n{cell['group']}"
                    else:
                        # Vista clásica
                        txt = f"{cell['subject']}\n{cell['group']}"

                # Nota: Desactivamos el click en vista semanal para simplificar, 
                # o tendrías que mapear el evento de borrado al día/salón correcto.
                tk.Button(parent, text=txt, bg=bg, font=('Arial', 8), height=4, width=18, relief="flat").grid(row=i+1, column=j+1, padx=1, pady=1, sticky="nsew")
                
    def on_cell_click(self, day, time, room):
        cell = self.scheduler_engine.grid[day].at[time, room]
        if not cell: return
        if messagebox.askyesno("Eliminar", f"¿Borrar clase en {day} {time}:00?"):
            self.scheduler_engine._remove_class(day, time, room, cell, f"{cell['subject']}_{cell['group']}")
            self.render_visual_notebook()

    def export_excel(self):
        if not self.scheduler_engine: return
        fname = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if fname:
            ok, msg = self.scheduler_engine.export_excel(fname)
            messagebox.showinfo("Exportar", msg)