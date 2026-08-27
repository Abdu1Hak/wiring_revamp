/**
 * project.jsx
 * ─────────────────────────────────────────────────────────────────────
 * Generation Pipeline UI (Interactive HITL Hardware Alignment Workspace):
 * 1. Left Panel: Interactive component bubbles with Quantity selection (+ / -)
 *    and Configurable Voltage for Power Supplies / Batteries.
 * 2. Right Panel: Textbox for User to describe Project Scope
 * 3. SSE Stream: Connects to /api/generate/start & /api/generate/confirm
 * 4. Interactive HITL Workspace:
 *    - Voltage recommendation alert (⚡ Electric Amber/Gold alert card)
 *    - Quantity adjustments alert (⚖️ Cyan/Sky Blue alert card)
 *    - Instance-based role assignments (e.g. servo_sg90_1, servo_sg90_2)
 *    - Live synchronization between quantities and role instance cards
 *    - Remove unassigned/unused components with 1 click
 *    - Assign custom roles to unassigned components
 *    - Add missing components from catalog with role assignment
 *    - Dismiss unwanted AI suggestions
 *    - Re-validate updated hardware batch or proceed to wiring synthesis
 */

import { useState, useEffect, useCallback, useMemo } from "react";

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

// Standard voltage presets for adjustable power supplies
const VOLTAGE_PRESETS = [
  { value: "3.3V", label: "3.3V (Logic / Sensors)" },
  { value: "5V", label: "5V (USB / Logic)" },
  { value: "6V", label: "6V (4xAA / Motors)" },
  { value: "7.4V", label: "7.4V (2S LiPo)" },
  { value: "9V", label: "9V (Transistor / Wall)" },
  { value: "11.1V", label: "11.1V (3S LiPo)" },
  { value: "12V", label: "12V (Motors / LED)" },
  { value: "24V", label: "24V (Industrial)" },
];

