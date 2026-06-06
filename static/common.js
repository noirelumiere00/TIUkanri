// 3画面で共通利用するヘルパー群

let serverOffset = 0;

async function syncTime() {
    try {
        const res = await fetch('/api/server_time');
        const data = await res.json();
        serverOffset = new Date(data.server_time).getTime() - Date.now();
        return true;
    } catch (e) {
        return false;
    }
}

function serverNow() {
    return new Date(Date.now() + serverOffset);
}

function pad2(n) {
    return String(n).padStart(2, '0');
}

function tickClock(id = 'clock') {
    const el = document.getElementById(id);
    if (!el) return;
    const now = serverNow();
    el.textContent = [now.getHours(), now.getMinutes(), now.getSeconds()].map(pad2).join(':');
}

function showToast(msg, type) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'toast show ' + (type || '');
    setTimeout(() => { t.className = 'toast'; }, 2500);
}

// POSTして JSON を返す。body を渡すと JSON として送信。
async function apiPost(url, body) {
    const opt = { method: 'POST' };
    if (body !== undefined) {
        opt.headers = { 'Content-Type': 'application/json' };
        opt.body = JSON.stringify(body);
    }
    const res = await fetch(url, opt);
    return res.json();
}

async function getConfig() {
    try {
        const res = await fetch('/api/config');
        return await res.json();
    } catch (e) {
        return { time_limit_min: 15, long_wait_min: 30 };
    }
}
