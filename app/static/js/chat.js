// VentureAgent - sohbet arayüzü mantığı

const messagesEl = document.getElementById("chat-messages");
const inputEl = document.getElementById("chat-input");
const sendBtn = document.getElementById("chat-send");
const resetBtn = document.getElementById("chat-reset");

function appendBubble(role, content) {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble chat-${role}`;
    bubble.textContent = content;
    messagesEl.appendChild(bubble);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return bubble;
}

async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;

    appendBubble("user", text);
    inputEl.value = "";
    sendBtn.disabled = true;
    const thinkingBubble = appendBubble("assistant", "Düşünüyor...");

    try {
        const res = await fetch("/chat/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text }),
        });
        const data = await res.json();

        if (data.error) {
            thinkingBubble.textContent = `Hata: ${data.error}`;
        } else {
            thinkingBubble.textContent = data.reply;
        }
    } catch (err) {
        thinkingBubble.textContent = "Bağlantı hatası oluştu, tekrar dener misin?";
    } finally {
        sendBtn.disabled = false;
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
}

sendBtn.addEventListener("click", sendMessage);

inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

resetBtn.addEventListener("click", async () => {
    await fetch("/chat/reset", { method: "POST" });
    messagesEl.innerHTML = "";
});
