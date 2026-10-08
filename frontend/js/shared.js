const STATUS_LABELS = {
  submitted: "Submitted",
  in_progress: "In Progress",
  resolved: "Resolved",
  rejected: "Rejected",
};

const STATUS_BADGE_CLASSES = {
  submitted: "bg-sky-100 text-sky-800",
  in_progress: "bg-amber-100 text-amber-800",
  resolved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
};

const SEVERITY_BADGE_CLASSES = {
  low: "bg-slate-100 text-slate-700",
  medium: "bg-sky-100 text-sky-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

function escapeHtml(value) {
  return String(value === null || value === undefined ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const styles = {
    success: "border-green-500 bg-green-600",
    error: "border-red-500 bg-red-600",
    warning: "border-amber-500 bg-amber-500",
    info: "border-sky-500 bg-sky-600",
  };

  const toast = document.createElement("div");
  toast.setAttribute("data-testid", "toast");
  toast.setAttribute("data-type", type);
  toast.setAttribute("role", "alert");
  toast.className =
    "pointer-events-auto flex w-full items-start justify-between gap-3 rounded border-l-4 px-4 py-3 text-sm font-medium text-white shadow-lg transition-opacity duration-300 " +
    (styles[type] || styles.info);

  const messageSpan = document.createElement("span");
  messageSpan.setAttribute("data-testid", "toast-message");
  messageSpan.textContent = message;

  const closeButton = document.createElement("button");
  closeButton.setAttribute("type", "button");
  closeButton.setAttribute("data-testid", "toast-close");
  closeButton.setAttribute("aria-label", "Close");
  closeButton.className = "toast-close font-bold leading-none hover:opacity-70";
  closeButton.innerHTML = "&times;";

  toast.appendChild(messageSpan);
  toast.appendChild(closeButton);
  container.appendChild(toast);

  const dismiss = () => {
    toast.classList.add("opacity-0");
    window.setTimeout(() => toast.remove(), 300);
  };

  closeButton.addEventListener("click", dismiss);
  window.setTimeout(dismiss, 4500);
}

async function apiRequest(path, options = {}) {
  const response = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let body = null;
  try {
    body = await response.json();
  } catch (parseError) {
    body = null;
  }

  if (!response.ok) {
    const error = new Error(
      (body && body.message) || "Request failed with status " + response.status
    );
    error.status = response.status;
    error.errors = (body && body.errors) || {};
    throw error;
  }

  return body;
}

const API = {
  createReport: (data) =>
    apiRequest("/reports", { method: "POST", body: JSON.stringify(data) }),

  listReports: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    const queryString = query.toString();
    return apiRequest("/reports" + (queryString ? "?" + queryString : ""));
  },

  updateReportStatus: (id, status) =>
    apiRequest("/reports/" + id, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }),

  deleteReport: (id) =>
    apiRequest("/reports/" + id, { method: "DELETE" }),

  getStats: () => apiRequest("/stats"),
};
