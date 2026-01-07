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
    def create_visual_tab(self):
        self.visual_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.visual_frame, text="👁️ Horario Interactivo")
        tool = ttk.Frame(self.visual_frame)
        tool.pack(fill='x', padx=5, pady=5)
        ttk.Button(tool, text="Exportar Excel", command=self.export_excel).pack(side='right')
        self.days_notebook = ttk.Notebook(self.visual_frame)
        self.days_notebook.pack(expand=True, fill='both', padx=5, pady=5)

    def render_visual_notebook(self):
        for tab in self.days_notebook.tabs(): self.days_notebook.forget(tab)
        if not self.scheduler_engine: return

        for day in self.scheduler_engine.days:
            f_day = ttk.Frame(self.days_notebook)
            self.days_notebook.add(f_day, text=day)
            
            canvas = tk.Canvas(f_day)
            scroll_v = ttk.Scrollbar(f_day, orient="vertical", command=canvas.yview)
            scroll_h = ttk.Scrollbar(f_day, orient="horizontal", command=canvas.xview)
            content = ttk.Frame(canvas)
            content.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
            canvas.create_window((0,0), window=content, anchor="nw")
            canvas.configure(yscrollcommand=scroll_v.set, xscrollcommand=scroll_h.set)
            
            canvas.grid(row=0, column=0, sticky="nsew")
            scroll_v.grid(row=0, column=1, sticky="ns")
            scroll_h.grid(row=1, column=0, sticky="ew")
            f_day.grid_rowconfigure(0, weight=1); f_day.grid_columnconfigure(0, weight=1)

            self.render_day_grid(content, day)

    def render_day_grid(self, parent, day):
        df = self.scheduler_engine.grid[day]
        hours = list(df.index); rooms = list(df.columns)
        for j, r in enumerate(rooms):
            tk.Label(parent, text=r, font=('Arial', 9, 'bold'), bg="#ddd", width=15).grid(row=0, column=j+1, padx=1, pady=1)
        for i, h in enumerate(hours):
            tk.Label(parent, text=f"{h}:00", font=('Arial', 8, 'bold'), bg="#eee", width=10).grid(row=i+1, column=0, padx=1, pady=1)
            for j, r in enumerate(rooms):
                cell = df.at[h, r]
                bg = "#c3e6cb" if cell else "white"
                txt = f"{cell['subject']}\n{cell['group']}" if cell else "---"
                btn = tk.Button(parent, text=txt, bg=bg, font=('Arial', 8), height=3, width=15, relief="flat",
                                command=lambda d=day, t=h, rm=r: self.on_cell_click(d, t, rm))
                btn.grid(row=i+1, column=j+1, padx=1, pady=1, sticky="nsew")

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