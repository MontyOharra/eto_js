import { createRootRoute, Outlet } from "@tanstack/react-router";
import type { JSX } from "react";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";

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
