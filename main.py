import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import random
import copy
import os

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
        if self.grid.at[time, room] is not None: return False
        if time in self.teacher_busy.get(teacher, set()): return False
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

        current_class = classes_to_schedule[0]
        remaining_classes = classes_to_schedule[1:]

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
        prof_counts = {}
        for c in class_requirements:
            prof_counts[c['teacher']] = prof_counts.get(c['teacher'], 0) + 1
            
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
            output = self.grid.applymap(formatter) 
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
        self.canvas = tk.Canvas(self)
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.scrollable_content = ttk.Frame(self.canvas)

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

class SchoolSchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Horarios (Python + Fedora)")
        self.root.geometry("1000x800")

        self.data = {
            "Horarios": [], "Salones": [], "Maestros": [], "Grupos": [], "Materias": []
        }
        self.requirements = [] 
        self.listboxes = {} # Referencias para actualizar UIs automáticamente

        # --- MENU SUPERIOR ---
        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="📥 Importar Catálogos (Excel)", command=self.import_catalogs)
        file_menu.add_command(label="❓ Ver Formato Esperado", command=self.show_format_help)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        root.config(menu=menubar)

        # Configuración del Notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        for var_name in ["Horarios", "Salones", "Maestros", "Grupos", "Materias"]:
            self.create_crud_tab(var_name)
        
        self.scheduler_engine = None
        self.create_requirements_tab()
        self.create_run_tab()
        self.create_visual_tab()

    # --- LOGICA DE IMPORTACIÓN ---
    def show_format_help(self):
        msg = (
            "Para importar datos masivamente, el archivo Excel debe tener:\n\n"
            "1. Pestañas (Hojas) llamadas EXACTAMENTE:\n"
            "   'Horarios', 'Salones', 'Maestros', 'Grupos', 'Materias'\n\n"
            "2. En cada hoja, los datos deben estar en la PRIMERA COLUMNA.\n"
            "   (La primera fila se considera encabezado y se ignora).\n\n"
            "Ejemplo: Hoja 'Maestros', Columna A:\n"
            "A1: Nombre (Header)\n"
            "A2: Dr. Strange\n"
            "A3: Tony Stark"
        )
        messagebox.showinfo("Formato de Excel", msg)

    def import_catalogs(self):
        filename = filedialog.askopenfilename(
            title="Seleccionar Excel de Datos",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        )
        if not filename: return

        try:
            # Leer todas las hojas
            xls = pd.read_excel(filename, sheet_name=None)
            
            imported_count = 0
            for category in self.data.keys():
                if category in xls:
                    df = xls[category]
                    if not df.empty:
                        # Asumimos que los datos están en la primera columna
                        # dropna() elimina celdas vacías, unique() evita duplicados
                        nuevos_datos = df.iloc[:, 0].dropna().astype(str).unique().tolist()
                        
                        # Agregar sin duplicar con lo existente
                        for item in nuevos_datos:
                            if item not in self.data[category]:
                                self.data[category].append(item)
                                imported_count += 1
            
            self.refresh_crud_views()
            messagebox.showinfo("Importación Exitosa", f"Se han importado/actualizado datos.\nRegistros nuevos: {imported_count}")
            
        except Exception as e:
            messagebox.showerror("Error de Importación", f"No se pudo leer el archivo:\n{str(e)}\n\nRevisa el formato en Archivo -> Ver Formato.")

    def refresh_crud_views(self):
        """Actualiza todas las Listboxes con los datos actuales en self.data"""
        for cat, listbox in self.listboxes.items():
            listbox.delete(0, tk.END)
            for item in self.data[cat]:
                listbox.insert(tk.END, item)
        
        # También actualizamos los comboboxes de la pestaña Clases si existen
        if hasattr(self, 'combos'):
             for k, cb in self.combos.items(): 
                 cb['values'] = self.data[k]

    # --- PESTAÑAS ---
    def on_tab_change(self, event):
        selected_tab = event.widget.select()
        tab_text = event.widget.tab(selected_tab, "text")
        if "Horario Interactivo" in tab_text:
            self.render_grid()
        elif "Clases" in tab_text:
            # Refrescar comboboxes al entrar a Clases
            if hasattr(self, 'combos'):
                for k, cb in self.combos.items(): 
                    cb['values'] = self.data[k]

    def create_visual_tab(self):
        self.visual_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.visual_frame, text="👁️ Horario Interactivo")
        
        toolbar = ttk.Frame(self.visual_frame, relief="raised", borderwidth=1)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        btn_export = ttk.Button(toolbar, text="💾 Exportar a Excel", command=self.action_export_excel)
        btn_export.pack(side='right', padx=5, pady=5)
        
        btn_refresh = ttk.Button(toolbar, text="🔄 Forzar Actualización", command=self.render_grid)
        btn_refresh.pack(side='left', padx=5, pady=5)
        
        lbl_info = ttk.Label(toolbar, text="Edita el horario y exporta al finalizar", font=('Arial', 9, 'italic'))
        lbl_info.pack(side='left', padx=15)

        self.grid_container = ScrollableFrame(self.visual_frame)
        self.grid_container.pack(expand=True, fill='both', padx=5, pady=5)
        
    def action_export_excel(self):
        if not self.scheduler_engine or self.scheduler_engine.grid.isnull().all().all():
            messagebox.showwarning("Cuidado", "No hay horario generado o la matriz está vacía.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
            title="Guardar Horario"
        )
        if filename:
            success, msg = self.scheduler_engine.export_excel(filename)
            if success:
                messagebox.showinfo("Exportación Exitosa", msg)
            else:
                messagebox.showerror("Error de Exportación", msg)

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
        
        # GUARDAR REFERENCIA PARA IMPORTACIÓN AUTOMÁTICA
        self.listboxes[category] = listbox

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
        
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill='x', padx=10, pady=10)

        self.cb_vars = {k: tk.StringVar() for k in ["Maestros", "Materias", "Grupos"]}
        self.combos = {}

        for i, k in enumerate(["Materias", "Maestros", "Grupos"]):
            lbl = ttk.Label(top_frame, text=k)
            lbl.grid(row=0, column=i, padx=5, sticky='w')
            cb = ttk.Combobox(top_frame, textvariable=self.cb_vars[k], state="readonly")
            cb.grid(row=1, column=i, padx=5)
            self.combos[k] = cb

        ttk.Label(top_frame, text="Sesiones").grid(row=0, column=3, padx=5, sticky='w')
        spin = ttk.Spinbox(top_frame, from_=1, to=10, width=5)
        spin.set(1)
        spin.grid(row=1, column=3, padx=5)

        # Botón Refresh manual
        ttk.Button(top_frame, text="Actualizar Listas", 
                   command=lambda: [cb.config(values=self.data[k]) for k, cb in self.combos.items()]
                   ).grid(row=1, column=4, padx=10)

        # Treeview
        columns = ("Materia", "Maestro", "Grupo", "Sesiones")
        tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col in columns: 
            tree.heading(col, text=col)
            tree.column(col, width=120)
        tree.pack(expand=True, fill='both', padx=10, pady=5)

        # --- BOTONES DE ACCIÓN (AGREGAR / ELIMINAR) ---
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill='x', padx=10, pady=10)

        def add_req():
            vals = {k: self.cb_vars[k].get() for k in self.cb_vars}
            n = spin.get()
            if all(vals.values()):
                req_entry = {'subject': vals['Materias'], 'teacher': vals['Maestros'], 
                             'group': vals['Grupos'], 'sessions': int(n)}
                self.requirements.append(req_entry)
                tree.insert("", tk.END, values=(vals['Materias'], vals['Maestros'], vals['Grupos'], n))

        def del_req():
            selected_item = tree.selection()
            if selected_item:
                # Obtener índice en el treeview
                # Nota: Esto asume que el orden del Treeview es igual al de la lista.
                # Como insertamos al final (tk.END), esto se cumple.
                idx = tree.index(selected_item[0])
                
                # Eliminar de la lista de datos
                del self.requirements[idx]
                
                # Eliminar visualmente
                tree.delete(selected_item[0])
            else:
                messagebox.showinfo("Información", "Selecciona una clase de la lista para eliminarla.")
        
        ttk.Button(action_frame, text="➕ Agregar Clase", command=add_req).pack(side='left', expand=True, fill='x', padx=5)
        ttk.Button(action_frame, text="🗑️ Eliminar Seleccionada", command=del_req).pack(side='right', expand=True, fill='x', padx=5)

    def create_run_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🚀 Generar")
        
        info_lbl = ttk.Label(frame, text="Presiona para calcular el horario óptimo", font=('Arial', 14))
        info_lbl.pack(pady=40)

        btn = ttk.Button(frame, text="EJECUTAR ALGORITMO", command=self.run_generation)
        btn.pack(ipadx=20, ipady=10)
        
        lbl_hint = ttk.Label(frame, text="(Luego ve a la pestaña 'Horario Interactivo' para ver y exportar)", foreground="gray")
        lbl_hint.pack(pady=10)
    
    def render_grid(self):
        for widget in self.grid_container.scrollable_content.winfo_children():
            widget.destroy()

        if not self.scheduler_engine:
            lbl = tk.Label(self.grid_container.scrollable_content, 
                           text="Aún no se ha generado ningún horario.\nVe a la pestaña 'Generar' primero.",
                           font=('Arial', 12), fg='gray')
            lbl.grid(row=0, column=0, padx=20, pady=20)
            return

        grid_df = self.scheduler_engine.grid
        tiempos = list(grid_df.index)
        salones = list(grid_df.columns)

        COLOR_HEADER = "#eee8d5"
        COLOR_BUSY = "#859900" 
        COLOR_FREE = "#fdf6e3" 
        COLOR_TEXT_BUSY = "#ffffff"
        COLOR_TEXT_FREE = "#657b83"

        for j, salon in enumerate(salones):
            lbl = tk.Label(self.grid_container.scrollable_content, text=salon, 
                           font=('Segoe UI', 9, 'bold'), bg=COLOR_HEADER, relief="flat", width=18, pady=5)
            lbl.grid(row=0, column=j+1, sticky="ew", padx=1, pady=1)

        for i, tiempo in enumerate(tiempos):
            lbl_time = tk.Label(self.grid_container.scrollable_content, text=tiempo, 
                                font=('Segoe UI', 9, 'bold'), bg=COLOR_HEADER, relief="flat", width=15)
            lbl_time.grid(row=i+1, column=0, sticky="ns", padx=1, pady=1)

            for j, salon in enumerate(salones):
                data = grid_df.at[tiempo, salon]
                if data:
                    bg_color = COLOR_BUSY
                    fg_color = COLOR_TEXT_BUSY
                    text_val = f"{data['subject']}\n{data['teacher']}\n({data['group']})"
                    cursor = "hand2"
                else:
                    bg_color = COLOR_FREE
                    fg_color = COLOR_TEXT_FREE
                    text_val = "---"
                    cursor = "arrow"

                btn = tk.Button(self.grid_container.scrollable_content, text=text_val, bg=bg_color, fg=fg_color,
                                font=('Segoe UI', 8), width=18, height=4, relief="flat", cursor=cursor,
                                command=lambda t=tiempo, s=salon: self.on_cell_click(t, s))
                btn.grid(row=i+1, column=j+1, sticky="nsew", padx=1, pady=1)

    def run_generation(self):
        if not self.data['Horarios'] or not self.data['Salones']:
            messagebox.showerror("Error", "Debes definir al menos 1 Horario y 1 Salón.")
            return
        if not self.requirements:
            messagebox.showerror("Error", "No has definido ninguna clase.")
            return

        self.scheduler_engine = AutoScheduler(self.data['Horarios'], self.data['Salones'])
        
        flat_requirements = []
        for req in self.requirements:
            count = req['sessions']
            for _ in range(count):
                flat_requirements.append({
                    'teacher': req['teacher'],
                    'subject': req['subject'],
                    'group': req['group']
                })

        success = self.scheduler_engine.generate_schedule(flat_requirements)

        if success:
            messagebox.showinfo("¡Éxito!", "Horario generado. Redirigiendo...")
            self.notebook.select(self.visual_frame) 
        else:
            messagebox.showwarning("Fallo", "No se encontró solución factible con los recursos actuales.")
            
    def on_cell_click(self, time, room):
        data = self.scheduler_engine.grid.at[time, room]
        popup = tk.Toplevel(self.root)
        popup.title(f"Edit: {time} @ {room}")
        popup.geometry("350x250")
        popup.transient(self.root)
        
        ttk.Label(popup, text=f"Bloque: {time}", font=('Arial', 12, 'bold')).pack(pady=5)
        ttk.Label(popup, text=f"Salón: {room}", font=('Arial', 10, 'italic')).pack(pady=2)
        
        info_frame = ttk.Frame(popup, relief="groove", borderwidth=2)
        info_frame.pack(pady=10, padx=20, fill='both', expand=True)

        if data:
            ttk.Label(info_frame, text=f"📚 {data['subject']}", font=('Arial', 11, 'bold')).pack(anchor='w', pady=2)
            ttk.Label(info_frame, text=f"👨‍🏫 {data['teacher']}").pack(anchor='w')
            ttk.Label(info_frame, text=f"👥 {data['group']}").pack(anchor='w')
            
            def delete_class():
                self.scheduler_engine._remove_class(time, room, data)
                popup.destroy()
                self.render_grid() 
                
            btn = ttk.Button(popup, text="🗑️ Eliminar Clase", command=delete_class)
            btn.pack(pady=10, fill='x', padx=20)
        else:
            ttk.Label(info_frame, text="Espacio Libre", foreground="green").pack(pady=20)
            ttk.Label(popup, text="(Edición manual pendiente)", font=("Arial", 8)).pack(pady=5)
            
        ttk.Button(popup, text="Cerrar", command=popup.destroy).pack(side='bottom', pady=5)

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use('clam') 
    except:
        pass
    style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))
    style.configure("TButton", padding=6, relief="flat", background="#ccc")
    
    app = SchoolSchedulerApp(root)
    root.mainloop()