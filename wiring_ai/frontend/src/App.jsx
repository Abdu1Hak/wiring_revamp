/* ==============================================================================
 * FRONTEND ORCHESTRATION: FASTAPI + REDIS + CELERY EXCHANGE (App.jsx)
 * ==============================================================================
 * HOW THE FRONTEND HANDLES THE EXCHANGE:
 * 1. USER SENDS LOOKUP: Frontend posts component name to `POST /components/lookup`.
 * 2. BRANCH A (CACHE HIT):
 *    If backend returns `source: "redis"`, result is displayed immediately!
 * 3. BRANCH B (CACHE MISS):
 *    If backend returns `source: "celery"` + `task_id`, the frontend:
 *    - Updates UI logs to: "Calling Celery... Querying PostgreSQL..."
 *    - Starts `pollJobStatus()` interval, calling `GET /jobs/{task_id}` every 500ms.
 * 4. JOB COMPLETION:
 *    When `/jobs/{task_id}` returns `status === "SUCCESS"`, the interval stops,
 *    UI updates to: "Saving result to Redis... Retrieved via Celery worker",
 *    and the final component category & description are rendered!
 * ==============================================================================
 */

import { useState } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [componentName, setComponentName] = useState("");
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);

  async function handleLookup(e) {
    e.preventDefault();
    const query = componentName.trim();
    if (!query || isProcessing) return;

    setIsProcessing(true);
    setComponentName("");

    const startTime = performance.now();

    // Append User Message to Chat Log
    const userMsg = {
      id: Date.now(),
      sender: "user",
      text: query,
    };

    // Append Assistant Placeholder Message
    const botMsgId = Date.now() + 1;
    const initialBotMsg = {
      id: botMsgId,
      sender: "system",
      query: query,
      steps: ["Checking Redis cache..."],
      status: "in_progress",
      source: null,
      elapsedMs: 0,
      data: null,
    };

    setMessages((prev) => [...prev, userMsg, initialBotMsg]);

    try {
      // 1. Send Lookup Request to FastAPI
      const res = await fetch(`${API_BASE}/components/lookup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ component_name: query }),
      });

      const initialResult = await res.json();
      console.log("[Lookup Response]:", initialResult);

      if (initialResult.status === "complete" && initialResult.source === "redis") {
        // --- CACHE HIT PATH ---
        const hitElapsed = initialResult.elapsed_ms;
        updateBotMessage(botMsgId, {
          status: "complete",
          source: "redis",
          elapsedMs: hitElapsed,
          steps: [`Retrieved from Redis in ${hitElapsed} ms`],
          data: initialResult.data,
        });
        setIsProcessing(false);
        return;
      }

      // --- CACHE MISS PATH (CELERY WORKFLOW) ---
      const taskId = initialResult.task_id;
      updateBotMessage(botMsgId, {
        source: "celery",
        steps: [
          "Calling Celery...",
          `Task ID: ${taskId}`,
          "Querying PostgreSQL...",
        ],
      });

      // Poll Celery Job Endpoint every 500ms
      pollJobStatus(taskId, botMsgId, startTime);
    } catch (err) {
      console.error("[Lookup Error]:", err);
      updateBotMessage(botMsgId, {
        status: "error",
        steps: ["Failed to connect to backend service."],
      });
      setIsProcessing(false);
    }
  }

  function updateBotMessage(msgId, updates) {
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id === msgId) {
          return {
            ...msg,
            ...updates,
            steps: updates.steps ? updates.steps : msg.steps,
          };
        }
        return msg;
      })
    );
  }

  function pollJobStatus(taskId, botMsgId, startTime) {
    let pollCount = 0;
    const interval = setInterval(async () => {
      pollCount++;
      try {
        const res = await fetch(`${API_BASE}/jobs/${taskId}`);
        const job = await res.json();
        console.log("[Job Poll Status]:", job);

        if (job.status === "PENDING" && pollCount > 5) {
          updateBotMessage(botMsgId, {
            steps: [
              "Calling Celery...",
              `Task ID: ${taskId}`,
              "Task queued in Redis (Waiting for Celery Worker process...)",
              "⚠️ Tip: Ensure Celery worker is running in a terminal:",
              ".venv\\Scripts\\celery -A celery_app worker --loglevel=info --pool=solo",
            ],
          });
        }

        if (job.status === "SUCCESS") {
          clearInterval(interval);
          const totalElapsed = Math.round(performance.now() - startTime);
          const celeryResult = job.result;

          if (celeryResult && celeryResult.found) {
            updateBotMessage(botMsgId, {
              status: "complete",
              elapsedMs: totalElapsed,
              steps: [
                "Calling Celery...",
                "Querying PostgreSQL...",
                "Saving result to Redis...",
                `Retrieved via Celery worker in ${totalElapsed} ms`,
              ],
              data: celeryResult.data,
            });
          } else {
            updateBotMessage(botMsgId, {
              status: "not_found",
              elapsedMs: totalElapsed,
              steps: [
                "Calling Celery...",
                "Querying PostgreSQL...",
                `Component not found in database.`,
              ],
              data: null,
            });
          }
          setIsProcessing(false);
        } else if (job.status === "FAILURE") {
          clearInterval(interval);
          updateBotMessage(botMsgId, {
            status: "error",
            steps: [
              "Calling Celery...",
              "Querying PostgreSQL...",
              `Celery task failed: ${job.error || "Unknown error"}`,
            ],
          });
          setIsProcessing(false);
        }
      } catch (err) {
        console.error("[Job Poll Error]:", err);
        clearInterval(interval);
        setIsProcessing(false);
      }
    }, 500);
  }

  return (
    <div className="chat-app">
      <header className="app-header">
        <h1>Wiring AI</h1>
        <p className="subtitle">Component Lookup — Celery + Redis Learning Workflow</p>
      </header>

      <div className="chat-container">
        {messages.length === 0 ? (
          <div className="welcome-box">
            <h3>Welcome to Component Lookup!</h3>
            <p>Enter a component name (e.g. <code>Arduino Uno</code>, <code>dht22</code>, <code>esp32</code>) to test Redis Caching and Celery Worker execution.</p>
            <div className="hint-tags">
              <span onClick={() => setComponentName("Arduino Uno")}>Arduino Uno</span>
              <span onClick={() => setComponentName("DHT22")}>DHT22</span>
              <span onClick={() => setComponentName("ESP32")}>ESP32</span>
            </div>
          </div>
        ) : (
          <div className="message-list">
            {messages.map((msg) => (
              <div key={msg.id} className={`message-bubble ${msg.sender}`}>
                {msg.sender === "user" ? (
                  <div className="user-text">{msg.text}</div>
                ) : (
                  <div className="bot-content">
                    <div className="query-title">
                      Lookup: <strong>{msg.query}</strong>
                    </div>

                    {/* Step-by-Step Workflow Logs */}
                    <div className="workflow-steps">
                      {msg.steps.map((step, idx) => (
                        <div key={idx} className="step-line">
                          <span className="step-icon">➔</span> {step}
                        </div>
                      ))}
                    </div>

                    {/* Cache Hit Badge */}
                    {msg.source === "redis" && (
                      <div className="badge redis-badge">
                        ⚡ Redis Cache Hit ({msg.elapsedMs} ms)
                      </div>
                    )}

                    {/* Celery Worker Badge */}
                    {msg.source === "celery" && msg.status === "complete" && (
                      <div className="badge celery-badge">
                        ⚙️ Celery Worker + Redis Saved ({msg.elapsedMs} ms)
                      </div>
                    )}

                    {/* Final Component Result Data */}
                    {msg.data && (
                      <div className="result-card">
                        <div className="card-row">
                          <span className="label">Category:</span>
                          <span className="value category-tag">{msg.data.category}</span>
                        </div>
                        <div className="card-row">
                          <span className="label">Description:</span>
                          <p className="value description">{msg.data.description}</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Chat Input Form */}
      <form onSubmit={handleLookup} className="chat-input-form">
        <input
          type="text"
          value={componentName}
          onChange={(e) => setComponentName(e.target.value)}
          placeholder="Enter component name (e.g. Arduino Uno)..."
          disabled={isProcessing}
        />
        <button type="submit" disabled={isProcessing || !componentName.trim()}>
          {isProcessing ? "Processing..." : "Send"}
        </button>
      </form>
    </div>
  );
}

export default App;