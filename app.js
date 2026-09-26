let employees = [];
let activeDept = null;

const DEPT_COLORS = {
  "Information Technology": "#2FA6A2",
  "Human Resources": "#C9A227",
  "Finance": "#6E8FD9",
  "Operations": "#D97757",
  "Compliance": "#8E7CE0",
  "Administration": "#4CAF7D",
};
function deptColor(name) {
  return DEPT_COLORS[name] || "#8CA0B5";
}

async function init() {
  try {
    const [empRes, statsRes, hbRes] = await Promise.all([
      fetch("/api/employees"),
      fetch("/api/stats"),
      fetch("/api/handbook"),
    ]);
    employees = await empRes.json();
    const stats = await statsRes.json();
    const hb = await hbRes.json();

    document.getElementById("statEmployees").textContent = stats.total_employees;
    document.getElementById("statSections").textContent = stats.handbook_sections;

    renderDeptBars(stats.departments);
    renderDeptChips(stats.departments);
    renderEmployees();

    renderHandbookBody(hb.content);
    renderHandbookIndex(hb.sections || []);
  } catch (err) {
    console.error(err);
  }
}

function showTab(id, btn) {
  document.querySelectorAll(".tab").forEach(x => x.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
  document.querySelectorAll(".nav").forEach(x => x.classList.remove("active"));
  if (btn) btn.classList.add("active");
  const titles = {
    home: ["Dashboard", "Overview of your workplace assistant"],
    assistant: ["AI Employee Assistant", "Ask a question, get a handbook-backed answer"],
    employees: ["Employee Directory", "Browse and search everyone at HCL Capital"],
    handbook: ["Employee Handbook", "The full policy text, organized by section"],
  };
  const [title, sub] = titles[id] || [id, ""];
  document.getElementById("pageTitle").textContent = title;
  document.getElementById("pageSub").textContent = sub;
}

function renderDeptBars(departments) {
  const total = Object.values(departments).reduce((a, b) => a + b, 0) || 1;
  const el = document.getElementById("deptBars");
  el.innerHTML = Object.entries(departments)
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => `
      <div class="deptbar-row">
        <span>${name}</span>
        <div class="deptbar-track"><div class="deptbar-fill" style="width:${(count / total) * 100}%;background:${deptColor(name)}"></div></div>
        <b>${count}</b>
      </div>`).join("");
}

function renderDeptChips(departments) {
  const el = document.getElementById("deptChips");
  const names = Object.keys(departments).sort();
  el.innerHTML = `<button class="chip active" data-dept="" onclick="filterDept('')">All</button>` +
    names.map(n => `<button class="chip" data-dept="${n}" onclick="filterDept('${n.replace(/'/g, "\\'")}')">${n}</button>`).join("");
}

function filterDept(name) {
  activeDept = name || null;
  document.querySelectorAll(".chip").forEach(c => {
    c.classList.toggle("active", c.dataset.dept === name);
  });
  renderEmployees();
}

function renderEmployees() {
  const q = (document.getElementById("search")?.value || "").toLowerCase();
  let list = employees;
  if (activeDept) list = list.filter(e => e.department === activeDept);
  if (q) list = list.filter(e => Object.values(e).some(v => String(v).toLowerCase().includes(q)));

  document.getElementById("employeeGrid").innerHTML = list.map(e => {
    const initials = e.name.split(" ").map(p => p[0]).slice(0, 2).join("").toUpperCase();
    const color = deptColor(e.department);
    return `
      <div class="employee" style="--dept-color:${color}">
        <div class="avatar">${initials}</div>
        <div>
          <h3>${e.name}</h3>
          <p class="role">${e.role}</p>
          <p>${e.department} — ${e.location}</p>
          <p>${e.email}</p>
          <p class="empid">${e.employee_id}</p>
        </div>
      </div>`;
  }).join("") || `<p class="muted">No employees match your search.</p>`;
}

function renderHandbookIndex(titles) {
  const el = document.getElementById("handbookNav");
  el.innerHTML = titles.map(t => `<button onclick="jumpToSection('${t.replace(/'/g, "\\'")}')">${t}</button>`).join("");
}

function slugify(title) {
  return "sec-" + title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function renderHandbookBody(content) {
  const body = document.getElementById("handbookText");
  const chunks = content.split(/\n(?=## )/);
  let html = "";
  for (const chunk of chunks) {
    const trimmed = chunk.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith("## ")) {
      const lines = trimmed.split("\n");
      const title = lines[0].replace("## ", "").trim();
      const rest = lines.slice(1).join("\n").trim();
      html += `<div class="hb-section" id="${slugify(title)}"><h4>${escapeHtml(title)}</h4><p>${escapeHtml(rest)}</p></div>`;
    } else {
      html += `<div class="hb-intro">${escapeHtml(trimmed)}</div>`;
    }
  }
  body.innerHTML = html;
}

function jumpToSection(title) {
  const el = document.getElementById(slugify(title));
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function askQuick(q) {
  showTab("assistant", document.querySelector('[data-tab="assistant"]'));
  document.getElementById("question").value = q;
  await ask();
}

async function ask() {
  const input = document.getElementById("question");
  const q = input.value.trim();
  if (!q) return;
  const box = document.getElementById("messages");

  box.innerHTML += `<div class="msg user"><b>You</b><p>${escapeHtml(q)}</p></div>`;
  input.value = "";
  const typingId = "typing-" + Date.now();
  box.innerHTML += `<div class="msg bot" id="${typingId}"><b>AI Employee</b><p class="typing"><span></span><span></span><span></span></p></div>`;
  box.scrollTop = box.scrollHeight;

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    const data = await res.json();
    const pct = Math.round((data.confidence || 0) * 100);
    const related = (data.related || [])
      .map(r => `<button onclick="askQuick('Tell me about ${r.title.replace(/'/g, "\\'")}')">${r.title}</button>`)
      .join("");

    document.getElementById(typingId).outerHTML = `
      <div class="msg bot">
        <b>AI Employee · ${escapeHtml(data.source || "Handbook")}</b>
        <p>${escapeHtml(data.answer)}</p>
        ${pct ? `<span class="confidence">${pct}% match</span>` : ""}
        ${related ? `<div class="related">${related}</div>` : ""}
      </div>`;
  } catch (err) {
    document.getElementById(typingId).outerHTML = `<div class="msg bot"><b>AI Employee</b><p>Something went wrong reaching the assistant. Please try again.</p></div>`;
  }
  box.scrollTop = box.scrollHeight;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));
}

init();
