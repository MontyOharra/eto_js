import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";

export const Route = createFileRoute("/dashboard/connection-status")({
  component: About,
});

export default function About() {
  const [connectionStatus, setConnectionStatus] = useState<boolean>(false);

  useEffect(() => {
    window.electron.testDatabaseConnection().then((status) => {
      setConnectionStatus(status);
    });
  }, []);

  return (
    <div className="p-2">
      <h3>Welcome Home!</h3>
      <p>
        Connection Status: {connectionStatus ? "Connected" : "Disconnected"}
      </p>
    </div>
  );
}
