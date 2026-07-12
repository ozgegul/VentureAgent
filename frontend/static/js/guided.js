const steps = [
    {
        key: "idea",
        type: "text",
        question: "Fikrini bir cümleyle anlat. Ne yapmak istiyorsun?",
    },
    {
        key: "problem",
        type: "text",
        question: "Bu fikir hangi problemi çözüyor?",
    },
    {
        key: "target_audience",
        type: "text",
        question: "Bunu ilk kimler kullanır? Hedef kitleni basitçe yaz.",
    },
    {
        key: "sector",
        type: "text",
        question: "Hangi sektöre daha yakın? Bilmiyorsan boş bırakabilirsin.",
        optional: true,
    },
    {
        key: "problem_severity",
        type: "score",
        question: "Bu problem kullanıcı için ne kadar acil?",
        low: "Çok acil değil",
        high: "Çok acil",
    },
    {
        key: "target_audience_clarity",
        type: "score",
        question: "Hedef kitlen ne kadar net?",
        low: "Belirsiz",
        high: "Çok net",
    },
    {
        key: "competition_intensity",
        type: "score",
        question: "Bu alanda rekabet sence ne kadar yoğun?",
        low: "Az rekabet",
        high: "Çok yoğun",
    },
    {
        key: "monetization_clarity",
        type: "score",
        question: "Para kazanma modelin ne kadar net?",
        low: "Belirsiz",
        high: "Çok net",
    },
];

const state = {
    index: 0,
    answers: {},
};

const shell = document.querySelector(".guided-shell");
const chat = document.getElementById("guided-chat");
const form = document.getElementById("guided-form");
const input = document.getElementById("guided-input");
const choiceRow = document.getElementById("guided-choice-row");
const progressLabel = document.getElementById("guided-progress-label");
const progressFill = document.getElementById("guided-progress-fill");
const result = document.getElementById("guided-result");

function addBubble(text, role = "assistant") {
    const bubble = document.createElement("div");
    bubble.className = `guided-bubble guided-${role}`;
    bubble.textContent = text;
    chat.appendChild(bubble);
    chat.scrollTop = chat.scrollHeight;
}

function updateProgress() {
    const current = Math.min(state.index + 1, steps.length);
    progressLabel.textContent = `${current} / ${steps.length}`;
    progressFill.style.width = `${(current / steps.length) * 100}%`;
}

function renderStep() {
    updateProgress();
    const step = steps[state.index];
    addBubble(step.question);

    if (step.type === "score") {
        form.hidden = true;
        choiceRow.hidden = false;
        choiceRow.innerHTML = "";

        for (let value = 1; value <= 5; value += 1) {
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = String(value);
            button.title = value === 1 ? step.low : value === 5 ? step.high : "";
            button.addEventListener("click", () => submitAnswer(String(value)));
            choiceRow.appendChild(button);
        }
    } else {
        choiceRow.hidden = true;
        form.hidden = false;
        input.value = "";
        input.placeholder = step.optional ? "İstersen boş bırakıp Gönder'e bas" : "Cevabını yaz...";
        input.required = !step.optional;
        input.focus();
    }
}

function submitAnswer(answer) {
    const step = steps[state.index];
    const normalized = answer.trim();

    if (!step.optional && !normalized) {
        return;
    }

    state.answers[step.key] = normalized || "";
    addBubble(normalized || "Belirtilmedi", "user");
    state.index += 1;

    if (state.index >= steps.length) {
        analyze();
        return;
    }

    renderStep();
}

async function analyze() {
    form.hidden = true;
    choiceRow.hidden = true;
    progressLabel.textContent = "Analiz ediliyor";
    progressFill.style.width = "100%";
    addBubble("Cevaplarını aldım. Şimdi fikrini skora ve aksiyon planına çeviriyorum...");

    try {
        const response = await fetch(shell.dataset.analyzeUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(state.answers),
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Analiz sırasında hata oluştu.");
        }

        renderResult(data);
    } catch (error) {
        addBubble(error.message);
    }
}

function renderResult(data) {
    addBubble(`Venture Score: ${data.score} / 100. Risk seviyesi: ${data.risk_level}.`);

    const recommendations = data.recommendations
        .map((recommendation) => `<li>${escapeHtml(recommendation)}</li>`)
        .join("");
    const aiBlock = data.ai_analysis
        ? `<div class="result"><h2>AI Yorumu</h2><pre>${escapeHtml(data.ai_analysis)}</pre></div>`
        : `<p class="error">AI yorumu alınamadı: ${escapeHtml(data.ai_error || "Bilinmeyen hata")}</p>`;

    result.hidden = false;
    result.innerHTML = `
        <section class="venture-score-card">
            <div class="venture-score-main">
                <span class="score-label">Venture Score</span>
                <strong>${data.score}</strong>
                <span class="score-caption">${escapeHtml(data.readiness_label)}</span>
            </div>
            <div class="venture-score-detail">
                <span class="risk-pill">${escapeHtml(data.risk_level)}</span>
                <h2>Sonraki adımlar</h2>
                <ul>${recommendations}</ul>
                <div class="guided-result-actions">
                    <a href="${data.detail_url}" class="secondary-button">Detayı Gör</a>
                    <a href="${data.dashboard_url}" class="cta-button">Dashboard</a>
                </div>
            </div>
        </section>
        ${aiBlock}
    `;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitAnswer(input.value);
});

renderStep();
