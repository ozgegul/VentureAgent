// VentureAgent - ana sayfa cockpit paneli: alttaki sekmelere tıklayınca üstteki
// görünüm (skor halkası / modül dağılımı / aktivite) değişir, bar'lar animasyonla dolar.

function resetBars(view) {
    view.querySelectorAll(".bar-chart-h-fill[data-target-width]").forEach((el) => {
        el.style.width = "0%";
    });
    view.querySelectorAll(".bar-chart-v-bar[data-target-height]").forEach((el) => {
        el.style.height = "0%";
    });
}

function animateBars(view) {
    // Bir sonraki frame'e ertelemezsek tarayıcı 0 -> hedef geçişini animasyon
    // olarak değil, doğrudan son hal olarak uygular.
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            view.querySelectorAll(".bar-chart-h-fill[data-target-width]").forEach((el) => {
                el.style.width = `${el.getAttribute("data-target-width")}%`;
            });
            view.querySelectorAll(".bar-chart-v-bar[data-target-height]").forEach((el) => {
                el.style.height = `${el.getAttribute("data-target-height")}%`;
            });
        });
    });
}

const cockpitTabs = document.querySelectorAll(".cockpit-tab[data-view-target]");
const statusDots = document.querySelectorAll(".status-dot");

function syncStatusDot(tab) {
    const index = Array.from(cockpitTabs).indexOf(tab);
    statusDots.forEach((dot, i) => dot.classList.toggle("is-active", i === index));
}

cockpitTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
        if (tab.classList.contains("is-active")) return;

        const targetView = document.getElementById(tab.getAttribute("data-view-target"));
        if (!targetView) return;

        document.querySelectorAll(".cockpit-view").forEach((view) => view.classList.remove("is-active"));
        cockpitTabs.forEach((t) => {
            t.classList.remove("is-active");
            t.setAttribute("aria-pressed", "false");
        });

        targetView.classList.add("is-active");
        tab.classList.add("is-active");
        tab.setAttribute("aria-pressed", "true");
        syncStatusDot(tab);

        resetBars(targetView);
        animateBars(targetView);
    });
});

const initialCockpitView = document.querySelector(".cockpit-view.is-active");
if (initialCockpitView) {
    resetBars(initialCockpitView);
    animateBars(initialCockpitView);
}
