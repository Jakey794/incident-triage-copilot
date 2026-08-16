import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Incident Triage Copilot",
    short_name: "Triage Copilot",
    description:
      "Turn incident context into a structured operational triage brief.",
    start_url: "/",
    display: "standalone",
    background_color: "#edf2f1",
    theme_color: "#0f766e",
    icons: [
      {
        src: "/favicon.ico",
        sizes: "256x256",
        type: "image/x-icon",
      },
    ],
  };
}
