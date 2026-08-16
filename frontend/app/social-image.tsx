import { ImageResponse } from "next/og";

export const socialImageAlt =
  "Incident Triage Copilot — structured operational briefs from incident context";
export const socialImageSize = { width: 1200, height: 630 };
export const socialImageContentType = "image/png";

export function createSocialImage() {
  return new ImageResponse(
    <div
      style={{
        alignItems: "center",
        background:
          "radial-gradient(circle at 15% 10%, #5eead4 0%, transparent 34%), linear-gradient(135deg, #071a22 0%, #123941 55%, #0f766e 100%)",
        color: "white",
        display: "flex",
        fontFamily: "Arial, sans-serif",
        height: "100%",
        justifyContent: "center",
        padding: "72px",
        width: "100%",
      }}
    >
      <div
        style={{
          border: "1px solid rgba(255,255,255,0.24)",
          borderRadius: "40px",
          display: "flex",
          flexDirection: "column",
          padding: "64px",
          width: "100%",
        }}
      >
        <div
          style={{
            color: "#99f6e4",
            display: "flex",
            fontSize: 24,
            fontWeight: 700,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          AI-assisted incident response
        </div>
        <div
          style={{
            display: "flex",
            fontSize: 68,
            fontWeight: 750,
            letterSpacing: "-0.045em",
            lineHeight: 1.05,
            marginTop: 28,
            maxWidth: 920,
          }}
        >
          Incident Triage Copilot
        </div>
        <div
          style={{
            color: "#d7f7f2",
            display: "flex",
            fontSize: 30,
            lineHeight: 1.35,
            marginTop: 30,
            maxWidth: 920,
          }}
        >
          Turn alerts, logs, metrics, and deployment context into a structured
          operational brief.
        </div>
      </div>
    </div>,
    socialImageSize,
  );
}
