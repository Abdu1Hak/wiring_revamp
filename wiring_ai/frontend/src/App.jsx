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
          <h3>{result.title}</h3>
          <p>{result.summary}</p>

          <h3>Components Returned by Backend</h3>
          <ul>
            {result.components.map((component) => (
              <li key={component.id}>
                {component.name} - {component.category}
              </li>
            ))}
          </ul>

          <h3>Steps</h3>
          <ol>
            {result.steps.map((step) => (
              <li key={step.id}>
                <strong>{step.title}</strong>
                <br />
                {step.instruction}
              </li>
            ))}
          </ol>

          <h3>Raw JSON</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default App;