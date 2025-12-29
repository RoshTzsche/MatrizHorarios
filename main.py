import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import random
import copy

# ==========================================
# 1. EL MOTOR MATEMÁTICO (BACKEND)
# ==========================================
class AutoScheduler:
    def __init__(self, time_slots, rooms):
        self.time_slots = time_slots
        self.rooms = rooms
        
        # Grid: Filas=Tiempos, Columnas=Salones
        self.grid = pd.DataFrame(index=time_slots, columns=rooms)
        self.grid[:] = None 
        
        # Restricciones rápidas (Sets)
        self.teacher_busy = {t: set() for t in []} 
        self.group_busy = {g: set() for g in []}   

    def _is_safe(self, time, room, teacher, group):
        # 1. Celda vacía
        if self.grid.at[time, room] is not None: return False
        # 2. Maestro libre
        if time in self.teacher_busy.get(teacher, set()): return False
        # 3. Grupo libre
        if time in self.group_busy.get(group, set()): return False
        return True

    def _place_class(self, time, room, class_obj):
        teacher = class_obj['teacher']
        group = class_obj['group']
        self.grid.at[time, room] = class_obj
        
        if teacher not in self.teacher_busy: self.teacher_busy[teacher] = set()
        if group not in self.group_busy: self.group_busy[group] = set()
        
        self.teacher_busy[teacher].add(time)
        self.group_busy[group].add(time)

    def _remove_class(self, time, room, class_obj):
        teacher = class_obj['teacher']
        group = class_obj['group']
        self.grid.at[time, room] = None
        self.teacher_busy[teacher].remove(time)
        self.group_busy[group].remove(time)

    def solve_backtracking(self, classes_to_schedule):
        if not classes_to_schedule:
            return True

        # Heurística: Tomar el primero (ya vienen ordenados por dificultad)
        current_class = classes_to_schedule[0]
        remaining_classes = classes_to_schedule[1:]

        # Randomizar salones para evitar saturar siempre el primero
        shuffled_rooms = self.rooms.copy()
        random.shuffle(shuffled_rooms)

        for time in self.time_slots:
            for room in shuffled_rooms:
                if self._is_safe(time, room, current_class['teacher'], current_class['group']):
                    self._place_class(time, room, current_class)
                    
                    if self.solve_backtracking(remaining_classes):
                        return True 

                    self._remove_class(time, room, current_class)
        return False

    def generate_schedule(self, class_requirements):
        # 1. Contar frecuencias para Heurística MRV
        prof_counts = {}
        for c in class_requirements:
            prof_counts[c['teacher']] = prof_counts.get(c['teacher'], 0) + 1
            
        # 2. Ordenar: Profesores con más carga primero
        sorted_classes = sorted(
            class_requirements, 
            key=lambda x: prof_counts.get(x['teacher'], 0), 
            reverse=True
        )

        return self.solve_backtracking(sorted_classes)

    def export_excel(self, filename="horario_generado.xlsx"):
        def formatter(x):
            if x is None: return ""
            return f"{x['subject']}\n({x['teacher']} - {x['group']})"
        
        try:
            output = self.grid.applymap(formatter) # Usa .map() si tienes pandas muy reciente
            output.to_excel(filename)
            return True, f"Guardado en {filename}"
        except Exception as e:
            return False, str(e)
        

# ==========================================
# 2. LA INTERFAZ GRÁFICA (FRONTEND)
# ==========================================

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Crear un Canvas y los Scrollbars
        self.canvas = tk.Canvas(self)
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        
        # Frame interno donde pondremos los botones
        self.scrollable_content = ttk.Frame(self.canvas)

        # Configurar el Canvas
        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # Layout (Grid)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        # Configurar pesos para que se expanda
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

class SchoolSchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Horarios (Python + Fedora)")
        self.root.geometry("900x700")

        self.data = {
            "Horarios": [], "Salones": [], "Maestros": [], "Grupos": [], "Materias": []
        }
        self.requirements = [] # Lista cruda de la UI (con 'sessions')

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        for var_name in ["Horarios", "Salones", "Maestros", "Grupos", "Materias"]:
            self.create_crud_tab(var_name)
        
        self.scheduler_engine = None
        self.create_requirements_tab()
        self.create_run_tab()
        self.create_visual_tab()

    def create_visual_tab(self):
        self.visual_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.visual_frame, text="👁️ Horario Interactivo")
        
        # Contenedor principal
        lbl = ttk.Label(self.visual_frame, text="Vista Interactiva (Click para editar)", font=('Arial', 10, 'bold'))
        lbl.pack(pady=5)
        
        # Usamos nuestra clase Scrollable
        self.grid_container = ScrollableFrame(self.visual_frame)
        self.grid_container.pack(expand=True, fill='both', padx=5, pady=5)
        
    def create_crud_tab(self, category):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=category)
        
        lbl = ttk.Label(frame, text=f"Catálogo de {category}", font=('Arial', 11, 'bold'))
        lbl.pack(pady=10)

        input_frame = ttk.Frame(frame)
        input_frame.pack(fill='x', padx=20)
        
        entry = ttk.Entry(input_frame)
        entry.pack(side='left', expand=True, fill='x', padx=(0, 5))
        
        listbox = tk.Listbox(frame, height=10)
        listbox.pack(expand=True, fill='both', padx=20, pady=5)

        def add_item():
            val = entry.get().strip()
            if val and val not in self.data[category]:
                self.data[category].append(val)
                listbox.insert(tk.END, val)
                entry.delete(0, tk.END)

        def del_item():
            sel = listbox.curselection()
            if sel:
                val = listbox.get(sel[0])
                self.data[category].remove(val)
                listbox.delete(sel[0])

        btn_add = ttk.Button(input_frame, text="Agregar", command=add_item)
        btn_add.pack(side='right')
        
        ttk.Button(frame, text="Eliminar", command=del_item).pack(pady=5)
        entry.bind('<Return>', lambda e: add_item())

    def create_requirements_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📝 Clases")
        
        # Contenedor superior para controles
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill='x', padx=10, pady=10)

        self.cb_vars = {k: tk.StringVar() for k in ["Maestros", "Materias", "Grupos"]}
        self.combos = {}

        # Crear Comboboxes
        for i, k in enumerate(["Materias", "Maestros", "Grupos"]):
            lbl = ttk.Label(top_frame, text=k)
            lbl.grid(row=0, column=i, padx=5, sticky='w')
            cb = ttk.Combobox(top_frame, textvariable=self.cb_vars[k], state="readonly")
            cb.grid(row=1, column=i, padx=5)
            self.combos[k] = cb

        # Spinbox sesiones
        ttk.Label(top_frame, text="Sesiones").grid(row=0, column=3, padx=5, sticky='w')
        spin = ttk.Spinbox(top_frame, from_=1, to=10, width=5)
        spin.set(1)
        spin.grid(row=1, column=3, padx=5)

        # Treeview
        columns = ("Materia", "Maestro", "Grupo", "Sesiones")
        tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col in columns: 
            tree.heading(col, text=col)
            tree.column(col, width=120)
        tree.pack(expand=True, fill='both', padx=10, pady=5)

        def refresh():
            for k, cb in self.combos.items(): cb['values'] = self.data[k]
        
        # Botón Refresh manual (aunque el evento Visibility lo maneja)
        ttk.Button(top_frame, text="Actualizar Listas", command=refresh).grid(row=1, column=4, padx=10)

        def add_req():
            vals = {k: self.cb_vars[k].get() for k in self.cb_vars}
            n = spin.get()
            if all(vals.values()):
                # Guardamos en requirements
                req_entry = {'subject': vals['Materias'], 'teacher': vals['Maestros'], 
                             'group': vals['Grupos'], 'sessions': int(n)}
                self.requirements.append(req_entry)
                tree.insert("", tk.END, values=(vals['Materias'], vals['Maestros'], vals['Grupos'], n))
        
        ttk.Button(top_frame, text="Agregar Clase", command=add_req).grid(row=2, column=0, columnspan=5, pady=10, sticky='ew')
        frame.bind('<Visibility>', lambda e: refresh())

    def create_run_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🚀 Generar")
        
        info_lbl = ttk.Label(frame, text="Presiona para calcular el horario óptimo", font=('Arial', 14))
        info_lbl.pack(pady=40)

        btn = ttk.Button(frame, text="GENERAR HORARIO Y EXPORTAR EXCEL", command=self.run_generation)
        btn.pack(ipadx=20, ipady=10)
    
    def render_grid(self):
        # Limpiar lo anterior
        for widget in self.grid_container.scrollable_content.winfo_children():
            widget.destroy()

        if not self.scheduler_engine:
            return

        grid_df = self.scheduler_engine.grid
        tiempos = list(grid_df.index)
        salones = list(grid_df.columns)

        # 1. CABECERAS (Salones)
        # Dejamos la esquina (0,0) vacía
        for j, salon in enumerate(salones):
            lbl = tk.Label(self.grid_container.scrollable_content, text=salon, 
                           font=('Arial', 9, 'bold'), bg="#ddd", relief="raised", width=15)
            lbl.grid(row=0, column=j+1, sticky="ew", padx=1, pady=1)

        # 2. FILAS (Horarios + Celdas)
        for i, tiempo in enumerate(tiempos):
            # Header de Fila (Tiempo)
            lbl_time = tk.Label(self.grid_container.scrollable_content, text=tiempo, 
                                font=('Arial', 9, 'bold'), bg="#ddd", relief="raised", width=15)
            lbl_time.grid(row=i+1, column=0, sticky="ns", padx=1, pady=1)

            # Celdas de Datos
            for j, salon in enumerate(salones):
                data = grid_df.at[tiempo, salon]
                
                # Determinamos color y texto
                if data:
                    bg_color = "#c3e6cb" # Verde claro (Ocupado)
                    text_val = f"{data['subject']}\n{data['teacher']}"
                else:
                    bg_color = "#ffffff" # Blanco (Libre)
                    text_val = "---"

                # Botón interactivo
                # IMPORTANTE: Usamos default args (t=tiempo, s=salon) para capturar el valor en el loop
                btn = tk.Button(self.grid_container.scrollable_content, text=text_val, bg=bg_color,
                                font=('Arial', 8), width=15, height=3,
                                command=lambda t=tiempo, s=salon: self.on_cell_click(t, s))
                btn.grid(row=i+1, column=j+1, sticky="nsew", padx=1, pady=1)
    # ==========================================
    # 3. FUSIÓN: LÓGICA DE EJECUCIÓN
    # ==========================================
    def run_generation(self):
        # A. Validaciones
        if not self.data['Horarios'] or not self.data['Salones']:
            messagebox.showerror("Error", "Debes definir al menos 1 Horario y 1 Salón.")
            return
        if not self.requirements:
            messagebox.showerror("Error", "No has definido ninguna clase.")
            return
