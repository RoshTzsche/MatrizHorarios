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

    def solve_backtracking(self, classes_to_schedule):
        if not classes_to_schedule:
            return True

        current_block = classes_to_schedule[0]
        remaining_blocks = classes_to_schedule[1:]
        
        teacher = current_block['teacher']
        group = current_block['group']
        duration = current_block['duration']
        subj_key = f"{current_block['subject']}_{group}"

        # Heurística: Intentar días no usados primero
        used_days = self.subject_days.get(subj_key, set())
        all_days = self.days.copy()
        random.shuffle(all_days)
        all_days.sort(key=lambda d: 1 if d in used_days else 0)

        shuffled_rooms = self.rooms.copy()
        random.shuffle(shuffled_rooms)

        for day in all_days:
            for time in self.hours:
                # Si dura 2 horas y son las 20:00, no cabe.
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

    def export_excel(self, filename="horario_generado.xlsx"):
        try:
            with pd.ExcelWriter(filename) as writer:
                for day in self.days:
                    df_export = self.grid[day].copy()
                    def formatter(x):
                        if x is None: return ""
                        return f"{x['subject']}\n({x['teacher']})"
                    df_export = df_export.applymap(formatter)
                    df_export.to_excel(writer, sheet_name=day)
            return True, f"Guardado exitosamente en {filename}"
        except Exception as e:
            return False, str(e)