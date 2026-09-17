// Simulation Player, Interactive Case Solving & AI Evaluator Connector
let pistasContador = 0;
let tiempoInicio = Date.now();

function addSimRow() {
  const tableBody = document.getElementById("simLinesBody");
  if (!tableBody) return;

  const selectTemplate = document.getElementById("accountSelectTemplate");
  const optionsHtml = selectTemplate ? selectTemplate.innerHTML : "";

  const row = document.createElement("tr");
  row.className = "sim-row";
  row.innerHTML = `
    <td>
      <select class="form-select form-select-sm sim-cuenta" required>
        <option value="">-- Seleccionar Cuenta --</option>
        ${optionsHtml}
      </select>
    </td>
    <td>
      <input type="number" step="0.01" min="0" class="form-control form-control-sm sim-debe text-end" value="0.00" oninput="calculateSimTotals()">
    </td>
    <td>
      <input type="number" step="0.01" min="0" class="form-control form-control-sm sim-haber text-end" value="0.00" oninput="calculateSimTotals()">
    </td>
    <td class="text-center">
      <button type="button" class="btn btn-outline-danger btn-sm p-1" onclick="this.closest('tr').remove(); calculateSimTotals();"><i class="bi bi-trash"></i></button>
    </td>
  `;
  tableBody.appendChild(row);
  calculateSimTotals();
}

function calculateSimTotals() {
  const debeInputs = document.querySelectorAll(".sim-debe");
  const haberInputs = document.querySelectorAll(".sim-haber");

  let totalDebe = 0;
  let totalHaber = 0;

  debeInputs.forEach((i) => (totalDebe += parseFloat(i.value || 0)));
  haberInputs.forEach((i) => (totalHaber += parseFloat(i.value || 0)));

  totalDebe = Math.round(totalDebe * 100) / 100;
  totalHaber = Math.round(totalHaber * 100) / 100;

  const tdEl = document.getElementById("simTotalDebe");
  const thEl = document.getElementById("simTotalHaber");
  if (tdEl) tdEl.textContent = `$${totalDebe.toFixed(2)}`;
  if (thEl) thEl.textContent = `$${totalHaber.toFixed(2)}`;
}

function requestHint(casoId) {
  pistasContador++;
  fetch("/tutor/preguntar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pregunta: "Quiero una pista para resolver este caso",
      nivel_ayuda: pistasContador === 1 ? "ORIENTACION" : "PISTA",
      context: { caso_id: casoId }
    })
  })
    .then((r) => r.json())
    .then((data) => {
      const hintBox = document.getElementById("hintDisplayBox");
      if (hintBox) {
        hintBox.innerHTML = `
          <div class="alert alert-info d-flex align-items-center mb-3">
            <i class="bi bi-lightbulb-fill text-warning fs-4 me-3"></i>
            <div>
              <strong>Pista #${pistasContador} del Tutor IA:</strong><br>
              ${data.respuesta}
              <div class="small text-muted mt-1">(Penalización: -5 pts por pista en la calificación final)</div>
            </div>
          </div>
        `;
        hintBox.style.display = "block";
      }
    });
}

function submitSimulationCase(intentoId, casoId) {
  const rows = document.querySelectorAll(".sim-row");
  const lineas = [];

  rows.forEach((r) => {
    const cId = r.querySelector(".sim-cuenta").value;
    const debe = parseFloat(r.querySelector(".sim-debe").value || 0);
    const haber = parseFloat(r.querySelector(".sim-haber").value || 0);
    if (cId && (debe > 0 || haber > 0)) {
      lineas.append ? lineas.push({ cuenta_id: parseInt(cId), debe: debe, haber: haber }) : lineas.push({ cuenta_id: parseInt(cId), debe: debe, haber: haber });
    }
  });

  if (lineas.length < 2) {
    alert("Debes ingresar al menos dos líneas contables para la partida doble.");
    return;
  }

  const tiempoSegundos = Math.round((Date.now() - tiempoInicio) / 1000);
  const btnSubmit = document.getElementById("btnSubmitCase");
  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Evaluando con Agente IA...`;
  }

  fetch("/simulador/evaluar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      intento_id: intentoId,
      caso_id: casoId,
      lineas: lineas,
      pistas_usadas: pistasContador,
      tiempo_segundos: tiempoSegundos
    })
  })
    .then((r) => r.json())
    .then((data) => {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = `<i class="bi bi-send-check me-1"></i> Enviar Asiento y Evaluar`;
      }

      if (data.success) {
        const ev = data.evaluacion;
        const resultModal = new bootstrap.Modal(document.getElementById("evaluationResultModal"));
        
        const badgeClass = ev.resultado === "CORRECTO" ? "bg-success" : (ev.resultado === "PARCIALMENTE_CORRECTO" ? "bg-warning text-dark" : "bg-danger");
        
        document.getElementById("evalScoreBadge").className = `badge fs-4 p-2 ${badgeClass}`;
        document.getElementById("evalScoreBadge").textContent = `${ev.puntuacion} / 100 pts`;
        document.getElementById("evalResultTitle").textContent = ev.resultado.replace("_", " ");
        document.getElementById("evalFeedbackContent").innerHTML = ev.retroalimentacion.replace(/\n/g, "<br>");

        document.getElementById("rubricAccounts").textContent = `${ev.detalles_evaluacion.cuentas} / 40`;
        document.getElementById("rubricPosition").textContent = `${ev.detalles_evaluacion.posicion} / 30`;
        document.getElementById("rubricAmounts").textContent = `${ev.detalles_evaluacion.importes} / 20`;
        document.getElementById("rubricBalance").textContent = `${ev.detalles_evaluacion.partida_doble} / 10`;

        resultModal.show();
      } else {
        alert("Error en la evaluación: " + data.error);
      }
    })
    .catch((err) => {
      if (btnSubmit) btnSubmit.disabled = false;
      alert("Error de conexión al evaluar: " + err);
    });
}
