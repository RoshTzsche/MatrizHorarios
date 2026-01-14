import pandas as pd
import random
import copy

class AutoScheduler:
    def __init__(self, rooms):
        self.rooms = rooms
        self.days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
        self.hours = list(range(7, 21)) # 7 a 20
        
        # Grid 3D: { Día: DataFrame(Filas=Horas, Cols=Salones) }
        self.grid = {}
        for d in self.days:
            self.grid[d] = pd.DataFrame(index=self.hours, columns=rooms)
            self.grid[d][:] = None 
        
        # Estructuras de control para búsqueda rápida
        self.teacher_busy = set()
        self.group_busy = set()
        self.subject_days = {}

    def _is_safe(self, day, time, room, teacher, group, duration, subject_key):
        # 1. Validar límites de horario
        if time + duration - 1 > 20: 
            return False
            
        # 2. Verificar colisiones en todos los bloques de tiempo
        for t_offset in range(duration):
            curr_time = time + t_offset
            
            # A. Celda ocupada
            if self.grid[day].at[curr_time, room] is not None:
                return False
            
            # B. Maestro ocupado
            if (day, curr_time, teacher) in self.teacher_busy:
                return False
                
            # C. Grupo ocupado
            if (day, curr_time, group) in self.group_busy:
                return False
        return True

    def _place_class(self, day, time, room, class_obj, subject_key):
        teacher = class_obj['teacher']
        group = class_obj['group']
        duration = class_obj['duration']
        
        for t_offset in range(duration):
            curr_time = time + t_offset
            self.grid[day].at[curr_time, room] = class_obj
            self.teacher_busy.add((day, curr_time, teacher))
            self.group_busy.add((day, curr_time, group))
            
        if subject_key not in self.subject_days: self.subject_days[subject_key] = set()
        self.subject_days[subject_key].add(day)

    def _remove_class(self, day, time, room, class_obj, subject_key):
        teacher = class_obj['teacher']
        group = class_obj['group']
        duration = class_obj['duration']
        
        for t_offset in range(duration):
            curr_time = time + t_offset
            self.grid[day].at[curr_time, room] = None
            self.teacher_busy.remove((day, curr_time, teacher))
            self.group_busy.remove((day, curr_time, group))
            
        if subject_key in self.subject_days:
            if day in self.subject_days[subject_key]:
                self.subject_days[subject_key].remove(day)

    # En scheduler.py -> AutoScheduler

    def solve_backtracking(self, classes_to_schedule):
        if not classes_to_schedule:
            return True

        current_block = classes_to_schedule[0]
        remaining_blocks = classes_to_schedule[1:]
        
        teacher = current_block['teacher']
        group = current_block['group']
        duration = current_block['duration']
        subj_key = f"{current_block['subject']}_{group}"
        
        # [NEW] Leemos la regla de sábado (default "Puede" por seguridad)
        sat_rule = current_block.get('saturday_rule', 'Puede')

        # Heurística: Intentar días no usados primero
        used_days = self.subject_days.get(subj_key, set())
        
        # [LOGIC CHANGE] Filtrado de días según la regla
        candidate_days = []
        
        if sat_rule == "No":
            # Excluimos Sábado
            candidate_days = [d for d in self.days if d != "Sábado"]
        elif sat_rule == "Sí o sí":
            # SOLO Sábado
            candidate_days = ["Sábado"]
        else:
            # Todos los días ("Puede")
            candidate_days = self.days.copy()

        # Mezclamos y ordenamos según uso previo (heurística estándar)
        random.shuffle(candidate_days)
        candidate_days.sort(key=lambda d: 1 if d in used_days else 0)

        shuffled_rooms = self.rooms.copy()
        random.shuffle(shuffled_rooms)

        for day in candidate_days:
            for time in self.hours:
                if duration == 2 and time == 20: continue 

                for room in shuffled_rooms:
                    if self._is_safe(day, time, room, teacher, group, duration, subj_key):
                        self._place_class(day, time, room, current_block, subj_key)
                        
                        if self.solve_backtracking(remaining_blocks):
                            return True

                        self._remove_class(day, time, room, current_block, subj_key)
        
        return False

    def generate_schedule(self, flat_requirements):
        # Limpiar estados
        self.teacher_busy.clear()
        self.group_busy.clear()
        self.subject_days.clear()
        for d in self.days:
            self.grid[d][:] = None

        # Ordenar por dificultad
        prof_counts = {}
        for c in flat_requirements:
            prof_counts[c['teacher']] = prof_counts.get(c['teacher'], 0) + c['duration']
            
        sorted_classes = sorted(
            flat_requirements, 
            key=lambda x: (prof_counts.get(x['teacher'], 0), x['duration']), 
            reverse=True
        )

        return self.solve_backtracking(sorted_classes)

    # En scheduler.py -> AutoScheduler

    def get_conflict_details(self, day, time, teacher, group):
        """Devuelve qué clase está estorbando en ese slot (si existe)."""
        # 1. Revisar si hay choque de maestro
        if (day, time, teacher) in self.teacher_busy:
            # Buscar manualmente en la grilla dónde está ese maestro
            # (Esto es ineficiente en O(N), pero aceptable para una interacción humana)
            for r in self.rooms:
                cell = self.grid[day].at[time, r]
                if cell and cell['teacher'] == teacher:
                    return "Maestro", cell, r
        
        # 2. Revisar si hay choque de grupo
        if (day, time, group) in self.group_busy:
            for r in self.rooms:
                cell = self.grid[day].at[time, r]
                if cell and cell['group'] == group:
                    return "Grupo", cell, r
                    
        return None, None, None

    def suggest_alternatives(self, duration, teacher, group, subject_key):
        """Busca todos los slots vacíos donde esta configuración cabe perfectamente."""
        alternatives = []
        
        # Para sugerir, ignoramos temporalmente las restricciones de la clase ACTUAL
        # (Asumimos que la estamos moviendo, así que su lugar actual no cuenta como ocupado)
        # Nota: Esto es una simplificación. Lo ideal es quitarla, buscar y volver a ponerla si falla.
        # Por seguridad, buscamos espacios que sean válidos ADEMÁS del actual.
        
        for d in self.days:
            for h in self.hours:
                # Filtrar horarios imposibles por duración
                if h + duration - 1 > 20: continue
                
                # Revisar cada salón
                for r in self.rooms:
                    # Usamos _is_safe. OJO: Si el maestro ya tiene clase en este slot (y no es esta misma),
                    # dará False, lo cual es correcto (no es una alternativa válida inmediata).
                    if self._is_safe(d, h, r, teacher, group, duration, "probe"):
                        alternatives.append(f"{d} {h}:00 - {r}")
        
        return alternatives
    def export_excel(self):
        if not self.scheduler_engine:
            messagebox.showwarning("Atención", "Primero debes generar o cargar un horario.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Exportar Horario Maestro"
        )
        if not filename: return

        try:
            # Usamos xlsxwriter como motor para poder dar estilos (colores)
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                workbook = writer.book
                
                # --- ESTILOS BASE ---
                fmt_header = workbook.add_format({
                    'bold': True, 'align': 'center', 'valign': 'vcenter',
                    'bg_color': '#2c3e50', 'font_color': 'white', 'border': 1
                })
                fmt_index = workbook.add_format({
                    'bold': True, 'align': 'center', 'valign': 'vcenter',
                    'bg_color': '#ecf0f1', 'border': 1
                })
                
                # Cache de formatos de materias para no recrearlos mil veces
                # Clave: HexColor -> Valor: Objeto Formato XlsxWriter
                color_formats = {}

                def get_color_format(hex_color):
                    if hex_color not in color_formats:
                        # Calcular color de texto (blanco o negro) basado en fondo
                        fg_color = self._get_contrast_text_color(hex_color)
                        color_formats[hex_color] = workbook.add_format({
                            'bg_color': hex_color,
                            'font_color': fg_color,
                            'text_wrap': True,
                            'valign': 'vcenter',
                            'align': 'center',
                            'border': 1,
                            'font_size': 9
                        })
                    return color_formats[hex_color]

                days = self.scheduler_engine.days
                hours = self.scheduler_engine.hours

                # ==========================================
                # 1. VISTA POR SALÓN (PRIORIDAD)
                # ==========================================
                for room in self.data['Salones']:
                    # Crear matriz para este salón: Index=Horas, Cols=Días
                    df_room = pd.DataFrame(index=hours, columns=days)
                    
                    # Matriz paralela para guardar los colores (metadata)
                    meta_colors = pd.DataFrame(index=hours, columns=days)

                    for d in days:
                        for h in hours:
                            cell = self.scheduler_engine.grid[d].at[h, room]
                            if cell:
                                # Texto detallado en la celda
                                text = f"{cell['subject']}\n({cell['group']})\n{cell['teacher']}"
                                df_room.at[h, d] = text
                                
                                # Guardar el color correspondiente a la materia
                                meta_colors.at[h, d] = self.subject_colors.get(cell['subject'], '#ffffff')
                            else:
                                df_room.at[h, d] = "" # Celda vacía

                    # Escribir a Excel (Hoja con nombre del salón)
                    sheet_name = f"Salón {room}"[:31] # Excel limita nombres a 31 chars
                    df_room.to_excel(writer, sheet_name=sheet_name)
                    
                    worksheet = writer.sheets[sheet_name]
                    
                    # --- APLICAR FORMATO VISUAL ---
                    # Ajustar ancho de columnas
                    worksheet.set_column(0, 0, 10, fmt_index) # Columna de horas
                    worksheet.set_column(1, len(days), 25)    # Columnas de días
                    
                    # Pintar celdas
                    for row_idx, h in enumerate(hours):
                        for col_idx, d in enumerate(days):
                            color = meta_colors.at[h, d]
                            val = df_room.at[h, d]
                            
                            if val: # Si hay clase
                                fmt = get_color_format(color)
                                # row_idx + 1 porque la fila 0 es el encabezado
                                # col_idx + 1 porque la col 0 es el index (Horas)
                                worksheet.write(row_idx + 1, col_idx + 1, val, fmt)
                            else:
                                # Celda vacía con borde simple
                                worksheet.write(row_idx + 1, col_idx + 1, "", workbook.add_format({'border': 1}))

                # ==========================================
                # 2. VISTA GENERAL (POR DÍA)
                # ==========================================
                for day in days:
                    df_orig = self.scheduler_engine.grid[day]
                    # Crear versión de texto plano para Excel
                    df_display = pd.DataFrame(index=df_orig.index, columns=df_orig.columns)
                    
                    sheet_name = f"General - {day}"
                    
                    worksheet = workbook.add_worksheet(sheet_name)
                    writer.sheets[sheet_name] = worksheet
                    
                    # Escribir encabezados manualmente para control total
                    worksheet.write(0, 0, "Hora", fmt_header)
                    for c_idx, col_name in enumerate(df_orig.columns):
                        worksheet.write(0, c_idx + 1, col_name, fmt_header)
                        
                    worksheet.set_column(0, 0, 8, fmt_index)
                    worksheet.set_column(1, len(df_orig.columns), 20)

                    for r_idx, h in enumerate(df_orig.index):
                        # Escribir hora
                        worksheet.write(r_idx + 1, 0, f"{h}:00", fmt_index)
                        
                        for c_idx, room in enumerate(df_orig.columns):
                            cell = df_orig.at[h, room]
                            if cell:
                                text = f"{cell['subject']}\n{cell['group']}\n{cell['teacher']}"
                                color = self.subject_colors.get(cell['subject'], '#ffffff')
                                fmt = get_color_format(color)
                                worksheet.write(r_idx + 1, c_idx + 1, text, fmt)
                            else:
                                worksheet.write(r_idx + 1, c_idx + 1, "", workbook.add_format({'border': 1}))

            messagebox.showinfo("Exportación Exitosa", f"Archivo generado:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo guardar el archivo.\nDetalle: {str(e)}")
            print(e)
