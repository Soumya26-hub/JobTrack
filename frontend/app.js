const API = "/api/applications";
const STATUSES = ["Wishlist", "Applied", "Interview", "Offer", "Rejected"];

const form = document.querySelector("#application-form");
const formTitle = document.querySelector("#form-title");
const toggleFormButton = document.querySelector("#toggle-form");
const cancelFormButton = document.querySelector("#cancel-form");
const list = document.querySelector("#application-list");
const searchInput = document.querySelector("#search");
const statusFilters = document.querySelector("#status-filters");
const errorBanner = document.querySelector("#error-banner");
const followUpBanner = document.querySelector("#follow-up-banner");

// What the list is currently showing, and which application the form is editing.
let currentStatus = "";
let searchText = "";
let editingId = null;
let searchTimer = null;

// ---------- Talking to the backend ----------

async function api(path = "", options = {}) {
  const response = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.status === 204 ? null : response.json();
}

async function readError(response) {
  try {
    const data = await response.json();
    // FastAPI validation errors arrive as a list; show the first readable message.
    if (Array.isArray(data.detail)) {
      const first = data.detail[0];
      return `${first.loc.at(-1)}: ${first.msg}`;
    }
    return data.detail || "Something went wrong.";
  } catch {
    return "Something went wrong.";
  }
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.hidden = !message;
}

// ---------- Helpers ----------

function todayString() {
  // en-CA formats dates as YYYY-MM-DD, the same format the API uses.
  return new Date().toLocaleDateString("en-CA");
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value + "T00:00:00").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function isFollowUpDue(application) {
  return (
    application.status === "Applied" &&
    application.follow_up_date &&
    application.follow_up_date <= todayString()
  );
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  // textContent (not innerHTML) keeps user-typed text from running as HTML.
  if (text !== undefined) node.textContent = text;
  return node;
}

// ---------- Rendering ----------

function renderApplications(applications) {
  list.replaceChildren();

  if (applications.length === 0) {
    const message = currentStatus || searchText
      ? "No applications match this filter."
      : "No applications yet. Tap + Add to log your first one.";
    list.append(element("p", "empty", message));
    return;
  }

  for (const application of applications) {
    list.append(createCard(application));
  }
}

function createCard(application) {
  const card = element("article", `card application status-${application.status.toLowerCase()}`);

  const top = element("div", "card-top");
  const titles = element("div");
  titles.append(
    element("h3", "", application.company),
    element("p", "role", application.role),
  );
  top.append(titles, createStatusSelect(application));

  const details = element("p", "meta");
  const parts = [`Applied ${formatDate(application.applied_date)}`];
  if (application.location) parts.push(application.location);
  details.textContent = parts.join(" · ");

  card.append(top, details);

  if (isFollowUpDue(application)) {
    card.append(element("p", "badge", "Follow-up due"));
  } else if (application.status === "Applied" && application.follow_up_date) {
    card.append(element("p", "meta", `Follow up on ${formatDate(application.follow_up_date)}`));
  }

  if (application.notes) {
    card.append(element("p", "notes", application.notes));
  }

  if (application.match_score !== null && application.tailored_summary) {
    const match = element("details", "match-line");
    match.append(
      element("summary", "", `Resume match: ${application.match_score}%`),
      element("p", "", application.tailored_summary),
    );
    card.append(match);
  }

  const actions = element("div", "actions");
  if (application.job_link) {
    const link = element("a", "button-link", "Open job");
    link.href = application.job_link;
    link.target = "_blank";
    link.rel = "noopener";
    actions.append(link);
  }
  const editButton = element("button", "", "Edit");
  editButton.type = "button";
  editButton.addEventListener("click", () => openForm(application));

  const deleteButton = element("button", "danger", "Delete");
  deleteButton.type = "button";
  deleteButton.addEventListener("click", () => deleteApplication(application));

  actions.append(editButton, deleteButton);
  card.append(actions);
  return card;
}

function createStatusSelect(application) {
  const select = element("select", "status-select");
  select.setAttribute("aria-label", `Status for ${application.company}`);
  for (const status of STATUSES) {
    const option = element("option", "", status);
    option.selected = status === application.status;
    select.append(option);
  }
  select.addEventListener("change", () => updateStatus(application.id, select.value));
  return select;
}

function renderStats(stats) {
  document.querySelector("#stat-total").textContent = stats.total;
  document.querySelector("#stat-interview").textContent = stats.by_status.Interview;
  document.querySelector("#stat-offer").textContent = stats.by_status.Offer;
  document.querySelector("#stat-rate").textContent = `${stats.response_rate}%`;

  const due = stats.follow_ups_due;
  followUpBanner.hidden = due === 0;
  followUpBanner.textContent = `${due} application${due === 1 ? "" : "s"} due for a follow-up.`;
}

// ---------- Loading data ----------

async function refresh() {
  const params = new URLSearchParams();
  if (currentStatus) params.set("status", currentStatus);
  if (searchText) params.set("search", searchText);
  const query = params.toString() ? `?${params}` : "";

  try {
    // Ask for the list and the summary at the same time.
    const [applications, stats] = await Promise.all([api(query), api("/stats")]);
    renderApplications(applications);
    renderStats(stats);
    showError("");
  } catch (error) {
    showError(error.message);
  }
}

// ---------- Actions ----------

