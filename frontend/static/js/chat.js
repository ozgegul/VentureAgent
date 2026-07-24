// VentureAgent - sohbet arayüzü mantığı

const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
const messagesEl = document.getElementById("chat-messages");
const inputEl = document.getElementById("chat-input");
const sendBtn = document.getElementById("chat-send");
const sendFileBtn = document.getElementById("chat-send-file");
const resetBtn = document.getElementById("chat-reset");
const fileInput = document.getElementById("chat-file-input");
const fileStatusEl = document.getElementById("chat-file-status");
const filePreviewEl = document.getElementById("chat-file-preview");
const voiceToggle = document.getElementById("chat-voice-toggle");
let useVoiceResponse = false;
if (sendFileBtn) {
    sendFileBtn.hidden = true;
}

if (fileInput) {
    fileInput.addEventListener("change", () => {
        if (!fileStatusEl || !filePreviewEl || !sendFileBtn) return;
        filePreviewEl.innerHTML = "";
        if (fileInput.files.length === 0) {
            fileStatusEl.textContent = "";
            fileStatusEl.classList.remove("error-text");
            sendFileBtn.hidden = true;
            return;
        }

        const file = fileInput.files[0];
        const supported = file.type.startsWith("text") || /\.(txt|md|json|csv|py|js|html|css|png|jpe?g|webp|gif)$/i.test(file.name);
        const isImage = file.type.startsWith("image/") || /\.(png|jpe?g|webp|gif)$/i.test(file.name);

        if (!supported) {
            fileStatusEl.textContent = `Desteklenmeyen dosya: ${file.name}. Sadece metin ve görsel dosyaları yükleyebilirsiniz.`;
            fileStatusEl.classList.add("error-text");
            sendFileBtn.hidden = true;
            return;
        }

        fileStatusEl.textContent = `Seçilen dosya: ${file.name}`;
        fileStatusEl.classList.remove("error-text");
        sendFileBtn.hidden = false;

        if (isImage) {
            const img = document.createElement("img");
            img.src = URL.createObjectURL(file);
            img.alt = file.name;
            img.className = "chat-file-image-preview";
            filePreviewEl.appendChild(img);
        }
    });
}

if (voiceToggle) {
    voiceToggle.addEventListener("click", () => {
        useVoiceResponse = !useVoiceResponse;
        voiceToggle.classList.toggle("active", useVoiceResponse);
        voiceToggle.textContent = useVoiceResponse ? "Sesli Yanıt Açık" : "Sesli Yanıt";
    });
}

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
    let attachment = null;
    if (fileInput && fileInput.files.length > 0) {
        const file = fileInput.files[0];
        const supported = file.type.startsWith("text") || /\.(txt|md|json|csv|py|js|html|css|png|jpe?g|webp|gif)$/i.test(file.name);
        const isImage = file.type.startsWith("image/") || /\.(png|jpe?g|webp|gif)$/i.test(file.name);
        if (!supported) {
            appendBubble("assistant", "Hata: Sadece metin ve görsel dosyaları yükleyebilirsiniz.");
            return;
        }

        if (isImage) {
            attachment = {
                name: file.name,
                type: file.type || "image",
                size: file.size,
                is_image: true,
            };
        } else {
            const content = await file.text();
            const trimmed = content.trim();
            if (trimmed) {
                attachment = {
                    name: file.name,
                    type: file.type,
                    content: trimmed.length > 3000 ? `${trimmed.slice(0, 3000)}\n\n... (dosya içeriği kısaltıldı)` : trimmed,
                };
            }
        }
    }

    if (!text && !attachment) return;

    appendBubble("user", (text || "") + (attachment ? `\n\n[Dosya: ${attachment.name}]` : ""));
    inputEl.value = "";
    if (fileInput) {
        fileInput.value = "";
    }
    if (sendFileBtn) {
        sendFileBtn.hidden = true;
    }
    if (fileStatusEl) {
        fileStatusEl.textContent = "";
        fileStatusEl.classList.remove("error-text");
    }
    if (filePreviewEl) {
        filePreviewEl.innerHTML = "";
    }
    sendBtn.disabled = true;
    const thinkingBubble = appendBubble("assistant", "Düşünüyor...");

    try {
        const res = await fetch("/chat/message", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
            body: JSON.stringify({ message: text, attachment, voice: useVoiceResponse }),
        });
        const data = await res.json();

        if (data.error) {
            thinkingBubble.textContent = `Hata: ${data.error}`;
        } else {
            thinkingBubble.textContent = data.reply;
            if (useVoiceResponse && window.speechSynthesis) {
                const utterance = new SpeechSynthesisUtterance(data.reply);
                utterance.lang = "tr-TR";
                window.speechSynthesis.speak(utterance);
            }
        }
    } catch (err) {
        thinkingBubble.textContent = "Bağlantı hatası oluştu, tekrar dener misin?";
    } finally {
        sendBtn.disabled = false;
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
}

sendBtn.addEventListener("click", sendMessage);
if (sendFileBtn) {
    sendFileBtn.addEventListener("click", sendMessage);
}

inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

resetBtn.addEventListener("click", async () => {
    await fetch("/chat/reset", { method: "POST", headers: { "X-CSRFToken": csrfToken } });
    messagesEl.innerHTML = "";
});
