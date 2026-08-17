const rootUrl = new URL("./", window.location.href);
const state = {
  language: "en",
  messages: {},
  meals: [],
  plan: null,
  weekStart: mondayFor(new Date()),
};

const elements = {
  language: document.querySelector("#language-select"),
  weekHeading: document.querySelector("#week-heading"),
  weekGrid: document.querySelector("#week-grid"),
  mealList: document.querySelector("#meal-list"),
  search: document.querySelector("#meal-search"),
  dialog: document.querySelector("#meal-dialog"),
  dialogTitle: document.querySelector("#meal-dialog-title"),
  form: document.querySelector("#meal-form"),
  formError: document.querySelector("#form-error"),
  toast: document.querySelector("#toast"),
  generateWeek: document.querySelector("#generate-week"),
};

function mondayFor(value) {
  const result = new Date(value.getFullYear(), value.getMonth(), value.getDate(), 12);
  const weekday = result.getDay() || 7;
  result.setDate(result.getDate() - weekday + 1);
  return result;
}

function addDays(value, days) {
  const result = new Date(value);
  result.setDate(result.getDate() + days);
  return result;
}

function dateKey(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day, 12);
}

function lookup(key) {
  return key.split(".").reduce((current, part) => current?.[part], state.messages) ?? key;
}

function t(key, variables = {}) {
  return Object.entries(variables).reduce(
    (message, [name, value]) => message.replaceAll(`{${name}}`, String(value)),
    lookup(key),
  );
}

