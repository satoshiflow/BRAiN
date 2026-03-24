import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "BRAiN AXE UI",
    short_name: "AXE UI",
    description: "Installierbare AXE Chat WebApp fuer mobile Nutzung.",
    start_url: "/chat",
    display: "standalone",
    background_color: "#020617",
    theme_color: "#020617",
    orientation: "portrait",
    scope: "/",
    categories: ["productivity", "utilities"],
    icons: [
      {
        src: "/icons/axe-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/axe-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icons/axe-512.svg",
        sizes: "512x512",
        type: "image/svg+xml",
        purpose: "any",
      },
    ],
  };
}
