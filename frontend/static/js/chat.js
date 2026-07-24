// VentureAgent - sohbet arayüzü mantığı

const messagesEl = document.getElementById("chat-messages");
const inputEl = document.getElementById("chat-input");
const sendBtn = document.getElementById("chat-send");
const resetBtn = document.getElementById("chat-reset");

// Multimodal elements
const fileInput = document.getElementById("chat-file");
const attachBtn = document.getElementById("chat-attach-btn");
const micBtn = document.getElementById("chat-mic-btn");
const statusEl = document.getElementById("chat-attachment-status");

let mediaRecorder = null;
let audioChunks = [];
let recordedAudioBlob = null;

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
    
    // Create FormData for multipart submission
    const formData = new FormData();
    formData.append("message", text);
    
    if (fileInput.files.length > 0) {
        formData.append("file", fileInput.files[0]);
    }
    
    if (recordedAudioBlob) {
        formData.append("audio", recordedAudioBlob, "audio.webm");
    }

    inputEl.value = "";
    sendBtn.disabled = true;
    attachBtn.disabled = true;
    micBtn.disabled = true;
    const thinkingBubble = appendBubble("assistant", "Düşünüyor...");

    try {
        const res = await fetch("/chat/message", {
            method: "POST",
            body: formData, // fetch will automatically set Content-Type to multipart/form-data with the correct boundary
        });
        const data = await res.json();

        if (data.error) {
            thinkingBubble.textContent = `Hata: ${data.error}`;
        } else {
            thinkingBubble.textContent = data.reply;
            
            // Phase 2: Render routing suggestion if available
            if (data.suggestion) {
                const card = document.createElement("div");
                card.className = "routing-suggestion-card";
                card.innerHTML = `
                    <p>${data.suggestion.text}</p>
                    <a href="${data.suggestion.url}?idea=${encodeURIComponent(data.suggestion.prefill_idea)}" class="suggestion-link">
                        Modüle git →
                    </a>`;
                messagesEl.appendChild(card);
            }
        }
    } catch (err) {
        thinkingBubble.textContent = "Bağlantı hatası oluştu, tekrar dener misin?";
    } finally {
        sendBtn.disabled = false;
        attachBtn.disabled = false;
        micBtn.disabled = false;
        
        // Reset attachments after sending
        fileInput.value = "";
        recordedAudioBlob = null;
        statusEl.textContent = "";
        
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
    fileInput.value = "";
    recordedAudioBlob = null;
    statusEl.textContent = "";
});

// --- Multimodal Handlers ---

attachBtn.addEventListener("click", () => {
    fileInput.click();
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        statusEl.textContent = `Ekli dosya: ${fileInput.files[0].name}`;
        recordedAudioBlob = null; // Can't send both at once easily in this UI, so we pick one
    } else {
        statusEl.textContent = "";
    }
});

micBtn.addEventListener("click", async () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        micBtn.textContent = "🎤";
        micBtn.style.color = "";
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            recordedAudioBlob = new Blob(audioChunks, { type: "audio/webm" });
            statusEl.textContent = "Ses kaydedildi. Göndermeye hazır.";
            fileInput.value = ""; // Clear file if audio is recorded
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        micBtn.textContent = "⏹";
        micBtn.style.color = "red";
        statusEl.textContent = "Ses kaydediliyor...";
    } catch (err) {
        console.error("Mikrofona erişilemedi:", err);
        statusEl.textContent = "Hata: Mikrofona erişilemedi.";
    }
});
