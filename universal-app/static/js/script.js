// --- THEME ---
if (localStorage.getItem("theme") === "light")
  document.documentElement.classList.add("light");
function toggleTheme() {
  document.documentElement.classList.toggle("light");
  localStorage.setItem(
    "theme",
    document.documentElement.classList.contains("light") ? "light" : "dark",
  );
}

// --- NAVIGATION ---
function nav(id) {
  document
    .querySelectorAll(".view")
    .forEach((e) => e.classList.remove("active"));
  document
    .querySelectorAll(".nav-item")
    .forEach((e) => e.classList.remove("active"));
  document.getElementById("view-" + id).classList.add("active");
  event.currentTarget.classList.add("active");
}

// --- API & DATA ---
const API = {
  get: async (ep) => (await fetch("/api/" + ep)).json(),
  post: async (ep, d) =>
    (
      await fetch("/api/" + ep, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(d),
      })
    ).json(),
  del: async (ep) => (await fetch("/api/" + ep, { method: "DELETE" })).json(),
};

let cachedDevices = [];
let cachedSchedules = [];
let currentSettings = { subnets: [] };

// --- DASHBOARD LOGIC ---
async function updateDashboard() {
  try {
    const data = await API.get("devices");
    const list = document.getElementById("device-list");
    const sel = document.getElementById("s-dev");

    if (data.length === 0 && list.children.length > 1) {
      list.innerHTML =
        '<div style="text-align:center; padding:40px; opacity:0.6; grid-column:1/-1;">No devices found.</div>';
      return;
    }

    if (data.length !== cachedDevices.length) {
      list.innerHTML = "";
      sel.innerHTML = "";
      data
        .sort((a, b) => a.name.localeCompare(b.name))
        .forEach((d) => {
          sel.add(new Option(d.name, d.name));
          let div = document.createElement("div");
          div.className = "card flex";
          div.id = "card-" + d.name.replace(/\s+/g, "-");
          div.innerHTML = `
                            <div>
                                <div style="font-weight:bold; font-size:1.1rem;">${d.name}</div>
                                <div style="font-size:0.8rem; color:var(--subtext);">${d.ip}</div>
                            </div>
                            <button id="btn-${d.name.replace(/\s+/g, "-")}" class="btn btn-toggle ${d.state ? "on" : ""}" onclick="toggle('${d.name}')">
                                ${d.state ? "ON" : "OFF"}
                            </button>`;
          list.appendChild(div);
        });
    } else {
      data.forEach((d) => {
        const btn = document.getElementById(
          "btn-" + d.name.replace(/\s+/g, "-"),
        );
        if (btn) {
          const isOn = d.state === 1 || d.state === true;
          if (btn.classList.contains("on") !== isOn) {
            btn.className = `btn btn-toggle ${isOn ? "on" : ""}`;
            btn.innerText = isOn ? "ON" : "OFF";
          }
        }
      });
    }
    cachedDevices = data;
  } catch (e) {
    console.log("Poll error", e);
  }
}

async function toggle(n) {
  const btn = document.getElementById("btn-" + n.replace(/\s+/g, "-"));
  if (btn) {
    const isNowOn = btn.innerText === "OFF";
    btn.className = `btn btn-toggle ${isNowOn ? "on" : ""}`;
    btn.innerText = isNowOn ? "ON" : "OFF";
  }
  await API.post("toggle/" + n);
  setTimeout(updateDashboard, 500);
}

// --- SCHEDULE LOGIC ---
async function updateSchedules() {
  try {
    const data = await API.get("schedules");
    if (JSON.stringify(data) === JSON.stringify(cachedSchedules)) return;

    const list = document.getElementById("sched-list");
    list.innerHTML = "";
    if (data.length === 0)
      list.innerHTML =
        '<div style="opacity:0.6; text-align:center; padding:20px;">No active rules.</div>';

    data.forEach((s) => {
      let div = document.createElement("div");
      div.className = "card flex";
      div.innerHTML = `
                        <div>
                            <div style="font-weight:bold; color:var(--accent);">${s.action} ${s.device}</div>
                            <div style="font-size:0.9rem; color:var(--subtext);">${s.type} ${s.value}</div>
                        </div>
                        <button class="btn btn-danger" style="padding:8px 12px;" onclick="delSched(${s.id})">🗑️</button>`;
      list.appendChild(div);
    });
    cachedSchedules = data;
  } catch (e) {}
}

async function addSchedule() {
  await API.post("schedules", {
    device: document.getElementById("s-dev").value,
    action: document.getElementById("s-action").value,
    type: document.getElementById("s-type").value,
    value: document.getElementById("s-val").value,
    days: [0, 1, 2, 3, 4, 5, 6],
  });
  updateSchedules();
  alert("Schedule Added");
}

async function delSched(id) {
  if (confirm("Delete this rule?")) {
    await API.del("schedules?id=" + id);
    updateSchedules();
  }
}

// --- SUBNET MANAGER LOGIC ---
async function loadSettings() {
  const s = await API.get("settings");
  currentSettings = s;
  if (!currentSettings.subnets) currentSettings.subnets = [];
  renderSubnetList();
}

function renderSubnetList() {
  const sel = document.getElementById("subnet-select");
  sel.innerHTML = '<option value="">-- Select Saved Subnet --</option>';
  currentSettings.subnets.forEach((sub) => {
    sel.add(new Option(sub, sub));
  });
}

function selectSubnet() {
  const sel = document.getElementById("subnet-select");
  if (sel.value) {
    document.getElementById("subnet-input").value = sel.value;
  }
}

async function saveSubnet() {
  const val = document.getElementById("subnet-input").value.trim();
  if (!val) return;

  // Add if unique
  if (!currentSettings.subnets.includes(val)) {
    currentSettings.subnets.push(val);
    await API.post("settings", { subnets: currentSettings.subnets });
    renderSubnetList();
    document.getElementById("subnet-select").value = val; // Select it
    alert("Subnet Saved");
  } else {
    alert("Subnet already in list");
  }
}

async function deleteSubnet() {
  const sel = document.getElementById("subnet-select");
  const val = sel.value;

  if (!val) {
    alert("Please select a subnet from the dropdown to delete.");
    return;
  }

  if (confirm("Delete saved subnet: " + val + "?")) {
    currentSettings.subnets = currentSettings.subnets.filter((s) => s !== val);
    await API.post("settings", { subnets: currentSettings.subnets });
    renderSubnetList();
    document.getElementById("subnet-input").value = "";
  }
}

function triggerScan() {
  API.post("scan");
  alert("Scanning Network...");
}

// --- POLLING LOOP ---
async function poller() {
  const s = await API.get("status");
  document.getElementById("scan-status").innerText = s.scan_status;

  await updateDashboard();
  await updateSchedules();
}

// Init
loadSettings();
updateDashboard();
updateSchedules();

// Fast Polling for Responsive UI
setInterval(poller, 2000);
