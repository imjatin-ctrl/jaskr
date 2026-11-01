/**
 * Jaskr GymGrid - Client Application Logic
 * Supports Global Command Palette (Cmd+K), Show SQL Drawer, Toast notifications,
 * Confetti effects, and interactive UI feedback.
 */

document.addEventListener("DOMContentLoaded", () => {
  initCmdPalette();
  initSqlDrawers();
  initToasts();
  initShortcutsModal();
  initNotificationsDropdown();
});

// 1. Global Command Palette (Cmd+K)
function initCmdPalette() {
  const backdrop = document.getElementById("cmdPaletteBackdrop");
  const input = document.getElementById("cmdPaletteInput");
  const results = document.getElementById("cmdPaletteResults");
  if (!backdrop || !input || !results) return;

  const routes = [
    { name: "Discover Gyms & Map", url: "/discover", group: "Public" },
    { name: "Compare Branches (Side-by-Side)", url: "/compare", group: "Public" },
    { name: "Crowd Explorer Heat Grid", url: "/crowd", group: "Public" },
    { name: "All Plans & Pricing", url: "/plans", group: "Public" },
    { name: "Under the Hood: DBMS Lab", url: "/lab", group: "DBMS Lab" },
    { name: "Query Lab (SQL Execution)", url: "/lab/query", group: "DBMS Lab" },
    { name: "Constraint Lab (Integrity Checks)", url: "/lab/constraints", group: "DBMS Lab" },
    { name: "Transaction Theater (ACID & Rollback)", url: "/lab/transactions", group: "DBMS Lab" },
    { name: "Permissions Lab (GRANT/REVOKE)", url: "/lab/permissions", group: "DBMS Lab" },
    { name: "Isolation Lab (Multi-Tenant Guard)", url: "/lab/isolation", group: "DBMS Lab" },
    { name: "Index Performance Lab (EXPLAIN)", url: "/lab/indexes", group: "DBMS Lab" },
    { name: "ER Diagram Explorer", url: "/lab/er", group: "DBMS Lab" },
    { name: "Member Portal Dashboard", url: "/member/dashboard", group: "Member" },
    { name: "Member Access Checker", url: "/member/access-checker", group: "Member" },
    { name: "Member Check-in / QR", url: "/member/check-in", group: "Member" },
    { name: "Member Billing & Invoices", url: "/member/billing", group: "Member" },
    { name: "Front Desk Console", url: "/staff/front-desk", group: "Staff" },
    { name: "Trainer Console", url: "/staff/trainer", group: "Staff" },
    { name: "Finance Desk & Reconciliation", url: "/staff/finance", group: "Staff" },
    { name: "Branch Manager Overview", url: "/staff/manager", group: "Staff" },
    { name: "Owner Dashboard & Bento KPIs", url: "/owner/dashboard", group: "Owner" },
    { name: "Owner Plans & Access Matrix", url: "/owner/plans-matrix", group: "Owner" },
    { name: "Owner Staff & Permissions", url: "/owner/staff", group: "Owner" },
    { name: "Owner Financials & Budgets", url: "/owner/finance", group: "Owner" },
    { name: "Admin Dashboard & Approvals", url: "/admin/dashboard", group: "Admin" },
    { name: "Admin DB Health Monitor", url: "/admin/health", group: "Admin" },
    { name: "Gap Analysis & Tech Scope", url: "/gap-analysis", group: "Public" },
    { name: "About the Project", url: "/about", group: "Public" },
  ];

  function openPalette() {
    backdrop.style.display = "flex";
    input.value = "";
    renderResults(routes);
    input.focus();
  }

  function closePalette() {
    backdrop.style.display = "none";
  }

  function renderResults(list) {
    results.innerHTML = "";
    if (list.length === 0) {
      results.innerHTML = '<li style="padding: 1rem; color: #64748B;">No matching pages found.</li>';
      return;
    }
    list.slice(0, 10).forEach((item, idx) => {
      const li = document.createElement("li");
      li.className = `cmd-palette-item ${idx === 0 ? "selected" : ""}`;
      li.innerHTML = `
        <span style="font-weight: 700;">${item.name}</span>
        <span class="badge" style="font-size: 0.7rem;">${item.group}</span>
      `;
      li.addEventListener("click", () => {
        window.location.href = item.url;
      });
      results.appendChild(li);
    });
  }

  // Keyboard shortcut Cmd+K / Ctrl+K
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (backdrop.style.display === "flex") {
        closePalette();
      } else {
        openPalette();
      }
    } else if (e.key === "Escape" && backdrop.style.display === "flex") {
      closePalette();
    }
  });

  input.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (!q) {
      renderResults(routes);
      return;
    }
    const filtered = routes.filter(r => r.name.toLowerCase().includes(q) || r.group.toLowerCase().includes(q));
    renderResults(filtered);
  });

  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) closePalette();
  });
}

