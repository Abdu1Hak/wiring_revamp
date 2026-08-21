/**
 * project.jsx
 * ─────────────────────────────────────────────────────────────────────
 * Generation Pipeline UI (Interactive HITL Hardware Alignment Workspace):
 * 1. Left Panel: Interactive component bubbles from catalog (multi-select)
 * 2. Right Panel: Textbox for User to describe Project Scope
 * 3. SSE Stream: Connects to /api/generate/start & /api/generate/confirm
 * 4. Interactive HITL Workspace:
 *    - Remove unassigned/unused components with 1 click
 *    - Assign custom roles to unassigned components
 *    - Add missing components from catalog with role assignment
 *    - Dismiss unwanted AI role suggestions
 *    - Re-validate updated hardware batch or proceed to wiring synthesis
 */

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://127.0.0.1:8000";

// Map component categories to emoji icons
const CATEGORY_ICON = {
  microcontroller: "🔲",
  board: "🔲",
  sensor: "🌡️",
  actuator: "⚙️",
  display: "🖥️",
  connectivity: "📡",
  power: "⚡",
  passive: "🔩",
  storage: "💾",
  default: "🔌",
};

export default function ProjectPanel() {
  const [availableComponents, setAvailableComponents] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [isFetchingCatalog, setIsFetchingCatalog] = useState(true);

  // Form & Stream state
  const [projectScope, setProjectScope] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [nodeMessage, setNodeMessage] = useState("");
  const [error, setError] = useState(null);

  // HITL State
  const [hitlData, setHitlData] = useState(null); // { role_assignments, missing_roles, unassigned_components, enriched_scope, is_aligned }
  const [editedRoles, setEditedRoles] = useState({});
  const [missingRolesList, setMissingRolesList] = useState([]);
  const [unassignedList, setUnassignedList] = useState([]);
  const [selectedForMissing, setSelectedForMissing] = useState({}); // { [roleIdx]: componentId }
  const [customRoleInput, setCustomRoleInput] = useState({}); // { [compId]: string }

  const [isEditing, setIsEditing] = useState(false);
  const [showRejectBox, setShowRejectBox] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  // Final Output State
  const [generationResult, setGenerationResult] = useState(null);

  // Fetch catalog components on mount
  const fetchCatalog = useCallback(async () => {
    setIsFetchingCatalog(true);
    try {
      const res = await fetch(`${API_BASE}/api/components`);
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      const list = Array.isArray(data) ? data : data.components || [];
      setAvailableComponents(list);
    } catch (err) {
      console.error("Failed to load catalog components for project page:", err);
    } finally {
      setIsFetchingCatalog(false);
    }
  }, []);

  useEffect(() => {
    fetchCatalog();
  }, [fetchCatalog]);

  // Toggle component selection
  const toggleComponentSelection = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    setSelectedIds(availableComponents.map((c) => c.id));
  };

  const clearSelection = () => {
    setSelectedIds([]);
  };

  // Helper to read and stream Server-Sent Events from backend response
  const readSseStream = async (response) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // Keep last partial chunk in buffer

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data: ")) continue;
        const rawData = trimmed.replace(/^data:\s*/, "");
        if (rawData === "[DONE]") continue;

        try {
          const event = JSON.parse(rawData);

          if (event.type === "node") {
            setNodeMessage(event.message || `Processing node: ${event.node}...`);
          } else if (event.type === "hitl_required") {
            // Pause stream and surface interactive HITL UI
            setHitlData(event);
            setEditedRoles({ ...(event.role_assignments || {}) });
            setMissingRolesList(Array.isArray(event.missing_roles) ? [...event.missing_roles] : []);
            setUnassignedList(Array.isArray(event.unassigned_components) ? [...event.unassigned_components] : []);
            setIsLoading(false);
            setNodeMessage("User review required — adjust and confirm hardware roles below.");
          } else if (event.type === "complete") {
            setGenerationResult(event);
            setHitlData(null);
            setIsLoading(false);
            setNodeMessage("✓ Wiring Diagram Synthesis Complete!");
          } else if (event.type === "failed") {
            setError(event.error || "Generation pipeline failed.");
            setIsLoading(false);
          }
        } catch (e) {
          console.error("Error parsing SSE line:", rawData, e);
        }
      }
    }
  };

  // 1. Kick off Generation Stream (POST /api/generate/start)
  const handleStartGeneration = async (e, overrideSelectedIds = null) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!projectScope.trim()) return;

    const activeIds = overrideSelectedIds || selectedIds;
    const newSessionId = `gen_${Date.now()}`;
    setSessionId(newSessionId);
    setIsLoading(true);
    setError(null);
    setHitlData(null);
    setGenerationResult(null);
    setShowRejectBox(false);
    setNodeMessage("Initiating generation graph...");

    try {
      const response = await fetch(`${API_BASE}/api/generate/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: newSessionId,
          component_ids: activeIds,
          project_scope: projectScope,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server error (${response.status}): ${response.statusText}`);
      }

      await readSseStream(response);
    } catch (err) {
      console.error("Start generation error:", err);
      setError(err.message || "Failed to start generation pipeline.");
      setIsLoading(false);
    }
  };

  // 2. Submit HITL Response (POST /api/generate/confirm)
  const handleConfirmAction = async (action, customReason = "") => {
    setIsLoading(true);
    setError(null);
    setNodeMessage(`Resuming graph with action: '${action}'...`);

    try {
      const response = await fetch(`${API_BASE}/api/generate/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          action: action,
          role_assignments: action === "edited" || action === "confirmed" ? editedRoles : null,
          reason: action === "rejected" ? customReason : null,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server error (${response.status}): ${response.statusText}`);
      }

      if (action === "confirmed" || action === "edited") {
        setHitlData(null);
      } else if (action === "rejected") {
        setShowRejectBox(false);
        setRejectReason("");
      }

      await readSseStream(response);
    } catch (err) {
      console.error("Confirm generation error:", err);
      setError(err.message || "Failed to submit HITL confirmation.");
      setIsLoading(false);
    }
  };

  // ─── Interactive HITL Mutation Handlers ─────────────────────────

  // Remove an unassigned component from selectedIds and HITL view
  const handleRemoveUnassigned = (cid) => {
    setSelectedIds((prev) => prev.filter((id) => id !== cid));
    setUnassignedList((prev) => prev.filter((item) => item.component_id !== cid));
    setEditedRoles((prev) => {
      const copy = { ...prev };
      delete copy[cid];
      return copy;
    });
  };

  // Assign a custom role to an unassigned component, moving it to role_assignments
  const handleAssignCustomRole = (cid) => {
    const roleText = customRoleInput[cid] || "Custom Project Component";
    setEditedRoles((prev) => ({ ...prev, [cid]: roleText }));
    setUnassignedList((prev) => prev.filter((item) => item.component_id !== cid));
  };

  // Add a component for a missing role from the catalog
  const handleAddMissingComponent = (roleIdx, roleObj) => {
    const cidToAdd = selectedForMissing[roleIdx];
    if (!cidToAdd) return;

    if (!selectedIds.includes(cidToAdd)) {
      setSelectedIds((prev) => [...prev, cidToAdd]);
    }

    const assignedRole = roleObj.role ? `${roleObj.role}: Required for project function` : "Required sensor/actuator";
    setEditedRoles((prev) => ({ ...prev, [cidToAdd]: assignedRole }));
    setMissingRolesList((prev) => prev.filter((_, idx) => idx !== roleIdx));
  };

  // Dismiss a missing role suggestion if not needed by user
  const handleDismissMissingRole = (roleIdx) => {
    setMissingRolesList((prev) => prev.filter((_, idx) => idx !== roleIdx));
  };

  // Calculate alignment status
  const hasMismatches = missingRolesList.length > 0 || unassignedList.length > 0;

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🛠️ Project Wiring Generator</h2>
      <p style={styles.subtitle}>
        Select hardware from your catalog and describe your project scope. The AI will analyze requirements, align component roles, verify compatibility, and synthesize a complete wiring plan.
      </p>

      <div style={styles.layout}>
        {/* ── LEFT PANEL: Component Selection Bubbles ── */}
        <div style={styles.leftPanel}>
          <div style={styles.panelHeader}>
            <h3 style={styles.panelTitle}>
              🧩 Selected Hardware ({selectedIds.length})
            </h3>
            <div style={styles.quickActions}>
              <button style={styles.textBtn} onClick={selectAll} type="button" disabled={isLoading}>
                Select All
              </button>
              <span style={styles.divider}>•</span>
              <button style={styles.textBtn} onClick={clearSelection} type="button" disabled={isLoading}>
                Clear
              </button>
            </div>
          </div>

          {isFetchingCatalog ? (
            <div style={styles.loadingCatalog}>⏳ Loading catalog components...</div>
          ) : availableComponents.length === 0 ? (
            <div style={styles.emptyCatalogNotice}>
              No components found in catalog. Onboard components first.
            </div>
          ) : (
            <div style={styles.bubbleGrid}>
              {availableComponents.map((comp) => {
                const isSelected = selectedIds.includes(comp.id);
                const icon = CATEGORY_ICON[comp.category?.toLowerCase()] || CATEGORY_ICON.default;
                return (
                  <button
                    key={comp.id}
                    type="button"
                    style={{
                      ...styles.bubble,
                      ...(isSelected ? styles.bubbleSelected : {}),
                    }}
                    onClick={() => !isLoading && toggleComponentSelection(comp.id)}
                    disabled={isLoading}
                  >
                    <span style={styles.bubbleIcon}>{icon}</span>
                    <span style={styles.bubbleName}>{comp.name || comp.id}</span>
                    {isSelected && <span style={styles.checkmark}>✓</span>}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* ── RIGHT PANEL: Project Scope & HITL Workflow ── */}
        <div style={styles.rightPanel}>
          <form onSubmit={(e) => handleStartGeneration(e)} style={styles.form}>
            <label style={styles.label}>
              Project Scope & Purpose
              <textarea
                style={styles.textarea}
                placeholder="Describe what you want to build (e.g. 'A simple Arduino-powered lid opener using a servo motor')..."
                value={projectScope}
                onChange={(e) => setProjectScope(e.target.value)}
                disabled={isLoading || !!hitlData}
                rows={4}
              />
            </label>

            {/* Selected Components Summary Badge */}
            <div style={styles.selectedSummary}>
              <span>
                {selectedIds.length === 0
                  ? "⚠️ No components selected. Click bubbles on the left to include hardware."
                  : `Included Hardware (${selectedIds.length}): ${selectedIds
                    .map((id) => availableComponents.find((c) => c.id === id)?.name || id)
                    .join(", ")}`}
              </span>
            </div>

            {!hitlData && (
              <button
                type="submit"
                style={{
                  ...styles.button,
                  ...(isLoading || !projectScope.trim() ? styles.buttonDisabled : {}),
                }}
                disabled={isLoading || !projectScope.trim()}
              >
                {isLoading ? `⏳ ${nodeMessage || "Analyzing Scope & Assigning Roles..."}` : "⚡ Generate Project Wiring Plan"}
              </button>
            )}
          </form>

          {/* ── Live Progress Indicator ── */}
          {isLoading && nodeMessage && (
            <div style={styles.progressBox}>
              <span style={styles.pulseDot} />
              <span>{nodeMessage}</span>
            </div>
          )}

          {/* ── Error Output ── */}
          {error && (
            <div style={styles.errorBox}>
              <span>❌ {error}</span>
            </div>
          )}

          {/* ── HUMAN-IN-THE-LOOP (HITL) HARDWARE ALIGNMENT WORKSPACE ── */}
          {hitlData && (
            <div style={styles.hitlCard}>
              <div style={styles.hitlHeader}>
                <div>
                  <h3 style={styles.hitlTitle}>🤝 Hardware Alignment & Role Assignment</h3>
                  <p style={styles.hitlSub}>
                    Review assigned roles, add or remove components, and ensure your hardware matches your intended scope.
                  </p>
                </div>
                <div
                  style={{
                    ...styles.alignBadge,
                    ...(!hasMismatches ? styles.alignBadgeSuccess : styles.alignBadgeWarning),
                  }}
                >
                  {!hasMismatches ? "✓ Hardware Aligned" : "⚠️ Alignment Adjustments Needed"}
                </div>
              </div>

              {/* 1. Missing Hardware Roles Cards */}
              {missingRolesList.length > 0 && (
                <div style={styles.warningCard}>
                  <h4 style={styles.warningTitle}>⚠️ AI Identified Missing Hardware Roles</h4>
                  <p style={styles.warningSubText}>
                    The AI noted these functions might be missing. You can add a matching component from your catalog or dismiss the suggestion.
                  </p>
                  <div style={styles.rolesGrid}>
                    {missingRolesList.map((m, idx) => (
                      <div key={idx} style={styles.missingItemCard}>
                        <div style={styles.missingHeader}>
                          <strong>Needed Role: {m.role}</strong>
                          <span style={styles.suggestionTag}>{m.suggestion ? `Suggested: ${m.suggestion}` : "Component Required"}</span>
                        </div>
                        <p style={styles.missingReason}>{m.reason}</p>

                        <div style={styles.missingActions}>
                          <select
                            style={styles.selectDropdown}
                            value={selectedForMissing[idx] || ""}
                            onChange={(e) =>
                              setSelectedForMissing({ ...selectedForMissing, [idx]: e.target.value })
                            }
                          >
                            <option value="">Select Catalog Component...</option>
                            {availableComponents.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.name || c.id} ({c.category || "hardware"})
                              </option>
                            ))}
                          </select>

                          <button
                            type="button"
                            style={styles.addMissingBtn}
                            onClick={() => handleAddMissingComponent(idx, m)}
                            disabled={!selectedForMissing[idx]}
                          >
                            ➕ Add to Project
                          </button>

                          <button
                            type="button"
                            style={styles.dismissBtn}
                            onClick={() => handleDismissMissingRole(idx)}
                          >
                            🚫 Dismiss
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 2. Unassigned Components Cards */}
              {unassignedList.length > 0 && (
                <div style={styles.unassignedCard}>
                  <h4 style={styles.unassignedTitle}>❓ Unassigned Components Detected</h4>
                  <p style={styles.warningSubText}>
                    These selected components do not have a defined role in your scope. Remove them or assign a custom role:
                  </p>
                  <div style={styles.rolesGrid}>
                    {unassignedList.map((u) => {
                      const compObj = availableComponents.find((c) => c.id === u.component_id);
                      const compName = compObj?.name || u.component_id;
                      const icon = CATEGORY_ICON[compObj?.category?.toLowerCase()] || CATEGORY_ICON.default;

                      return (
                        <div key={u.component_id} style={styles.unassignedItemCard}>
                          <div style={styles.unassignedHeader}>
                            <span>{icon} <strong>{compName}</strong> ({u.component_id})</span>
                            <span style={styles.reasonBadge}>{u.reason || "No role specified in scope"}</span>
                          </div>

                          <div style={styles.unassignedControls}>
                            <input
                              type="text"
                              style={styles.customRoleInput}
                              placeholder="Or define custom role (e.g. 'Status alert indicator')..."
                              value={customRoleInput[u.component_id] || ""}
                              onChange={(e) =>
                                setCustomRoleInput({ ...customRoleInput, [u.component_id]: e.target.value })
                              }
                            />

                            {customRoleInput[u.component_id] ? (
                              <button
                                type="button"
                                style={styles.assignRoleBtn}
                                onClick={() => handleAssignCustomRole(u.component_id)}
                              >
                                ✓ Assign Role
                              </button>
                            ) : null}

                            <button
                              type="button"
                              style={styles.removeBtn}
                              onClick={() => handleRemoveUnassigned(u.component_id)}
                            >
                              ❌ Deselect & Remove
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 3. Assigned Component Roles */}
              <div style={styles.section}>
                <div style={styles.sectionHeader}>
                  <h4 style={styles.sectionTitle}>
                    📌 Confirmed Component Roles ({Object.keys(editedRoles).length})
                  </h4>
                  <button
                    style={styles.textBtn}
                    onClick={() => setIsEditing(!isEditing)}
                    type="button"
                  >
                    {isEditing ? "Done Editing" : "✏️ Edit Role Descriptions"}
                  </button>
                </div>
                <div style={styles.rolesGrid}>
                  {Object.entries(editedRoles || {}).map(([cid, roleStr]) => {
                    const compObj = availableComponents.find((c) => c.id === cid);
                    const compName = compObj?.name || cid;
                    const icon = CATEGORY_ICON[compObj?.category?.toLowerCase()] || CATEGORY_ICON.default;

                    return (
                      <div key={cid} style={styles.roleItem}>
                        <div style={styles.roleHeader}>
                          <span style={styles.roleIcon}>{icon}</span>
                          <strong style={styles.roleCompName}>{compName}</strong>
                          <span style={styles.roleIdBadge}>({cid})</span>
                        </div>
                        {isEditing ? (
                          <input
                            type="text"
                            style={styles.roleInput}
                            value={editedRoles[cid] || ""}
                            onChange={(e) =>
                              setEditedRoles({ ...editedRoles, [cid]: e.target.value })
                            }
                          />
                        ) : (
                          <p style={styles.roleDesc}>{roleStr}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 4. Enriched Technical Scope */}
              {hitlData.enriched_scope && (
                <div style={styles.scopePreviewBox}>
                  <h4 style={styles.scopePreviewTitle}>📝 Enriched Technical Scope</h4>
                  <p style={styles.scopePreviewText}>{hitlData.enriched_scope}</p>
                </div>
              )}

              {/* Rejection Feedback Prompt */}
              {showRejectBox && (
                <div style={styles.rejectBox}>
                  <h4 style={styles.rejectTitle}>🔄 Provide Rejection Feedback</h4>
                  <textarea
                    style={styles.textarea}
                    placeholder="Tell the AI why you disagree with these roles (e.g. 'The servo should tilt the tray, not open the lid')..."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    rows={3}
                  />
                  <div style={styles.rejectActions}>
                    <button
                      type="button"
                      style={styles.cancelBtn}
                      onClick={() => setShowRejectBox(false)}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      style={styles.rejectSubmitBtn}
                      onClick={() => handleConfirmAction("rejected", rejectReason)}
                      disabled={!rejectReason.trim()}
                    >
                      Retry Role Assignment with Feedback
                    </button>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              {!showRejectBox && (
                <div style={styles.hitlActions}>
                  {hasMismatches ? (
                    <>
                      <button
                        type="button"
                        style={styles.revalidateBtn}
                        onClick={() => handleStartGeneration(null, selectedIds)}
                        disabled={isLoading}
                      >
                        🔄 Re-Validate Updated Hardware Batch
                      </button>
                      <button
                        type="button"
                        style={styles.overrideBtn}
                        onClick={() => handleConfirmAction("edited")}
                        disabled={isLoading}
                      >
                        ⚡ Proceed With Current Edits
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      style={styles.confirmBtn}
                      onClick={() => handleConfirmAction(isEditing ? "edited" : "confirmed")}
                      disabled={isLoading}
                    >
                      {isEditing ? "✏️ Save Edits & Synthesize Wiring" : "✓ Confirm Roles & Synthesize Wiring"}
                    </button>
                  )}

                  <button
                    type="button"
                    style={styles.rejectBtn}
                    onClick={() => setShowRejectBox(true)}
                    disabled={isLoading}
                  >
                    🔄 Reject & Revise
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ── Final Generation Output ── */}
          {generationResult && (
            <div style={styles.resultBox}>
              <h3 style={styles.resultTitle}>📋 Generation Output</h3>
              <pre style={styles.jsonPreview}>
                {JSON.stringify(generationResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Component Styles ──────────────────────────────────────────────────────────
const styles = {
  container: {
    padding: "28px",
    background: "var(--bg-surface)",
    borderRadius: "var(--radius-lg)",
    border: "1px solid var(--border)",
    boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
  },
  title: {
    fontSize: "20px",
    fontWeight: 700,
    marginBottom: "8px",
    color: "var(--text-primary)",
    fontFamily: "var(--font-heading)",
  },
  subtitle: {
    fontSize: "14px",
    color: "var(--text-secondary)",
    marginBottom: "24px",
  },
  layout: {
    display: "grid",
    gridTemplateColumns: "320px 1fr",
    gap: "24px",
    alignItems: "start",
  },
  leftPanel: {
    background: "var(--bg-card)",
    borderRadius: "var(--radius-md)",
    padding: "18px",
    border: "1px solid var(--border)",
  },
  panelHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "14px",
  },
  panelTitle: {
    fontSize: "14px",
    fontWeight: 700,
    color: "var(--text-primary)",
    margin: 0,
    fontFamily: "var(--font-heading)",
  },
  quickActions: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  textBtn: {
    background: "none",
    border: "none",
    color: "var(--accent)",
    fontSize: "12px",
    fontWeight: 600,
    cursor: "pointer",
    padding: 0,
  },
  divider: {
    color: "var(--text-muted)",
    fontSize: "10px",
  },
  loadingCatalog: {
    fontSize: "13px",
    color: "var(--text-muted)",
    padding: "12px 0",
  },
  emptyCatalogNotice: {
    fontSize: "13px",
    color: "var(--text-muted)",
    padding: "12px 0",
  },
  bubbleGrid: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
    maxHeight: "480px",
    overflowY: "auto",
    paddingRight: "4px",
  },
  bubble: {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "8px 12px",
    borderRadius: "20px",
    background: "rgba(255, 255, 255, 0.05)",
    border: "1px solid var(--border)",
    color: "var(--text-secondary)",
    fontSize: "13px",
    fontWeight: 500,
    cursor: "pointer",
    transition: "all 0.2s ease",
    textAlign: "left",
  },
  bubbleSelected: {
    background: "rgba(99, 102, 241, 0.18)",
    border: "1px solid var(--accent)",
    color: "#fff",
    boxShadow: "0 0 10px rgba(99, 102, 241, 0.3)",
  },
  bubbleIcon: {
    fontSize: "14px",
  },
  bubbleName: {
    fontSize: "13px",
  },
  checkmark: {
    fontSize: "12px",
    color: "#10b981",
    fontWeight: 700,
    marginLeft: "2px",
  },
  rightPanel: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    fontSize: "14px",
    fontWeight: 600,
    color: "var(--text-primary)",
  },
  textarea: {
    padding: "14px",
    borderRadius: "var(--radius-md)",
    border: "1px solid var(--border)",
    background: "var(--bg-card)",
    color: "var(--text-primary)",
    fontSize: "14px",
    outline: "none",
    fontFamily: "inherit",
    resize: "vertical",
    minHeight: "110px",
  },
  selectedSummary: {
    padding: "10px 14px",
    background: "rgba(99, 102, 241, 0.08)",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border-active)",
    fontSize: "13px",
    color: "var(--accent-2)",
  },
  button: {
    padding: "14px",
    borderRadius: "var(--radius-md)",
    background: "var(--accent)",
    color: "#fff",
    fontWeight: 700,
    fontSize: "15px",
    border: "none",
    cursor: "pointer",
    transition: "all 0.2s ease",
    boxShadow: "0 4px 14px var(--accent-glow)",
  },
  buttonDisabled: {
    opacity: 0.6,
    cursor: "not-allowed",
  },
  progressBox: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "12px 16px",
    background: "rgba(99, 102, 241, 0.1)",
    border: "1px solid rgba(99, 102, 241, 0.3)",
    borderRadius: "var(--radius-md)",
    fontSize: "13px",
    color: "var(--accent-2)",
  },
  pulseDot: {
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    background: "var(--accent)",
    boxShadow: "0 0 8px var(--accent)",
  },
  errorBox: {
    padding: "14px",
    background: "rgba(239, 68, 68, 0.15)",
    border: "1px solid rgba(239, 68, 68, 0.4)",
    borderRadius: "var(--radius-md)",
    color: "#ef4444",
    fontSize: "14px",
  },

  /* HITL Card Styles */
  hitlCard: {
    marginTop: "10px",
    padding: "24px",
    background: "var(--bg-card)",
    borderRadius: "var(--radius-lg)",
    border: "1.5px solid var(--accent)",
    boxShadow: "0 10px 30px rgba(99, 102, 241, 0.2)",
    display: "flex",
    flexDirection: "column",
    gap: "20px",
  },
  hitlHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: "16px",
  },
  hitlTitle: {
    margin: "0 0 6px",
    fontSize: "17px",
    fontWeight: 700,
    color: "#fff",
    fontFamily: "var(--font-heading)",
  },
  hitlSub: {
    margin: 0,
    fontSize: "13px",
    color: "var(--text-secondary)",
  },
  alignBadge: {
    padding: "6px 12px",
    borderRadius: "20px",
    fontSize: "12px",
    fontWeight: 700,
    whiteSpace: "nowrap",
  },
  alignBadgeSuccess: {
    background: "rgba(16, 185, 129, 0.15)",
    color: "#10b981",
    border: "1px solid rgba(16, 185, 129, 0.4)",
  },
  alignBadgeWarning: {
    background: "rgba(245, 158, 11, 0.15)",
    color: "#f59e0b",
    border: "1px solid rgba(245, 158, 11, 0.4)",
  },
  section: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  sectionTitle: {
    margin: 0,
    fontSize: "14px",
    fontWeight: 700,
    color: "var(--accent-2)",
  },
  rolesGrid: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  roleItem: {
    padding: "12px 14px",
    background: "rgba(0, 0, 0, 0.25)",
    borderRadius: "var(--radius-md)",
    border: "1px solid var(--border)",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  roleHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  roleIcon: {
    fontSize: "14px",
  },
  roleCompName: {
    fontSize: "14px",
    color: "#fff",
  },
  roleIdBadge: {
    fontSize: "11px",
    color: "var(--text-muted)",
    fontFamily: "monospace",
  },
  roleDesc: {
    margin: 0,
    fontSize: "13px",
    color: "var(--text-secondary)",
  },
  roleInput: {
    padding: "8px 12px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--accent)",
    background: "var(--bg-surface)",
    color: "#fff",
    fontSize: "13px",
    outline: "none",
  },

  /* Missing Roles Styling */
  warningCard: {
    padding: "16px 18px",
    background: "rgba(245, 158, 11, 0.08)",
    borderRadius: "var(--radius-md)",
    border: "1px solid rgba(245, 158, 11, 0.3)",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  warningTitle: {
    margin: 0,
    fontSize: "14px",
    fontWeight: 700,
    color: "#f59e0b",
  },
  warningSubText: {
    margin: 0,
    fontSize: "12px",
    color: "var(--text-secondary)",
  },
  missingItemCard: {
    padding: "12px 14px",
    background: "rgba(0,0,0,0.3)",
    borderRadius: "var(--radius-sm)",
    border: "1px solid rgba(245, 158, 11, 0.2)",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  missingHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: "13px",
    color: "#fff",
  },
  missingReason: {
    margin: 0,
    fontSize: "12px",
    color: "var(--text-secondary)",
  },
  missingActions: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
  },
  selectDropdown: {
    flex: 1,
    padding: "8px 10px",
    borderRadius: "var(--radius-sm)",
    background: "var(--bg-surface)",
    color: "var(--text-primary)",
    border: "1px solid var(--border)",
    fontSize: "12px",
    outline: "none",
  },
  addMissingBtn: {
    padding: "8px 12px",
    borderRadius: "var(--radius-sm)",
    background: "#10b981",
    color: "#fff",
    fontWeight: 600,
    fontSize: "12px",
    border: "none",
    cursor: "pointer",
    whiteSpace: "nowrap",
  },
  dismissBtn: {
    padding: "8px 12px",
    borderRadius: "var(--radius-sm)",
    background: "transparent",
    color: "var(--text-muted)",
    border: "1px solid var(--border)",
    fontSize: "12px",
    cursor: "pointer",
  },

  /* Unassigned Components Styling */
  unassignedCard: {
    padding: "16px 18px",
    background: "rgba(239, 68, 68, 0.08)",
    borderRadius: "var(--radius-md)",
    border: "1px solid rgba(239, 68, 68, 0.3)",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  unassignedTitle: {
    margin: 0,
    fontSize: "14px",
    fontWeight: 700,
    color: "#f87171",
  },
  unassignedItemCard: {
    padding: "12px 14px",
    background: "rgba(0,0,0,0.3)",
    borderRadius: "var(--radius-sm)",
    border: "1px solid rgba(239, 68, 68, 0.2)",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  unassignedHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: "13px",
    color: "#fff",
  },
  reasonBadge: {
    fontSize: "11px",
    padding: "2px 8px",
    borderRadius: "4px",
    background: "rgba(239, 68, 68, 0.2)",
    color: "#fca5a5",
  },
  unassignedControls: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
  },
  customRoleInput: {
    flex: 1,
    padding: "8px 10px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border)",
    background: "var(--bg-surface)",
    color: "#fff",
    fontSize: "12px",
    outline: "none",
  },
  assignRoleBtn: {
    padding: "8px 12px",
    borderRadius: "var(--radius-sm)",
    background: "var(--accent)",
    color: "#fff",
    fontWeight: 600,
    fontSize: "12px",
    border: "none",
    cursor: "pointer",
  },
  removeBtn: {
    padding: "8px 12px",
    borderRadius: "var(--radius-sm)",
    background: "rgba(239, 68, 68, 0.2)",
    color: "#ef4444",
    border: "1px solid rgba(239, 68, 68, 0.4)",
    fontWeight: 600,
    fontSize: "12px",
    cursor: "pointer",
    whiteSpace: "nowrap",
  },

  suggestionTag: {
    padding: "2px 8px",
    borderRadius: "4px",
    background: "rgba(245, 158, 11, 0.2)",
    color: "#fbbf24",
    fontSize: "11px",
    fontWeight: 600,
  },
  scopePreviewBox: {
    padding: "14px",
    background: "rgba(255, 255, 255, 0.03)",
    borderRadius: "var(--radius-md)",
    border: "1px solid var(--border)",
  },
  scopePreviewTitle: {
    margin: "0 0 6px",
    fontSize: "13px",
    fontWeight: 700,
    color: "var(--accent-2)",
  },
  scopePreviewText: {
    margin: 0,
    fontSize: "13px",
    color: "var(--text-secondary)",
    lineHeight: 1.5,
  },
  rejectBox: {
    padding: "16px",
    background: "rgba(239, 68, 68, 0.08)",
    borderRadius: "var(--radius-md)",
    border: "1px solid rgba(239, 68, 68, 0.3)",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  rejectTitle: {
    margin: 0,
    fontSize: "14px",
    fontWeight: 700,
    color: "#f87171",
  },
  rejectActions: {
    display: "flex",
    gap: "10px",
    justifyContent: "flex-end",
  },
  cancelBtn: {
    padding: "8px 16px",
    borderRadius: "var(--radius-sm)",
    background: "transparent",
    border: "1px solid var(--border)",
    color: "var(--text-secondary)",
    fontSize: "13px",
    cursor: "pointer",
  },
  rejectSubmitBtn: {
    padding: "8px 16px",
    borderRadius: "var(--radius-sm)",
    background: "#dc2626",
    color: "#fff",
    fontWeight: 700,
    fontSize: "13px",
    border: "none",
    cursor: "pointer",
  },
  hitlActions: {
    display: "flex",
    gap: "12px",
    alignItems: "center",
  },
  confirmBtn: {
    flex: 1,
    padding: "12px",
    borderRadius: "var(--radius-md)",
    background: "var(--accent)",
    color: "#fff",
    fontWeight: 700,
    fontSize: "14px",
    border: "none",
    cursor: "pointer",
    boxShadow: "0 4px 14px var(--accent-glow)",
  },
  revalidateBtn: {
    flex: 1,
    padding: "12px",
    borderRadius: "var(--radius-md)",
    background: "var(--accent)",
    color: "#fff",
    fontWeight: 700,
    fontSize: "14px",
    border: "none",
    cursor: "pointer",
    boxShadow: "0 4px 14px var(--accent-glow)",
  },
  overrideBtn: {
    padding: "12px 18px",
    borderRadius: "var(--radius-md)",
    background: "rgba(99, 102, 241, 0.15)",
    border: "1px solid var(--accent)",
    color: "var(--accent-2)",
    fontWeight: 600,
    fontSize: "13px",
    cursor: "pointer",
  },
  rejectBtn: {
    padding: "12px 20px",
    borderRadius: "var(--radius-md)",
    background: "rgba(239, 68, 68, 0.15)",
    border: "1px solid rgba(239, 68, 68, 0.4)",
    color: "#ef4444",
    fontWeight: 700,
    fontSize: "14px",
    cursor: "pointer",
  },
  resultBox: {
    marginTop: "20px",
    padding: "20px",
    background: "var(--bg-card)",
    borderRadius: "var(--radius-md)",
    border: "1px solid var(--border-active)",
  },
  resultTitle: {
    margin: "0 0 12px",
    fontSize: "16px",
    fontWeight: 600,
    color: "var(--accent-2)",
  },
  jsonPreview: {
    margin: 0,
    padding: "14px",
    background: "rgba(0, 0, 0, 0.4)",
    borderRadius: "var(--radius-sm)",
    color: "#a7f3d0",
    fontSize: "13px",
    overflowX: "auto",
    fontFamily: "monospace",
  },
};
