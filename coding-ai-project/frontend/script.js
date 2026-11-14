const API_URL = "http://127.0.0.1:8000";
const SESSION_ID = "user_01";

const chatBox = document.getElementById("chat-box");
const promptInput = document.getElementById("prompt-input");
const languageSelect = document.getElementById("language-select");

// بارگذاری خودکار حافظه گفتگوها هنگام باز شدن صفحه
window.addEventListener("DOMContentLoaded", async () => {
    try {
        const res = await fetch(`${API_URL}/history/${SESSION_ID}`);
        const data = await res.json();
        if (data.history && data.history.length > 0) {
            chatBox.innerHTML = "";
            data.history.forEach(msg => {
                appendMessage(msg.role === "user" ? "user" : "ai", msg.content);
            });
        }
    } catch (err) {
        console.log("سرور هنوز روشن نشده است.");
    }
});

function appendMessage(sender, text) {
    const div = document.createElement("div");
    div.className = `message ${sender === "user" ? "user-message" : "ai-message"}`;
    if (sender === "ai") {
        div.innerHTML = marked.parse(text);
        div.querySelectorAll("pre code").forEach(block => {
            hljs.highlightElement(block);
        });
    } else {
        div.textContent = text;
    }
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

document.getElementById("send-btn").addEventListener("click", async () => {
    const prompt = promptInput.value.trim();
    const language = languageSelect.value;
    if (!prompt) return;

    appendMessage("user", prompt);
    promptInput.value = "";

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: SESSION_ID, prompt, language })
        });
        const data = await response.json();
        if (response.ok) {
            appendMessage("ai", data.full_response);
        } else {
            appendMessage("ai", "خطا در سرور: " + data.detail);
        }
    } catch (error) {
        appendMessage("ai", "ارتباط با سرور برقرار نشد. مطمئن شوید FastAPI روشن است.");
    }
});

async function downloadFile(endpoint, filename) {
    const prompt = promptInput.value.trim();
    const language = languageSelect.value;
    if (!prompt) {
        alert("لطفاً ابتدا درخواست کدنویسی خود را در کادر متن بنویسید.");
        return;
    }

    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: SESSION_ID, prompt, language })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } else {
            alert("خطا در تولید فایل.");
        }
    } catch (error) {
        alert("خطا در ارتباط با سرور.");
    }
}

document.getElementById("download-txt-btn").addEventListener("click", () => {
    downloadFile("/export/notepad", "generated_code.txt");
});

document.getElementById("download-pdf-btn").addEventListener("click", () => {
    downloadFile("/export/pdf", "generated_code.pdf");
});

document.getElementById("clear-btn").addEventListener("click", async () => {
    try {
        await fetch(`${API_URL}/clear/${SESSION_ID}`, { method: "DELETE" });
        chatBox.innerHTML = '<div class="message ai-message">حافظه گفتگو پاک شد. می‌توانید گفتگوی جدیدی را شروع کنید.</div>';
    } catch (error) {
        alert("خطا در پاک کردن حافظه.");
    }
});
