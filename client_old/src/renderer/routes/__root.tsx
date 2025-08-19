import { createRootRoute, Outlet } from "@tanstack/react-router";
import type { JSX } from "react";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";

function RootLayout(): JSX.Element {
  return (
    <>
      <Outlet />
      <TanStackRouterDevtools />
    </>
  );
}

export const Route = createRootRoute({
  component: RootLayout,
});
