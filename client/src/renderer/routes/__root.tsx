import {
  createRootRoute,
  Link,
  Outlet,
  useRouterState,
} from "@tanstack/react-router";
import type { JSX } from "react";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";

function RootLayout(): JSX.Element {
  const location = useRouterState({ select: (s) => s.location });
  const showNav = !location.pathname.startsWith("/pdf-view");

  return (
    <>
      {showNav && (
        <>
          <div className="p-2 flex gap-2">
            <Link to="/" className="[&.active]:font-bold">
              Home
            </Link>{" "}
            <Link to="/about" className="[&.active]:font-bold">
              About
            </Link>{" "}
            <Link to="/conn-definition" className="[&.active]:font-bold">
              Database Config
            </Link>
            <Link to="/pdf-picker" className="[&.active]:font-bold">
              PDF View
            </Link>
          </div>
          <hr />
        </>
      )}
      <Outlet />
      <TanStackRouterDevtools />
    </>
  );
}

export const Route = createRootRoute({
  component: RootLayout,
});
