async function refreshLogs() {
  const logBox = document.getElementById("logbox");
  const status = document.getElementById("logstatus");

  if (!logBox) {
    return;
  }

  try {
    const response = await fetch("/api/logs?lines=300&_=" + Date.now());
    const data = await response.json();
    logBox.textContent = data.text || "";
    logBox.scrollTop = logBox.scrollHeight;

    if (status) {
      status.textContent = "Letzte Aktualisierung: " + data.refreshed_at;
    }
  } catch (error) {
    logBox.textContent = "Logdaten konnten nicht geladen werden: " + error;
  }
}

window.addEventListener("load", function () {
  const logBox = document.getElementById("logbox");
  if (logBox) {
    refreshLogs();
    window.setInterval(refreshLogs, 2000);
  }
});
