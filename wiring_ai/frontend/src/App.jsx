import { useState, useEffect, useCallback } from "react";
import OnboardPanel from "./onboard.jsx";
import ProjectPanel from "./project.jsx";
import "./App.css";

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

export default function App() {
  const [components, setComponents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [selectedComponent, setSelectedComponent] = useState(null);
  const [activeTab, setActiveTab] = useState("catalog"); // "catalog" | "onboard"
  const [deletingComponent, setDeletingComponent] = useState(null); // { id, name }
  const [isDeleting, setIsDeleting] = useState(false);

  // Fetch component list from backend database
  const fetchComponents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/components`);
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();

      // Handle both array response and { components: [...] } dictionary response
      const list = Array.isArray(data) ? data : data.components || [];
      setComponents(list);
    } catch (err) {
      console.error("Failed to load components:", err);
      setError("Could not connect to PostgreSQL backend. Ensure main.py is running on port 8000.");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleOpenDeleteModal = (e, id, name) => {
    if (e) e.stopPropagation();
    setDeletingComponent({ id, name });
  };

  const handleConfirmDelete = async () => {
    if (!deletingComponent) return;
    setIsDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/api/components/${deletingComponent.id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setComponents((prev) => prev.filter((c) => c.id !== deletingComponent.id));
        if (selectedComponent?.id === deletingComponent.id) setSelectedComponent(null);
        setDeletingComponent(null);
      } else {
        alert("Failed to delete component from backend.");
      }
    } catch (err) {
      alert(`Error deleting component: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };


  useEffect(() => {
    fetchComponents();
  }, [fetchComponents]);

  // Extract unique categories for filter tabs
  const categories = ["all", ...new Set(components.map((c) => (c.category || "other").toLowerCase()))];

  // Filter components by search query and active category tab
  const filteredComponents = components.filter((c) => {
    const matchesCategory =
      activeCategory === "all" || (c.category || "").toLowerCase() === activeCategory;
    const query = searchQuery.toLowerCase().trim();
    if (!query) return matchesCategory;

    const matchesName = (c.name || "").toLowerCase().includes(query);
    const matchesId = (c.id || "").toLowerCase().includes(query);
    const matchesDesc = (c.description || "").toLowerCase().includes(query);
    const matchesCategoryName = (c.category || "").toLowerCase().includes(query);
    const matchesTags = Array.isArray(c.tags) && c.tags.some((t) => t.toLowerCase().includes(query));

    return matchesCategory && (matchesName || matchesId || matchesDesc || matchesCategoryName || matchesTags);
  });

  return (
    <div className="app-root">
      {/* ── HEADER ── */}
      <header className="app-header">
        <div className="header-brand">
          <div className="header-logo">⚡</div>
          <div>
            <h1 className="header-title">Wiring AI Catalog</h1>
            <p className="header-sub">Hardware Database · Datasheet RAG Ingestion · Qdrant Vector Search</p>
          </div>
        </div>

        <div className="header-actions">
          <div className="tab-switcher">
            <button
              className={`nav-tab ${activeTab === "catalog" ? "active" : ""}`}
              onClick={() => setActiveTab("catalog")}
            >
              📦 Catalog ({components.length})
            </button>
            <button
              className={`nav-tab ${activeTab === "onboard" ? "active" : ""}`}
              onClick={() => setActiveTab("onboard")}
            >
              ➕ Onboard Datasheet
            </button>
            <button
              className={`nav-tab ${activeTab === "project" ? "active" : ""}`}
              onClick={() => setActiveTab("project")}
            >
              🛠️ Project Scope
            </button>
          </div>

          <button className="refresh-btn" onClick={fetchComponents} title="Refetch catalog from database">
            🔄 Refresh
          </button>
        </div>
      </header>

      <div className="app-body">
        {/* ── MAIN DASHBOARD CONTENT ── */}
        <main className="main-content">
          {/* ── CATALOG TAB ── */}
          {activeTab === "catalog" && (
            <div className="catalog-view">
              {/* Controls: Search & Category Filter Tabs */}
              <div className="controls-bar">
                <div className="search-box">
                  <span className="search-icon">🔍</span>
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Search by component name, ID, category, pins, or protocols (e.g. DHT22, I2C, 5V)..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button className="clear-search" onClick={() => setSearchQuery("")}>
                      ✕
                    </button>
                  )}
                </div>

                <div className="category-tabs">
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      className={`cat-tab ${activeCategory === cat ? "active" : ""}`}
                      onClick={() => setActiveCategory(cat)}
                    >
                      {cat === "all" ? "All Components" : cat}
                    </button>
                  ))}
                </div>
              </div>

              {/* Status alerts */}
              {error && (
                <div className="alert-card alert-error">
                  <span>❌ {error}</span>
                  <button className="retry-btn" onClick={fetchComponents}>Retry</button>
                </div>
              )}

              {loading && (
                <div className="loading-grid">
                  {[1, 2, 3, 4, 5, 6].map((n) => (
                    <div key={n} className="skeleton-card" />
                  ))}
                </div>
              )}

              {/* Empty state */}
              {!loading && !error && filteredComponents.length === 0 && (
                <div className="empty-catalog">
                  <div className="empty-icon">🔍</div>
                  <h3>No components found</h3>
                  <p>
                    {searchQuery
                      ? `No catalog items matched "${searchQuery}". Try clearing your search filter.`
                      : "The database is currently empty. Use the Onboard tab to ingest component datasheets."}
                  </p>
                  {searchQuery && (
                    <button className="reset-filter-btn" onClick={() => setSearchQuery("")}>
                      Clear Search Filter
                    </button>
                  )}
                </div>
              )}

              {/* Component Cards Grid */}
              {!loading && !error && filteredComponents.length > 0 && (
                <div className="components-grid">
                  {filteredComponents.map((comp) => (
                    <ComponentCard
                      key={comp.id}
                      component={comp}
                      isSelected={selectedComponent?.id === comp.id}
                      onSelect={() =>
                        setSelectedComponent(selectedComponent?.id === comp.id ? null : comp)
                      }
                      onDelete={(e) => handleOpenDeleteModal(e, comp.id, comp.name)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── ONBOARD TAB ── */}
          {activeTab === "onboard" && (
            <div className="onboard-view">
              <div className="onboard-wrapper">
                <OnboardPanel
                  onComponentAdded={() => {
                    fetchComponents();
                    // Optionally stay on onboard or show success notification
                  }}
                />
              </div>
            </div>
          )}

          {/* ── PROJECT GENERATION TAB ── */}
          {activeTab === "project" && (
            <div className="onboard-view">
              <div className="project-wrapper">
                <ProjectPanel />
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ── COMPONENT DETAIL MODAL / DRAWER ── */}
      {selectedComponent && (
        <ComponentDetailModal
          component={selectedComponent}
          onClose={() => setSelectedComponent(null)}
          onUpdate={(updated) => {
            setComponents((prev) =>
              prev.map((c) => (c.id === updated.id ? { ...c, ...updated } : c))
            );
            setSelectedComponent((prev) => (prev ? { ...prev, ...updated } : prev));
          }}
          onDelete={(e) => handleOpenDeleteModal(e, selectedComponent.id, selectedComponent.name)}
        />
      )}

      {/* ── DELETE CONFIRMATION MODAL ── */}
      {deletingComponent && (
        <DeleteConfirmModal
          component={deletingComponent}
          onConfirm={handleConfirmDelete}
          onCancel={() => setDeletingComponent(null)}
          isDeleting={isDeleting}
        />
      )}
    </div>
  );
}

/* ─── COMPONENT CARD ITEM ────────────────────────────────────────────── */
function ComponentCard({ component, isSelected, onSelect, onDelete }) {
  const icon =
    CATEGORY_ICON[(component.category || "").toLowerCase()] || CATEGORY_ICON.default;

  const pinsCount = Array.isArray(component.pins)
    ? component.pins.length
    : component.pin_count || 0;

  const protocols = Array.isArray(component.protocols) ? component.protocols : [];

  return (
    <div className={`comp-card ${isSelected ? "selected" : ""}`} onClick={onSelect}>
      <div className="card-header">
        <span className="card-icon">{icon}</span>
        <div className="card-title-group">
          <h3 className="card-name">{component.name}</h3>
          <span className="card-id-badge">{component.id}</span>
        </div>
        <span className="card-cat-badge">{component.category || "General"}</span>
        <button
          className="delete-card-btn"
          onClick={(e) => onDelete(e)}
          title="Delete component from catalog & vector DB"
        >
          🗑️
        </button>
      </div>

      <p className="card-desc">
        {component.description || "No description provided."}
      </p>

      {/* Spec Badges */}
      <div className="spec-row">
        {pinsCount > 0 && (
          <span className="spec-badge">📌 {pinsCount} Pins</span>
        )}
        {component.operating_voltage && (
          <span className="spec-badge">⚡ {component.operating_voltage}V</span>
        )}
        {component.power?.operating_voltage && !component.operating_voltage && (
          <span className="spec-badge">⚡ {component.power.operating_voltage}</span>
        )}
        {protocols.map((proto) => (
          <span key={proto} className="spec-badge proto-badge">
            📡 {proto}
          </span>
        ))}
      </div>

      {/* Card Footer */}
      <div className="card-footer">
        {component.qdrant_indexed || component.datasheet_summary ? (
          <span className="status-tag status-rag">✓ Vector Indexed</span>
        ) : (
          <span className="status-tag status-base">Database Row</span>
        )}
        <span className="card-expand-hint">Click for details ➔</span>
      </div>
    </div>
  );
}

/* ─── COMPONENT DETAIL MODAL ────────────────────────────────────────── */
function ComponentDetailModal({ component, onClose, onUpdate, onDelete }) {
  const icon =
    CATEGORY_ICON[(component.category || "").toLowerCase()] || CATEGORY_ICON.default;

  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(component.name || "");
  const [isSavingName, setIsSavingName] = useState(false);
  const [saveError, setSaveError] = useState(null);

  useEffect(() => {
    setNameInput(component.name || "");
    setIsEditingName(false);
    setSaveError(null);
  }, [component.id, component.name]);

  const handleSaveName = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    const clean = nameInput.trim();
    if (!clean) return;
    if (clean === component.name) {
      setIsEditingName(false);
      return;
    }

    setIsSavingName(true);
    setSaveError(null);
    try {
      const res = await fetch(`${API_BASE}/api/components/${component.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: clean }),
      });
      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }
      const updated = await res.json();
      if (onUpdate) onUpdate(updated);
      setIsEditingName(false);
    } catch (err) {
      console.error("Failed to update component name:", err);
      setSaveError(err.message || "Failed to update name");
    } finally {
      setIsSavingName(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <header className="modal-header">
          <div className="modal-title-box">
            <span className="modal-icon">{icon}</span>
            <div style={{ flex: 1 }}>
              {isEditingName ? (
                <form
                  onSubmit={handleSaveName}
                  style={{
                    display: "flex",
                    gap: "8px",
                    alignItems: "center",
                    marginBottom: "4px",
                    flexWrap: "wrap",
                  }}
                >
                  <input
                    type="text"
                    value={nameInput}
                    onChange={(e) => setNameInput(e.target.value)}
                    autoFocus
                    disabled={isSavingName}
                    style={{
                      padding: "6px 10px",
                      borderRadius: "6px",
                      border: "1px solid var(--accent)",
                      background: "rgba(0, 0, 0, 0.4)",
                      color: "#fff",
                      fontSize: "16px",
                      fontWeight: 700,
                      outline: "none",
                      flex: 1,
                      minWidth: "220px",
                    }}
                  />
                  <button
                    type="submit"
                    disabled={isSavingName || !nameInput.trim()}
                    style={{
                      padding: "6px 12px",
                      borderRadius: "6px",
                      background: "var(--accent)",
                      color: "#fff",
                      border: "none",
                      fontWeight: 700,
                      fontSize: "12px",
                      cursor: "pointer",
                    }}
                  >
                    {isSavingName ? "Saving..." : "✓ Save"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setNameInput(component.name || "");
                      setIsEditingName(false);
                    }}
                    disabled={isSavingName}
                    style={{
                      padding: "6px 10px",
                      borderRadius: "6px",
                      background: "transparent",
                      border: "1px solid var(--border)",
                      color: "var(--text-secondary)",
                      fontSize: "12px",
                      cursor: "pointer",
                    }}
                  >
                    ✕
                  </button>
                </form>
              ) : (
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <h2 style={{ margin: 0 }}>{component.name}</h2>
                  <button
                    type="button"
                    onClick={() => setIsEditingName(true)}
                    title="Rename component"
                    style={{
                      background: "rgba(255, 255, 255, 0.08)",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      padding: "3px 8px",
                      color: "var(--accent-2)",
                      fontSize: "12px",
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    ✏️ Rename
                  </button>
                </div>
              )}
              {saveError && (
                <span style={{ color: "#ef4444", fontSize: "11px", display: "block", marginTop: "2px" }}>
                  {saveError}
                </span>
              )}
              <span className="modal-sub">ID: {component.id} · Category: {component.category}</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <button
              className="delete-card-btn"
              onClick={(e) => onDelete(e, component.id, component.name)}
              title="Delete component"
            >
              🗑️
            </button>
            <button className="modal-close" onClick={onClose}>
              ✕
            </button>
          </div>
        </header>

        <div className="modal-body">
          {/* Description */}
          <div className="detail-group">
            <h4>Description</h4>
            <p>{component.description || "No detailed description available."}</p>
          </div>

          {/* Technical Specs Grid */}
          <div className="specs-grid">
            <div className="spec-box">
              <span className="spec-label">Operating Voltage</span>
              <span className="spec-value">
                {component.operating_voltage
                  ? `${component.operating_voltage}V`
                  : component.power?.operating_voltage || "N/A"}
              </span>
            </div>

            <div className="spec-box">
              <span className="spec-label">Max Current</span>
              <span className="spec-value">
                {component.power?.current_mA
                  ? `${component.power.current_mA} mA`
                  : component.max_current_per_pin_mA
                    ? `${component.max_current_per_pin_mA} mA/pin`
                    : "N/A"}
              </span>
            </div>

            <div className="spec-box">
              <span className="spec-label">Total Digital Pins</span>
              <span className="spec-value">{component.total_digital_pins ?? "N/A"}</span>
            </div>

            <div className="spec-box">
              <span className="spec-label">Total Analog Pins</span>
              <span className="spec-value">{component.total_analog_pins ?? "N/A"}</span>
            </div>
          </div>

          {/* Pins List */}
          {Array.isArray(component.pins) && component.pins.length > 0 && (
            <div className="detail-group">
              <h4>Pinout Definition ({component.pins.length} pins)</h4>
              <div className="pins-table">
                {component.pins.map((pin, i) => (
                  <div key={i} className="pin-row">
                    <span className="pin-number">#{i + 1}</span>
                    <span className="pin-name">
                      {typeof pin === "string" ? pin : pin.name || pin.designation || `Pin ${i + 1}`}
                    </span>
                    {typeof pin === "object" && pin.type && (
                      <span className="pin-type-badge">{pin.type}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Datasheet Summary */}
          {component.datasheet_summary && (
            <div className="detail-group">
              <h4>📄 Datasheet Summary (RAG Context)</h4>
              <div className="summary-box">{component.datasheet_summary}</div>
            </div>
          )}

          {/* Datasheet URL link */}
          {component.datasheet_url && (
            <div className="detail-group">
              <a
                href={component.datasheet_url}
                target="_blank"
                rel="noopener noreferrer"
                className="datasheet-link"
              >
                🔗 Open Original Datasheet PDF ↗
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── CUSTOM DELETE CONFIRMATION MODAL ────────────────────────────────── */
function DeleteConfirmModal({ component, onConfirm, onCancel, isDeleting }) {
  if (!component) return null;
  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-content delete-confirm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="delete-modal-icon">⚠️</div>
        <h3 className="delete-modal-title">Delete Component</h3>
        <p className="delete-modal-desc">
          Are you sure you want to delete <strong>{component.name || component.id}</strong>? This will permanently remove its catalog record from PostgreSQL and purge its vector embeddings from Qdrant.
        </p>
        <div className="delete-modal-actions">
          <button className="delete-cancel-btn" onClick={onCancel} disabled={isDeleting}>
            Cancel
          </button>
          <button className="delete-confirm-btn" onClick={onConfirm} disabled={isDeleting}>
            {isDeleting ? "Deleting..." : "Delete Component"}
          </button>
        </div>
      </div>
    </div>
  );
}