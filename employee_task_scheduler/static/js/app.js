function updateClock() {
  const now = new Date();
  const clockEl = document.getElementById("clockNow");
  const dateEl = document.getElementById("dateNow");
  if (clockEl) {
    clockEl.textContent = now.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  if (dateEl) {
    const days = ["Chu nhat","Thu hai","Thu ba","Thu tu","Thu nam","Thu sau","Thu bay"];
    const d = String(now.getDate()).padStart(2,'0');
    const m = String(now.getMonth()+1).padStart(2,'0');
    dateEl.textContent = `${days[now.getDay()]}, ${d}/${m}/${now.getFullYear()}`;
  }
}
setInterval(updateClock, 1000);
updateClock();

const hamburgerBtn = document.getElementById("hamburgerBtn");
if (hamburgerBtn) {
  hamburgerBtn.addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("open");
  });
}
