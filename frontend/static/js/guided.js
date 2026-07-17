const shell = document.querySelector(".guided-shell");
const chat = document.getElementById("guided-chat");
const form = document.getElementById("guided-form");
const input = document.getElementById("guided-input");
const choiceRow = document.getElementById("guided-choice-row");
const progressLabel = document.getElementById("guided-progress-label");
const status = document.getElementById("guided-status");
const result = document.getElementById("guided-result");

function addBubble(text, role = "assistant") {
    const bubble = document.createElement("div");
    bubble.className = `guided-bubble guided-${role}`;
    if (role === "assistant") {
        bubble.innerHTML = formatAssistantText(text);
    } else {
        bubble.textContent = text;
    }
    chat.appendChild(bubble);
    chat.scrollTop = chat.scrollHeight;
}

function setBusy(isBusy) {
    input.disabled = isBusy;
    form.querySelector("button").disabled = isBusy;
    setStatus(isBusy ? "Analiz ediliyor" : "Hazır", isBusy ? "busy" : "ready");
}

function setStatus(label, state) {
    progressLabel.textContent = label;
    status.dataset.state = state;
}

async function sendMessage(message) {
    addBubble(message, "user");
    setBusy(true);

    try {
        const response = await fetch(shell.dataset.messageUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ message }),
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Mesaj gönderilemedi.");
        }

        addBubble(data.reply);

        if (data.done) {
            renderResult(data);
            setBusy(false);
            input.placeholder = "Devam sorusu yaz: neden olmaz, nasıl olur, başka nerede?";
            setStatus("Analiz hazır · Sohbete devam edebilirsin", "active");
        } else {
            setBusy(false);
            if (data.awaiting_location) {
                input.placeholder = "Şehir, ilçe veya bölge yaz...";
                setStatus("Lokasyon bekleniyor", "waiting");
                input.focus();
            } else if (data.analysis_ready) {
                input.placeholder = "Devam sorusu yaz...";
                setStatus("Sohbet devam ediyor", "active");
            }
        }
    } catch (error) {
        addBubble(error.message);
        setBusy(false);
    }
}

function renderResult(data) {
    const recommendations = data.recommendations
        .map((recommendation) => `<li>${escapeHtml(recommendation)}</li>`)
        .join("");

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
                    <a href="${data.history_url}" class="cta-button">Analizlerim</a>
                </div>
            </div>
        </section>
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

function cleanAssistantText(value) {
    return String(value)
        .replace(/\*\*(.*?)\*\*/g, "$1")
        .replace(/^\s*[*#]+\s*/gm, "")
        .replace(/\*/g, "")
        .trim();
}

function formatAssistantText(value) {
    return cleanAssistantText(value)
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
            const heading = line.match(/^\d+[.)]\s*(.+)$/);
            if (heading) {
                return `<div class="guided-answer-heading">${escapeHtml(heading[1])}</div>`;
            }
            const item = line.match(/^[-•]\s*(.+)$/);
            if (item) {
                return `<div class="guided-answer-item">${escapeHtml(item[1])}</div>`;
            }
            return `<p>${escapeHtml(line)}</p>`;
        })
        .join("");
}

form.addEventListener("submit", (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) {
        return;
    }
    input.value = "";
    sendMessage(message);
});

choiceRow.hidden = true;
progressLabel.textContent = "Hazır";
setStatus("Hazır · Fikrini yazabilirsin", "ready");
addBubble("Fikrini anlat. Nerede yapmak istediğini de yazarsan doğrudan bölgesel analize geçerim; yazmazsan sana tek bir kısa soru sorarım.");
input.focus();
