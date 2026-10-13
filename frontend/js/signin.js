(async function () {
  const existing = await fetchCurrentUser();
  if (existing) {
    window.location.href = "index.html";
    return;
  }

  const form = document.getElementById("signin-form");
  const errorBox = document.getElementById("signin-error");
  const button = document.getElementById("signin-button");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.classList.add("hidden");
    button.disabled = true;
    button.textContent = "Signing in...";

    try {
      const user = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          username: document.getElementById("signin-username").value.trim(),
          password: document.getElementById("signin-password").value,
        }),
      });

      CURRENT_USER = user;
      showToast("Welcome back, " + user.username + "!", "success");
      window.setTimeout(() => {
        window.location.href = "index.html";
      }, 400);
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.classList.remove("hidden");
      showToast(error.message, "error");
      button.disabled = false;
      button.textContent = "Sign in";
    }
  });
})();
