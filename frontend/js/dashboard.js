(function () {
  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  }

  function barHtml(label, count, max, badgeClass) {
    const percentage = Math.round((count / Math.max(max, 1)) * 100);
    const labelHtml = badgeClass
      ? '<span class="rounded-full px-2 py-0.5 text-xs font-semibold ' +
        badgeClass +
        '">' +
        escapeHtml(label) +
        "</span>"
      : escapeHtml(label);
    return (
      '<div data-testid="breakdown-row" class="mb-3">' +
      '<div class="mb-1 flex items-center justify-between text-sm">' +
      "<span>" +
      labelHtml +
      "</span>" +
      '<span class="font-semibold">' +
      count +
      "</span>" +
      "</div>" +
      '<div class="h-2 rounded bg-slate-200">' +
      '<div class="h-2 rounded bg-water-500 transition-all" style="width:' +
      percentage +
      '%"></div>' +
      "</div>" +
      "</div>"
    );
  }

  function renderStats(stats) {
    setText("stat-total", stats.total);
    setText("stat-submitted", stats.by_status.submitted);
    setText("stat-in-progress", stats.by_status.in_progress);
    setText("stat-resolved", stats.by_status.resolved);
    setText("stat-critical-open", stats.critical_open);
    setText("last-updated", "Last updated: " + stats.last_updated + " UTC");

    const statusMax = Math.max(1, ...Object.values(stats.by_status));
    document.getElementById("status-breakdown").innerHTML = Object.entries(
      stats.by_status
    )
      .map(([status, count]) =>
        barHtml(
          STATUS_LABELS[status] || status,
          count,
          statusMax,
          STATUS_BADGE_CLASSES[status]
        )
      )
      .join("");

    const areaMax = Math.max(1, ...stats.by_area.map((item) => item.count));
    document.getElementById("area-breakdown").innerHTML = stats.by_area.length
      ? stats.by_area
          .map((item) => barHtml(item.area, item.count, areaMax, ""))
          .join("")
      : '<p class="text-sm text-slate-400">No reports yet.</p>';

    const recentList = document.getElementById("recent-reports");
    if (!stats.recent.length) {
      recentList.innerHTML =
        '<li data-testid="recent-item" class="py-3 text-sm text-slate-400">No reports yet.</li>';
      return;
    }
    recentList.innerHTML = stats.recent
      .map(
        (report) =>
          '<li data-testid="recent-item" class="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">' +
          "<div>" +
          '<span class="font-semibold text-water-700">#' +
          report.id +
          "</span> " +
          escapeHtml(report.full_name) +
          ' <span class="text-slate-400">&middot;</span> ' +
          escapeHtml(report.area) +
          "</div>" +
          '<div class="flex items-center gap-2">' +
          '<span data-testid="recent-severity" class="rounded-full px-2 py-1 text-xs font-semibold ' +
          (SEVERITY_BADGE_CLASSES[report.severity] || "") +
          '">' +
          escapeHtml(report.severity) +
          "</span>" +
          '<span data-testid="recent-status" class="rounded-full px-2 py-1 text-xs font-semibold ' +
          (STATUS_BADGE_CLASSES[report.status] || "") +
          '">' +
          (STATUS_LABELS[report.status] || escapeHtml(report.status)) +
          "</span>" +
          "</div>" +
          "</li>"
      )
      .join("");
  }

  async function loadDashboard() {
    try {
      const stats = await API.getStats();
      renderStats(stats);
    } catch (error) {
      showToast(error.message, "error");
    }
  }

  document.getElementById("refresh-dashboard").addEventListener("click", () => {
    loadDashboard();
    showToast("Dashboard refreshed.", "info");
  });

  loadDashboard();
})();
