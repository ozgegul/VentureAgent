// VentureAgent - ana sayfa cockpit panelindeki istatistiklere tıklayınca ilgili grafiği aç/kapat

document.querySelectorAll(".cockpit-stat[data-chart-target]").forEach((trigger) => {
    trigger.addEventListener("click", () => {
        const target = document.getElementById(trigger.getAttribute("data-chart-target"));
        if (!target) return;

        const wasOpen = !target.hidden;

        document.querySelectorAll(".cockpit-chart").forEach((panel) => {
            panel.hidden = true;
        });
        document.querySelectorAll(".cockpit-stat[data-chart-target]").forEach((btn) => {
            btn.setAttribute("aria-expanded", "false");
        });

        if (!wasOpen) {
            target.hidden = false;
            trigger.setAttribute("aria-expanded", "true");
        }
    });
});

document.querySelectorAll(".cockpit-chart-close").forEach((closeBtn) => {
    closeBtn.addEventListener("click", () => {
        const panel = closeBtn.closest(".cockpit-chart");
        if (!panel) return;
        panel.hidden = true;
        const trigger = document.querySelector(`[data-chart-target="${panel.id}"]`);
        if (trigger) trigger.setAttribute("aria-expanded", "false");
    });
});
