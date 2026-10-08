(function () {
  const reportsBody = document.getElementById("reports-body");
  const tableWrapper = document.getElementById("table-wrapper");
  const emptyState = document.getElementById("empty-state");
  const reportsCount = document.getElementById("reports-count");

  function statusOptions(currentStatus) {
    return Object.entries(STATUS_LABELS)
      .map(
        ([value, label]) =>
          '<option value="' +
          value +
          '"' +
          (value === currentStatus ? " selected" : "") +
          ">" +
          label +
          "</option>"
      )
      .join("");
  }

  function rowHtml(report) {
    return (
      '<tr data-testid="report-row" data-id="' +
      report.id +
      '" class="border-b border-slate-100 hover:bg-slate-50">' +
      '<td data-testid="report-id" class="px-4 py-3 text-sm font-semibold text-water-700">#' +
      report.id +
      "</td>" +
      '<td class="px-4 py-3 text-sm">' +
      '<div class="font-medium">' +
      escapeHtml(report.full_name) +
      "</div>" +
      '<div class="text-xs text-slate-500">' +
      escapeHtml(report.email) +
      "</div>" +
      "</td>" +
      '<td class="px-4 py-3 text-sm">' +
      "<div>" +
      escapeHtml(report.area) +
      "</div>" +
      '<div class="text-xs text-slate-500">' +
      escapeHtml(report.address) +
      "</div>" +
      "</td>" +
      '<td class="px-4 py-3 text-sm">' +
      '<span data-testid="severity-badge" class="rounded-full px-2 py-1 text-xs font-semibold ' +
      (SEVERITY_BADGE_CLASSES[report.severity] || "") +
      '">' +
      escapeHtml(report.severity) +
      "</span>" +
      "</td>" +
      '<td class="px-4 py-3 text-sm">' +
      '<span data-testid="status-badge" data-status="' +
      report.status +
      '" class="status-badge rounded-full px-2 py-1 text-xs font-semibold ' +
      (STATUS_BADGE_CLASSES[report.status] || "") +
      '">' +
      (STATUS_LABELS[report.status] || escapeHtml(report.status)) +
      "</span>" +
      "</td>" +
      '<td class="px-4 py-3 text-sm">' +
      '<select data-testid="status-select" data-id="' +
      report.id +
      '" data-previous="' +
      report.status +
      '" class="status-select rounded border border-slate-300 bg-white px-2 py-1 text-sm focus:border-water-500 focus:outline-none">' +
      statusOptions(report.status) +
      "</select>" +
      "</td>" +
      '<td data-testid="report-date" class="px-4 py-3 text-sm text-slate-500">' +
      escapeHtml(report.created_at) +
      "</td>" +
      '<td class="px-4 py-3 text-sm">' +
      '<button type="button" data-testid="delete-report" data-id="' +
      report.id +
      '" class="delete-report rounded bg-red-50 px-3 py-1 text-xs font-semibold text-red-600 hover:bg-red-100">Delete</button>' +
      "</td>" +
      "</tr>"
    );
  }

  function updateCount(count) {
    reportsCount.textContent = count + " report(s)";
  }

  function renderReports(reports) {
    updateCount(reports.length);
    if (!reports.length) {
      reportsBody.innerHTML = "";
      tableWrapper.classList.add("hidden");
      emptyState.classList.remove("hidden");
      return;
    }
    emptyState.classList.add("hidden");
    tableWrapper.classList.remove("hidden");
    reportsBody.innerHTML = reports.map(rowHtml).join("");
  }

  async function loadReports() {
    try {
      const reports = await API.listReports({
        status: document.getElementById("filter-status").value,
        area: document.getElementById("filter-area").value,
        q: document.getElementById("search-reports").value.trim(),
      });
      renderReports(reports);
    } catch (error) {
      showToast(error.message, "error");
    }
  }

  document.getElementById("filter-status").addEventListener("change", loadReports);
  document.getElementById("filter-area").addEventListener("change", loadReports);
  document.getElementById("refresh-reports").addEventListener("click", () => {
    loadReports();
    showToast("Report list refreshed.", "info");
  });
  document.getElementById("search-button").addEventListener("click", loadReports);
  document.getElementById("search-reports").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loadReports();
    }
  });

  reportsBody.addEventListener("change", async (event) => {
    const select = event.target.closest(".status-select");
    if (!select) return;

    const id = select.dataset.id;
    const row = select.closest("tr");
    const badge = row.querySelector(".status-badge");
    const previousStatus = select.dataset.previous || "submitted";
    const nextStatus = select.value;

    try {
      const updated = await API.updateReportStatus(id, nextStatus);
      badge.textContent = STATUS_LABELS[updated.status] || updated.status;
      badge.dataset.status = updated.status;
      badge.className =
        "status-badge rounded-full px-2 py-1 text-xs font-semibold " +
        (STATUS_BADGE_CLASSES[updated.status] || "");
      select.dataset.previous = updated.status;
      showToast(
        "Report #" + id + " marked as " + (STATUS_LABELS[updated.status] || updated.status) + ".",
        "success"
      );
    } catch (error) {
      select.value = previousStatus;
      showToast(error.message, "error");
    }
  });

  reportsBody.addEventListener("click", async (event) => {
    const button = event.target.closest(".delete-report");
    if (!button) return;

    const id = button.dataset.id;
    const confirmed = window.confirm(
      "Are you sure you want to delete report #" + id + "?"
    );
    if (!confirmed) return;

    try {
      await API.deleteReport(id);
      const row = button.closest("tr");
      row.remove();
      showToast("Report #" + id + " deleted.", "success");

      const remaining = reportsBody.querySelectorAll("tr").length;
      updateCount(remaining);
      if (!remaining) {
        tableWrapper.classList.add("hidden");
        emptyState.classList.remove("hidden");
      }
    } catch (error) {
      showToast(error.message, "error");
    }
  });

  loadReports();
})();