// 2. "Show SQL" Drawer Toggle
function initSqlDrawers() {
  document.querySelectorAll(".sql-drawer-header").forEach(header => {
    header.addEventListener("click", () => {
      const body = header.nextElementSibling;
      if (body) {
        body.style.display = body.style.display === "none" ? "block" : "none";
      }
    });
  });
}

// 3. Toasts Auto-dismiss
function initToasts() {
  document.querySelectorAll(".toast").forEach(t => {
    setTimeout(() => {
      t.style.opacity = "0";
      t.style.transition = "opacity 0.4s ease";
      setTimeout(() => t.remove(), 400);
    }, 4500);
  });
}

// 4. Confetti Celebration Effect
function fireConfetti() {
  const container = document.createElement("div");
  container.style.position = "fixed";
  container.style.inset = "0";
  container.style.pointerEvents = "none";
  container.style.zIndex = "9999";
  document.body.appendChild(container);

  const colors = ["#FFD60A", "#2563EB", "#F43F5E", "#10B981", "#8B5CF6"];
  for (let i = 0; i < 40; i++) {
    const particle = document.createElement("div");
    particle.style.position = "absolute";
    particle.style.width = `${Math.random() * 10 + 6}px`;
    particle.style.height = `${Math.random() * 10 + 6}px`;
    particle.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
    particle.style.border = "1.5px solid #14121F";
    particle.style.borderRadius = "2px";
    particle.style.left = `${Math.random() * 100}vw`;
    particle.style.top = "-20px";
    particle.style.transform = `rotate(${Math.random() * 360}deg)`;
    particle.style.transition = `all ${Math.random() * 1.5 + 1.2}s cubic-bezier(0.25, 1, 0.5, 1)`;

    container.appendChild(particle);

    setTimeout(() => {
      particle.style.top = `${Math.random() * 60 + 40}vh`;
      particle.style.transform = `rotate(${Math.random() * 720}deg) scale(0.8)`;
      particle.style.opacity = "0";
    }, 20);
  }

  setTimeout(() => container.remove(), 3000);
}
// 5. Keyboard Shortcuts Modal (?)
function initShortcutsModal() {
  const backdrop = document.getElementById("shortcutsBackdrop");
  if (!backdrop) return;

  function toggleShortcuts() {
    backdrop.style.display = backdrop.style.display === "flex" ? "none" : "flex";
  }

  document.addEventListener("keydown", (e) => {
    // Only handle if not typing in input or textarea
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
      return;
    }

    if (e.key === "?" || (e.shiftKey && e.key === "/")) {
      e.preventDefault();
      toggleShortcuts();
    } else if (e.key === "Escape" && backdrop.style.display === "flex") {
      backdrop.style.display = "none";
    } else if (e.key.toLowerCase() === "l" && !e.metaKey && !e.ctrlKey) {
      window.location.href = "/lab";
    }
  });

  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) backdrop.style.display = "none";
  });
}

// 6. Notification Bell Dropdown Handling
function initNotificationsDropdown() {
  const notifDropdown = document.getElementById("notifDropdown");
  const bellBtn = document.getElementById("notifBellBtn");
  if (!notifDropdown || !bellBtn) return;

  document.addEventListener("click", (e) => {
    if (!bellBtn.contains(e.target) && !notifDropdown.contains(e.target)) {
      notifDropdown.style.display = "none";
    }
  });
}

// 7. Client-Side Table to CSV Exporter
function exportTableToCsv(tableId, filename = "gymgrid_export.csv") {
  const table = typeof tableId === "string" ? document.getElementById(tableId) : tableId;
  if (!table) return;

  let csvContent = "";
  const rows = table.querySelectorAll("tr");
  rows.forEach(row => {
    const cols = row.querySelectorAll("th, td");
    const rowData = [];
    cols.forEach(col => {
      // Clean up text content
      let text = col.innerText.replace(/"/g, '""').trim();
      rowData.push(`"${text}"`);
    });
    csvContent += rowData.join(",") + "\r\n";
  });

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
window.exportTableToCsv = exportTableToCsv;
