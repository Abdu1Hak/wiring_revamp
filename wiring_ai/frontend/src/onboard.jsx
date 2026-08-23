/**
 * onboard.jsx
 * ─────────────────────────────────────────────────────────────────────
 * Pre-processing pipeline UI:
 * 1. Component ID + name input
 * 2. Datasheet upload (drag-drop PDF) OR URL input
 * 3. Live SSE status tracker — streams events from FastAPI/LangGraph/Celery
 * 4. Success state: shows extracted metadata, updates parent catalog
 */

import { useState, useRef, useCallback } from "react";

// ─── Status tracker config ────────────────────────────────────────────────────

const NODE_CONFIG = {
  check_vector_db: { label: "Checking Catalog", icon: "🔍" },
  validate_datasheet: { label: "Validating Datasheet", icon: "📋" },
  web_search: { label: "Searching Web", icon: "🌐" },
  dispatch_ingestion: { label: "Initiating Ingestion", icon: "🚀" },
  poll_and_finalize: { label: "Finalizing", icon: "✅" },
};

const PROGRESS_STEP_LABELS = {
  loading: "Loading Datasheet",
  fetching: "Fetching from Web",
  extracting: "Extracting Text",
  analyzing: "Analyzing Metadata",
  chunking: "Chunking Datasheet",
  embedding: "Generating Embeddings",
  storing: "Storing in Vector DB",
  updating_catalog: "Updating Catalog",
  rate_limited: "AI Rates are Limited",
  complete: "Complete",
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatusLine({ event }) {
  if (event.type === "node") {
    const config = NODE_CONFIG[event.node] || { label: event.node, icon: "⚙️" };
    return (
      <div style={styles.statusLine}>
        <span style={styles.icon}>{config.icon}</span>
        <span style={styles.label}>{config.label}</span>
        {event.message && (
          <span style={styles.detail}>{event.message}</span>
        )}
      </div>
    );
  }

  if (event.type === "progress" && event.step !== "failed") {
    const label = PROGRESS_STEP_LABELS[event.step] || event.step;
    return (
      <div style={styles.statusLine}>
        <span style={styles.icon}>⚡</span>
        <span style={styles.label}>{label}</span>
        <span style={styles.detail}>{event.message || `${event.progress}% complete`}</span>
      </div>
    );
  }

  if (event.type === "error" || event.type === "failed" || event.step === "failed") {
    return (
      <div style={{ ...styles.statusLine, color: "#f87171" }}>
        <span style={styles.icon}>❌</span>
        <span style={{ ...styles.label, color: "#f87171" }}>Failed</span>
        <span style={styles.detail}>{event.message || event.error || "Ingestion failed"}</span>
      </div>
    );
  }

  return null;
}

function MetadataPreview({ metadata }) {
  if (!metadata || !Object.keys(metadata).length) return null;
  return (
    <div style={styles.metadataBox}>
      <h4 style={styles.metadataTitle}>📦 Extracted Component Data</h4>
      <div style={styles.metadataGrid}>
        {metadata.name && <div><b>Name:</b> {metadata.name}</div>}
        {metadata.category && <div><b>Category:</b> {metadata.category}</div>}
        {metadata.voltage_min != null && (
          <div><b>Voltage:</b> {metadata.voltage_min}V – {metadata.voltage_max}V</div>
        )}
        {metadata.pin_count != null && <div><b>Pins:</b> {metadata.pin_count}</div>}
        {metadata.protocols?.length > 0 && (
          <div><b>Protocols:</b> {metadata.protocols.join(", ")}</div>
        )}
        {metadata.description && (
          <div style={{ gridColumn: "1/-1" }}><b>Description:</b> {metadata.description}</div>
        )}
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function OnboardPanel({ onComponentAdded }) {
  const [componentId, setComponentId] = useState("");
  const [componentName, setComponentName] = useState("");
  const [datasheetUrl, setDatasheetUrl] = useState("");
  const [pdfFile, setPdfFile] = useState(null);
  const [skipValidation, setSkipValidation] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [events, setEvents] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [finalStatus, setFinalStatus] = useState(null); // "complete" | "failed" | null
  const [metadata, setMetadata] = useState(null);

  const fileInputRef = useRef();
  const eventsEndRef = useRef();

  const appendEvent = useCallback((event) => {
    setEvents(prev => [...prev, event]);
    setTimeout(() => eventsEndRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }, []);

  // ── File Drag + Drop ──────────────────────────────────────────────────────
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file?.type === "application/pdf") {
      setPdfFile(file);
    } else {
      alert("Please upload a PDF file.");
    }
  };

  // ── Submit: Build FormData, Open SSE ──────────────────────────────────────
  const handleSubmit = async () => {
    if (!componentId.trim() || !componentName.trim()) {
      alert("Component ID and name are required.");
      return;
    }
    if (!pdfFile && !datasheetUrl.trim() && !skipValidation) {
      alert("Please provide a datasheet PDF or URL.");
      return;
    }

    setEvents([]);
    setFinalStatus(null);
    setMetadata(null);
    setIsStreaming(true);

    const formData = new FormData();
    formData.append("component_id", componentId.trim().toLowerCase().replace(/\s+/g, "_"));
    formData.append("component_name", componentName.trim());
    formData.append("skip_validation", skipValidation ? "true" : "false");
    if (datasheetUrl.trim()) formData.append("datasheet_url", datasheetUrl.trim());
    if (pdfFile) formData.append("datasheet_file", pdfFile);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/preprocess/onboard", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      // ── Parse SSE stream ────────────────────────────────────────────────
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (raw === "[DONE]") break;

          try {
            const event = JSON.parse(raw);

            if (event.type === "complete") {
              setFinalStatus("complete");
              setMetadata(event.metadata);
              appendEvent(event);
              onComponentAdded?.({
                id: componentId,
                name: componentName,
                ...event.metadata,
              });
            } else if (event.type === "failed") {
              setFinalStatus("failed");
              appendEvent({ ...event, message: event.error || "Ingestion failed" });
            } else if (event.type !== "done") {
              appendEvent(event);
            }
          } catch {
            // Ignore malformed events (e.g., keepalive pings)
          }
        }
      }
    } catch (err) {
      appendEvent({ type: "error", message: err.message });
      setFinalStatus("failed");
    } finally {
      setIsStreaming(false);
    }
  };

  const reset = () => {
    setComponentId(""); setComponentName(""); setDatasheetUrl("");
    setPdfFile(null); setEvents([]); setFinalStatus(null); setMetadata(null);
  };

  // Derive latest active progress event for header bar
  const latestProgressEvent = [...events].reverse().find((e) => e.type === "progress" && e.step !== "failed");
  const activePct = latestProgressEvent ? latestProgressEvent.progress : 0;
  const activeLabel = latestProgressEvent
    ? (PROGRESS_STEP_LABELS[latestProgressEvent.step] || latestProgressEvent.message || latestProgressEvent.step)
    : "Processing...";

  // Detect rate limiting state
  const lastEvent = events[events.length - 1];
  const isRateLimited = isStreaming && (
    latestProgressEvent?.step === "rate_limited" ||
    lastEvent?.step === "rate_limited" ||
    lastEvent?.status === "rate_limited" ||
    (lastEvent?.message && (
      lastEvent.message.toLowerCase().includes("ai rates are limited") ||
      lastEvent.message.toLowerCase().includes("rate limit") ||
      lastEvent.message.toLowerCase().includes("overloaded") ||
      lastEvent.message.toLowerCase().includes("quota")
    ))
  );

  // ─── Render ──────────────────────────────────────────────────────────────
  return (
    <div style={styles.panel}>
      <h2 style={styles.title}>➕ Add Component to Catalog</h2>

      {/* ── Form ── */}
      <div style={styles.form}>
        <input
          style={styles.input}
          placeholder="Component ID (e.g., dht22)"
          value={componentId}
          onChange={e => setComponentId(e.target.value)}
          disabled={isStreaming}
        />
        <input
          style={styles.input}
          placeholder="Component Name (e.g., DHT22 Temperature Sensor)"
          value={componentName}
          onChange={e => setComponentName(e.target.value)}
          disabled={isStreaming}
        />
        <input
          style={styles.input}
          placeholder="Datasheet URL (optional if uploading PDF)"
          value={datasheetUrl}
          onChange={e => setDatasheetUrl(e.target.value)}
          disabled={isStreaming}
        />

        {/* Drag-drop zone */}
        <div
          style={{ ...styles.dropZone, ...(isDragging ? styles.dropZoneActive : {}) }}
          onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            style={{ display: "none" }}
            onChange={e => setPdfFile(e.target.files[0])}
          />
          {pdfFile
            ? <span>📄 {pdfFile.name} ({(pdfFile.size / 1024).toFixed(0)} KB)</span>
            : <span>📂 Drag & drop datasheet PDF here, or click to browse</span>
          }
        </div>

        {/* Bypass / Skip Validation Option (For Scribd or direct web docs) */}
        <label style={styles.checkboxRow}>
          <input
            type="checkbox"
            checked={skipValidation}
            onChange={e => setSkipValidation(e.target.checked)}
            disabled={isStreaming}
            style={styles.checkbox}
          />
          <span style={styles.checkboxLabel}>
            ⚡ <strong>Bypass AI Datasheet Validation</strong> (Direct ingest for Scribd links, web docs, or unverified files)
          </span>
        </label>

        <button
          style={{ ...styles.button, ...(isStreaming ? styles.buttonDisabled : {}) }}
          onClick={handleSubmit}
          disabled={isStreaming}
        >
          {isStreaming ? "⏳ Onboarding..." : "🚀 Onboard Component"}
        </button>
      </div>

      {/* ── Live Status Stream ── */}
      {events.length > 0 && (
        <div style={styles.statusPanel}>
          <h3 style={styles.statusTitle}>
            {isStreaming ? "⚙️ Ingestion in Progress..." : finalStatus === "complete" ? "✅ Complete" : "❌ Failed"}
          </h3>

          {/* Dedicated Live Progress Header */}
          {(isStreaming || finalStatus === "complete") && (
            <div style={styles.activeProgressBox}>
              <div style={styles.activeProgressHeader}>
                <span style={styles.activeProgressLabel}>
                  ⚡ {finalStatus === "complete" ? "Datasheet Onboarding Complete" : activeLabel}
                </span>
                <span style={styles.activeProgressPct}>
                  {finalStatus === "complete" ? 100 : activePct}%
                </span>
              </div>
              <div style={styles.activeProgressBarTrack}>
                <div
                  style={{
                    ...styles.activeProgressBarFill,
                    width: `${finalStatus === "complete" ? 100 : activePct}%`,
                    background: finalStatus === "complete" ? "#10b981" : "linear-gradient(90deg, var(--accent), var(--accent-2))"
                  }}
                />
              </div>

              {/* Rate Limit Alert right below the progress bar */}
              {isRateLimited && (
                <div style={styles.rateLimitBanner}>
                  <span style={styles.rateLimitIcon}>⚠️</span>
                  <span><strong>AI Rates are limited</strong> — Automatically retrying in a moment...</span>
                </div>
              )}
            </div>
          )}

          <div style={styles.eventList}>
            {events.map((ev, i) => <StatusLine key={i} event={ev} />)}
            <div ref={eventsEndRef} />
          </div>

          {finalStatus === "complete" && <MetadataPreview metadata={metadata} />}
          {finalStatus && (
            <button style={styles.resetButton} onClick={reset}>
              {finalStatus === "complete" ? "➕ Add Another Component" : "🔄 Try Again"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = {
  panel: { padding: "28px", background: "var(--bg-surface)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)", boxShadow: "0 10px 30px rgba(0,0,0,0.5)" },
  title: { fontSize: "20px", fontWeight: 700, marginBottom: "20px", color: "var(--text-primary)" },
  form: { display: "flex", flexDirection: "column", gap: "14px" },
  input: {
    padding: "12px 16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)",
    background: "var(--bg-card)", color: "var(--text-primary)", fontSize: "14px", outline: "none"
  },
  dropZone: {
    padding: "28px 20px", borderRadius: "var(--radius-md)", border: "2px dashed var(--border)",
    textAlign: "center", cursor: "pointer", color: "var(--text-secondary)", fontSize: "14px",
    transition: "all 0.2s ease", background: "var(--bg-card)"
  },
  dropZoneActive: { borderColor: "var(--accent)", background: "rgba(99, 102, 241, 0.1)", color: "var(--accent-2)" },
  checkboxRow: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "10px 14px",
    borderRadius: "var(--radius-md)",
    background: "rgba(255, 255, 255, 0.03)",
    border: "1px solid var(--border)",
    cursor: "pointer",
  },
  checkbox: {
    width: "16px",
    height: "16px",
    cursor: "pointer",
    accentColor: "var(--accent)",
  },
  checkboxLabel: {
    fontSize: "12px",
    color: "var(--text-secondary)",
    lineHeight: 1.4,
  },
  button: {
    padding: "14px", borderRadius: "var(--radius-md)", background: "var(--accent)",
    color: "#fff", fontWeight: 700, fontSize: "15px", border: "none",
    cursor: "pointer", transition: "all 0.2s ease", boxShadow: "0 4px 14px var(--accent-glow)"
  },
  buttonDisabled: { opacity: 0.6, cursor: "not-allowed" },
  statusPanel: {
    marginTop: "24px", background: "var(--bg-card)", borderRadius: "var(--radius-md)",
    padding: "20px", border: "1px solid var(--border)"
  },
  statusTitle: { margin: "0 0 14px", fontSize: "16px", fontWeight: 600, color: "var(--text-primary)" },
  
  // Dedicated Header Progress Bar
  activeProgressBox: {
    marginBottom: "16px", padding: "14px", background: "rgba(99, 102, 241, 0.1)",
    borderRadius: "var(--radius-md)", border: "1px solid var(--border-active)"
  },
  activeProgressHeader: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    marginBottom: "8px", fontSize: "13px", fontWeight: 600
  },
  activeProgressLabel: { color: "var(--accent-2)" },
  activeProgressPct: { color: "var(--accent)", fontWeight: 700 },
  activeProgressBarTrack: {
    width: "100%", height: "8px", background: "rgba(255, 255, 255, 0.1)",
    borderRadius: "4px", overflow: "hidden"
  },
  activeProgressBarFill: {
    height: "100%", background: "linear-gradient(90deg, var(--accent), var(--accent-2))",
    transition: "width 0.4s ease", borderRadius: "4px"
  },
  rateLimitBanner: {
    marginTop: "10px",
    padding: "8px 12px",
    background: "rgba(245, 158, 11, 0.15)",
    border: "1px solid rgba(245, 158, 11, 0.4)",
    borderRadius: "var(--radius-sm)",
    color: "#f59e0b",
    fontSize: "13px",
    fontWeight: 500,
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  rateLimitIcon: {
    fontSize: "15px",
  },

  eventList: {
    display: "flex", flexDirection: "column", gap: "10px", maxHeight: "300px",
    overflowY: "auto", paddingRight: "4px"
  },
  statusLine: {
    display: "flex", alignItems: "center", gap: "10px", fontSize: "13px",
    color: "var(--text-secondary)", padding: "6px 0", borderBottom: "1px solid var(--border)"
  },
  icon: { fontSize: "16px", minWidth: "22px" },
  label: { fontWeight: 600, minWidth: "160px", color: "var(--text-primary)" },
  detail: { color: "var(--text-muted)", fontSize: "12px", flex: 1 },

  metadataBox: {
    marginTop: "20px", padding: "16px", background: "rgba(99, 102, 241, 0.08)",
    borderRadius: "var(--radius-md)", border: "1px solid var(--border-active)"
  },
  metadataTitle: { margin: "0 0 12px", fontSize: "14px", fontWeight: 700, color: "var(--accent-2)" },
  metadataGrid: {
    display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px",
    fontSize: "13px", color: "var(--text-secondary)"
  },
  resetButton: {
    marginTop: "16px", padding: "10px 18px", borderRadius: "var(--radius-sm)",
    background: "var(--bg-glass)", color: "var(--text-primary)", border: "1px solid var(--border)",
    cursor: "pointer", fontSize: "13px", fontWeight: 600
  },
};