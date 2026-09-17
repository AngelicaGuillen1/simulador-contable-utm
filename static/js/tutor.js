// Tutor Contable IA Interactive Chat Controller
function sendTutorMessage() {
  const input = document.getElementById("tutorChatInput");
  const messagesBox = document.getElementById("tutorMessagesBox");
  const nivelAyuda = document.getElementById("tutorNivelAyuda") ? document.getElementById("tutorNivelAyuda").value : "PISTA";

  if (!input || !messagesBox) return;
  const text = input.value.trim();
  if (!text) return;

  // Add User Message
  const userMsgDiv = document.createElement("div");
  userMsgDiv.className = "d-flex justify-content-end mb-3";
  userMsgDiv.innerHTML = `
    <div class="bg-primary text-white p-3 rounded-3 shadow-sm" style="max-width: 75%;">
      <div class="small fw-bold mb-1"><i class="bi bi-person-fill me-1"></i> Tú</div>
      <div>${escapeHtml(text)}</div>
    </div>
  `;
  messagesBox.appendChild(userMsgDiv);
  input.value = "";
  messagesBox.scrollTop = messagesBox.scrollHeight;

  // Add Typing Indicator
  const typingDiv = document.createElement("div");
  typingDiv.id = "tutorTypingIndicator";
  typingDiv.className = "d-flex justify-content-start mb-3";
  typingDiv.innerHTML = `
    <div class="bg-light p-3 rounded-3 border" style="max-width: 75%;">
      <div class="spinner-grow spinner-grow-sm text-primary me-1" role="status"></div>
      <span class="text-muted small">Tutor IA analizando concepto contable...</span>
    </div>
  `;
  messagesBox.appendChild(typingDiv);
  messagesBox.scrollTop = messagesBox.scrollHeight;

  fetch("/tutor/preguntar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pregunta: text, nivel_ayuda: nivelAyuda })
  })
    .then((r) => r.json())
    .then((data) => {
      const typingEl = document.getElementById("tutorTypingIndicator");
      if (typingEl) typingEl.remove();

      const aiMsgDiv = document.createElement("div");
      aiMsgDiv.className = "d-flex justify-content-start mb-3";
      aiMsgDiv.innerHTML = `
        <div class="bg-white p-3 rounded-3 border shadow-sm" style="max-width: 80%;">
          <div class="small fw-bold text-primary mb-1">
            <i class="bi bi-robot me-1"></i> ${data.agente || "Tutor Contable IA"}
            ${data.tipo_ayuda ? `<span class="badge bg-light text-dark border ms-2">${data.tipo_ayuda}</span>` : ""}
          </div>
          <div style="white-space: pre-line;">${escapeHtml(data.respuesta || "No se pudo procesar la respuesta.")}</div>
        </div>
      `;
      messagesBox.appendChild(aiMsgDiv);
      messagesBox.scrollTop = messagesBox.scrollHeight;
    })
    .catch((err) => {
      const typingEl = document.getElementById("tutorTypingIndicator");
      if (typingEl) typingEl.remove();
      alert("Error al comunicarse con el Tutor IA: " + err);
    });
}

function escapeHtml(string) {
  return String(string).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
