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

/* ─── HELPER: Check for missing critical fields ────────────────────── */
function getMissingCriticalFields(component) {
  const missing = [];
  const category = (component.category || "").toLowerCase();
  const protocol = component.interface?.protocol || "";
  
  // Skip validation for non-active categories
  const skipCategories = ["passive", "sub_peripheral", "platform", "power"];
  if (skipCategories.includes(category)) {
    return missing;
  }

  // Skip validation if protocol is passive or sub_peripheral
  if (protocol === "passive" || protocol === "sub_peripheral") {
    return missing;
  }

  // Check interface dict - protocol is always critical
  const iface = component.interface || {};
  if (!iface.protocol) {
    missing.push("protocol");
  }
  if (iface.protocol === "i2c" && !iface.i2c_address) {
    missing.push("i2c_address");
  }

  // Check power dict - at least some power info must exist
  const power = component.power || {};
  
  // For external powered components (motors, relays, etc), logic_voltage is not applicable
  // For logic-level components, logic_voltage should be defined
  const isExternalPowered = power.is_external_powered === true;
  if (!isExternalPowered && (power.logic_voltage === null || power.logic_voltage === undefined)) {
    missing.push("logic_voltage");
  }

  // voltage_range is critical for all non-passive components
  if (!power.voltage_range || !Array.isArray(power.voltage_range) || power.voltage_range.length !== 2) {
    missing.push("voltage_range");
  }

  // operating_current_mA should be defined for all powered components
  if (power.operating_current_mA === null || power.operating_current_mA === undefined) {
    missing.push("operating_current_mA");
  }

  // is_external_powered is critical to know - it cannot be undefined/null
  if (power.is_external_powered === null || power.is_external_powered === undefined) {
    missing.push("is_external_powered");
  }

  return missing;
}

