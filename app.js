(function () {
  "use strict";

  var STORAGE_KEY = "daily-tasks";
  var CATEGORIES = ["work", "personal", "study"];
  var CATEGORY_LABELS = { work: "업무", personal: "개인", study: "공부" };

  var tasks = [];
  var currentFilter = "all";

  // ---------- Storage ----------

  function loadTasks() {
    var raw;
    try {
      raw = localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return [];
    }
    if (!raw) return [];
    try {
      var parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  function saveTasks() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
    } catch (e) {
      // localStorage unavailable (private mode, quota, etc.) - fail silently
    }
  }

  // ---------- Data CRUD ----------

  function generateId() {
    return Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 9);
  }

  function addTask(text, category) {
    var trimmed = (text || "").trim();
    if (!trimmed) return null;
    if (CATEGORIES.indexOf(category) === -1) category = "work";

    var task = {
      id: generateId(),
      text: trimmed,
      category: category,
      completed: false,
      createdAt: new Date().toISOString()
    };
    tasks.push(task);
    saveTasks();
    return task;
  }

  function updateTask(id, changes) {
    var task = tasks.find(function (t) {
      return t.id === id;
    });
    if (!task) return null;

    if (typeof changes.text === "string") {
      var trimmed = changes.text.trim();
      if (!trimmed) return null;
      task.text = trimmed;
    }
    if (changes.category && CATEGORIES.indexOf(changes.category) !== -1) {
      task.category = changes.category;
    }
    saveTasks();
    return task;
  }

  function deleteTask(id) {
    var index = tasks.findIndex(function (t) {
      return t.id === id;
    });
    if (index === -1) return false;
    tasks.splice(index, 1);
    saveTasks();
    return true;
  }

  function toggleComplete(id) {
    var task = tasks.find(function (t) {
      return t.id === id;
    });
    if (!task) return null;
    task.completed = !task.completed;
    saveTasks();
    return task;
  }

  // ---------- Rendering ----------

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function updateFilterCounts() {
    var counts = { all: tasks.length, work: 0, personal: 0, study: 0 };
    tasks.forEach(function (t) {
      if (counts[t.category] !== undefined) counts[t.category]++;
    });
    CATEGORIES.concat("all").forEach(function (key) {
      var el = document.getElementById("count-" + key);
      if (el) el.textContent = counts[key];
    });
  }

  function updateFilterButtons() {
    document.querySelectorAll(".filter-btn").forEach(function (btn) {
      var isActive = btn.dataset.filter === currentFilter;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  }

  function getFilteredTasks() {
    if (currentFilter === "all") return tasks;
    return tasks.filter(function (t) {
      return t.category === currentFilter;
    });
  }

  function renderTasks() {
    var listEl = document.getElementById("taskList");
    var emptyEl = document.getElementById("emptyState");
    var filtered = getFilteredTasks();

    listEl.innerHTML = "";

    if (filtered.length === 0) {
      emptyEl.hidden = false;
    } else {
      emptyEl.hidden = true;
      filtered.forEach(function (task) {
        listEl.appendChild(buildTaskItem(task));
      });
    }

    updateFilterCounts();
    updateFilterButtons();
  }

  function buildTaskItem(task) {
    var li = document.createElement("li");
    li.className = "task-item" + (task.completed ? " completed" : "");
    li.dataset.id = task.id;

    var checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "task-checkbox";
    checkbox.checked = task.completed;
    checkbox.id = "check-" + task.id;
    checkbox.setAttribute("aria-label", (task.completed ? "완료 취소: " : "완료 처리: ") + task.text);
    checkbox.addEventListener("change", function () {
      toggleComplete(task.id);
      renderTasks();
    });

    var text = document.createElement("span");
    text.className = "task-text";
    text.textContent = task.text;
    text.addEventListener("dblclick", function (e) {
      e.preventDefault();
      enterEditMode(li, task);
    });

    var category = document.createElement("span");
    category.className = "task-category " + task.category;
    category.textContent = CATEGORY_LABELS[task.category] || task.category;

    var actions = document.createElement("div");
    actions.className = "task-actions";

    var editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "edit-btn";
    editBtn.textContent = "수정";
    editBtn.setAttribute("aria-label", "수정: " + task.text);
    editBtn.addEventListener("click", function () {
      enterEditMode(li, task);
    });

    var deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "delete-btn";
    deleteBtn.textContent = "삭제";
    deleteBtn.setAttribute("aria-label", "삭제: " + task.text);
    deleteBtn.addEventListener("click", function () {
      if (window.confirm("정말 삭제하시겠습니까?")) {
        deleteTask(task.id);
        renderTasks();
      }
    });

    actions.appendChild(editBtn);
    actions.appendChild(deleteBtn);

    li.appendChild(checkbox);
    li.appendChild(text);
    li.appendChild(category);
    li.appendChild(actions);

    return li;
  }

  function enterEditMode(li, task) {
    li.classList.add("editing");
    li.innerHTML = "";

    var textInput = document.createElement("input");
    textInput.type = "text";
    textInput.className = "edit-text-input";
    textInput.value = task.text;
    textInput.setAttribute("aria-label", "할 일 내용 수정");

    var categorySelect = document.createElement("select");
    categorySelect.className = "edit-category-select";
    categorySelect.setAttribute("aria-label", "카테고리 수정");
    CATEGORIES.forEach(function (cat) {
      var opt = document.createElement("option");
      opt.value = cat;
      opt.textContent = CATEGORY_LABELS[cat];
      if (cat === task.category) opt.selected = true;
      categorySelect.appendChild(opt);
    });

    var actions = document.createElement("div");
    actions.className = "task-actions";

    var saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.textContent = "저장";
    saveBtn.setAttribute("aria-label", "수정 내용 저장");

    var cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.textContent = "취소";
    cancelBtn.setAttribute("aria-label", "수정 취소");

    function commit() {
      var newText = textInput.value.trim();
      if (!newText) {
        renderTasks();
        return;
      }
      updateTask(task.id, { text: newText, category: categorySelect.value });
      renderTasks();
    }

    saveBtn.addEventListener("click", commit);
    cancelBtn.addEventListener("click", function () {
      renderTasks();
    });
    textInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        commit();
      } else if (e.key === "Escape") {
        renderTasks();
      }
    });

    actions.appendChild(saveBtn);
    actions.appendChild(cancelBtn);

    li.appendChild(textInput);
    li.appendChild(categorySelect);
    li.appendChild(actions);

    textInput.focus();
    textInput.select();
  }

  // ---------- Header date ----------

  function renderTodayDate() {
    var el = document.getElementById("todayDate");
    if (!el) return;
    var today = new Date();
    var days = ["일", "월", "화", "수", "목", "금", "토"];
    var formatted =
      today.getFullYear() +
      "년 " +
      (today.getMonth() + 1) +
      "월 " +
      today.getDate() +
      "일 (" +
      days[today.getDay()] +
      ")";
    el.textContent = formatted;
  }

  // ---------- Event wiring ----------

  function handleAddSubmit(e) {
    e.preventDefault();
    var input = document.getElementById("taskInput");
    var select = document.getElementById("categorySelect");
    var errorEl = document.getElementById("inputError");

    var value = input.value.trim();
    if (!value) {
      errorEl.textContent = "할 일을 입력해주세요.";
      input.focus();
      return;
    }
    errorEl.textContent = "";

    addTask(value, select.value);
    input.value = "";
    input.focus();
    renderTasks();
  }

  function handleFilterClick(e) {
    var btn = e.target.closest(".filter-btn");
    if (!btn) return;
    currentFilter = btn.dataset.filter;
    renderTasks();
  }

  function init() {
    tasks = loadTasks();
    renderTodayDate();

    var form = document.getElementById("taskForm");
    form.addEventListener("submit", handleAddSubmit);

    var filterArea = document.getElementById("filterArea");
    filterArea.addEventListener("click", handleFilterClick);

    renderTasks();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
