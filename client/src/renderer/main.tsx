import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import "./App.css";
// Import the generated route tree
import App from "./app.js";

// Create a new router instance


// Render the app
const rootElement = document.getElementById("root")!;
if (!rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <StrictMode>
      <App />
    </StrictMode>
  );
}