/* ─── COMPONENT CARD ITEM ────────────────────────────────────────────── */
function ComponentCard({ component, isSelected, onSelect, onDelete }) {
  const icon =
    CATEGORY_ICON[(component.category || "").toLowerCase()] || CATEGORY_ICON.default;

  const pinsCount = Array.isArray(component.pins)
    ? component.pins.length
    : component.pin_count || 0;

  const protocols = Array.isArray(component.protocols) ? component.protocols : [];
  const missingFields = getMissingCriticalFields(component);
  const hasWarnings = missingFields.length > 0;

  return (
    <div className={`comp-card ${isSelected ? "selected" : ""} ${hasWarnings ? "has-warnings" : ""}`} onClick={onSelect}>
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

      {/* Warning Badge for Missing Fields */}
      {hasWarnings && (
        <div className="warning-banner">
          <span className="warning-icon">⚠️</span>
          <span className="warning-text">{missingFields.length} critical field(s) missing</span>
        </div>
      )}

      {/* Spec Badges */}
      <div className="spec-row">
        {pinsCount > 0 && (
          <span className="spec-badge">📌 {pinsCount} Pins</span>
        )}
        
        {/* Voltage - prefer voltage_range from power dict */}
        {component.power?.voltage_range && component.power.voltage_range.length === 2 ? (
          <span className="spec-badge">
            ⚡ {component.power.voltage_range[0]}-{component.power.voltage_range[1]}V
          </span>
        ) : component.operating_voltage ? (
          <span className="spec-badge">⚡ {component.operating_voltage}V</span>
        ) : component.power?.operating_voltage ? (
          <span className="spec-badge">⚡ {component.power.operating_voltage}V</span>
        ) : null}
        
        {/* Operating Current */}
        {component.power?.operating_current_mA ? (
          <span className="spec-badge">🔌 {component.power.operating_current_mA}mA</span>
        ) : null}
        
        {/* Interface Protocol */}
        {component.interface?.protocol && (
          <span className="spec-badge proto-badge">
            📡 {component.interface.protocol.toUpperCase()}
          </span>
        )}
        
        {/* Fallback for legacy protocols array */}
        {protocols.map((proto) => (
          <span key={proto} className="spec-badge proto-badge">
            📡 {proto}
          </span>
        ))}
        
        {/* External Power Indicator */}
        {component.power?.is_external_powered && (
          <span className="spec-badge" style={{ background: "rgba(239, 68, 68, 0.2)", borderColor: "rgba(239, 68, 68, 0.4)", color: "#fca5a5" }}>
            🔋 External
          </span>
        )}
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

  // Metadata editing state
  const [isEditingMetadata, setIsEditingMetadata] = useState(false);
  const [isSavingMetadata, setIsSavingMetadata] = useState(false);
  const [metadataError, setMetadataError] = useState(null);
  const [power, setPower] = useState(component.power || {});
  const [iface, setIface] = useState(component.interface || {});

  const missingFields = getMissingCriticalFields(component);

  useEffect(() => {
    setNameInput(component.name || "");
    setIsEditingName(false);
    setSaveError(null);
    setPower(component.power || {});
    setIface(component.interface || {});
    setIsEditingMetadata(false);
    setMetadataError(null);
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

  const handleSaveMetadata = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    
    setIsSavingMetadata(true);
    setMetadataError(null);
    try {
      const res = await fetch(`${API_BASE}/api/components/${component.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          power,
          interface: iface,
        }),
      });
      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }
      const updated = await res.json();
      if (onUpdate) onUpdate(updated);
      setIsEditingMetadata(false);
    } catch (err) {
      console.error("Failed to update metadata:", err);
      setMetadataError(err.message || "Failed to update metadata");
    } finally {
      setIsSavingMetadata(false);
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

          {/* Missing Fields Warning & Editor */}
          {missingFields.length > 0 && (
            <div className="alert-card" style={{ background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", marginBottom: "16px" }}>
              <span style={{ color: "var(--accent-amber)" }}>⚠️ Missing critical fields: {missingFields.join(", ")}</span>
            </div>
          )}

          {/* Technical Specs Grid */}
          <div className="specs-grid">
            {/* Interface Protocol */}
            <div className="spec-box">
              <span className="spec-label">Interface Protocol</span>
              <span className="spec-value">
                {component.interface?.protocol
                  ? component.interface.protocol.charAt(0).toUpperCase() + component.interface.protocol.slice(1)
                  : "N/A"}
              </span>
            </div>

            {/* I2C Address (if applicable) */}
            {component.interface?.protocol === "i2c" && (
              <div className="spec-box">
                <span className="spec-label">I2C Address</span>
                <span className="spec-value">{component.interface.i2c_address || "N/A"}</span>
              </div>
            )}

            {/* Logic Voltage (single value from power dict) */}
            <div className="spec-box">
              <span className="spec-label">Logic Voltage</span>
              <span className="spec-value">
                {component.power?.logic_voltage ? `${component.power.logic_voltage}V` : "N/A"}
              </span>
            </div>

            {/* Operating Current */}
            <div className="spec-box">
              <span className="spec-label">Operating Current</span>
              <span className="spec-value">
                {component.power?.operating_current_mA !== null && component.power?.operating_current_mA !== undefined
                  ? `${component.power.operating_current_mA} mA`
                  : component.max_current_per_pin_mA
                    ? `${component.max_current_per_pin_mA} mA/pin`
                    : "N/A"}
              </span>
            </div>

            {/* External Power */}
            <div className="spec-box">
              <span className="spec-label">External Powered</span>
              <span className="spec-value">
                {component.power?.is_external_powered !== null && component.power?.is_external_powered !== undefined
                  ? component.power.is_external_powered ? "Yes 🔋" : "No"
                  : "N/A"}
              </span>
            </div>

            {/* Total Digital Pins */}
            {component.total_digital_pins !== null && component.total_digital_pins !== undefined && (
              <div className="spec-box">
                <span className="spec-label">Total Digital Pins</span>
                <span className="spec-value">{component.total_digital_pins}</span>
              </div>
            )}

            {/* Total Analog Pins */}
            {component.total_analog_pins !== null && component.total_analog_pins !== undefined && (
              <div className="spec-box">
                <span className="spec-label">Total Analog Pins</span>
                <span className="spec-value">{component.total_analog_pins}</span>
              </div>
            )}
          </div>

          {/* Edit Metadata Section (Always Available) */}
          <div className="detail-group">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
              <h4 style={{ display: "flex", alignItems: "center", gap: "6px", margin: 0 }}>
                ⚙️ Component Metadata
              </h4>
              <button
                onClick={() => setIsEditingMetadata(!isEditingMetadata)}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  background: isEditingMetadata ? "var(--accent-green)" : "var(--accent)",
                  color: "#fff",
                  border: "none",
                  fontWeight: 600,
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                {isEditingMetadata ? "Close" : "✏️ Edit"}
              </button>
            </div>

            {isEditingMetadata && (
              <form
                onSubmit={handleSaveMetadata}
                style={{
                  background: "var(--bg-glass)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "12px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                {/* Interface Section */}
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)" }}>
                    Protocol
                  </label>
                  <select
                    value={iface.protocol || ""}
                    onChange={(e) => setIface({ ...iface, protocol: e.target.value })}
                    style={{
                      width: "100%",
                      padding: "6px 8px",
                      marginTop: "4px",
                      borderRadius: "6px",
                      border: "1px solid var(--border)",
                      background: "rgba(0, 0, 0, 0.3)",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                  >
                    <option value="">-- Select Protocol --</option>
                    <option value="gpio">GPIO</option>
                    <option value="i2c">I2C</option>
                    <option value="spi">SPI</option>
                    <option value="uart">UART</option>
                    <option value="onewire">1-Wire</option>
                    <option value="analog">Analog</option>
                    <option value="passive">Passive</option>
                    <option value="sub_peripheral">Sub-Peripheral</option>
                  </select>
                </div>

                {iface.protocol === "i2c" && (
                  <div>
                    <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)" }}>
                      I2C Address (e.g., 0x27)
                    </label>
                    <input
                      type="text"
                      value={iface.i2c_address || ""}
                      onChange={(e) => setIface({ ...iface, i2c_address: e.target.value })}
                      placeholder="0x27"
                      style={{
                        width: "100%",
                        padding: "6px 8px",
                        marginTop: "4px",
                        borderRadius: "6px",
                        border: "1px solid var(--border)",
                        background: "rgba(0, 0, 0, 0.3)",
                        color: "#fff",
                        fontSize: "12px",
                      }}
                    />
                  </div>
                )}

                {/* Power Section - Conditional based on Protocol */}
                {iface.protocol && iface.protocol !== "passive" && (
                  <>
                    {/* Show Logic Voltage only for active communication protocols */}
                    {["gpio", "i2c", "spi", "uart", "onewire", "analog"].includes(iface.protocol) && (
                      <div>
                        <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)" }}>
                          Logic Voltage (3.3 or 5.0)
                        </label>
                        <select
                          value={power.logic_voltage || ""}
                          onChange={(e) => setPower({ ...power, logic_voltage: e.target.value ? parseFloat(e.target.value) : null })}
                          style={{
                            width: "100%",
                            padding: "6px 8px",
                            marginTop: "4px",
                            borderRadius: "6px",
                            border: "1px solid var(--border)",
                            background: "rgba(0, 0, 0, 0.3)",
                            color: "#fff",
                            fontSize: "12px",
                          }}
                        >
                          <option value="">-- Select --</option>
                          <option value="3.3">3.3V</option>
                          <option value="5.0">5.0V</option>
                        </select>
                      </div>
                    )}

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)" }}>
                        Voltage Range Min (e.g., 3.0)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={(power.voltage_range?.[0] ?? "")}
                        onChange={(e) => {
                          const newRange = [...(power.voltage_range || [0, 0])];
                          newRange[0] = e.target.value ? parseFloat(e.target.value) : 0;
                          setPower({ ...power, voltage_range: newRange });
                        }}
                        placeholder="3.0"
                        style={{
                          width: "100%",
                          padding: "6px 8px",
                          marginTop: "4px",
                          borderRadius: "6px",
                          border: "1px solid var(--border)",
                          background: "rgba(0, 0, 0, 0.3)",
                          color: "#fff",
                          fontSize: "12px",
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)" }}>
                        Voltage Range Max (e.g., 5.5)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={(power.voltage_range?.[1] ?? "")}
                        onChange={(e) => {
                          const newRange = [...(power.voltage_range || [0, 0])];
                          newRange[1] = e.target.value ? parseFloat(e.target.value) : 0;
                          setPower({ ...power, voltage_range: newRange });
                        }}
                        placeholder="5.5"
                        style={{
                          width: "100%",
                          padding: "6px 8px",
                          marginTop: "4px",
                          borderRadius: "6px",
                          border: "1px solid var(--border)",
                          background: "rgba(0, 0, 0, 0.3)",
                          color: "#fff",
                          fontSize: "12px",
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)" }}>
                        Operating Current (mA)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={power.operating_current_mA ?? ""}
                        onChange={(e) => setPower({ ...power, operating_current_mA: e.target.value ? parseFloat(e.target.value) : null })}
                        placeholder="2.5"
                        style={{
                          width: "100%",
                          padding: "6px 8px",
                          marginTop: "4px",
                          borderRadius: "6px",
                          border: "1px solid var(--border)",
                          background: "rgba(0, 0, 0, 0.3)",
                          color: "#fff",
                          fontSize: "12px",
                        }}
                      />
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <input
                        type="checkbox"
                        id="is_external_powered"
                        checked={power.is_external_powered || false}
                        onChange={(e) => setPower({ ...power, is_external_powered: e.target.checked })}
                        style={{ cursor: "pointer" }}
                      />
                      <label htmlFor="is_external_powered" style={{ fontSize: "12px", cursor: "pointer" }}>
                        Requires External Power (motors, supplies, high-power devices)
                      </label>
                    </div>
                  </>
                )}

                {/* Passive/Sub-Peripheral Section - Simplified */}
                {(iface.protocol === "passive" || iface.protocol === "sub_peripheral") && (
                  <>
                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)" }}>
                        Voltage Range Min
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={(power.voltage_range?.[0] ?? "")}
                        onChange={(e) => {
                          const newRange = [...(power.voltage_range || [0, 0])];
                          newRange[0] = e.target.value ? parseFloat(e.target.value) : 0;
                          setPower({ ...power, voltage_range: newRange });
                        }}
                        placeholder="0.0 or 3.0"
                        style={{
                          width: "100%",
                          padding: "6px 8px",
                          marginTop: "4px",
                          borderRadius: "6px",
                          border: "1px solid var(--border)",
                          background: "rgba(0, 0, 0, 0.3)",
                          color: "#fff",
                          fontSize: "12px",
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)" }}>
                        Voltage Range Max
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={(power.voltage_range?.[1] ?? "")}
                        onChange={(e) => {
                          const newRange = [...(power.voltage_range || [0, 0])];
                          newRange[1] = e.target.value ? parseFloat(e.target.value) : 0;
                          setPower({ ...power, voltage_range: newRange });
                        }}
                        placeholder="2.2 or 5.5"
                        style={{
                          width: "100%",
                          padding: "6px 8px",
                          marginTop: "4px",
                          borderRadius: "6px",
                          border: "1px solid var(--border)",
                          background: "rgba(0, 0, 0, 0.3)",
                          color: "#fff",
                          fontSize: "12px",
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-secondary)" }}>
                        Operating Current (mA)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={power.operating_current_mA ?? ""}
                        onChange={(e) => setPower({ ...power, operating_current_mA: e.target.value ? parseFloat(e.target.value) : null })}
                        placeholder="10.0"
                        style={{
                          width: "100%",
                          padding: "6px 8px",
                          marginTop: "4px",
                          borderRadius: "6px",
                          border: "1px solid var(--border)",
                          background: "rgba(0, 0, 0, 0.3)",
                          color: "#fff",
                          fontSize: "12px",
                        }}
                      />
                    </div>

                    {iface.protocol === "sub_peripheral" && (
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <input
                          type="checkbox"
                          id="is_external_powered"
                          checked={power.is_external_powered || false}
                          onChange={(e) => setPower({ ...power, is_external_powered: e.target.checked })}
                          style={{ cursor: "pointer" }}
                        />
                        <label htmlFor="is_external_powered" style={{ fontSize: "12px", cursor: "pointer" }}>
                          Requires External Power
                        </label>
                      </div>
                    )}
                  </>
                )}

                {metadataError && (
                  <span style={{ color: "#ef4444", fontSize: "11px" }}>{metadataError}</span>
                )}

                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    type="submit"
                    disabled={isSavingMetadata}
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      borderRadius: "6px",
                      background: "var(--accent-green)",
                      color: "#fff",
                      border: "none",
                      fontWeight: 600,
                      fontSize: "12px",
                      cursor: "pointer",
                    }}
                  >
                    {isSavingMetadata ? "Saving..." : "✓ Save Metadata"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsEditingMetadata(false)}
                    disabled={isSavingMetadata}
                    style={{
                      padding: "8px 12px",
                      borderRadius: "6px",
                      background: "transparent",
                      border: "1px solid var(--border)",
                      color: "var(--text-secondary)",
                      fontSize: "12px",
                      cursor: "pointer",
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
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