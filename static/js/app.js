// Global Application Utilities & Search Autocomplete
document.addEventListener("DOMContentLoaded", function () {
  // 1. Sidebar Toggle for Mobile / Tablet
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebarWrapper = document.getElementById("sidebar-wrapper");
  if (sidebarToggle && sidebarWrapper) {
    sidebarToggle.addEventListener("click", function () {
      sidebarWrapper.classList.toggle("active");
    });
  }

  // 2. Global Search Autocomplete
  const searchInput = document.getElementById("globalSearchInput");
  const searchDropdown = document.getElementById("searchDropdown");

  if (searchInput && searchDropdown) {
    searchInput.addEventListener("input", function () {
      const q = this.value.trim();
      if (q.length < 2) {
        searchDropdown.style.display = "none";
        return;
      }

      fetch(`/api/search?q=${encodeURIComponent(q)}`)
        .then((res) => res.json())
        .then((data) => {
          const res = data.results || {};
          let html = "";
          let hasResults = false;

          if (res.cuentas && res.cuentas.length > 0) {
            hasResults = true;
            html += `<div class="search-group-title"><i class="bi bi-journal-bookmark me-1"></i> Cuentas Contables</div>`;
            res.cuentas.forEach((c) => {
              html += `<a href="/contabilidad/mayor?cuenta_id=${c.id}" class="search-item text-decoration-none text-dark"><span><strong>${c.codigo}</strong> ${c.nombre}</span><span class="badge bg-secondary">Cuenta</span></a>`;
            });
          }

          if (res.productos && res.productos.length > 0) {
            hasResults = true;
            html += `<div class="search-group-title"><i class="bi bi-box-seam me-1"></i> Productos / Kardex</div>`;
            res.productos.forEach((p) => {
              html += `<a href="/inventarios/kardex/${p.id}" class="search-item text-decoration-none text-dark"><span><strong>${p.codigo}</strong> ${p.descripcion}</span><span class="badge bg-primary">Producto</span></a>`;
            });
          }

          if (res.clientes && res.clientes.length > 0) {
            hasResults = true;
            html += `<div class="search-group-title"><i class="bi bi-people me-1"></i> Clientes</div>`;
            res.clientes.forEach((cl) => {
              html += `<a href="/clientes" class="search-item text-decoration-none text-dark"><span>${cl.nombre_razon_social} (${cl.identificacion})</span><span class="badge bg-success">Cliente</span></a>`;
            });
          }

          if (res.asientos && res.asientos.length > 0) {
            hasResults = true;
            html += `<div class="search-group-title"><i class="bi bi-card-checklist me-1"></i> Asientos Contables</div>`;
            res.asientos.forEach((a) => {
              html += `<a href="/contabilidad/diario" class="search-item text-decoration-none text-dark"><span>Asiento #${a.numero_asiento}: ${a.glosa}</span><span class="badge bg-dark">${a.fecha}</span></a>`;
            });
          }

          if (hasResults) {
            searchDropdown.innerHTML = html;
            searchDropdown.style.display = "block";
          } else {
            searchDropdown.innerHTML = `<div class="p-3 text-muted text-center small">No se encontraron coincidencias para "${q}"</div>`;
            searchDropdown.style.display = "block";
          }
        })
        .catch((err) => console.error("Search error:", err));
    });

    document.addEventListener("click", function (e) {
      if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
        searchDropdown.style.display = "none";
      }
    });
  }
});
