export interface AnalyzeIncidentRequest {
  incident_packet: string;
  service: string | null;
  environment: string | null;
  recent_deployment: string | null;
  metric_summary: string | null;
}

export type IncidentSeverity = "sev-1" | "sev-2" | "sev-3" | "sev-4";

export interface AnalyzeIncidentResponse {
  summary: string;
  impacted_service: string;
  severity: IncidentSeverity;
  likely_root_cause_hypothesis: string;
  immediate_next_actions: string[];
  confidence_score: number;
}

const ANALYZE_INCIDENT_ERROR =
  "Unable to analyze incident. Check the backend connection and try again.";
const validSeverities = new Set<IncidentSeverity>([
  "sev-1",
  "sev-2",
  "sev-3",
  "sev-4",
]);

function createAnalyzeIncidentError(): Error {
  return new Error(ANALYZE_INCIDENT_ERROR);
}

function isAnalyzeIncidentResponse(
  value: unknown,
): value is AnalyzeIncidentResponse {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;

  return (
    typeof candidate.summary === "string" &&
    typeof candidate.impacted_service === "string" &&
    typeof candidate.severity === "string" &&
    validSeverities.has(candidate.severity as IncidentSeverity) &&
    typeof candidate.likely_root_cause_hypothesis === "string" &&
    Array.isArray(candidate.immediate_next_actions) &&
    candidate.immediate_next_actions.every(
      (action) => typeof action === "string",
    ) &&
    typeof candidate.confidence_score === "number"
  );
}

export async function analyzeIncident(
  payload: AnalyzeIncidentRequest,
): Promise<AnalyzeIncidentResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!baseUrl) {
    throw createAnalyzeIncidentError();
  }

  let response: Response;

  try {
    response = await fetch(`${baseUrl}/api/triage`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch {
    throw createAnalyzeIncidentError();
  }

  if (!response.ok) {
    throw createAnalyzeIncidentError();
  }

  let data: unknown;

  try {
    data = await response.json();
  } catch {
    throw createAnalyzeIncidentError();
  }

  if (!isAnalyzeIncidentResponse(data)) {
    throw createAnalyzeIncidentError();
  }

  return data;
}
