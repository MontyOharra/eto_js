import { createFileRoute } from "@tanstack/react-router";
import App from "../app";

export const Route = createFileRoute("/about")({
  component: About,
});

function About() {
  return (
    <div className="p-2">
      Hello from About!
      <App />
    </div>
  );
}
