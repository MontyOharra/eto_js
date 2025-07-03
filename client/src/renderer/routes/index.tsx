import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import type { position } from "../../../prisma/generated/prisma/index.js";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  const [connectionStatus, setConnectionStatus] = useState<boolean>(false);
  const [positions, setPositions] = useState<position[]>([]);

  useEffect(() => {
    window.electron.testDatabaseConnection().then((status) => {
      setConnectionStatus(status);
    });
  }, []);

  function handleGetPositions() {
    window.electron.getPositions().then((positions) => {
      setPositions(positions);
    });
  };

  return (
    <div className="p-2">
      <h3>Welcome Home!</h3>
      <p>Connection Status: {connectionStatus ? "Connected" : "Disconnected"}</p>
      <button onClick={handleGetPositions}>Get Positions</button>
      <pre>{JSON.stringify(positions, null, 2)}</pre>
    </div>
  );
}
