# Evaluation Engine & Pedagogical Feedback Service
import sqlite3
import json
from models import get_db_contable
from services.audit_service import AuditService

class EvaluationService:
    @staticmethod
    def evaluate_attempt(intento_id, caso_id, user_lines, pistas_usadas=0, tiempo_segundos=0, usuario_id=3, db_path=None):
        """
        Evaluates student submitted journal entry against expected solution.
        user_lines format: [
            {'cuenta_id': 3, 'debe': 92.58, 'haber': 0.0},
            {'cuenta_id': 31, 'debe': 0.0, 'haber': 80.50},
            ...
        ]
        Calculates score from 0 to 100 based on:
        - 40% Correct accounts chosen
        - 30% Correct Debit/Credit positioning
        - 20% Correct numerical amounts
        - 10% Balanced Double-entry
        Deducts 5 points per hint used.
        """
        conn = get_db_contable(db_path)
        try:
            cursor = conn.cursor()
            caso = cursor.execute("SELECT * FROM casos_simulacion WHERE id = ?", (caso_id,)).fetchone()
            if not caso:
                raise ValueError("Caso de simulación no encontrado.")

            try:
                solucion = json.loads(caso["solucion_esperada_json"])
            except:
                solucion = {}

            # Gather expected lines (from single or multiple sub-entries)
            expected_lines = []
            if "asiento" in solucion:
                expected_lines.extend(solucion["asiento"])
            if "asiento_venta" in solucion:
                expected_lines.extend(solucion["asiento_venta"])
            if "asiento_costo" in solucion:
                expected_lines.extend(solucion["asiento_costo"])

            # Map user account IDs to account codes
            cuentas_map = {}
            for r in conn.execute("SELECT id, codigo, nombre, naturaleza FROM cuentas").fetchall():
                cuentas_map[r["id"]] = dict(r)
                cuentas_map[r["codigo"]] = dict(r)

            feedback_messages = []
            score_accounts = 0.0
            score_position = 0.0
            score_amounts = 0.0
            score_balance = 0.0

            # 1. Double entry balance check
            total_u_debe = round(sum(float(l.get("debe", 0.0)) for l in user_lines), 2)
            total_u_haber = round(sum(float(l.get("haber", 0.0)) for l in user_lines), 2)
            diff_balance = abs(total_u_debe - total_u_haber)

            if diff_balance < 0.02 and total_u_debe > 0:
                score_balance = 10.0
                feedback_messages.append("✓ Partida doble cuadrada: Total Debe es igual a Total Haber.")
            else:
                feedback_messages.append(f"✗ Asiento descuadrado: Total Debe (${total_u_debe:,.2f}) != Total Haber (${total_u_haber:,.2f}). Diferencia de ${diff_balance:,.2f}.")

            # 2. Match accounts and amounts
            matched_expected = set()
            total_expected_count = len(expected_lines) if expected_lines else 1

            for u_idx, u_line in enumerate(user_lines):
                c_id = u_line.get("cuenta_id")
                u_cta = cuentas_map.get(c_id)
                if not u_cta:
                    feedback_messages.append(f"✗ Línea {u_idx+1}: Cuenta no válida seleccionada.")
                    continue

                u_code = u_cta["codigo"]
                u_name = u_cta["nombre"]
                u_debe = round(float(u_line.get("debe", 0.0)), 2)
                u_haber = round(float(u_line.get("haber", 0.0)), 2)

                # Find match in expected
                found_match = False
                for e_idx, e_line in enumerate(expected_lines):
                    if e_idx in matched_expected:
                        continue
                    e_code = e_line.get("cuenta")
                    if e_code == u_code:
                        found_match = True
                        matched_expected.add(e_idx)
                        score_accounts += (40.0 / total_expected_count)

                        # Check debit/credit position
                        e_debe = round(float(e_line.get("debe", 0.0)), 2)
                        e_haber = round(float(e_line.get("haber", 0.0)), 2)

                        if (e_debe > 0 and u_debe > 0) or (e_haber > 0 and u_haber > 0):
                            score_position += (30.0 / total_expected_count)
                            # Check amounts
                            if abs(e_debe - u_debe) < 0.02 and abs(e_haber - u_haber) < 0.02:
                                score_amounts += (20.0 / total_expected_count)
                                feedback_messages.append(f"✓ Cuenta '{u_name}' registrada correctamente en {'Debe' if u_debe > 0 else 'Haber'} por ${max(u_debe, u_haber):,.2f}.")
                            else:
                                feedback_messages.append(f"⚠ Cuenta '{u_name}' en posición correcta ({'Debe' if u_debe > 0 else 'Haber'}), pero el importe ${max(u_debe, u_haber):,.2f} no coincide con el valor esperado de ${max(e_debe, e_haber):,.2f}.")
                        else:
                            nat = u_cta.get("naturaleza", "DEUDORA")
                            feedback_messages.append(f"✗ La cuenta '{u_name}' ({nat}) fue seleccionada correctamente, pero su movimiento se registró en {'Haber' if u_haber > 0 else 'Debe'} en lugar de {'Debe' if e_debe > 0 else 'Haber'}.")
                        break

                if not found_match:
                    feedback_messages.append(f"✗ La cuenta '{u_name}' no corresponde al registro contable de esta operación.")

            # Missing accounts
            for e_idx, e_line in enumerate(expected_lines):
                if e_idx not in matched_expected:
                    feedback_messages.append(f"✗ Faltó registrar la cuenta '{e_line.get('nombre')}' ({e_line.get('cuenta')}) por ${max(e_line.get('debe', 0), e_line.get('haber', 0)):,.2f}.")

            # Total score calculation
            raw_score = score_accounts + score_position + score_amounts + score_balance
            hint_penalty = float(pistas_usadas) * 5.0
            final_score = max(0.0, min(100.0, round(raw_score - hint_penalty, 2)))

            if final_score >= 85.0:
                resultado = "CORRECTO"
            elif final_score >= 50.0:
                resultado = "PARCIALMENTE_CORRECTO"
            else:
                resultado = "INCORRECTO"

            feedback_text = "\n".join(feedback_messages)
            if caso["explicacion_pedagogica"]:
                feedback_text += f"\n\nFundamento Teórico:\n{caso['explicacion_pedagogica']}"

            # Save detail attempt
            cursor.execute("""
                INSERT INTO detalle_intentos (
                    intento_id, caso_id, respuestas_json, puntuacion, resultado,
                    pistas_utilizadas, retroalimentacion_especifica, tiempo_segundos
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (intento_id, caso_id, json.dumps(user_lines), final_score, resultado,
                  int(pistas_usadas), feedback_text, int(tiempo_segundos)))

            # Update overall attempt score
            cursor.execute("""
                UPDATE intentos_estudiante
                SET puntuacion_total = (
                    SELECT AVG(puntuacion) FROM detalle_intentos WHERE intento_id = ?
                ), tiempo_segundos = tiempo_segundos + ?, estado = 'COMPLETADO', fecha_fin = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (intento_id, int(tiempo_segundos), intento_id))

            conn.commit()

            AuditService.log(usuario_id, "estudiante", "EVALUAR_CASO", "SIMULACION", caso_id, None, {
                "intento_id": intento_id, "puntuacion": final_score, "resultado": resultado
            }, db_path=db_path)

            return {
                "puntuacion": final_score,
                "resultado": resultado,
                "retroalimentacion": feedback_text,
                "detalles_evaluacion": {
                    "cuentas": round(score_accounts, 2),
                    "posicion": round(score_position, 2),
                    "importes": round(score_amounts, 2),
                    "partida_doble": round(score_balance, 2),
                    "penalizacion_pistas": hint_penalty
                }
            }
        finally:
            conn.close()