export default function ProjectPanel() {
  const [availableComponents, setAvailableComponents] = useState([]);
  const [isFetchingCatalog, setIsFetchingCatalog] = useState(true);

  // ── Board-Scoped Buckets ──
  // Each bucket: { boardId, boardName, microcontrollerId, microcontrollerName, components: { [comp_id]: qty }, configs: {} }
  const [boardBuckets, setBoardBuckets] = useState([]);
  const [activeBoardIdx, setActiveBoardIdx] = useState(0);

  // Helper to detect if a component is a microcontroller (strictly dev boards / MCUs)
  const isMicrocontroller = useCallback((comp) => {
    if (!comp) return false;
    const cat = (comp.category || "").toLowerCase();
    const id = (comp.id || "").toLowerCase();
    const name = (comp.name || "").toLowerCase();

    // Explicitly exclude shift registers, logic ICs, motor drivers, shields
    if (
      id.includes("595") ||
      id.includes("74hc") ||
      id.includes("shift_register") ||
      name.includes("shift register") ||
      name.includes("74hc") ||
      name.includes("sn74") ||
      id.includes("driver") ||
      id.includes("l298n") ||
      id.includes("shield")
    ) {
      return false;
    }

    return (
      cat === "microcontroller" ||
      id.includes("arduino") ||
      id.includes("esp32") ||
      id.includes("raspberry_pi") ||
      id.includes("stm32") ||
      id.includes("pico") ||
      name.includes("arduino") ||
      name.includes("microcontroller")
    );
  }, []);

  // Helper to check if a component is an adjustable power supply (exclude fixed breadboard power modules)
  const isAdjustablePowerSupply = useCallback((comp) => {
    if (!comp) return false;
    const cid = (comp.id || "").toLowerCase();
    const cname = (comp.name || "").toLowerCase();
    if (cid.includes("breadboard") || cname.includes("breadboard")) {
      return false;
    }
    return (
      cid === "dc_power_supply" ||
      cid === "battery_pack" ||
      comp.tags?.includes("adjustable_voltage") ||
      comp.power?.is_adjustable === true
    );
  }, []);

  // Compute aggregate selected quantities across all boards
  const selectedQuantities = useMemo(() => {
    const map = {};
    boardBuckets.forEach((b) => {
      if (b.microcontrollerId) {
        map[b.microcontrollerId] = (map[b.microcontrollerId] || 0) + 1;
      }
      Object.entries(b.components || {}).forEach(([cid, q]) => {
        if (q > 0) {
          map[cid] = (map[cid] || 0) + q;
        }
      });
    });
    return map;
  }, [boardBuckets]);

  // Compute aggregate component configs across all boards
  const componentConfigs = useMemo(() => {
    const cfgs = { dc_power_supply: { voltage: "7.4V" } };
    boardBuckets.forEach((b) => {
      Object.entries(b.configs || {}).forEach(([cid, ccfg]) => {
        if (ccfg) {
          cfgs[cid] = { ...(cfgs[cid] || {}), ...ccfg };
        }
      });
    });
    return cfgs;
  }, [boardBuckets]);

  const hasMicrocontroller = boardBuckets.length > 0;

  // Form & Stream state
  const [projectScope, setProjectScope] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [nodeMessage, setNodeMessage] = useState("");
  const [error, setError] = useState(null);

  // HITL State
  const [hitlData, setHitlData] = useState(null);
  const [editedRoles, setEditedRoles] = useState({});
  const [categorizedRolesList, setCategorizedRolesList] = useState([]);
  const [missingRolesList, setMissingRolesList] = useState([]);
  const [unassignedList, setUnassignedList] = useState([]);
  const [quantityAdjustmentsList, setQuantityAdjustmentsList] = useState([]);
  const [voltageAdjustmentsList, setVoltageAdjustmentsList] = useState([]);
  const [selectedForMissing, setSelectedForMissing] = useState({});
  const [missingQuantities, setMissingQuantities] = useState({});
  const [customRoleInput, setCustomRoleInput] = useState({});

  const [isEditing, setIsEditing] = useState(false);
  const [showRejectBox, setShowRejectBox] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  // Final Output State
  const [generationResult, setGenerationResult] = useState(null);

  // Pre-Compatibility Isolated Check State
  const [preCompatResult, setPreCompatResult] = useState(null);
  const [isCheckingPreCompat, setIsCheckingPreCompat] = useState(false);

  // Derived selected IDs & total counts
  const selectedIds = Object.keys(selectedQuantities).filter(
    (id) => selectedQuantities[id] > 0
  );
  const totalUnits = Object.values(selectedQuantities).reduce(
    (sum, count) => sum + (count > 0 ? count : 0),
    0
  );

  // Search and Category filter for Hardware Catalog
  const [catalogSearch, setCatalogSearch] = useState("");
  const [selectedCatFilter, setSelectedCatFilter] = useState("all");

  // Filter catalog components based on active search text and category chip
  const filteredCatalog = useMemo(() => {
    return availableComponents.filter((comp) => {
      const isMicro = isMicrocontroller(comp);
      const isPower = isAdjustablePowerSupply(comp);
      const cat = (comp.category || "").toLowerCase();

      // 1. Category Chip Filter
      if (selectedCatFilter === "microcontroller" && !isMicro) return false;
      if (selectedCatFilter === "sensor" && !cat.includes("sensor")) return false;
      if (
        selectedCatFilter === "actuator" &&
        !cat.includes("actuator") &&
        !cat.includes("motor") &&
        !cat.includes("servo") &&
        !cat.includes("driver")
      )
        return false;
      if (selectedCatFilter === "power" && !cat.includes("power") && !isPower)
        return false;
      if (
        selectedCatFilter === "other" &&
        (isMicro ||
          cat.includes("sensor") ||
          cat.includes("actuator") ||
          cat.includes("motor") ||
          cat.includes("servo") ||
          cat.includes("driver") ||
          cat.includes("power") ||
          isPower)
      )
        return false;

      // 2. Text Search Query
      if (!catalogSearch.trim()) return true;
      const q = catalogSearch.toLowerCase().trim();
      const name = (comp.name || "").toLowerCase();
      const id = (comp.id || "").toLowerCase();
      const desc = (comp.description || "").toLowerCase();
      const tags = Array.isArray(comp.tags) ? comp.tags.join(" ").toLowerCase() : "";

      return (
        name.includes(q) ||
        id.includes(q) ||
        cat.includes(q) ||
        desc.includes(q) ||
        tags.includes(q)
      );
    });
  }, [availableComponents, catalogSearch, selectedCatFilter, isMicrocontroller, isAdjustablePowerSupply]);

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

  // ── Sync Helper: Keeps editedRoles instance cards in 1:1 sync with selected quantities ──
  const syncRolesWithQuantities = useCallback(
    (quantities, roles) => {
      const updatedRoles = { ...roles };

      Object.entries(quantities).forEach(([compId, qty]) => {
        const compObj = availableComponents.find((c) => c.id === compId);
        const compDisplayName = compObj?.name || compId;

        if (qty <= 0) {
          Object.keys(updatedRoles).forEach((k) => {
            if (k === compId || k.startsWith(`${compId}_`)) {
              delete updatedRoles[k];
            }
          });
          return;
        }

        const existingKeys = Object.keys(updatedRoles).filter(
          (k) => k === compId || k.startsWith(`${compId}_`)
        );

        if (qty === 1) {
          if (existingKeys.length === 0) {
            updatedRoles[compId] = `${compDisplayName}: Core hardware unit for project`;
          } else if (existingKeys.length > 1) {
            existingKeys.slice(1).forEach((k) => delete updatedRoles[k]);
          }
        } else {
          if (updatedRoles[compId] && !updatedRoles[`${compId}_1`]) {
            updatedRoles[`${compId}_1`] = updatedRoles[compId];
            delete updatedRoles[compId];
          }

          for (let i = 1; i <= qty; i++) {
            const key = `${compId}_${i}`;
            if (!updatedRoles[key]) {
              updatedRoles[key] = `${compDisplayName} (Unit #${i}): Assigned unit for project`;
            }
          }

          existingKeys.forEach((k) => {
            const match = k.match(/^.+_(\d+)$/);
            if (match && parseInt(match[1], 10) > qty) {
              delete updatedRoles[k];
            }
          });
        }
      });

      Object.keys(updatedRoles).forEach((k) => {
        const match = k.match(/^(.+)_(\d+)$/);
        const baseId = match ? match[1] : k;
        if (!quantities[baseId] || quantities[baseId] <= 0) {
          delete updatedRoles[k];
        }
      });

      return updatedRoles;
    },
    [availableComponents]
  );

  // ── Board Management Handlers ──

  // Add Microcontroller Board Bucket
  const addBoard = useCallback((microComp) => {
    setBoardBuckets((prev) => {
      const nextNum = prev.length + 1;
      const newBoard = {
        boardId: `${microComp.id}_${nextNum}`,
        boardName: `${microComp.name || microComp.id} (Board #${nextNum})`,
        microcontrollerId: microComp.id,
        microcontrollerName: microComp.name || microComp.id,
        components: {},
        configs: {},
      };
      const nextList = [...prev, newBoard];
      setActiveBoardIdx(prev.length); // automatically focus new board for next components
      return nextList;
    });
  }, []);

  // Remove Highest Board Bucket
  const removeBoard = useCallback(() => {
    setBoardBuckets((prev) => {
      if (prev.length <= 1) {
        setActiveBoardIdx(0);
        return [];
      }
      const nextList = prev.slice(0, -1);
      setActiveBoardIdx((curr) => Math.min(curr, nextList.length - 1));
      return nextList;
    });
  }, []);

  // Change Quantity of a Component
  const changeComponentQuantity = useCallback(
    (compId, delta) => {
      const compObj = availableComponents.find((c) => c.id === compId);
      const isMicro = isMicrocontroller(compObj || { id: compId });

      if (isMicro) {
        if (delta > 0) {
          addBoard(compObj || { id: compId, name: compId });
        } else {
          removeBoard();
        }
        return;
      }

      // If peripheral component: must have an active board
      if (boardBuckets.length === 0) return;

      const targetIdx = Math.max(0, Math.min(activeBoardIdx, boardBuckets.length - 1));
      setBoardBuckets((prev) => {
        const next = [...prev];
        const targetBoard = { ...next[targetIdx] };
        const currComps = { ...(targetBoard.components || {}) };
        const currentQty = currComps[compId] || 0;
        const nextQty = currentQty + delta;

        if (nextQty <= 0) {
          delete currComps[compId];
        } else {
          currComps[compId] = nextQty;
        }

        targetBoard.components = currComps;
        next[targetIdx] = targetBoard;
        return next;
      });
    },
    [availableComponents, isMicrocontroller, addBoard, removeBoard, boardBuckets.length, activeBoardIdx]
  );

  const toggleComponentSelection = (id) => {
    const qty = selectedQuantities[id] || 0;
    changeComponentQuantity(id, qty > 0 ? -qty : 1);
  };

  const setComponentQuantity = (id, quantity) => {
    const currentQty = selectedQuantities[id] || 0;
    changeComponentQuantity(id, quantity - currentQty);
  };

  // Config helpers for per-instance voltages
  const getComponentVoltage = (id, instanceIndex = 0) => {
    const cfg = componentConfigs[id];
    if (!cfg) return "7.4V";
    if (Array.isArray(cfg.voltages)) {
      return cfg.voltages[instanceIndex] || cfg.voltage || "7.4V";
    }
    return cfg.voltage || "7.4V";
  };

  const setComponentInstanceVoltage = (id, instanceIndex, voltage) => {
    if (boardBuckets.length === 0) return;
    const targetIdx = Math.max(0, Math.min(activeBoardIdx, boardBuckets.length - 1));

    setBoardBuckets((prev) => {
      const next = [...prev];
      const targetBoard = { ...next[targetIdx] };
      const currConfigs = { ...(targetBoard.configs || {}) };
      const current = currConfigs[id] || {};
      const currentList = Array.isArray(current.voltages)
        ? [...current.voltages]
        : [current.voltage || "7.4V"];

      currentList[instanceIndex] = voltage;
      currConfigs[id] = {
        ...current,
        voltage: currentList[0],
        voltages: currentList,
      };

      targetBoard.configs = currConfigs;
      next[targetIdx] = targetBoard;
      return next;
    });
  };

  const setComponentVoltage = (id, voltage) => {
    setComponentInstanceVoltage(id, 0, voltage);
  };

  const selectAll = () => {
    if (availableComponents.length === 0) return;
    const micro = availableComponents.find((c) => isMicrocontroller(c)) || { id: "arduino_uno", name: "Arduino Uno" };

    // Create 1 board with all non-micro components
    const comps = {};
    availableComponents.forEach((c) => {
      if (!isMicrocontroller(c)) {
        comps[c.id] = 1;
      }
    });

    setBoardBuckets([
      {
        boardId: `${micro.id}_1`,
        boardName: `${micro.name || micro.id} (Board #1)`,
        microcontrollerId: micro.id,
        microcontrollerName: micro.name || micro.id,
        components: comps,
        configs: { dc_power_supply: { voltage: "7.4V" } },
      },
    ]);
    setActiveBoardIdx(0);
  };

  const clearSelection = () => {
    setBoardBuckets([]);
    setActiveBoardIdx(0);
    setEditedRoles({});
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
            const initialRoles = event.role_assignments || {};
            setEditedRoles(initialRoles);

            const qas = Array.isArray(event.quantity_adjustments) ? [...event.quantity_adjustments] : [];
            const vas = Array.isArray(event.voltage_adjustments) ? [...event.voltage_adjustments] : [];
            const qaCompIds = new Set([
              ...qas.map(q => (q.component_id || "").toLowerCase().replace(/[- ]/g, "_")),
              ...vas.map(v => (v.component_id || "").toLowerCase().replace(/[- ]/g, "_")),
            ]);

            const rawMissing = Array.isArray(event.missing_roles) ? [...event.missing_roles] : [];
            const rawUnassigned = Array.isArray(event.unassigned_components) ? [...event.unassigned_components] : [];

            // Golden rule: If adjustment exists for component, do not show unassigned or missing alert for it
            const filteredUnassigned = rawUnassigned.filter(u => {
              const uId = (u.component_id || "").toLowerCase().replace(/[- ]/g, "_");
              return !qaCompIds.has(uId);
            });

            const filteredMissing = rawMissing.filter(m => {
              const sugg = (m.suggestion || "").toLowerCase().replace(/[- ]/g, "_");
              const role = (m.role || "").toLowerCase();
              return !Array.from(qaCompIds).some(qId => qId && (sugg.includes(qId) || role.includes(qId)));
            });

            setMissingRolesList(filteredMissing);
            setUnassignedList(filteredUnassigned);
            setQuantityAdjustmentsList(qas);
            setVoltageAdjustmentsList(vas);
            setCategorizedRolesList(
              Array.isArray(event.categorized_roles) ? event.categorized_roles : []
            );
            setIsLoading(false);
            setNodeMessage(
              "User review required — review hardware quantities, voltages, and roles below."
            );
          } else if (event.type === "pre_compatibility" || event.node === "pre_compatibility") {
            setPreCompatResult(event);
            if (event.status === "pre_compat_failed") {
              setNodeMessage(`⚠️ Pre-compatibility checks flagged ${event.errors?.length || 0} issue(s).`);
            } else {
              setNodeMessage("✓ Circuit Pre-Compatibility Verified!");
            }
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

  // 0. Isolated Pre-Compatibility Check (POST /api/generate/check-pre-compat)
  const handleCheckPreCompat = async () => {
    if (selectedIds.length === 0) return;
    setIsCheckingPreCompat(true);
    setPreCompatResult(null);

    try {
      const response = await fetch(`${API_BASE}/api/generate/check-pre-compat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          board_buckets: boardBuckets.map((b) => ({
            boardId: b.boardId,
            boardName: b.boardName,
            microcontrollerId: b.microcontrollerId,
            microcontrollerName: b.microcontrollerName,
            components: b.components || {},
          })),
          component_quantities: selectedQuantities,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server error (${response.status}): ${response.statusText}`);
      }

      const data = await response.json();
      setPreCompatResult(data);
    } catch (err) {
      console.error("Pre-compatibility check error:", err);
      setPreCompatResult({
        status: "pre_compat_failed",
        errors: [{ type: "network_error", message: err.message || "Failed to check compatibility" }],
        warnings: [],
      });
    } finally {
      setIsCheckingPreCompat(false);
    }
  };

  // 1. Kick off Generation Stream (POST /api/generate/start)
  const handleStartGeneration = async (e, overrideQuantities = null) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!projectScope.trim()) return;

    const activeQuantities = overrideQuantities || selectedQuantities;
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
          component_quantities: activeQuantities,
          component_configs: componentConfigs,
          board_categories: boardBuckets.map((b) => ({
            board_id: b.boardId,
            board_name: b.boardName,
            components: { [b.microcontrollerId]: 1, ...b.components },
            configs: b.configs,
          })),
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
          role_assignments:
            action === "edited" || action === "confirmed" ? editedRoles : null,
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

  // Apply Voltage Recommendation
  const handleApplyVoltageAdjustment = (compId, recommendedVoltage) => {
    setComponentInstanceVoltage(compId, 0, recommendedVoltage);
    setVoltageAdjustmentsList((prev) =>
      prev.filter((item) => item.component_id !== compId)
    );
  };

  // Dismiss Voltage Recommendation
  const handleDismissVoltageAdjustment = (compId) => {
    setVoltageAdjustmentsList((prev) =>
      prev.filter((item) => item.component_id !== compId)
    );
  };

  // Apply Quantity Adjustment Recommendation
  const handleApplyQuantityAdjustment = (compId, recommendedQty) => {
    setComponentQuantity(compId, recommendedQty);
    setQuantityAdjustmentsList((prev) =>
      prev.filter((item) => item.component_id !== compId)
    );
  };

  // Dismiss Quantity Adjustment (keep current quantity)
  const handleDismissQuantityAdjustment = (compId) => {
    setQuantityAdjustmentsList((prev) =>
      prev.filter((item) => item.component_id !== compId)
    );
  };

  // Remove an unassigned component from selectedQuantities and HITL view
  const handleRemoveUnassigned = (cid) => {
    setComponentQuantity(cid, 0);
    setUnassignedList((prev) => prev.filter((item) => item.component_id !== cid));
  };

  // Remove an assigned component role instance during HITL review
  const handleRemoveRoleInstance = (roleKey) => {
    const { baseId } = parseInstanceKey(roleKey);
    // Decrement quantity in boardBuckets / selectedQuantities by 1
    changeComponentQuantity(baseId, -1);

    // Remove from editedRoles
    setEditedRoles((prev) => {
      const copy = { ...prev };
      delete copy[roleKey];
      return copy;
    });

    // Remove from categorizedRolesList if multi-board
    setCategorizedRolesList((prev) =>
      prev.map((cat) => {
        const rolesCopy = { ...(cat.roles || {}) };
        delete rolesCopy[roleKey];
        return { ...cat, roles: rolesCopy };
      })
    );
  };

  // Assign a custom role to an unassigned component, moving it to role_assignments
  const handleAssignCustomRole = (cid) => {
    const roleText = customRoleInput[cid] || "Custom Project Component";
    setEditedRoles((prev) => ({ ...prev, [cid]: roleText }));
    setUnassignedList((prev) => prev.filter((item) => item.component_id !== cid));
  };

  // Add a component for a missing role from the catalog (with quantity support)
  const handleAddMissingComponent = (roleIdx, roleObj) => {
    const cidToAdd = selectedForMissing[roleIdx] || (roleObj.suggestion && availableComponents.some(c => c.id === roleObj.suggestion) ? roleObj.suggestion : null);
    if (!cidToAdd) return;

    const qtyToAdd = Math.max(
      1,
      parseInt(missingQuantities[roleIdx] ?? (roleObj.quantity_needed || roleObj.count || 1), 10)
    );

    const currentQty = selectedQuantities[cidToAdd] || 0;

    // Increment quantity in boardBuckets by qtyToAdd
    changeComponentQuantity(cidToAdd, qtyToAdd);

    // Add indexed instance roles for all newly added units
    setEditedRoles((prev) => {
      const compObj = availableComponents.find((c) => c.id === cidToAdd);
      const nextRoles = { ...prev };
      for (let i = 1; i <= qtyToAdd; i++) {
        const instanceNum = currentQty + i;
        const targetKey = instanceNum > 1 ? `${cidToAdd}_${instanceNum}` : cidToAdd;
        const roleLabel = roleObj.role
          ? `${roleObj.role}${qtyToAdd > 1 ? ` (#${i})` : ""}`
          : `${compObj?.name || cidToAdd}: Required component`;
        nextRoles[targetKey] = roleLabel;
      }
      return nextRoles;
    });

    setMissingRolesList((prev) => prev.filter((_, idx) => idx !== roleIdx));
    setSelectedForMissing((prev) => {
      const copy = { ...prev };
      delete copy[roleIdx];
      return copy;
    });
    setMissingQuantities((prev) => {
      const copy = { ...prev };
      delete copy[roleIdx];
      return copy;
    });
  };

  // Dismiss a missing role suggestion if not needed by user
  const handleDismissMissingRole = (roleIdx) => {
    setMissingRolesList((prev) => prev.filter((_, idx) => idx !== roleIdx));
  };

  // Calculate alignment status
  const hasMismatches =
    missingRolesList.length > 0 ||
    unassignedList.length > 0 ||
    quantityAdjustmentsList.length > 0 ||
    voltageAdjustmentsList.length > 0;

  // Helper to parse instance keys (e.g., servo_sg90_1 -> base: servo_sg90, instance: 1)
  const parseInstanceKey = (key) => {
    const match = key.match(/^(.+)_(\d+)$/);
    if (match) {
      return { baseId: match[1], instanceNum: match[2] };
    }
    return { baseId: key, instanceNum: null };
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🛠️ Project Wiring Generator</h2>
      <p style={styles.subtitle}>
        Select hardware components, define quantities and power supply voltages, and describe your project scope.
        The AI will align instance-based roles, verify electrical requirements, check compatibility, and synthesize a complete wiring plan.
      </p>

      <div style={styles.layout}>
        {/* ── LEFT PANEL: Component Selection & Quantity Bubbles ── */}
        <div style={styles.leftPanel}>
          <div style={styles.panelHeader}>
            <div>
              <h3 style={styles.panelTitle}>
                🧩 Catalog Hardware ({selectedIds.length} types, {totalUnits} units)
              </h3>
              <span style={styles.panelSubText}>
                Click to add, adjust count (+ / −) & voltage
              </span>
            </div>
            <div style={styles.quickActions}>
              <button
                style={styles.textBtn}
                onClick={selectAll}
                type="button"
                disabled={isLoading}
              >
                Select All
              </button>
              <span style={styles.divider}>•</span>
              <button
                style={styles.textBtn}
                onClick={clearSelection}
                type="button"
                disabled={isLoading}
              >
                Clear
              </button>
            </div>
          </div>

          {/* ── Board-Scoped Switcher Bar & Microcontroller Prompt ── */}
          {!hasMicrocontroller ? (
            <div style={styles.microPromptBanner}>
              <span style={styles.microPromptIcon}>⚡</span>
              <div>
                <strong style={styles.microPromptTitle}>Select a Microcontroller to Begin</strong>
                <p style={styles.microPromptSub}>
                  Click <strong>+</strong> on a board (e.g. Arduino Uno) below to create Board #1 and unlock peripheral sensors & actuators.
                </p>
              </div>
            </div>
          ) : (
            <div style={styles.boardSwitcherContainer}>
              <div style={styles.boardTabsList}>
                {boardBuckets.map((b, bIdx) => {
                  const itemCount = Object.values(b.components || {}).reduce((s, c) => s + c, 0);
                  const isActive = activeBoardIdx === bIdx;
                  const isCapped = itemCount >= 10;
                  return (
                    <button
                      key={bIdx}
                      type="button"
                      style={{
                        ...styles.boardTabBtn,
                        ...(isActive ? styles.boardTabBtnActive : {}),
                      }}
                      onClick={() => setActiveBoardIdx(bIdx)}
                    >
                      <span style={styles.boardTabIcon}>🔲</span>
                      <span style={styles.boardTabTitle}>{b.boardName}</span>
                      <span
                        style={{
                          ...styles.boardTabBadge,
                          ...(isCapped ? styles.boardTabBadgeWarning : {}),
                        }}
                      >
                        {itemCount}/10 items {isCapped ? "⚠️" : ""}
                      </span>
                    </button>
                  );
                })}
              </div>
              <div style={styles.boardActiveHint}>
                <span>
                  🎯 Target Bucket: Adding components to <strong>{boardBuckets[activeBoardIdx]?.boardName}</strong> (
                  {Object.values(boardBuckets[activeBoardIdx]?.components || {}).reduce((s, c) => s + c, 0)}/10 items)
                </span>
              </div>

              {/* Softcap Warning Notification if active board has 10 or more components */}
              {Object.values(boardBuckets[activeBoardIdx]?.components || {}).reduce((s, c) => s + c, 0) >= 10 && (
                <div style={styles.softcapBanner}>
                  <span style={styles.softcapIcon}>⚠️</span>
                  <div>
                    <strong style={styles.softcapTitle}>
                      Softcap Notice: {boardBuckets[activeBoardIdx]?.boardName} has reached 10 components
                    </strong>
                    <p style={styles.softcapText}>
                      Arduino Uno has limited GPIO pins (14 digital, 6 analog). You can still attach more passives or components, but consider partitioning additional hardware to another board or using I²C/shift registers if you exceed pin capacity.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Catalog Search & Category Filter Bar ── */}
          <div style={styles.catalogSearchPanel}>
            <div style={styles.searchInputWrapper}>
              <span style={styles.searchIcon}>🔍</span>
              <input
                type="text"
                style={styles.searchInput}
                placeholder="Search components (e.g. 'resistor', 'motor', 'HC-SR04', 'sensor')..."
                value={catalogSearch}
                onChange={(e) => {
                  setCatalogSearch(e.target.value);
                  if (e.target.value && selectedCatFilter !== "all") {
                    setSelectedCatFilter("all");
                  }
                }}
              />
              {catalogSearch && (
                <button
                  type="button"
                  style={styles.searchClearBtn}
                  onClick={() => setCatalogSearch("")}
                  title="Clear search"
                >
                  ✕
                </button>
              )}
            </div>

            <div style={styles.catFilterChips}>
              {[
                { id: "all", label: "All" },
                { id: "microcontroller", label: "🔲 MCUs" },
                { id: "sensor", label: "🌡️ Sensors" },
                { id: "actuator", label: "⚙️ Actuators" },
                { id: "power", label: "⚡ Power" },
                { id: "other", label: "🔩 Other" },
              ].map((cat) => (
                <button
                  key={cat.id}
                  type="button"
                  style={{
                    ...styles.catFilterChip,
                    ...(selectedCatFilter === cat.id ? styles.catFilterChipActive : {}),
                  }}
                  onClick={() => setSelectedCatFilter(cat.id)}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {isFetchingCatalog ? (
            <div style={styles.loadingCatalog}>⏳ Loading catalog components...</div>
          ) : availableComponents.length === 0 ? (
            <div style={styles.emptyCatalogNotice}>
              No components found in catalog. Onboard components first.
            </div>
          ) : filteredCatalog.length === 0 ? (
            <div style={styles.noSearchMatch}>
              <span>
                🔍 No components matched "<strong>{catalogSearch}</strong>"
                {selectedCatFilter !== "all" ? ` in filter '${selectedCatFilter}'` : ""}.
              </span>
              <button
                type="button"
                style={styles.clearSearchFilterBtn}
                onClick={() => {
                  setCatalogSearch("");
                  setSelectedCatFilter("all");
                }}
              >
                Reset Search & Filters
              </button>
            </div>
          ) : (
            <div style={styles.bubbleGrid}>
              {filteredCatalog.map((comp) => {
                const isMicro = isMicrocontroller(comp);
                const isLocked = !isMicro && !hasMicrocontroller;
                const totalQty = selectedQuantities[comp.id] || 0;
                const activeQty = isMicro
                  ? boardBuckets.length
                  : boardBuckets[activeBoardIdx]?.components?.[comp.id] || 0;
                const isSelectedInActive = activeQty > 0;
                const isPower = isAdjustablePowerSupply(comp);
                const icon =
                  CATEGORY_ICON[comp.category?.toLowerCase()] || CATEGORY_ICON.default;

                return (
                  <div
                    key={comp.id}
                    style={{
                      ...styles.bubbleCard,
                      ...(isSelectedInActive ? styles.bubbleCardSelected : {}),
                      ...(isPower ? styles.bubbleCardPower : {}),
                      ...(isLocked ? styles.bubbleCardLocked : {}),
                    }}
                    title={isLocked ? "Select a microcontroller first to attach this component" : ""}
                  >
                    <div style={styles.bubbleCardTopRow}>
                      <div
                        style={{
                          ...styles.bubbleClickArea,
                          ...(isLocked ? { cursor: "not-allowed" } : {}),
                        }}
                        onClick={() => {
                          if (!isLoading && !isLocked) {
                            toggleComponentSelection(comp.id);
                          }
                        }}
                      >
                        <span style={styles.bubbleIcon}>{icon}</span>
                        <div style={styles.bubbleTextGroup}>
                          <div style={styles.bubbleNameRow}>
                            <span style={styles.bubbleName}>{comp.name || comp.id}</span>
                            {isMicro && (
                              <span style={styles.microTagBadge}>🧠 Controller</span>
                            )}
                          </div>
                          {isPower && (
                            <span style={styles.adjustableBadge}>
                              ⚡ Adjustable (3.3V – 24V)
                            </span>
                          )}
                          {isLocked && (
                            <span style={styles.lockedBadge}>🔒 Pick board first</span>
                          )}
                        </div>
                      </div>

                      {!isLocked ? (
                        isSelectedInActive ? (
                          <div style={styles.quantityControl}>
                            <button
                              type="button"
                              style={styles.qtyBtn}
                              onClick={(e) => {
                                e.stopPropagation();
                                changeComponentQuantity(comp.id, -1);
                              }}
                              disabled={isLoading}
                              title="Decrease quantity"
                            >
                              −
                            </button>
                            <span style={styles.qtyBadge}>×{activeQty}</span>
                            <button
                              type="button"
                              style={styles.qtyBtn}
                              onClick={(e) => {
                                e.stopPropagation();
                                changeComponentQuantity(comp.id, 1);
                              }}
                              disabled={isLoading}
                              title={isMicro ? "Add another microcontroller board" : "Increase quantity"}
                            >
                              +
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            style={styles.addInitialBtn}
                            onClick={() => !isLoading && changeComponentQuantity(comp.id, 1)}
                            disabled={isLoading}
                            title={isMicro ? "Add microcontroller board" : "Add 1 unit to active board"}
                          >
                            +
                          </button>
                        )
                      ) : (
                        <span style={styles.lockIconMini}>🔒</span>
                      )}
                    </div>

                    {/* Adjustable Voltage Selector Rows for each unit of Power Supply */}
                    {isSelectedInActive && isPower && (
                      <div style={styles.multiVoltageContainer}>
                        {Array.from({ length: activeQty }).map((_, unitIdx) => (
                          <div key={unitIdx} style={styles.voltageConfigRow}>
                            <span style={styles.voltageLabel}>
                              {activeQty > 1 ? `Unit #${unitIdx + 1} Voltage:` : "Voltage:"}
                            </span>
                            <select
                              style={styles.voltageDropdown}
                              value={getComponentVoltage(comp.id, unitIdx)}
                              onChange={(e) =>
                                setComponentInstanceVoltage(comp.id, unitIdx, e.target.value)
                              }
                              disabled={isLoading}
                            >
                              {VOLTAGE_PRESETS.map((p) => (
                                <option key={p.value} value={p.value}>
                                  {p.label}
                                </option>
                              ))}
                            </select>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
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
                placeholder="Describe what you want to build (e.g. 'A 4-wheel drive rover with 4 DC motors powered by a 7.4V battery pack, controlled by an Arduino Uno')..."
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
                  ? "⚠️ No components selected. Select hardware and set quantities on the left."
                  : `Selected Hardware (${selectedIds.length} components, ${totalUnits} total units): ${selectedIds
                    .map((id) => {
                      const compObj = availableComponents.find((c) => c.id === id);
                      const name = compObj?.name || id;
                      const qty = selectedQuantities[id];
                      let voltStr = "";
                      if (isAdjustablePowerSupply(compObj || { id })) {
                        if (qty === 1) {
                          voltStr = ` @ ${getComponentVoltage(id, 0)}`;
                        } else {
                          const unitList = Array.from({ length: qty })
                            .map((_, i) => `#${i + 1}: ${getComponentVoltage(id, i)}`)
                            .join(", ");
                          voltStr = ` (${unitList})`;
                        }
                      }
                      return `${name} (×${qty}${voltStr})`;
                    })
                    .join(", ")}`}
              </span>
            </div>

            {!hitlData && (
              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                <button
                  type="submit"
                  style={{
                    ...styles.button,
                    flex: 2,
                    minWidth: "220px",
                    ...(isLoading || !projectScope.trim() || selectedIds.length === 0
                      ? styles.buttonDisabled
                      : {}),
                  }}
                  disabled={isLoading || !projectScope.trim() || selectedIds.length === 0}
                >
                  {isLoading
                    ? `⏳ ${nodeMessage || "Analyzing Scope & Verifying Hardware..."}`
                    : "⚡ Generate Project Wiring Plan"}
                </button>

                <button
                  type="button"
                  onClick={handleCheckPreCompat}
                  disabled={isCheckingPreCompat || selectedIds.length === 0}
                  style={{
                    padding: "12px 18px",
                    borderRadius: "8px",
                    background: "rgba(59, 130, 246, 0.15)",
                    border: "1px solid rgba(59, 130, 246, 0.4)",
                    color: "#93c5fd",
                    fontWeight: 700,
                    fontSize: "13px",
                    cursor: selectedIds.length === 0 ? "not-allowed" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    transition: "all 0.2s",
                    flex: 1,
                    minWidth: "180px",
                    justifyContent: "center",
                  }}
                  title="Run deterministic circuit rules (Pin Budget, PWM Timers, I2C Collision, 5V Regulator Current)"
                >
                  {isCheckingPreCompat ? "⏳ Checking..." : "🔍 Check Circuit Compatibility"}
                </button>
              </div>
            )}
          </form>

          {/* ── Pre-Compatibility Results Card (Node 3 Standalone) ── */}
          {preCompatResult && (
            <div
              style={{
                marginTop: "16px",
                padding: "16px",
                borderRadius: "10px",
                background:
                  preCompatResult.status === "pre_compat_passed"
                    ? "rgba(16, 185, 129, 0.1)"
                    : "rgba(239, 68, 68, 0.1)",
                border: `1px solid ${
                  preCompatResult.status === "pre_compat_passed"
                    ? "rgba(16, 185, 129, 0.3)"
                    : "rgba(239, 68, 68, 0.3)"
                }`,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "18px" }}>
                    {preCompatResult.status === "pre_compat_passed" ? "✅" : "⚠️"}
                  </span>
                  <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: preCompatResult.status === "pre_compat_passed" ? "#6ee7b7" : "#fca5a5" }}>
                    {preCompatResult.status === "pre_compat_passed"
                      ? "Circuit Pre-Compatibility: PASSED"
                      : `Circuit Pre-Compatibility: ${preCompatResult.errors?.length || 0} Error(s) Found`}
                  </h4>
                </div>
                <button
                  type="button"
                  onClick={() => setPreCompatResult(null)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                    fontSize: "14px",
                  }}
                >
                  ✕
                </button>
              </div>

              {preCompatResult.status === "pre_compat_passed" && (
                <p style={{ margin: 0, fontSize: "12px", color: "var(--text-secondary)" }}>
                  ✓ All hardware checks verified: Digital Pin Budget, Analog Channels, PWM Timers, I2C Addresses, and 5V Regulator Current draw are within safety limits.
                </p>
              )}

              {/* Errors List */}
              {Array.isArray(preCompatResult.errors) && preCompatResult.errors.length > 0 && (
                <div style={{ marginTop: "8px", display: "flex", flexDirection: "column", gap: "6px" }}>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: "#ef4444", textTransform: "uppercase" }}>
                    Blocking Errors:
                  </span>
                  {preCompatResult.errors.map((err, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "8px 12px",
                        background: "rgba(239, 68, 68, 0.15)",
                        border: "1px solid rgba(239, 68, 68, 0.25)",
                        borderRadius: "6px",
                        fontSize: "12px",
                        color: "#fca5a5",
                        display: "flex",
                        gap: "6px",
                        alignItems: "flex-start",
                      }}
                    >
                      <span>❌</span>
                      <div>
                        <strong>[{err.type}]</strong> {err.message}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Warnings List */}
              {Array.isArray(preCompatResult.warnings) && preCompatResult.warnings.length > 0 && (
                <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: "#f59e0b", textTransform: "uppercase" }}>
                    Notices & Warnings:
                  </span>
                  {preCompatResult.warnings.map((warn, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "8px 12px",
                        background: "rgba(245, 158, 11, 0.15)",
                        border: "1px solid rgba(245, 158, 11, 0.25)",
                        borderRadius: "6px",
                        fontSize: "12px",
                        color: "#fcd34d",
                        display: "flex",
                        gap: "6px",
                        alignItems: "flex-start",
                      }}
                    >
                      <span>⚠️</span>
                      <div>
                        <strong>[{warn.type}]</strong> {warn.message}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

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

          {/* ── HUMAN-IN-THE-LOOP (HITL) HARDWARE & ALIGNMENT WORKSPACE ── */}
          {hitlData && (
            <div style={styles.hitlCard}>
              <div style={styles.hitlHeader}>
                <div>
                  <h3 style={styles.hitlTitle}>
                    🤝 Hardware & Configuration Alignment Review
                  </h3>
                  <p style={styles.hitlSub}>
                    Review instance-based roles, inspect voltage & quantity adjustments, and resolve any hardware discrepancies before synthesis.
                  </p>
                </div>
                <div
                  style={{
                    ...styles.alignBadge,
                    ...(!hasMismatches
                      ? styles.alignBadgeSuccess
                      : styles.alignBadgeWarning),
                  }}
                >
                  {!hasMismatches
                    ? "✓ Hardware, Quantities & Voltage Aligned"
                    : "⚠️ Adjustments Needed"}
                </div>
              </div>

              {/* 1. VOLTAGE ADJUSTMENT ALERT CARD (⚡ Gold / Amber Alert) */}
              {voltageAdjustmentsList.length > 0 && (
                <div style={styles.voltageAdjustmentCard}>
                  <div style={styles.voltageCardHeader}>
                    <div style={styles.voltageTitleGroup}>
                      <span style={styles.voltageAlertIcon}>⚡</span>
                      <div>
                        <h4 style={styles.voltageAdjustmentTitle}>
                          Power Supply Voltage Adjustment Suggested
                        </h4>
                        <p style={styles.voltageSubText}>
                          The AI analyzed your circuit's actuator loads and recommends adjusting the power supply voltage.
                        </p>
                      </div>
                    </div>
                    <span style={styles.voltageBadgeCount}>
                      {voltageAdjustmentsList.length} suggestion{voltageAdjustmentsList.length > 1 ? "s" : ""}
                    </span>
                  </div>

                  <div style={styles.rolesGrid}>
                    {voltageAdjustmentsList.map((item, idx) => {
                      const compObj = availableComponents.find(
                        (c) => c.id === item.component_id
                      );
                      const compName = compObj?.name || item.component_id;
                      const currentVolt =
                        componentConfigs[item.component_id]?.voltage ||
                        item.current_voltage ||
                        "5V";

                      return (
                        <div key={idx} style={styles.voltageItemCard}>
                          <div style={styles.voltageItemTop}>
                            <div style={styles.voltageItemTitle}>
                              <span style={styles.voltageItemIcon}>🔋</span>
                              <strong>{compName}</strong>
                              <span style={styles.voltageIdBadge}>({item.component_id})</span>
                            </div>
                            <div style={styles.voltageComparisonPill}>
                              <span style={styles.pillSelected}>
                                Current: <strong>{currentVolt}</strong>
                              </span>
                              <span style={styles.pillArrowGold}>➔</span>
                              <span style={styles.pillRecommendedGold}>
                                Recommended: <strong>{item.recommended_voltage}</strong>
                              </span>
                            </div>
                          </div>

                          <p style={styles.voltageReasonText}>{item.reason}</p>

                          <div style={styles.voltageActionRow}>
                            <div style={styles.voltageSelectInline}>
                              <span style={styles.stepperLabel}>Set Voltage:</span>
                              <select
                                style={styles.voltageDropdownSmall}
                                value={currentVolt}
                                onChange={(e) =>
                                  setComponentVoltage(item.component_id, e.target.value)
                                }
                              >
                                {VOLTAGE_PRESETS.map((p) => (
                                  <option key={p.value} value={p.value}>
                                    {p.label}
                                  </option>
                                ))}
                              </select>
                            </div>

                            <div style={styles.quantityBtnGroup}>
                              <button
                                type="button"
                                style={styles.applyVoltageBtn}
                                onClick={() =>
                                  handleApplyVoltageAdjustment(
                                    item.component_id,
                                    item.recommended_voltage
                                  )
                                }
                              >
                                ✓ Set to {item.recommended_voltage}
                              </button>
                              <button
                                type="button"
                                style={styles.dismissQuantityBtn}
                                onClick={() =>
                                  handleDismissVoltageAdjustment(item.component_id)
                                }
                              >
                                Keep {currentVolt}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 2. QUANTITY ADJUSTMENT ALERT CARD (Cyan/Sky Blue Alert) */}
              {quantityAdjustmentsList.length > 0 && (
                <div style={styles.quantityAdjustmentCard}>
                  <div style={styles.quantityCardHeader}>
                    <div style={styles.quantityTitleGroup}>
                      <span style={styles.quantityAlertIcon}>⚖️</span>
                      <div>
                        <h4 style={styles.quantityAdjustmentTitle}>
                          Quantity Adjustments Suggested
                        </h4>
                        <p style={styles.quantitySubText}>
                          The AI detected that the component quantities in your scope differ from your current selection.
                        </p>
                      </div>
                    </div>
                    <span style={styles.quantityBadgeCount}>
                      {quantityAdjustmentsList.length} adjustment{quantityAdjustmentsList.length > 1 ? "s" : ""}
                    </span>
                  </div>

                  <div style={styles.rolesGrid}>
                    {quantityAdjustmentsList.map((item, idx) => {
                      const compObj = availableComponents.find(
                        (c) => c.id === item.component_id
                      );
                      const compName = compObj?.name || item.component_id;
                      const icon =
                        CATEGORY_ICON[compObj?.category?.toLowerCase()] ||
                        CATEGORY_ICON.default;
                      const currentQty =
                        selectedQuantities[item.component_id] || item.selected_quantity;

                      return (
                        <div key={idx} style={styles.quantityItemCard}>
                          <div style={styles.quantityItemTop}>
                            <div style={styles.quantityItemTitle}>
                              <span style={styles.quantityItemIcon}>{icon}</span>
                              <strong>{compName}</strong>
                              <span style={styles.quantityIdBadge}>({item.component_id})</span>
                            </div>
                            <div style={styles.quantityComparisonPill}>
                              <span style={styles.pillSelected}>
                                Selected: <strong>{currentQty}</strong>
                              </span>
                              <span style={styles.pillArrow}>➔</span>
                              <span style={styles.pillRecommended}>
                                Scope Needs: <strong>{item.recommended_quantity}</strong>
                              </span>
                            </div>
                          </div>

                          <p style={styles.quantityReasonText}>{item.reason}</p>

                          <div style={styles.quantityActionRow}>
                            <div style={styles.quantityStepperInline}>
                              <span style={styles.stepperLabel}>Set Quantity:</span>
                              <button
                                type="button"
                                style={styles.inlineQtyBtn}
                                onClick={() =>
                                  changeComponentQuantity(item.component_id, -1)
                                }
                              >
                                −
                              </button>
                              <span style={styles.inlineQtyValue}>{currentQty}</span>
                              <button
                                type="button"
                                style={styles.inlineQtyBtn}
                                onClick={() =>
                                  changeComponentQuantity(item.component_id, 1)
                                }
                              >
                                +
                              </button>
                            </div>

                            <div style={styles.quantityBtnGroup}>
                              <button
                                type="button"
                                style={styles.applyQuantityBtn}
                                onClick={() =>
                                  handleApplyQuantityAdjustment(
                                    item.component_id,
                                    item.recommended_quantity
                                  )
                                }
                              >
                                ✓ Set to {item.recommended_quantity}
                              </button>
                              <button
                                type="button"
                                style={styles.dismissQuantityBtn}
                                onClick={() =>
                                  handleDismissQuantityAdjustment(item.component_id)
                                }
                              >
                                Keep {currentQty}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 3. Missing Hardware Roles Cards */}
              {missingRolesList.length > 0 && (
                <div style={styles.warningCard}>
                  <h4 style={styles.warningTitle}>⚠️ AI Identified Missing Hardware Categories</h4>
                  <p style={styles.warningSubText}>
                    These hardware categories are required by your scope but currently have 0 units selected.
                  </p>
                  <div style={styles.rolesGrid}>
                    {missingRolesList.map((m, idx) => {
                      const neededCount = m.quantity_needed || m.count || 1;
                      return (
                        <div key={idx} style={styles.missingItemCard}>
                          <div style={styles.missingHeader}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                              <strong>Needed Role: {m.role}</strong>
                              <span
                                style={{
                                  padding: "2px 8px",
                                  borderRadius: "12px",
                                  background: neededCount > 1 ? "rgba(239, 68, 68, 0.2)" : "rgba(245, 158, 11, 0.2)",
                                  border: `1px solid ${neededCount > 1 ? "rgba(239, 68, 68, 0.4)" : "rgba(245, 158, 11, 0.4)"}`,
                                  color: neededCount > 1 ? "#fca5a5" : "#fcd34d",
                                  fontSize: "11px",
                                  fontWeight: 700,
                                }}
                              >
                                {neededCount > 1 ? `Requires ${neededCount} units` : "1 unit needed"}
                              </span>
                            </div>
                            <span style={styles.suggestionTag}>
                              {m.suggestion ? `Suggested: ${m.suggestion}` : "Component Required"}
                            </span>
                          </div>

                          {/* Reason */}
                          <p style={styles.missingReason}>{m.reason}</p>

                        <div style={styles.missingActions}>
                          <select
                            style={styles.selectDropdown}
                            value={selectedForMissing[idx] || (m.suggestion && availableComponents.some(c => c.id === m.suggestion) ? m.suggestion : "")}
                            onChange={(e) =>
                              setSelectedForMissing({
                                ...selectedForMissing,
                                [idx]: e.target.value,
                              })
                            }
                          >
                            <option value="">Select Catalog Component to Add...</option>
                            {availableComponents.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.name || c.id} ({c.category || "hardware"})
                              </option>
                            ))}
                          </select>

                          {/* Quantity Selector for Missing Components */}
                          <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "rgba(0,0,0,0.3)", padding: "4px 8px", borderRadius: "6px", border: "1px solid var(--border)" }}>
                            <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Qty:</span>
                            <input
                              type="number"
                              min="1"
                              max="50"
                              value={missingQuantities[idx] ?? (m.quantity_needed || m.count || 1)}
                              onChange={(e) =>
                                setMissingQuantities({
                                  ...missingQuantities,
                                  [idx]: Math.max(1, parseInt(e.target.value || "1", 10)),
                                })
                              }
                              style={{
                                width: "50px",
                                padding: "4px",
                                borderRadius: "4px",
                                background: "rgba(0,0,0,0.4)",
                                border: "1px solid var(--border)",
                                color: "#fff",
                                fontSize: "12px",
                                textAlign: "center",
                              }}
                            />
                          </div>

                          <button
                            type="button"
                            style={styles.addMissingBtn}
                            onClick={() => handleAddMissingComponent(idx, m)}
                            disabled={!selectedForMissing[idx] && (!m.suggestion || !availableComponents.some(c => c.id === m.suggestion))}
                          >
                            ➕ Add ×{missingQuantities[idx] ?? (m.quantity_needed || m.count || 1)} to Selection
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
                    );
                  })}
                  </div>
                </div>
              )}

              {/* 4. Unassigned Components Cards */}
              {unassignedList.length > 0 && (
                <div style={styles.unassignedCard}>
                  <h4 style={styles.unassignedTitle}>❓ Unassigned Components Detected</h4>
                  <p style={styles.warningSubText}>
                    These selected components have zero functional role in the described project scope.
                  </p>
                  <div style={styles.rolesGrid}>
                    {unassignedList.map((u) => {
                      const compObj = availableComponents.find(
                        (c) => c.id === u.component_id
                      );
                      const compName = compObj?.name || u.component_id;
                      const icon =
                        CATEGORY_ICON[compObj?.category?.toLowerCase()] ||
                        CATEGORY_ICON.default;

                      return (
                        <div key={u.component_id} style={styles.unassignedItemCard}>
                          <div style={styles.unassignedHeader}>
                            <span>
                              {icon} <strong>{compName}</strong> ({u.component_id})
                            </span>
                            <span style={styles.reasonBadge}>
                              {u.reason || "No role specified in scope"}
                            </span>
                          </div>

                          <div style={styles.unassignedControls}>
                            <input
                              type="text"
                              style={styles.customRoleInput}
                              placeholder="Or define custom role (e.g. 'Status alert indicator')..."
                              value={customRoleInput[u.component_id] || ""}
                              onChange={(e) =>
                                setCustomRoleInput({
                                  ...customRoleInput,
                                  [u.component_id]: e.target.value,
                                })
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

              {/* 5. Categorized or Instance-Based Role Assignments */}
              <div style={styles.section}>
                <div style={styles.sectionHeader}>
                  <div>
                    <h4 style={styles.sectionTitle}>
                      📌 Component Role Assignments ({Object.keys(editedRoles).length})
                    </h4>
                    <span style={styles.sectionSub}>
                      {categorizedRolesList.length > 1
                        ? "Roles are partitioned by microcontroller batch according to your hardware selection."
                        : "Each hardware unit has a distinct operational role matching your selection."}
                    </span>
                  </div>
                  <button
                    style={styles.textBtn}
                    onClick={() => setIsEditing(!isEditing)}
                    type="button"
                  >
                    {isEditing ? "Done Editing" : "✏️ Edit Role Descriptions"}
                  </button>
                </div>

                {categorizedRolesList.length > 1 ? (
                  <div style={styles.categorizedBoardsStack}>
                    {categorizedRolesList.map((cat, cIdx) => (
                      <div key={cIdx} style={styles.boardSubsystemCard}>
                        <div style={styles.boardSubsystemHeader}>
                          <span style={styles.boardSubsystemBadge}>
                            {cIdx === 0 ? "🔲 BOARD BATCH #1 (Primary Controller)" : `🔲 BOARD BATCH #${cIdx + 1} (Secondary Controller)`}
                          </span>
                          <span style={styles.boardSubsystemId}>{cat.board_id}</span>
                        </div>
                        <h5 style={styles.boardSubsystemTitle}>{cat.board_name || `Board #${cIdx + 1}`}</h5>

                        <div style={styles.rolesGrid}>
                          {Object.entries(cat.roles || {}).map(([roleKey, roleStr]) => {
                            const { baseId, instanceNum } = parseInstanceKey(roleKey);
                            const compObj = availableComponents.find((c) => c.id === baseId);
                            const compName = compObj?.name || baseId;
                            const icon =
                              CATEGORY_ICON[compObj?.category?.toLowerCase()] ||
                              CATEGORY_ICON.default;

                            return (
                              <div key={roleKey} style={styles.roleItem}>
                                <div style={styles.roleHeader}>
                                  <span style={styles.roleIcon}>{icon}</span>
                                  <strong style={styles.roleCompName}>{compName}</strong>
                                  {instanceNum ? (
                                    <span style={styles.instanceBadge}>Unit #{instanceNum}</span>
                                  ) : (
                                    <span style={styles.singleUnitBadge}>Unit #1</span>
                                  )}
                                  <span style={styles.roleIdBadge}>({roleKey})</span>
                                  <button
                                    type="button"
                                    onClick={() => handleRemoveRoleInstance(roleKey)}
                                    title={`Remove ${compName} from project selection`}
                                    style={{
                                      marginLeft: "auto",
                                      background: "rgba(239, 68, 68, 0.12)",
                                      border: "1px solid rgba(239, 68, 68, 0.3)",
                                      borderRadius: "4px",
                                      color: "#fca5a5",
                                      cursor: "pointer",
                                      fontSize: "12px",
                                      padding: "2px 6px",
                                      lineHeight: "1",
                                    }}
                                  >
                                    🗑️
                                  </button>
                                </div>
                                {isEditing ? (
                                  <input
                                    type="text"
                                    style={styles.roleInput}
                                    value={editedRoles[roleKey] || ""}
                                    onChange={(e) =>
                                      setEditedRoles({
                                        ...editedRoles,
                                        [roleKey]: e.target.value,
                                      })
                                    }
                                  />
                                ) : (
                                  <p style={styles.roleDesc}>{editedRoles[roleKey] || roleStr}</p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={styles.rolesGrid}>
                    {Object.entries(editedRoles || {}).map(([roleKey, roleStr]) => {
                      const { baseId, instanceNum } = parseInstanceKey(roleKey);
                      const compObj = availableComponents.find((c) => c.id === baseId);
                      const compName = compObj?.name || baseId;
                      const icon =
                        CATEGORY_ICON[compObj?.category?.toLowerCase()] ||
                        CATEGORY_ICON.default;

                      return (
                        <div key={roleKey} style={styles.roleItem}>
                          <div style={styles.roleHeader}>
                            <span style={styles.roleIcon}>{icon}</span>
                            <strong style={styles.roleCompName}>{compName}</strong>
                            {instanceNum ? (
                              <span style={styles.instanceBadge}>Unit #{instanceNum}</span>
                            ) : (
                              <span style={styles.singleUnitBadge}>Unit #1</span>
                            )}
                            <span style={styles.roleIdBadge}>({roleKey})</span>
                            <button
                              type="button"
                              onClick={() => handleRemoveRoleInstance(roleKey)}
                              title={`Remove ${compName} from project selection`}
                              style={{
                                marginLeft: "auto",
                                background: "rgba(239, 68, 68, 0.12)",
                                border: "1px solid rgba(239, 68, 68, 0.3)",
                                borderRadius: "4px",
                                color: "#fca5a5",
                                cursor: "pointer",
                                fontSize: "12px",
                                padding: "2px 6px",
                                lineHeight: "1",
                              }}
                            >
                              🗑️
                            </button>
                          </div>
                          {isEditing ? (
                            <input
                              type="text"
                              style={styles.roleInput}
                              value={editedRoles[roleKey] || ""}
                              onChange={(e) =>
                                setEditedRoles({
                                  ...editedRoles,
                                  [roleKey]: e.target.value,
                                })
                              }
                            />
                          ) : (
                            <p style={styles.roleDesc}>{editedRoles[roleKey] || roleStr}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* 6. Enriched Technical Scope */}
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
                    placeholder="Tell the AI why you disagree with these roles, voltages, or quantities..."
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
                        onClick={() => handleStartGeneration(null, selectedQuantities)}
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
                      onClick={() =>
                        handleConfirmAction(isEditing ? "edited" : "confirmed")
                      }
                      disabled={isLoading}
                    >
                      {isEditing
                        ? "✏️ Save Edits & Synthesize Wiring"
                        : "✓ Confirm Roles & Synthesize Wiring"}
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
    gridTemplateColumns: "360px 1fr",
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
    alignItems: "flex-start",
    marginBottom: "14px",
  },
  panelTitle: {
    fontSize: "14px",
    fontWeight: 700,
    color: "var(--text-primary)",
    margin: "0 0 2px",
    fontFamily: "var(--font-heading)",
  },
  panelSubText: {
    fontSize: "11px",
    color: "var(--text-muted)",
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
    flexDirection: "column",
    gap: "8px",
    maxHeight: "520px",
    overflowY: "auto",
    paddingRight: "4px",
  },
  bubbleCard: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    padding: "8px 12px",
    borderRadius: "var(--radius-md)",
    background: "rgba(255, 255, 255, 0.04)",
    border: "1px solid var(--border)",
    transition: "all 0.2s ease",
  },
  bubbleCardSelected: {
    background: "rgba(99, 102, 241, 0.16)",
    border: "1px solid var(--accent)",
    boxShadow: "0 0 10px rgba(99, 102, 241, 0.25)",
  },
  bubbleCardPower: {
    borderLeft: "3px solid #eab308",
  },
  bubbleCardTopRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  bubbleClickArea: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    cursor: "pointer",
    flex: 1,
    overflow: "hidden",
  },
  bubbleIcon: {
    fontSize: "15px",
    flexShrink: 0,
  },
  bubbleTextGroup: {
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  bubbleName: {
    fontSize: "13px",
    fontWeight: 500,
    color: "var(--text-primary)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  adjustableBadge: {
    fontSize: "10px",
    fontWeight: 600,
    color: "#eab308",
  },
  multiVoltageContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    paddingTop: "6px",
    marginTop: "2px",
    borderTop: "1px dashed rgba(234, 179, 8, 0.3)",
  },
  voltageConfigRow: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  voltageLabel: {
    fontSize: "11px",
    fontWeight: 600,
    color: "#eab308",
    whiteSpace: "nowrap",
  },
  voltageDropdown: {
    flex: 1,
    padding: "4px 8px",
    borderRadius: "4px",
    background: "rgba(0, 0, 0, 0.4)",
    color: "#fef08a",
    border: "1px solid rgba(234, 179, 8, 0.4)",
    fontSize: "11px",
    fontWeight: 600,
    outline: "none",
  },
  quantityControl: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
    marginLeft: "8px",
    background: "rgba(0, 0, 0, 0.3)",
    padding: "2px 6px",
    borderRadius: "16px",
    border: "1px solid rgba(99, 102, 241, 0.4)",
  },
  qtyBtn: {
    width: "22px",
    height: "22px",
    borderRadius: "50%",
    border: "none",
    background: "rgba(255, 255, 255, 0.1)",
    color: "#fff",
    fontSize: "13px",
    fontWeight: 700,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "background 0.15s ease",
  },
  qtyBadge: {
    fontSize: "12px",
    fontWeight: 700,
    color: "var(--accent-2)",
    padding: "0 4px",
    minWidth: "22px",
    textAlign: "center",
  },
  addInitialBtn: {
    width: "24px",
    height: "24px",
    borderRadius: "50%",
    border: "1px solid var(--border)",
    background: "rgba(255, 255, 255, 0.06)",
    color: "var(--text-secondary)",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
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

  /* VOLTAGE RECOMMENDATION ALERT STYLING (⚡ Gold / Amber) */
  voltageAdjustmentCard: {
    padding: "18px 20px",
    background: "rgba(234, 179, 8, 0.08)",
    borderRadius: "var(--radius-md)",
    border: "1.5px solid rgba(234, 179, 8, 0.45)",
    boxShadow: "0 4px 20px rgba(234, 179, 8, 0.15)",
    display: "flex",
    flexDirection: "column",
    gap: "14px",
  },
  voltageCardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  voltageTitleGroup: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  voltageAlertIcon: {
    fontSize: "20px",
  },
  voltageAdjustmentTitle: {
    margin: 0,
    fontSize: "15px",
    fontWeight: 700,
    color: "#facc15",
  },
  voltageSubText: {
    margin: "2px 0 0",
    fontSize: "12px",
    color: "var(--text-secondary)",
  },
  voltageBadgeCount: {
    fontSize: "11px",
    fontWeight: 700,
    padding: "4px 8px",
    borderRadius: "12px",
    background: "rgba(234, 179, 8, 0.2)",
    color: "#facc15",
    border: "1px solid rgba(234, 179, 8, 0.4)",
  },
  voltageItemCard: {
    padding: "14px 16px",
    background: "rgba(0, 0, 0, 0.35)",
    borderRadius: "var(--radius-sm)",
    border: "1px solid rgba(234, 179, 8, 0.25)",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  voltageItemTop: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "10px",
  },
  voltageItemTitle: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "14px",
    color: "#fff",
  },
  voltageItemIcon: {
    fontSize: "16px",
  },
  voltageIdBadge: {
    fontSize: "11px",
    color: "var(--text-muted)",
    fontFamily: "monospace",
  },
  voltageComparisonPill: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "4px 10px",
    borderRadius: "14px",
    background: "rgba(234, 179, 8, 0.12)",
    border: "1px solid rgba(234, 179, 8, 0.35)",
    fontSize: "12px",
  },
  pillArrowGold: {
    color: "#facc15",
    fontWeight: 700,
  },
  pillRecommendedGold: {
    color: "#fde047",
  },
  voltageReasonText: {
    margin: 0,
    fontSize: "13px",
    color: "var(--text-secondary)",
    lineHeight: 1.4,
  },
  voltageActionRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "10px",
    paddingTop: "6px",
    borderTop: "1px solid rgba(255, 255, 255, 0.06)",
  },
  voltageSelectInline: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  voltageDropdownSmall: {
    padding: "6px 10px",
    borderRadius: "4px",
    background: "var(--bg-surface)",
    color: "#facc15",
    border: "1px solid rgba(234, 179, 8, 0.4)",
    fontSize: "12px",
    fontWeight: 600,
    outline: "none",
  },
  applyVoltageBtn: {
    padding: "6px 14px",
    borderRadius: "var(--radius-sm)",
    background: "#d97706",
    color: "#fff",
    fontWeight: 600,
    fontSize: "12px",
    border: "none",
    cursor: "pointer",
    transition: "background 0.15s ease",
  },

  /* QUANTITY ADJUSTMENTS ALERT STYLING (Cyan / Sky Blue) */
  quantityAdjustmentCard: {
    padding: "18px 20px",
    background: "rgba(6, 182, 212, 0.08)",
    borderRadius: "var(--radius-md)",
    border: "1.5px solid rgba(6, 182, 212, 0.4)",
    boxShadow: "0 4px 20px rgba(6, 182, 212, 0.12)",
    display: "flex",
    flexDirection: "column",
    gap: "14px",
  },
  quantityCardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  quantityTitleGroup: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  quantityAlertIcon: {
    fontSize: "20px",
  },
  quantityAdjustmentTitle: {
    margin: 0,
    fontSize: "15px",
    fontWeight: 700,
    color: "#22d3ee",
  },
  quantitySubText: {
    margin: "2px 0 0",
    fontSize: "12px",
    color: "var(--text-secondary)",
  },
  quantityBadgeCount: {
    fontSize: "11px",
    fontWeight: 700,
    padding: "4px 8px",
    borderRadius: "12px",
    background: "rgba(6, 182, 212, 0.2)",
    color: "#22d3ee",
    border: "1px solid rgba(6, 182, 212, 0.4)",
  },
  quantityItemCard: {
    padding: "14px 16px",
    background: "rgba(0, 0, 0, 0.35)",
    borderRadius: "var(--radius-sm)",
    border: "1px solid rgba(6, 182, 212, 0.25)",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  quantityItemTop: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "10px",
  },
  quantityItemTitle: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "14px",
    color: "#fff",
  },
  quantityItemIcon: {
    fontSize: "16px",
  },
  quantityIdBadge: {
    fontSize: "11px",
    color: "var(--text-muted)",
    fontFamily: "monospace",
  },
  quantityComparisonPill: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "4px 10px",
    borderRadius: "14px",
    background: "rgba(6, 182, 212, 0.12)",
    border: "1px solid rgba(6, 182, 212, 0.3)",
    fontSize: "12px",
  },
  pillSelected: {
    color: "#cbd5e1",
  },
  pillArrow: {
    color: "#22d3ee",
    fontWeight: 700,
  },
  pillRecommended: {
    color: "#22d3ee",
  },
  quantityReasonText: {
    margin: 0,
    fontSize: "13px",
    color: "var(--text-secondary)",
    lineHeight: 1.4,
  },
  quantityActionRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "10px",
    paddingTop: "6px",
    borderTop: "1px solid rgba(255, 255, 255, 0.06)",
  },
  quantityStepperInline: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  stepperLabel: {
    fontSize: "12px",
    color: "var(--text-muted)",
  },
  inlineQtyBtn: {
    width: "24px",
    height: "24px",
    borderRadius: "4px",
    border: "1px solid rgba(255, 255, 255, 0.15)",
    background: "rgba(255, 255, 255, 0.08)",
    color: "#fff",
    fontSize: "13px",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  inlineQtyValue: {
    fontSize: "13px",
    fontWeight: 700,
    color: "#22d3ee",
    minWidth: "20px",
    textAlign: "center",
  },
  quantityBtnGroup: {
    display: "flex",
    gap: "8px",
  },
  applyQuantityBtn: {
    padding: "6px 14px",
    borderRadius: "var(--radius-sm)",
    background: "#0891b2",
    color: "#fff",
    fontWeight: 600,
    fontSize: "12px",
    border: "none",
    cursor: "pointer",
    transition: "background 0.15s ease",
  },
  dismissQuantityBtn: {
    padding: "6px 12px",
    borderRadius: "var(--radius-sm)",
    background: "transparent",
    color: "var(--text-muted)",
    border: "1px solid var(--border)",
    fontSize: "12px",
    cursor: "pointer",
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
  section: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },
  sectionTitle: {
    margin: "0 0 2px",
    fontSize: "14px",
    fontWeight: 700,
    color: "var(--accent-2)",
  },
  sectionSub: {
    fontSize: "12px",
    color: "var(--text-muted)",
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
  instanceBadge: {
    fontSize: "11px",
    fontWeight: 700,
    padding: "2px 6px",
    borderRadius: "4px",
    background: "rgba(99, 102, 241, 0.25)",
    color: "#a5b4fc",
    border: "1px solid rgba(99, 102, 241, 0.4)",
  },
  singleUnitBadge: {
    fontSize: "11px",
    fontWeight: 600,
    padding: "2px 6px",
    borderRadius: "4px",
    background: "rgba(255, 255, 255, 0.08)",
    color: "var(--text-muted)",
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
  /* BOARD-SCOPED CATALOG STYLES */
  microPromptBanner: {
    padding: "14px 16px",
    background: "rgba(99, 102, 241, 0.12)",
    borderRadius: "var(--radius-sm)",
    border: "1.5px dashed var(--accent)",
    display: "flex",
    alignItems: "center",
    gap: "12px",
    marginBottom: "16px",
  },
  microPromptIcon: {
    fontSize: "20px",
  },
  microPromptTitle: {
    color: "#fff",
    fontSize: "13px",
    display: "block",
    marginBottom: "2px",
  },
  microPromptSub: {
    margin: 0,
    fontSize: "12px",
    color: "var(--text-secondary)",
    lineHeight: 1.4,
  },
  boardSwitcherContainer: {
    marginBottom: "16px",
    padding: "10px 12px",
    background: "rgba(0, 0, 0, 0.3)",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border)",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  boardTabsList: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
  },
  boardTabBtn: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    padding: "6px 12px",
    borderRadius: "6px",
    border: "1px solid var(--border)",
    background: "rgba(255, 255, 255, 0.04)",
    color: "var(--text-secondary)",
    fontSize: "12px",
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  boardTabBtnActive: {
    background: "var(--accent)",
    color: "#fff",
    borderColor: "var(--accent)",
    boxShadow: "0 2px 10px var(--accent-glow)",
  },
  boardTabIcon: {
    fontSize: "12px",
  },
  boardTabTitle: {
    fontWeight: 700,
  },
  boardTabBadge: {
    fontSize: "10px",
    padding: "2px 6px",
    borderRadius: "10px",
    background: "rgba(0, 0, 0, 0.3)",
    color: "#e2e8f0",
  },
  boardTabBadgeWarning: {
    background: "rgba(245, 158, 11, 0.3)",
    color: "#fde68a",
    border: "1px solid rgba(245, 158, 11, 0.5)",
  },
  softcapBanner: {
    marginTop: "8px",
    padding: "10px 12px",
    background: "rgba(245, 158, 11, 0.12)",
    borderRadius: "var(--radius-sm)",
    border: "1px solid rgba(245, 158, 11, 0.35)",
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
  },
  softcapIcon: {
    fontSize: "16px",
    marginTop: "1px",
  },
  softcapTitle: {
    fontSize: "12px",
    color: "#fde68a",
    display: "block",
    marginBottom: "2px",
  },
  softcapText: {
    margin: 0,
    fontSize: "11px",
    color: "var(--text-secondary)",
    lineHeight: 1.4,
  },
  boardActiveHint: {
    fontSize: "11px",
    color: "var(--accent-2)",
  },
  bubbleCardLocked: {
    opacity: 0.45,
    cursor: "not-allowed",
    filter: "grayscale(30%)",
  },
  bubbleNameRow: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  microTagBadge: {
    fontSize: "9px",
    fontWeight: 700,
    padding: "1px 5px",
    borderRadius: "4px",
    background: "rgba(99, 102, 241, 0.25)",
    color: "#c7d2fe",
    border: "1px solid rgba(99, 102, 241, 0.4)",
    textTransform: "uppercase",
  },
  lockedBadge: {
    fontSize: "10px",
    color: "#fca5a5",
    marginTop: "2px",
    display: "block",
  },
  lockIconMini: {
    fontSize: "12px",
    opacity: 0.7,
  },

  /* CATEGORIZED BOARD HITL STYLES */
  categorizedBoardsStack: {
    display: "flex",
    flexDirection: "column",
    gap: "18px",
  },
  boardSubsystemCard: {
    padding: "16px",
    background: "rgba(0, 0, 0, 0.25)",
    borderRadius: "var(--radius-md)",
    border: "1.5px solid rgba(99, 102, 241, 0.35)",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  boardSubsystemHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  boardSubsystemBadge: {
    fontSize: "12px",
    fontWeight: 700,
    color: "var(--accent-2)",
  },
  boardSubsystemId: {
    fontSize: "11px",
    color: "var(--text-muted)",
    fontFamily: "monospace",
  },
  boardSubsystemTitle: {
    margin: 0,
    fontSize: "14px",
    fontWeight: 600,
    color: "#fff",
  },
  /* CATALOG SEARCH & CATEGORY FILTER STYLES */
  catalogSearchPanel: {
    marginBottom: "16px",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  searchInputWrapper: {
    position: "relative",
    display: "flex",
    alignItems: "center",
    width: "100%",
  },
  searchIcon: {
    position: "absolute",
    left: "12px",
    fontSize: "14px",
    opacity: 0.6,
    pointerEvents: "none",
  },
  searchInput: {
    width: "100%",
    padding: "9px 36px 9px 36px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border)",
    background: "rgba(0, 0, 0, 0.35)",
    color: "#fff",
    fontSize: "13px",
    outline: "none",
    transition: "border-color 0.2s ease, box-shadow 0.2s ease",
  },
  searchClearBtn: {
    position: "absolute",
    right: "10px",
    background: "transparent",
    border: "none",
    color: "var(--text-muted)",
    fontSize: "13px",
    cursor: "pointer",
    padding: "2px 6px",
    borderRadius: "4px",
  },
  catFilterChips: {
    display: "flex",
    flexWrap: "wrap",
    gap: "6px",
  },
  catFilterChip: {
    padding: "4px 10px",
    borderRadius: "14px",
    border: "1px solid var(--border)",
    background: "rgba(255, 255, 255, 0.03)",
    color: "var(--text-secondary)",
    fontSize: "11px",
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  catFilterChipActive: {
    background: "rgba(99, 102, 241, 0.25)",
    color: "var(--accent-2)",
    borderColor: "var(--accent)",
    fontWeight: 700,
  },
  noSearchMatch: {
    padding: "24px 16px",
    background: "rgba(0, 0, 0, 0.2)",
    borderRadius: "var(--radius-sm)",
    border: "1px dashed var(--border)",
    textAlign: "center",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "10px",
    color: "var(--text-secondary)",
    fontSize: "13px",
  },
  clearSearchFilterBtn: {
    padding: "6px 14px",
    borderRadius: "var(--radius-sm)",
    background: "var(--accent)",
    color: "#fff",
    border: "none",
    fontSize: "12px",
    fontWeight: 600,
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
