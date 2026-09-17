// Libro Diario Dynamic Multi-Line Entry & Live Balance Calculation
function addJournalRow() {
  const tableBody = document.getElementById("journalLinesBody");
  if (!tableBody) return;

  const selectTemplate = document.getElementById("accountSelectTemplate");
  const optionsHtml = selectTemplate ? selectTemplate.innerHTML : "";

  const row = document.createElement("tr");
  row.className = "journal-row";
  row.innerHTML = `
    <td>
      <select name="cuenta_id[]" class="form-select form-select-sm account-select" required>
        <option value="">-- Seleccione Cuenta --</option>
        ${optionsHtml}
      </select>
    </td>
    <td>
      <input type="number" step="0.01" min="0" name="debe[]" class="form-control form-control-sm debe-input text-end" value="0.00" oninput="calculateJournalTotals()">
    </td>
    <td>
      <input type="number" step="0.01" min="0" name="haber[]" class="form-control form-control-sm haber-input text-end" value="0.00" oninput="calculateJournalTotals()">
    </td>
    <td>
      <input type="text" name="referencia[]" class="form-control form-control-sm" placeholder="Referencia / Detalle">
    </td>
    <td class="text-center">
      <button type="button" class="btn btn-outline-danger btn-sm p-1" onclick="removeJournalRow(this)"><i class="bi bi-trash"></i></button>
    </td>
  `;
  tableBody.appendChild(row);
  calculateJournalTotals();
}

function removeJournalRow(button) {
  const row = button.closest("tr");
  const tableBody = document.getElementById("journalLinesBody");
  if (tableBody.querySelectorAll("tr").length > 2) {
    row.remove();
    calculateJournalTotals();
  } else {
    alert("Un asiento contable debe tener al menos dos líneas de movimiento.");
  }
}

function calculateJournalTotals() {
  const debeInputs = document.querySelectorAll(".debe-input");
  const haberInputs = document.querySelectorAll(".haber-input");

  let totalDebe = 0;
  let totalHaber = 0;

  debeInputs.forEach((input) => {
    totalDebe += parseFloat(input.value || 0);
  });

  haberInputs.forEach((input) => {
    totalHaber += parseFloat(input.value || 0);
  });

  totalDebe = Math.round(totalDebe * 100) / 100;
  totalHaber = Math.round(totalHaber * 100) / 100;
  const diff = Math.round(Math.abs(totalDebe - totalHaber) * 100) / 100;

  const totalDebeEl = document.getElementById("totalDebeDisplay");
  const totalHaberEl = document.getElementById("totalHaberDisplay");
  const bannerEl = document.getElementById("balanceBanner");
  const submitBtn = document.getElementById("btnSubmitJournal");

  if (totalDebeEl) totalDebeEl.textContent = `$${totalDebe.toLocaleString("es-EC", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (totalHaberEl) totalHaberEl.textContent = `$${totalHaber.toLocaleString("es-EC", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  if (bannerEl) {
    if (diff === 0 && totalDebe > 0) {
      bannerEl.className = "balance-banner balanced";
      bannerEl.innerHTML = `<span><i class="bi bi-check-circle-fill me-2"></i> Asiento Cuadrado: Partida Doble Verificada (Total: $${totalDebe.toFixed(2)})</span><span class="badge bg-success">Diferencia: $0.00</span>`;
      if (submitBtn) submitBtn.disabled = false;
    } else {
      bannerEl.className = "balance-banner unbalanced";
      bannerEl.innerHTML = `<span><i class="bi bi-exclamation-triangle-fill me-2"></i> Asiento Descuadrado (Debe: $${totalDebe.toFixed(2)} | Haber: $${totalHaber.toFixed(2)})</span><span class="badge bg-danger">Diferencia: $${diff.toFixed(2)}</span>`;
      if (submitBtn) submitBtn.disabled = true;
    }
  }
}
