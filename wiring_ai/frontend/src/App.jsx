import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [scope, setScope] = useState("");
  const [catalog, setCatalog] = useState([]);
  const [selectedComponents, setSelectedComponents] = useState([]);
  const [result, setResult] = useState(null);

  useEffect(() => {
    async function loadComponents() {
      const response = await fetch("http://127.0.0.1:8000/api/components");
      const data = await response.json();

      console.log("Component catalog from backend:", data);
      setCatalog(data);
    }

    loadComponents();
  }, []);

  function toggleComponent(componentId) {
    if (selectedComponents.includes(componentId)) {
      setSelectedComponents(
        selectedComponents.filter((id) => id !== componentId)
      );
    } else {
      setSelectedComponents([...selectedComponents, componentId]);
    }
  }

  async function handleGenerate() {
    const response = await fetch("http://127.0.0.1:8000/api/generate-project", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        scope: scope,
        selectedComponents: selectedComponents,
      }),
    });

    const data = await response.json();
    console.log("Backend response:", data);
    setResult(data);
  }

  return (
    <div className="app">
      <h1>Wiring AI</h1>

      <h2>1. Project Scope</h2>

      <textarea
        value={scope}
        onChange={(e) => setScope(e.target.value)}
        placeholder="Describe your project..."
      />

      <h2>2. Component Catalog from Backend</h2>

      {catalog.map((component) => (
        <div key={component.id} className="component-row">
          <input
            type="checkbox"
            checked={selectedComponents.includes(component.id)}
            onChange={() => toggleComponent(component.id)}
          />

          <div>
            <strong>{component.name}</strong>
            <p>{component.category}</p>
            <p>{component.description}</p>
          </div>
        </div>
      ))}

      <h2>3. Selected Component IDs</h2>

      {selectedComponents.length === 0 ? (
        <p>No components selected.</p>
      ) : (
        <ul>
          {selectedComponents.map((id) => (
            <li key={id}>{id}</li>
          ))}
        </ul>
      )}

      <button onClick={handleGenerate}>Generate Wiring</button>

      <hr />

      <h2>4. Backend Response</h2>

      {!result && <p>No response yet.</p>}

      {result && (
        <div>
          <h3>Scope sent to backend</h3>
          <p>{result.scope}</p>

          <h3>Components backend found from database</h3>
          <ul>
            {result.components.map((component) => (
              <li key={component.id}>
                {component.name} - {component.category}
              </li>
            ))}
          </ul>

          <h3>AI Compatibility Check</h3>
          <p>
            <strong>Compatible:</strong>{" "}
            {result.aiResult.compatible ? "Yes" : "No"}
          </p>
          <p>{result.aiResult.compatibilitySummary}</p>

          <h3>Missing Components</h3>
          {result.aiResult.missingComponents.length === 0 ? (
            <p>None</p>
          ) : (
            <ul>
              {result.aiResult.missingComponents.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          )}

          <h3>Warnings</h3>
          {result.aiResult.warnings.length === 0 ? (
            <p>None</p>
          ) : (
            <ul>
              {result.aiResult.warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          )}

          <h3>AI Wiring Steps</h3>
          {result.aiResult.steps.length === 0 ? (
            <p>No steps generated.</p>
          ) : (
            <ol>
              {result.aiResult.steps.map((step) => (
                <li key={step.id}>
                  <strong>{step.title}</strong>
                  <br />
                  {step.instruction}
                </li>
              ))}
            </ol>
          )}

          <h3>Connections</h3>
          {result.aiResult.connections.length === 0 ? (
            <p>No connections generated.</p>
          ) : (
            <ul>
              {result.aiResult.connections.map((connection) => (
                <li key={connection.id}>
                  {connection.fromComponent} {connection.fromPin} to{" "}
                  {connection.toComponent} {connection.toPin} - {connection.label}
                </li>
              ))}
            </ul>
          )}

          <h3>Raw JSON</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default App;