(async function () {
  const message = document.getElementById("login-message");
  const params = new URLSearchParams(window.location.search);

  if (params.has("error")) {
    message.hidden = false;
    message.textContent = "用户名或密码不正确。";
    message.className = "notice notice-error";
  } else if (params.has("logout")) {
    message.hidden = false;
    message.textContent = "已安全退出。";
    message.className = "notice notice-success";
  }

  try {
    const response = await fetch("/api/csrf", { credentials: "same-origin" });
    if (!response.ok) throw new Error("csrf");
    const data = await response.json();
    document.getElementById("csrf-field").name = data.parameter_name || "_csrf";
    document.getElementById("csrf-field").value = data.token;
  } catch (_) {
    message.hidden = false;
    message.textContent = "暂时无法初始化登录，请刷新页面重试。";
    message.className = "notice notice-error";
    document.getElementById("login-form").querySelector("button").disabled = true;
  }
})();
