/**
 * Live counterpart to mockBackend.js — connects to the real backend's
 * /ws/dashboard WebSocket instead of simulating data. Emits the same
 * message shapes App.jsx already handles (sensorId, type, ...), so it can
 * be swapped in for the mock without touching the message-handling code.
 *
 * The real backend only tracks cycle state (cleaning/verifying/passed/failed)
 * and raw temp/turbidity readings — it has no concept of the mock's CIP
 * sub-stages (pre-rinse, caustic wash, ...), so stageId/stageIndex/timers are
 * not emitted here. The stage strip simply keeps whatever it was seeded with.
 */
export function createRealBackend(onMessage, { wsUrl } = {}) {
  let socket = null;
  let reconnectTimer = null;
  let manuallyClosed = false;

  function resolveWsUrl() {
    if (wsUrl) return wsUrl;
    const host = window.location.hostname || "localhost";
    return `ws://${host}:8000/ws/dashboard`;
  }

  function connect() {
    socket = new WebSocket(resolveWsUrl());

    socket.onmessage = (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      const sensorId = msg.lineId;
      if (!sensorId) return;

      if (msg.type === "reading") {
        onMessage({
          type: "reading",
          sensorId,
          ts: msg.ts,
          temp: msg.temp,
          turbidity: msg.turbidity,
        });
      } else if (msg.type === "cycle_state") {
        onMessage({
          type: "cycle_state",
          sensorId,
          cycleState: msg.state,
        });
      } else if (msg.type === "verdict") {
        // Cycle state already flips to passed/failed via the message above;
        // confidence/top features aren't shown yet, just logged for now.
        console.info(
          `[live] verdict for ${sensorId}: ${msg.verdict} (confidence ${msg.confidence})`
        );
      }
    };

    socket.onclose = () => {
      socket = null;
      if (!manuallyClosed) {
        reconnectTimer = setTimeout(connect, 2000);
      }
    };

    socket.onerror = () => {
      socket?.close();
    };
  }

  return {
    start() {
      manuallyClosed = false;
      connect();
    },
    stop() {
      manuallyClosed = true;
      clearTimeout(reconnectTimer);
      socket?.close();
      socket = null;
    },
    inject() {
      // No-op: hardware readings can't be spiked from the UI.
    },
  };
}
