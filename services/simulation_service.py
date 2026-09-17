# Simulation & Educational Cases Engine
import sqlite3
import json
from datetime import datetime
from models import get_db_connection
from services.audit_service import AuditService

class SimulationService:
    @staticmethod
    def get_simulations(activo_only=True, db_path=None):
        conn = get_db_connection(db_path)
        try:
            query = """
                SELECT s.*, u.nombre_completo as docente_nombre, c.nombre as curso_nombre,
                       (SELECT COUNT(*) FROM casos_simulacion WHERE simulacion_id = s.id) as total_casos
                FROM simulaciones s
                LEFT JOIN usuarios u ON s.docente_id = u.id
                LEFT JOIN cursos c ON s.curso_id = c.id
            """
            if activo_only:
                query += " WHERE s.activo = 1"
            query += " ORDER BY s.nivel ASC, s.id ASC"
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_simulation_by_id(simulacion_id, db_path=None):
        conn = get_db_connection(db_path)
        try:
            sim = conn.execute("SELECT * FROM simulaciones WHERE id = ?", (simulacion_id,)).fetchone()
            if not sim:
                return None
            s_dict = dict(sim)
            casos = conn.execute("""
                SELECT * FROM casos_simulacion
                WHERE simulacion_id = ?
                ORDER BY orden ASC
            """, (simulacion_id,)).fetchall()
            
            casos_list = []
            for c in casos:
                c_dict = dict(c)
                try:
                    c_dict["datos_transaccion"] = json.loads(c["datos_transaccion_json"])
                except:
                    c_dict["datos_transaccion"] = {}
                try:
                    c_dict["pistas"] = json.loads(c["pistas_json"])
                except:
                    c_dict["pistas"] = []
                casos_list.append(c_dict)

            s_dict["casos"] = casos_list
            return s_dict
        finally:
            conn.close()

    @staticmethod
    def start_attempt(simulacion_id, estudiante_id, db_path=None):
        conn = get_db_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO intentos_estudiante (simulacion_id, estudiante_id, estado, puntuacion_total)
                VALUES (?, ?, 'EN_PROGRESO', 0.0)
            """, (simulacion_id, estudiante_id))
            intento_id = cursor.lastrowid
            conn.commit()
            return intento_id
        finally:
            conn.close()

    @staticmethod
    def get_student_attempts(estudiante_id=None, db_path=None):
        conn = get_db_connection(db_path)
        try:
            query = """
                SELECT i.*, s.titulo as simulacion_titulo, s.nivel as simulacion_nivel, s.modo_examen,
                       u.nombre_completo as estudiante_nombre
                FROM intentos_estudiante i
                JOIN simulaciones s ON i.simulacion_id = s.id
                JOIN usuarios u ON i.estudiante_id = u.id
            """
            params = []
            if estudiante_id:
                query += " WHERE i.estudiante_id = ?"
                params.append(estudiante_id)
            query += " ORDER BY i.id DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_teacher_analytics(docente_id=None, db_path=None):
        conn = get_db_connection(db_path)
        try:
            total_estudiantes = conn.execute("SELECT COUNT(*) as cnt FROM usuarios WHERE rol_id = 3 AND activo = 1").fetchone()["cnt"]
            total_intentos = conn.execute("SELECT COUNT(*) as cnt FROM intentos_estudiante").fetchone()["cnt"]
            intentos_completados = conn.execute("SELECT COUNT(*) as cnt FROM intentos_estudiante WHERE estado = 'COMPLETADO'").fetchone()["cnt"]
            
            avg_row = conn.execute("SELECT AVG(puntuacion_total) as prom FROM intentos_estudiante WHERE estado = 'COMPLETADO'").fetchone()
            promedio_general = round(float(avg_row["prom"] or 0.0), 2)

            # Performance by level
            niveles_stats = conn.execute("""
                SELECT s.nivel, COUNT(i.id) as total_intentos, AVG(i.puntuacion_total) as promedio_nivel
                FROM intentos_estudiante i
                JOIN simulaciones s ON i.simulacion_id = s.id
                GROUP BY s.nivel
                ORDER BY s.nivel ASC
            """).fetchall()

            # Error details
            errores_detalle = conn.execute("""
                SELECT d.resultado, COUNT(*) as cnt
                FROM detalle_intentos d
                GROUP BY d.resultado
            """).fetchall()

            return {
                "total_estudiantes": total_estudiantes,
                "total_intentos": total_intentos,
                "intentos_completados": intentos_completados,
                "promedio_general": promedio_general,
                "niveles_stats": [dict(r) for r in niveles_stats],
                "errores_distribucion": [dict(r) for r in errores_detalle]
            }
        finally:
            conn.close()
