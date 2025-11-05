import { createRootRoute, Outlet } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";
import type { JSX } from "react";

export const Route = createRootRoute({
    component: RootLayout,
  });

function RootLayout(): JSX.Element {
  return (
    <>
      <Outlet />
      <TanStackRouterDevtools />
    </>
  );
}
