# Period & Simulation Working-Date Service
# Centraliza la "fecha de trabajo" de la simulación y los parámetros del sistema.
# Todas las operaciones contables se registran con la fecha de trabajo (por defecto 2026-04-30),
# lo que permite reproducir un período académico completo (Abril 2026) sin depender del reloj real.
from datetime import date, datetime, timedelta
from models import get_db_contable

DEFAULT_FECHA_TRABAJO = "2026-04-30"
PARAM_FECHA_TRABAJO = "fecha_trabajo"


class PeriodService:
    @staticmethod
    def get_param(clave, default=None, db_path=None):
        conn = get_db_contable(db_path)
        try:
            row = conn.execute("SELECT valor FROM parametros WHERE clave = ?", (clave,)).fetchone()
            return row["valor"] if row else default
        finally:
            conn.close()

    @staticmethod
    def set_param(clave, valor, descripcion=None, db_path=None):
        conn = get_db_contable(db_path)
        try:
            conn.execute("""
                INSERT INTO parametros (clave, valor, descripcion) VALUES (?, ?, ?)
                ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor,
                    descripcion = COALESCE(excluded.descripcion, parametros.descripcion)
            """, (clave, str(valor), descripcion))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def get_parameters(db_path=None):
        conn = get_db_contable(db_path)
        try:
            rows = conn.execute("SELECT clave, valor, descripcion FROM parametros ORDER BY clave ASC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_fecha_trabajo(db_path=None):
        """Fecha (ISO) con la que se registran las operaciones de la simulación."""
        valor = PeriodService.get_param(PARAM_FECHA_TRABAJO, None, db_path=db_path)
        if valor:
            return valor
        return DEFAULT_FECHA_TRABAJO

    @staticmethod
    def set_fecha_trabajo(fecha, db_path=None):
        """Cambia la fecha de trabajo validando que esté dentro del período abierto."""
        valido, msg = PeriodService.is_fecha_valida(fecha, db_path=db_path)
        if not valido:
            raise ValueError(msg)
        PeriodService.set_param(
            PARAM_FECHA_TRABAJO, fecha,
            "Fecha de trabajo de la simulacion: fecha con la que se registran las nuevas operaciones.",
            db_path=db_path
        )
        return True

    @staticmethod
    def is_fecha_valida(fecha, db_path=None):
        """Valida formato ISO y pertenencia al período contable ABIERTO."""
        if not fecha:
            return False, "La fecha es obligatoria."
        try:
            fecha_dt = datetime.strptime(str(fecha), "%Y-%m-%d").date()
        except ValueError:
            return False, f"Fecha invalida '{fecha}'. Se espera el formato AAAA-MM-DD."
        per = PeriodService.get_active_period(db_path=db_path)
        if per:
            if str(per["estado"]) == "CERRADO":
                return False, "El periodo contable esta CERRADO: no se pueden registrar nuevas operaciones."
            if not (per["fecha_inicio"] <= fecha_dt.isoformat() <= per["fecha_fin"]):
                return False, (f"La fecha {fecha_dt.isoformat()} esta fuera del periodo abierto "
                               f"'{per['nombre']}' ({per['fecha_inicio']} a {per['fecha_fin']}).")
        return True, "Fecha valida dentro del periodo abierto."

    @staticmethod
    def get_active_period(db_path=None):
        conn = get_db_contable(db_path)
        try:
            row = conn.execute("""
                SELECT * FROM periodos WHERE estado = 'ABIERTO'
                ORDER BY fecha_inicio DESC LIMIT 1
            """).fetchone()
            if row:
                return dict(row)
            row = conn.execute("SELECT * FROM periodos ORDER BY fecha_inicio DESC LIMIT 1").fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_periods(db_path=None):
        conn = get_db_contable(db_path)
        try:
            rows = conn.execute("SELECT * FROM periodos ORDER BY fecha_inicio DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def next_fecha(dias=1, db_path=None):
        base = datetime.strptime(PeriodService.get_fecha_trabajo(db_path=db_path), "%Y-%m-%d").date()
        return (base + timedelta(days=dias)).isoformat()
