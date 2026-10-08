(function () {
  const form = document.getElementById("report-form");
  const fieldIds = [
    "full-name",
    "email",
    "phone",
    "address",
    "area",
    "severity",
    "description",
  ];

  function clearErrors() {
    fieldIds.forEach((id) => {
      const input = document.getElementById(id);
      const error = document.getElementById(id + "-error");
      if (input) input.classList.remove("border-red-500");
      if (error) {
        error.textContent = "";
        error.classList.add("hidden");
      }
    });
    document.getElementById("form-error-summary").classList.add("hidden");
    document.getElementById("success-panel").classList.add("hidden");
  }

  function showFieldErrors(errors) {
    const summary = document.getElementById("form-error-summary");
    const messages = [];

    Object.entries(errors).forEach(([field, message]) => {
      const elementId = field.replace(/_/g, "-");
      const input = document.getElementById(elementId);
      const error = document.getElementById(elementId + "-error");
      if (input) input.classList.add("border-red-500");
      if (error) {
        error.textContent = message;
        error.classList.remove("hidden");
      }
      messages.push(message);
    });

    if (messages.length) {
      summary.textContent =
        "Please fix " + messages.length + " error(s): " + messages.join(" ");
      summary.classList.remove("hidden");
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    const payload = {
      full_name: document.getElementById("full-name").value.trim(),
      email: document.getElementById("email").value.trim(),
      phone: document.getElementById("phone").value.trim(),
      address: document.getElementById("address").value.trim(),
      area: document.getElementById("area").value,
      severity: document.getElementById("severity").value,
      description: document.getElementById("description").value.trim(),
    };

    const submitButton = document.getElementById("submit-report");
    submitButton.disabled = true;
    submitButton.textContent = "Submitting...";

    try {
      const report = await API.createReport(payload);
      form.reset();

      const panel = document.getElementById("success-panel");
      panel.textContent =
        "Thank you! Report #" +
        report.id +
        " was submitted for " +
        report.area +
        ". Track it on the Reports page.";
      panel.classList.remove("hidden");

      showToast("Report #" + report.id + " submitted successfully.", "success");
    } catch (error) {
      if (error.errors && Object.keys(error.errors).length) {
        showFieldErrors(error.errors);
      }
      showToast(error.message, "error");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Submit Report";
    }
  });
})();
