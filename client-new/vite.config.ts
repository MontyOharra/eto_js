import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    tanstackRouter({
      "target": "react",
      "routesDirectory": "./src/renderer/pages",
      "generatedRouteTree": "./src/renderer/routeTree.gen.ts",
      "autoCodeSplitting": true,
    }),
    react(),
    tailwindcss(),
  ],
  base: "./",
  root: "./src/renderer",
  build: {
    outDir: "../../build/dist-react",
  },
  server: {
    port: 5002,
    strictPort: true,
  },
});
