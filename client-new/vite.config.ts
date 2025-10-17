import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import tailwindcss from "@tailwindcss/vite";

import path from 'node:path';
import { fileURLToPath } from 'node:url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RENDERER = path.resolve(__dirname, 'src/renderer');


// https://vite.dev/config/
export default defineConfig({
  plugins: [
    tanstackRouter({
      "target": "react",
      "routesDirectory": path.join(RENDERER, 'pages'),        // absolute
      "generatedRouteTree": path.join(RENDERER, 'routeTree.gen.ts'), // absolute
      "autoCodeSplitting": true,
    }),
    react(),
    tailwindcss(),
  ],
  base: "./",
  root: "./src/renderer",
  publicDir: path.resolve(__dirname, 'public'),  // Point to client-new/public/
  build: {
    outDir: "../../build/dist-react",
  },
  server: {
    port: 5002,
    strictPort: true,
  },
});
