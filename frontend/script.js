const API_BASE_URL = "http://127.0.0.1:8000";

const chatBox = document.getElementById("chat-box");
const promptInput = document.getElementById("prompt-input");
const sendBtn = document.getElementById("send-btn");
const languageSelect = document.getElementById("language-select");
const sessionInput = document.getElementById("session-input");
const clearBtn = document.getElementById("clear-btn");
const loadHistoryBtn = document.getElementById("load-history-btn");
const downloadTxtBtn = document.getElementById("download-txt-btn");
const downloadPdfBtn = document.getElementById("download-pdf-btn");

// تبدیل بلوک‌های Markdown به HTML رنگی با دکمه کپی
function formatMessageContent(text) {
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    let formatted = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");

    formatted = formatted.replace(codeBlockRegex, (match, lang, code) => {
        const language = lang || "code";
        const cleanCode = code.trim();
        return `
            <div class="code-wrapper">
                <div class="code-toolbar">
                    <span>${language.toUpperCase()}</span>
                    <button class="copy-btn" onclick="copyCode(this)">کپی کد</button>
                </div>
                <pre><code class="language-${language}">${cleanCode}</code></pre>
            </div>
        `;
    });

    return formatted.replace(/\n/g, "<br>");
}

// کپی کردن کد در کلیپ‌بورد
window.copyCode = function(button) {
    const codeElement = button.closest(".code-wrapper").querySelector("code");
    navigator.clipboard.writeText(codeElement.innerText).then(() => {
        const originalText = button.innerText;
        button.innerText = "کپی شد!";
        setTimeout(() => {
            button.innerText = originalText;
        }, 1500);
    });
};

// افزودن پیام به صفحه چت
function appendMessage(role, content) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role === "user" ? "user-message" : "ai-message"}`;

    const header = document.createElement("div");
    header.className = "message-header";
    header.innerText = role === "user" ? "شما" : "دستیار کدنویسی";

    const body = document.createElement("div");
    body.className = "message-body";
    body.innerHTML = role === "user" ? content.replace(/\n/g, "<br>") : formatMessageContent(content);

    msgDiv.appendChild(header);
    msgDiv.appendChild(body);
    chatBox.appendChild(msgDiv);

    // اعمال رنگ‌بندی سینتکس روی کدهای جدید
    msgDiv.querySelectorAll("pre code").forEach((block) => {
        hljs.highlightElement(block);
    });

    chatBox.scrollTop = chatBox.scrollHeight;
}

// ارسال درخواست کدنویسی به سرور
async function sendPrompt() {
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    const sessionId = sessionInput.value.trim() || "default_user";
    const language = languageSelect.value;

    appendMessage("user", prompt);
    promptInput.value = "";
    sendBtn.disabled = true;
    sendBtn.innerText = "در حال کدنویسی...";

    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                prompt: prompt,
                language: language
            })
        });

        const data = await response.json();
        if (response.ok) {
            appendMessage("assistant", data.full_response);
        } else {
            appendMessage("assistant", `خطا از سمت سرور: ${data.detail || "نامشخص"}`);
        }
    } catch (error) {
        appendMessage("assistant", "خطا در اتصال به سرور. مطمئن شوید سرور FastAPI روشن است.");
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerText = "ارسال درخواست";
    }
}

// دانلود خروجی در قالب نوت‌پد (.txt) یا PDF
async function exportCode(format) {
    const prompt = promptInput.value.trim();
    if (!prompt) {
        alert("لطفاً ابتدا دستور کدنویسی را در کادر پایین بنویسید تا فایل آن ساخته شود.");
        return;
    }

    const sessionId = sessionInput.value.trim() || "default_user";
    const language = languageSelect.value;
    const endpoint = format === "pdf" ? "/export/pdf" : "/export/notepad";
    const filename = format === "pdf" ? "generated_code.pdf" : "generated_code.txt";

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                prompt: prompt,
                language: language
            })
        });

        if (!response.ok) throw new Error("خطا در تولید فایل");

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        alert("خطا در دانلود فایل. اتصال به سرور را بررسی کنید.");
    }
}

// بارگذاری تاریخچه گفتگو از سرور
async function loadHistory() {
    const sessionId = sessionInput.value.trim() || "default_user";
    try {
        const response = await fetch(`${API_BASE_URL}/history/${sessionId}`);
        if (!response.ok) return;
        const data = await response.json();
        if (data.history && data.history.length > 0) {
            chatBox.innerHTML = "";
            data.history.forEach(msg => {
                appendMessage(msg.role, msg.content);
            });
        }
    } catch (e) {
        console.log("سرور در دسترس نیست یا تاریخچه‌ای وجود ندارد.");
    }
}

// پاک کردن حافظه گفتگو
async function clearMemory() {
    const sessionId = sessionInput.value.trim() || "default_user";
    if (!confirm(`آیا مطمئن هستید که حافظه گفتگوی "${sessionId}" پاک شود؟`)) return;

    try {
        await fetch(`${API_BASE_URL}/clear/${sessionId}`, { method: "DELETE" });
        chatBox.innerHTML = `
            <div class="message ai-message">
                <div class="message-header">سیستم</div>
                <div class="message-body">حافظه این گفتگو با موفقیت پاک شد.</div>
            </div>
        `;
    } catch (error) {
        alert("خطا در ارتباط با سرور برای پاک کردن حافظه.");
    }
}

sendBtn.addEventListener("click", sendPrompt);
promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendPrompt();
    }
});

downloadTxtBtn.addEventListener("click", () => exportCode("txt"));
downloadPdfBtn.addEventListener("click", () => exportCode("pdf"));
loadHistoryBtn.addEventListener("click", loadHistory);
clearBtn.addEventListener("click", clearMemory);
