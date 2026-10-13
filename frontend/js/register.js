(async function () {
  const existing = await fetchCurrentUser();
  if (existing) {
    window.location.href = "index.html";
    return;
  }

  const form = document.getElementById("register-form");
  const summary = document.getElementById("register-error");
  const button = document.getElementById("register-button");
  const fields = ["username", "email", "password", "confirm"];

  function clearErrors() {
    fields.forEach((field) => {
      const input = document.getElementById("register-" + field);
      const error = document.getElementById("register-" + field + "-error");
      if (input) input.classList.remove("border-red-500");
      if (error) {
        error.textContent = "";
        error.classList.add("hidden");
      }
    });
    summary.classList.add("hidden");
  }

  function showFieldErrors(errors) {
    const messages = [];
    Object.entries(errors).forEach(([field, message]) => {
      const input = document.getElementById("register-" + field);
      const error = document.getElementById("register-" + field + "-error");
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

    const password = document.getElementById("register-password").value;
    const confirm = document.getElementById("register-confirm").value;

    if (password !== confirm) {
      showFieldErrors({ confirm: "Passwords do not match." });
      showToast("Passwords do not match.", "error");
      return;
    }

    button.disabled = true;
    button.textContent = "Creating account...";

    try {
      const user = await apiRequest("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          username: document.getElementById("register-username").value.trim(),
          email: document.getElementById("register-email").value.trim(),
          password,
        }),
      });

      CURRENT_USER = user;
      showToast("Account created. Welcome, " + user.username + "!", "success");
      window.setTimeout(() => {
        window.location.href = "index.html";
      }, 400);
    } catch (error) {
      if (error.errors && Object.keys(error.errors).length) {
        showFieldErrors(error.errors);
      }
      showToast(error.message, "error");
      button.disabled = false;
      button.textContent = "Create account";
    }
  });
})();
