// VentureAgent - sohbet arayüzü mantığı

const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
const messagesEl = document.getElementById("chat-messages");
const inputEl = document.getElementById("chat-input");
const sendBtn = document.getElementById("chat-send");
const resetBtn = document.getElementById("chat-reset");

const attachBtn = document.getElementById("chat-attach-btn");
const fileInput = document.getElementById("chat-file");
const micBtn = document.getElementById("chat-mic-btn");
const previewEl = document.getElementById("chat-attachments-preview");

let currentAttachments = [];
let mediaRecorder = null;
let audioChunks = [];

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
    if (!text && currentAttachments.length === 0) return;

    let userContent = text;
    if (currentAttachments.length > 0) {
        userContent += ` [${currentAttachments.length} dosya eklendi]`;
    }
    appendBubble("user", userContent);
    
    inputEl.value = "";
    const attachmentsToSend = [...currentAttachments];
    currentAttachments = [];
    previewEl.innerHTML = "";
    
    sendBtn.disabled = true;
    const thinkingBubble = appendBubble("assistant", "Düşünüyor...");

    try {
        const res = await fetch("/chat/message", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
            body: JSON.stringify({ 
                message: text,
                attachments: attachmentsToSend
            }),
        });
        const data = await res.json();

        if (data.error) {
            thinkingBubble.textContent = `Hata: ${data.error}`;
        } else {
            thinkingBubble.textContent = data.reply;
            if (data.suggested_route && data.suggested_route !== "none") {
                const routeUrls = {
                    "swot": "/swot",
                    "competitors": "/competitors",
                    "revenue": "/revenue",
                    "roadmap": "/roadmap",
                    "kanban": "/kanban",
                    "investors": "/investors",
                    "pitch": "/pitch"
                };
                if (routeUrls[data.suggested_route]) {
                    const btn = document.createElement("a");
                    btn.href = routeUrls[data.suggested_route];
                    btn.className = "btn btn-route";
                    btn.style.display = "inline-block";
                    btn.style.marginTop = "10px";
                    btn.style.padding = "10px 15px";
                    btn.style.backgroundColor = "#e0e7ff";
                    btn.style.color = "#3730a3";
                    btn.style.borderRadius = "8px";
                    btn.style.textDecoration = "none";
                    btn.style.fontWeight = "bold";
                    btn.textContent = `🚀 Detaylı ${data.suggested_route.toUpperCase()} analizi yapmak ister misin?`;
                    messagesEl.appendChild(btn);
                }
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

// MULTIMODAL LOGIC
function updatePreview() {
    previewEl.innerHTML = "";
    currentAttachments.forEach((att, idx) => {
        const div = document.createElement("div");
        div.style.padding = "5px 10px";
        div.style.background = "#e5e7eb";
        div.style.borderRadius = "4px";
        div.style.fontSize = "12px";
        div.style.display = "flex";
        div.style.alignItems = "center";
        div.style.gap = "5px";
        
        let typeIcon = "📄";
        if (att.mimeType.startsWith("image/")) typeIcon = "🖼️";
        else if (att.mimeType.startsWith("audio/")) typeIcon = "🎵";
        
        div.innerHTML = `<span>${typeIcon} ${att.mimeType.split('/')[1]}</span>`;
        
        const removeBtn = document.createElement("button");
        removeBtn.textContent = "x";
        removeBtn.style.border = "none";
        removeBtn.style.background = "none";
        removeBtn.style.cursor = "pointer";
        removeBtn.style.color = "red";
        removeBtn.onclick = () => {
            currentAttachments.splice(idx, 1);
            updatePreview();
        };
        div.appendChild(removeBtn);
        previewEl.appendChild(div);
    });
}

function toBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = error => reject(error);
    });
}

if(attachBtn && fileInput) {
    attachBtn.addEventListener("click", () => fileInput.click());
    
    fileInput.addEventListener("change", async (e) => {
        if (!e.target.files.length) return;
        const file = e.target.files[0];
        try {
            const b64 = await toBase64(file);
            currentAttachments.push({ mimeType: file.type, data: b64 });
            updatePreview();
        } catch (err) {
            console.error("File upload error", err);
            alert("Dosya yüklenemedi.");
        }
        fileInput.value = "";
    });
}

if(micBtn) {
    micBtn.addEventListener("click", async () => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
            micBtn.style.background = "white";
            micBtn.textContent = "🎤";
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            mediaRecorder.ondataavailable = e => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };
            
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const b64 = await toBase64(audioBlob);
                currentAttachments.push({ mimeType: 'audio/webm', data: b64 });
                updatePreview();
            };
            
            mediaRecorder.start();
            micBtn.style.background = "#fee2e2";
            micBtn.textContent = "⏹️";
        } catch (err) {
            console.error("Microphone error", err);
            alert("Mikrofona erişilemedi.");
        }
    });
}