async function api(path, options = {}) {
  const response = await fetch(new URL(`api/${path}`, rootUrl), {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const error = new Error(payload.detail || response.statusText);
    error.code = payload.code;
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

async function setLanguage(language) {
  const response = await fetch(new URL(`locales/${language}.json`, rootUrl));
  if (!response.ok) throw new Error("Locale could not be loaded");
  state.language = language;
  state.messages = await response.json();
  document.documentElement.lang = language;
  elements.language.value = language;
  localStorage.setItem("meal-planner-language", language);
  translatePage();
  renderWeek();
  renderMeals();
}

function translatePage() {
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.placeholder = t(element.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((element) => {
    element.title = t(element.dataset.i18nTitle);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
  });
}

function element(tag, className, text) {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (text !== undefined) result.textContent = text;
  return result;
}

function localizedError(error) {
  if (error.code && lookup(`errors.${error.code}`) !== `errors.${error.code}`) {
    return t(`errors.${error.code}`);
  }
  return t("status.error");
}

function renderWeek() {
  if (!state.plan) return;
  const locale = state.language === "sv" ? "sv-SE" : "en-GB";
  const start = parseDate(state.plan.week_start);
  const end = parseDate(state.plan.week_end);
  const rangeFormat = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short" });
  elements.weekHeading.textContent = `${rangeFormat.format(start)} – ${rangeFormat.format(end)}`;
  elements.generateWeek.textContent = t(
    state.plan.days.some((day) => day.meal) ? "week.regenerate" : "week.generate",
  );
  elements.weekGrid.replaceChildren();

  const dayKeys = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
  const today = dateKey(new Date());
  state.plan.days.forEach((day, index) => {
    const card = element("article", "day-card");
    if (day.date === today) card.classList.add("day-card--today");
    card.append(
      element("p", "day-card__weekday", t(`days.${dayKeys[index]}`)),
      element(
        "p",
        "day-card__date",
        new Intl.DateTimeFormat(locale, { day: "numeric", month: "long" }).format(parseDate(day.date)),
      ),
    );

    const select = element("select");
    select.setAttribute("aria-label", `${t(`days.${dayKeys[index]}`)} — ${t("common.none")}`);
    const emptyOption = element("option", "", t("common.none"));
    emptyOption.value = "";
    select.append(emptyOption);
    state.meals.forEach((meal) => {
      const option = element("option", "", meal.name);
      option.value = meal.id;
      option.selected = day.meal?.id === meal.id;
      select.append(option);
    });
    select.addEventListener("change", () => updateAssignment(day.date, select.value));
    card.append(select);
    if (day.meal) {
      const footer = element("div", "day-card__footer");
      footer.append(
        element(
          "span",
          "day-card__status",
          t(day.is_manual_override ? "week.manual" : "week.generated"),
        ),
      );
      if (!day.is_manual_override) {
        const regenerateButton = element(
          "button",
          "button button--small",
          t("week.regenerateDay"),
        );
        regenerateButton.type = "button";
        regenerateButton.addEventListener("click", () => regenerateDay(day.date));
        footer.append(regenerateButton);
      }
      card.append(footer);
    }
    elements.weekGrid.append(card);
  });
}

function renderMeals() {
  const query = elements.search.value.trim().toLocaleLowerCase(state.language);
  const meals = state.meals.filter((meal) =>
    [meal.name, meal.description, meal.protein_source, ...meal.tags]
      .join(" ")
      .toLocaleLowerCase(state.language)
      .includes(query),
  );
  elements.mealList.replaceChildren();
  if (!meals.length) {
    elements.mealList.append(element("p", "empty-state", t(state.meals.length ? "meals.noResults" : "meals.empty")));
    return;
  }

  meals.forEach((meal) => {
    const card = element("article", "meal-card");
    const copy = element("div");
    copy.append(
      element("h3", "", meal.name),
      element(
        "p",
        "",
        t("meal.meta", {
          preference: meal.preference,
          effort: meal.cooking_effort,
          protein: meal.protein_source,
        }),
      ),
    );
    const actions = element("div", "meal-card__actions");
    const editButton = element("button", "button", t("common.edit"));
    editButton.type = "button";
    editButton.addEventListener("click", () => openMealDialog(meal));
    const deleteButton = element("button", "button button--danger", t("common.delete"));
    deleteButton.type = "button";
    deleteButton.addEventListener("click", () => deleteMeal(meal));
    actions.append(editButton, deleteButton);
    card.append(copy, actions);
    elements.mealList.append(card);
  });
}

async function loadWeek() {
  state.plan = await api(`plans/${dateKey(state.weekStart)}`);
  renderWeek();
}

async function updateAssignment(day, mealId) {
  try {
    const path = `plans/${state.plan.week_start}/days/${day}`;
    state.plan = mealId
      ? await api(path, { method: "PUT", body: JSON.stringify({ meal_id: mealId }) })
      : await api(path, { method: "DELETE" });
    renderWeek();
    showToast(t("status.assigned"));
  } catch (error) {
    console.error(error);
    showToast(localizedError(error));
    await loadWeek();
  }
}

async function generateWeek() {
  setPlanningBusy(true);
  try {
    state.plan = await api(`plans/${state.plan.week_start}/generate`, { method: "POST" });
    renderWeek();
    showToast(t("status.generated"));
  } catch (error) {
    console.error(error);
    showToast(localizedError(error));
  } finally {
    setPlanningBusy(false);
  }
}

async function regenerateDay(day) {
  setPlanningBusy(true);
  try {
    state.plan = await api(`plans/${state.plan.week_start}/days/${day}/regenerate`, {
      method: "POST",
    });
    renderWeek();
    showToast(t("status.regeneratedDay"));
  } catch (error) {
    console.error(error);
    showToast(localizedError(error));
  } finally {
    setPlanningBusy(false);
  }
}

function setPlanningBusy(busy) {
  document
    .querySelectorAll(".week-controls button, .week-grid button, .week-grid select")
    .forEach((control) => {
      control.disabled = busy;
    });
}

function openMealDialog(meal = null) {
  elements.form.reset();
  elements.formError.textContent = "";
  document.querySelector("#meal-id").value = meal?.id ?? "";
  document.querySelector("#meal-name").value = meal?.name ?? "";
  document.querySelector("#meal-description").value = meal?.description ?? "";
  document.querySelector("#meal-type").value = meal?.meal_type ?? "dinner";
  document.querySelector("#meal-protein").value = meal?.protein_source ?? "other";
  document.querySelector("#meal-preference").value = meal?.preference ?? 3;
  document.querySelector("#meal-effort").value = meal?.cooking_effort ?? 3;
  document.querySelector("#meal-tags").value = meal?.tags.join(", ") ?? "";
  document.querySelector("#meal-excluded").checked = meal?.excluded ?? false;
  elements.dialogTitle.textContent = t(meal ? "meal.editTitle" : "meal.addTitle");
  elements.dialog.showModal();
  document.querySelector("#meal-name").focus();
}

async function saveMeal(event) {
  event.preventDefault();
  const mealId = document.querySelector("#meal-id").value;
  const payload = {
    name: document.querySelector("#meal-name").value,
    description: document.querySelector("#meal-description").value,
    meal_type: document.querySelector("#meal-type").value,
    protein_source: document.querySelector("#meal-protein").value,
    preference: Number(document.querySelector("#meal-preference").value),
    cooking_effort: Number(document.querySelector("#meal-effort").value),
    tags: document.querySelector("#meal-tags").value.split(",").map((tag) => tag.trim()).filter(Boolean),
    excluded: document.querySelector("#meal-excluded").checked,
  };
  try {
    await api(mealId ? `meals/${mealId}` : "meals", {
      method: mealId ? "PATCH" : "POST",
      body: JSON.stringify(payload),
    });
    elements.dialog.close();
    state.meals = await api("meals");
    await loadWeek();
    renderMeals();
    showToast(t("status.saved"));
  } catch (error) {
    elements.formError.textContent = localizedError(error);
  }
}

async function deleteMeal(meal) {
  if (!window.confirm(t("meal.deleteConfirm", { name: meal.name }))) return;
  try {
    await api(`meals/${meal.id}`, { method: "DELETE" });
    state.meals = await api("meals");
    await loadWeek();
    renderMeals();
    showToast(t("status.deleted"));
  } catch (error) {
    console.error(error);
    showToast(t("status.error"));
  }
}

let toastTimer;
function showToast(message) {
  clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.add("toast--visible");
  toastTimer = setTimeout(() => elements.toast.classList.remove("toast--visible"), 2500);
}

function bindEvents() {
  document.querySelector("#add-meal").addEventListener("click", () => openMealDialog());
  document.querySelector("#close-dialog").addEventListener("click", () => elements.dialog.close());
  document.querySelector("#cancel-dialog").addEventListener("click", () => elements.dialog.close());
  elements.form.addEventListener("submit", saveMeal);
  elements.search.addEventListener("input", renderMeals);
  elements.language.addEventListener("change", (event) => setLanguage(event.target.value));
  elements.generateWeek.addEventListener("click", generateWeek);
  document.querySelector("#previous-week").addEventListener("click", async () => {
    state.weekStart = addDays(state.weekStart, -7);
    await loadWeek();
  });
  document.querySelector("#next-week").addEventListener("click", async () => {
    state.weekStart = addDays(state.weekStart, 7);
    await loadWeek();
  });
  document.querySelector("#current-week").addEventListener("click", async () => {
    state.weekStart = mondayFor(new Date());
    await loadWeek();
  });
}

async function start() {
  bindEvents();
  try {
    const settings = await api("settings");
    const preferred = localStorage.getItem("meal-planner-language") || settings.language;
    await setLanguage(preferred);
    [state.meals, state.plan] = await Promise.all([
      api("meals"),
      api(`plans/${dateKey(state.weekStart)}`),
    ]);
    renderMeals();
    renderWeek();
  } catch (error) {
    console.error(error);
    if (!Object.keys(state.messages).length) await setLanguage("en");
    showToast(t("status.error"));
  }
}

start();
