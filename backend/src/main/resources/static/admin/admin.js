(function () {
  const state = {
    status: "PENDING",
    items: [],
    selected: null,
    csrfToken: null,
    csrfHeader: null,
    selectedIds: new Set(),
  };

  const listEl = document.getElementById("review-list");
  const detailCard = document.getElementById("detail-card");
  const emptyState = document.getElementById("empty-state");
  const messageEl = document.getElementById("action-message");

  function escapeText(value) {
    return String(value == null ? "" : value);
  }

  async function api(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      ...options,
    });
    const type = response.headers.get("content-type") || "";
    if (!type.includes("application/json")) {
      window.location.href = "/admin/login.html";
      throw new Error("session expired");
    }
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || data.error || "请求失败");
    }
    return data;
  }

  async function loadSession() {
    const data = await api("/api/admin/session");
    state.csrfToken = readCookie("XSRF-TOKEN");
    state.csrfHeader = data.csrf_header;
    if (!state.csrfToken) throw new Error("CSRF token unavailable");
    document.getElementById("session-user").textContent = data.username;
  }

  function readCookie(name) {
    const prefix = name + "=";
    const item = document.cookie
      .split(";")
      .map(value => value.trim())
      .find(value => value.startsWith(prefix));
    return item ? decodeURIComponent(item.slice(prefix.length)) : null;
  }

  async function loadCounts() {
    const statuses = ["PENDING", "APPROVED", "REJECTED"];
    const results = await Promise.all(
      statuses.map(status => api("/api/admin/reviews?status=" + status))
    );
    results.forEach((items, index) => {
      const key = statuses[index].toLowerCase();
      document.getElementById("count-" + key).textContent = items.length;
      if (statuses[index] === state.status) state.items = items;
    });
  }

  function renderList() {
    listEl.innerHTML = "";
    state.selectedIds = new Set(
      [...state.selectedIds].filter(id => state.items.some(item => item.id === id))
    );
    updateBulkUi();
    if (!state.items.length) {
      listEl.innerHTML = '<div class="empty-state"><strong>这里还没有记录</strong><span>切换其它状态看看。</span></div>';
      showEmpty();
      return;
    }

    state.items.forEach(item => {
      const row = document.createElement("div");
      row.className = "review-row";
      if (state.status === "PENDING") {
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "review-check";
        checkbox.checked = state.selectedIds.has(item.id);
        checkbox.setAttribute("aria-label", "选择 " + item.name);
        checkbox.addEventListener("change", () => {
          if (checkbox.checked) state.selectedIds.add(item.id);
          else state.selectedIds.delete(item.id);
          updateBulkUi();
        });
        row.appendChild(checkbox);
      }

      const button = document.createElement("button");
      button.type = "button";
      button.className = "review-item" + (state.selected && state.selected.id === item.id ? " is-active" : "");
      button.innerHTML =
        "<strong></strong><div class=\"review-meta\"><span></span><span></span></div>";
      button.querySelector("strong").textContent = item.name;
      const spans = button.querySelectorAll("span");
      spans[0].textContent = item.source_name || item.source || "未知来源";
      spans[1].textContent = item.ai_confidence ? "AI " + item.ai_confidence : item.review_status;
      button.addEventListener("click", () => selectItem(item.id));
      row.appendChild(button);
      listEl.appendChild(row);
    });
  }

  function updateBulkUi() {
    const toolbar = document.getElementById("bulk-toolbar");
    toolbar.hidden = state.status !== "PENDING";
    document.getElementById("selected-count").textContent = "已选 " + state.selectedIds.size;
    document.getElementById("bulk-approve-button").disabled = state.selectedIds.size === 0;
    const highCount = state.items.filter(
      item => item.review_status === "PENDING" && item.ai_confidence === "HIGH"
    ).length;
    document.getElementById("approve-high-button").textContent =
      highCount ? "一键批准 HIGH (" + highCount + ")" : "一键批准 HIGH";
    document.getElementById("approve-high-button").disabled = highCount === 0;
    document.getElementById("select-all-button").textContent =
      state.items.length > 0 && state.selectedIds.size === state.items.length ? "取消全选" : "全选";
  }

  function showEmpty() {
    state.selected = null;
    detailCard.hidden = true;
    emptyState.hidden = false;
  }

  async function selectItem(id) {
    try {
      state.selected = await api("/api/admin/reviews/" + encodeURIComponent(id));
      renderList();
      renderDetail();
    } catch (error) {
      showMessage(error.message, true);
    }
  }

  function renderDetail() {
    const item = state.selected;
    if (!item) return showEmpty();

    emptyState.hidden = true;
    detailCard.hidden = false;
    document.getElementById("detail-title").textContent = item.name;
    document.getElementById("detail-source").textContent = item.source_name || item.source || "未知来源";
    document.getElementById("detail-status").textContent = item.review_status;
    document.getElementById("raw-json").textContent = JSON.stringify(item.raw_data, null, 2);

    const link = document.getElementById("detail-link");
    if (item.link) {
      link.hidden = false;
      link.href = item.link;
    } else {
      link.hidden = true;
      link.removeAttribute("href");
    }

    const raw = item.raw_data || {};
    setField("field-name", raw.name || item.name);
    setField("field-kind", raw.kind);
    setField("field-level", raw.level);
    setField("field-organizer", raw.organizer);
    setField("field-link", raw.link || item.link);
    setField("field-description", raw.description);
    setField("review-note", item.review_note);

    const ai = [];
    if (item.ai_verdict) ai.push("结论：" + item.ai_verdict);
    if (item.ai_confidence) ai.push("置信度：" + item.ai_confidence);
    if (item.ai_reason) ai.push("原因：" + item.ai_reason);
    document.getElementById("ai-summary").textContent = ai.length ? ai.join(" · ") : "暂无 AI 审核结果";

    const editable = item.review_status === "PENDING";
    ["field-name", "field-kind", "field-level", "field-organizer", "field-link", "field-description", "review-note"]
      .forEach(id => document.getElementById(id).disabled = !editable);
    document.getElementById("review-actions").hidden = !editable;
    hideMessage();
  }

  function setField(id, value) {
    document.getElementById(id).value = value == null ? "" : value;
  }

  function editedData() {
    return {
      name: document.getElementById("field-name").value.trim(),
      kind: document.getElementById("field-kind").value.trim(),
      level: document.getElementById("field-level").value.trim(),
      organizer: document.getElementById("field-organizer").value.trim(),
      link: document.getElementById("field-link").value.trim(),
      description: document.getElementById("field-description").value.trim(),
    };
  }

  async function review(action) {
    if (!state.selected) return;
    const button = action === "approve"
      ? document.getElementById("approve-button")
      : document.getElementById("reject-button");
    button.disabled = true;
    try {
      const body = {
        note: document.getElementById("review-note").value.trim(),
      };
      if (action === "approve") body.data = editedData();

      await api(
        "/api/admin/reviews/" + encodeURIComponent(state.selected.id) + "/" + action,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            [state.csrfHeader]: state.csrfToken,
          },
          body: JSON.stringify(body),
        }
      );
      showMessage(action === "approve" ? "已通过并写入正式竞赛库。" : "已拒绝该候选。", false);
      await loadCounts();
      renderList();
      showEmpty();
    } catch (error) {
      showMessage(error.message, true);
    } finally {
      button.disabled = false;
    }
  }

  async function bulkApprove(ids, label) {
    const uniqueIds = [...new Set(ids)];
    if (!uniqueIds.length) return;
    if (!window.confirm("确认" + label + " " + uniqueIds.length + " 条候选？")) return;

    const buttons = [
      document.getElementById("bulk-approve-button"),
      document.getElementById("approve-high-button"),
      document.getElementById("select-all-button"),
    ];
    buttons.forEach(button => button.disabled = true);
    try {
      const result = await api("/api/admin/reviews/bulk/approve", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          [state.csrfHeader]: state.csrfToken,
        },
        body: JSON.stringify({
          ids: uniqueIds,
          note: label,
        }),
      });
      state.selectedIds.clear();
      showMessage("已批量通过 " + result.approved + " 条，并写入正式竞赛库。", false);
      await loadCounts();
      renderList();
      showEmpty();
    } catch (error) {
      showMessage(error.message, true);
    } finally {
      updateBulkUi();
    }
  }

  function showMessage(text, isError) {
    messageEl.hidden = false;
    messageEl.textContent = escapeText(text);
    messageEl.className = "notice " + (isError ? "notice-error" : "notice-success");
  }

  function hideMessage() {
    messageEl.hidden = true;
  }

  async function refresh() {
    try {
      await loadCounts();
      renderList();
    } catch (error) {
      showMessage(error.message, true);
    }
  }

  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", async () => {
      state.status = tab.dataset.status;
      state.selectedIds.clear();
      document.querySelectorAll(".tab").forEach(x => x.classList.toggle("is-active", x === tab));
      showEmpty();
      await refresh();
    });
  });

  document.getElementById("refresh-button").addEventListener("click", refresh);
  document.getElementById("select-all-button").addEventListener("click", () => {
    if (state.selectedIds.size === state.items.length) {
      state.selectedIds.clear();
    } else {
      state.selectedIds = new Set(state.items.map(item => item.id));
    }
    renderList();
  });
  document.getElementById("bulk-approve-button").addEventListener("click", () => {
    bulkApprove([...state.selectedIds], "批量人工通过");
  });
  document.getElementById("approve-high-button").addEventListener("click", () => {
    const highIds = state.items
      .filter(item => item.review_status === "PENDING" && item.ai_confidence === "HIGH")
      .map(item => item.id);
    bulkApprove(highIds, "人工确认 DeepSeek HIGH 建议");
  });
  document.getElementById("approve-button").addEventListener("click", () => review("approve"));
  document.getElementById("reject-button").addEventListener("click", () => review("reject"));
  document.getElementById("logout-button").addEventListener("click", async () => {
    try {
      await fetch("/admin/logout", {
        method: "POST",
        credentials: "same-origin",
        headers: { [state.csrfHeader]: state.csrfToken },
      });
    } finally {
      window.location.href = "/admin/login.html?logout";
    }
  });

  (async function init() {
    try {
      await loadSession();
      await refresh();
    } catch (_) {
      window.location.href = "/admin/login.html";
    }
  })();
})();
