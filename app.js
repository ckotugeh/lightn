const ws = new WebSocket("ws://127.0.0.1:8000/ws/dashboard");
const balanceEl = document.getElementById("balance");
const statusEl = document.getElementById("status");
const dotEl = document.getElementById("dot");
const logEl = document.getElementById("log");
const breakerBtn = document.getElementById("breakerBtn");

let powerActive = true;

// This function catches the button click from your HTML file
function togglePower() {
    powerActive = !powerActive;
    
    if (powerActive) {
        breakerBtn.innerText = "🛑 Disconnect Power Breaker";
        breakerBtn.className = "breaker-btn btn-on";
    } else {
        breakerBtn.innerText = "⚡ Connect Power Breaker";
        breakerBtn.className = "breaker-btn btn-off";
    }
    
    // Send the stop or start signal over the live WebSocket channel to server.py
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ "action": "toggle_breaker", "enabled": powerActive }));
    }
}

ws.onopen = () => {
    statusEl.innerText = "Active Meter Stream Connected";
    dotEl.className = "status-dot connected";
};

ws.onclose = () => {
    statusEl.innerText = "Disconnected from Server";
    dotEl.className = "status-dot";
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.total_earned !== undefined) {
        balanceEl.innerText = data.total_earned.toLocaleString() + " sats";
    }
    if (data.event === "payment_sent") {
        const item = document.createElement("div");
        item.className = "log-item";
        item.innerHTML = `
            <span class="log-text">⚡ Meter update: +${data.kwh_delta} kWh</span>
            <span class="log-sats">+${data.sats_paid} sats</span>
        `;
        logEl.prepend(item);
    }
};
