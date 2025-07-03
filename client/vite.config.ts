import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { tanstackRouter } from "@tanstack/router-plugin/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    tanstackRouter({
      target: "react",
      autoCodeSplitting: true,
      routesDirectory: "./src/renderer/routes",
      generatedRouteTree: "./src/renderer/routeTree.gen.ts",
    }),
    react(),
  ],
  base: "./",
  build: {
    outDir: "build/dist-react",
  },
  server: {
    port: 5000,
    strictPort: true,
  },
});
