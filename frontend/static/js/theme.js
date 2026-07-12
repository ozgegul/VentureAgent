const themeButton = document.getElementById("theme-toggle");
const themeIcon = document.getElementById("theme-toggle-icon");
const storedTheme = localStorage.getItem("ventureagent-theme");
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    if (themeIcon) {
        themeIcon.textContent = theme === "dark" ? "Light" : "Dark";
    }
}

applyTheme(storedTheme || (prefersDark ? "dark" : "light"));

if (themeButton) {
    themeButton.addEventListener("click", () => {
        const currentTheme = document.documentElement.dataset.theme || "light";
        const nextTheme = currentTheme === "dark" ? "light" : "dark";
        localStorage.setItem("ventureagent-theme", nextTheme);
        applyTheme(nextTheme);
    });
}