# Instanciar Motor
        # GUARDAMOS en self.scheduler_engine para poder acceder desde la UI visual
        self.scheduler_engine = AutoScheduler(self.data['Horarios'], self.data['Salones'])
        # C. APLANAR REQUERIMIENTOS (Matemática: Multiplicación de Entidades)
        # La UI tiene: 1 registro de "Mate, 3 sesiones".
        # El Solver necesita: 3 registros de "Mate".
        flat_requirements = []
        
        print(f"Procesando {len(self.requirements)} grupos de requerimientos...")
        
        for req in self.requirements:
            count = req['sessions']
            # Creamos N copias individuales para que el solver las coloque en N huecos
            for _ in range(count):
                flat_requirements.append({
                    'teacher': req['teacher'],
                    'subject': req['subject'],
                    'group': req['group']
                    # Nota: No pasamos 'sessions' al solver, ya no es necesario
                })

        print(f"Total de bloques a agendar: {len(flat_requirements)}")

        # D. Ejecutar Algoritmo (Backtracking)
        success = self.scheduler_engine.generate_schedule(flat_requirements)

        if success:
            messagebox.showinfo("¡Éxito!", "Horario generado. Cambiando a vista interactiva...")
            
            # RENDERIZAR LA VISTA VISUAL
            self.render_grid()
            
            # CAMBIAR AUTOMATICAMENTE A LA PESTAÑA VISUAL
            # (El índice depende de cuántas tabs tengas, usualmente es la última)
            idx = self.notebook.index(self.visual_frame)
            self.notebook.select(idx)
        else:
            messagebox.showwarning("Fallo", "No se encontró solución factible.")
            
    def on_cell_click(self, time, room):
        data = self.scheduler_engine.grid.at[time, room]
        
        # Crear ventana popup
        popup = tk.Toplevel(self.root)
        popup.title(f"{time} - {room}")
        popup.geometry("300x250")
        
        ttk.Label(popup, text=f"Detalles del Bloque", font=('Arial', 12, 'bold')).pack(pady=10)
        
        info_frame = ttk.Frame(popup)
        info_frame.pack(pady=5, padx=10, fill='x')

        if data:
            # Si hay clase, mostrar info
            ttk.Label(info_frame, text=f"Materia: {data['subject']}").pack(anchor='w')
            ttk.Label(info_frame, text=f"Maestro: {data['teacher']}").pack(anchor='w')
            ttk.Label(info_frame, text=f"Grupo: {data['group']}").pack(anchor='w')
            
            # Botón de acción: Borrar (Liberar espacio)
            def delete_class():
                # Llamamos al método interno del engine para limpiar índices
                self.scheduler_engine._remove_class(time, room, data)
                popup.destroy()
                self.render_grid() # Re-renderizar para ver el cambio
                
            ttk.Button(popup, text="🗑️ Eliminar Clase", command=delete_class).pack(pady=20, fill='x')
            
        else:
            # Si está vacío
            ttk.Label(info_frame, text="Espacio Disponible", foreground="green").pack()
            ttk.Label(info_frame, text="Puedes agregar una clase manualmente aquí (pendiente)").pack(pady=5)
            
        ttk.Button(popup, text="Cerrar", command=popup.destroy).pack(side='bottom', pady=10)
if __name__ == "__main__":
    root = tk.Tk()
    # Estilo para Linux/Fedora (clam suele verse bien integrado)
    style = ttk.Style()
    style.theme_use('clam')
    
    app = SchoolSchedulerApp(root)
    root.mainloop()