async function updateStatus(id, status) {
  try {
    await api(`/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    await refresh();
  } catch (error) {
    showError(error.message);
  }
}

async function deleteApplication(application) {
  if (!confirm(`Delete ${application.company} – ${application.role}?`)) return;
  try {
    await api(`/${application.id}`, { method: "DELETE" });
    await refresh();
  } catch (error) {
    showError(error.message);
  }
}

function readForm() {
  const data = Object.fromEntries(new FormData(form));
  // Empty optional fields are sent as null instead of "".
  for (const key of ["location", "job_link", "notes", "applied_date", "follow_up_date"]) {
    data[key] = data[key].trim() || null;
  }
  return data;
}

async function saveForm(event) {
  event.preventDefault();
  const data = readForm();
  const isEditing = editingId !== null;

  try {
    await api(isEditing ? `/${editingId}` : "", {
      method: isEditing ? "PATCH" : "POST",
      body: JSON.stringify(data),
    });
    closeForm();
    await refresh();
  } catch (error) {
    showError(error.message);
  }
}

function openForm(application = null) {
  form.reset();
  editingId = application ? application.id : null;
  formTitle.textContent = application ? "Edit application" : "New application";

  if (application) {
    for (const [key, value] of Object.entries(application)) {
      if (form.elements[key]) form.elements[key].value = value ?? "";
    }
  } else {
    form.elements.applied_date.value = todayString();
  }

  form.hidden = false;
  form.scrollIntoView({ behavior: "smooth" });
  form.elements.company.focus();
}

function closeForm() {
  form.reset();
  form.hidden = true;
  editingId = null;
}

// ---------- Wiring up the page ----------

toggleFormButton.addEventListener("click", () => (form.hidden ? openForm() : closeForm()));
cancelFormButton.addEventListener("click", closeForm);
form.addEventListener("submit", saveForm);

statusFilters.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  statusFilters.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === chip));
  currentStatus = chip.dataset.status;
  refresh();
});

searchInput.addEventListener("input", () => {
  // Wait until typing pauses before searching, instead of calling the API on every key.
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    searchText = searchInput.value.trim();
    refresh();
  }, 300);
});

// ---------- Tabs ----------

const tabs = document.querySelectorAll(".tab");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.toggle("active", t === tab));
    document.querySelector("#applications-view").hidden = tab.dataset.tab !== "applications-view";
    document.querySelector("#match-view").hidden = tab.dataset.tab !== "match-view";
    // The + Add button only makes sense on the Applications tab.
    toggleFormButton.hidden = tab.dataset.tab !== "applications-view";
    showError("");
    if (tab.dataset.tab === "match-view") {
      loadApplicationChoices();
      loadProfile();
    } else {
      refresh();
    }
  });
});

// ---------- Resume Match agent ----------

const matchForm = document.querySelector("#match-form");
const matchApplication = document.querySelector("#match-application");
const matchResult = document.querySelector("#match-result");
const profileForm = document.querySelector("#profile-form");

async function loadApplicationChoices() {
  try {
    const applications = await api();
    const selected = matchApplication.value;
    matchApplication.replaceChildren(new Option("Don't save", ""));
    for (const application of applications) {
      matchApplication.append(new Option(`${application.company} – ${application.role}`, application.id));
    }
    matchApplication.value = selected;
  } catch (error) {
    showError(error.message);
  }
}

function renderSkills(container, skills, className, emptyText) {
  container.replaceChildren();
  if (skills.length === 0) {
    container.append(element("span", "meta", emptyText));
    return;
  }
  for (const skill of skills) {
    container.append(element("span", `skill ${className}`, skill));
  }
}

function renderMatch(result) {
  document.querySelector("#result-title").textContent = result.job_title || "Match result";
  document.querySelector("#result-years").textContent = result.years_required
    ? `Asks for about ${result.years_required}+ years of experience`
    : "";
  document.querySelector("#result-score").textContent = `${result.match_score}%`;
  renderSkills(document.querySelector("#result-matched"), result.matched_skills, "have", "No listed skills matched.");
  renderSkills(document.querySelector("#result-missing"), result.missing_skills, "missing", "Nothing missing. Great fit!");
  document.querySelector("#result-summary").textContent = result.tailored_summary;
  document.querySelector("#result-saved").textContent = result.saved_to_application
    ? "Saved to the application. You'll see it on its card."
    : "";
  matchResult.hidden = false;
  matchResult.scrollIntoView({ behavior: "smooth" });
}

matchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = {
    job_description: matchForm.elements.job_description.value,
    application_id: matchApplication.value ? Number(matchApplication.value) : null,
  };
  try {
    const response = await fetch("/api/agent/resume-match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(await readError(response));
    renderMatch(await response.json());
    showError("");
  } catch (error) {
    showError(error.message);
  }
});

document.querySelector("#copy-summary").addEventListener("click", async (event) => {
  const text = document.querySelector("#result-summary").textContent;
  try {
    await navigator.clipboard.writeText(text);
    event.target.textContent = "Copied!";
  } catch {
    // Clipboard access can be blocked on plain http; selecting the text lets you copy by hand.
    window.getSelection().selectAllChildren(document.querySelector("#result-summary"));
    event.target.textContent = "Text selected – copy it";
  }
  setTimeout(() => (event.target.textContent = "Copy summary"), 2000);
});

async function loadProfile() {
  try {
    const response = await fetch("/api/profile");
    if (!response.ok) throw new Error(await readError(response));
    const profile = await response.json();
    for (const field of ["intro", "skills", "highlights"]) {
      profileForm.elements[field].value = profile[field];
    }
  } catch (error) {
    showError(error.message);
  }
}

profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(profileForm));
  const status = document.querySelector("#profile-status");
  try {
    const response = await fetch("/api/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(await readError(response));
    status.textContent = "Profile saved.";
    showError("");
  } catch (error) {
    status.textContent = "";
    showError(error.message);
  }
});

refresh();
