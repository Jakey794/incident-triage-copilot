"use client";

import { useState } from "react";
import {
  type AnalyzeIncidentRequest,
  type AnalyzeIncidentResponse,
  analyzeIncident,
} from "@/lib/api";
import { ResultCards } from "./result-cards";

type ResultState =
  | { status: "empty" }
  | { status: "loading" }
  | { message: string; status: "error" }
  | { data: AnalyzeIncidentResponse; status: "success" };

type DemoIncident = AnalyzeIncidentRequest & {
  label: string;
};

const initialForm: AnalyzeIncidentRequest = {
  incident_packet: "",
  service: "",
  environment: "",
  recent_deployment: "",
  metric_summary: "",
};

const demoIncidents: DemoIncident[] = [
  {
    label: "Load demo: deployment failure",
    incident_packet:
      "Production alerts fired 8 minutes after a rollout to checkout-api. HTTP 500 rate increased from 0.4% to 19.2%. Checkout requests are failing across web and mobile. Customer support reports users cannot complete purchases. Error logs show a spike in null reference exceptions in the payment routing path. Request volume is steady and rollback has not started yet.",
    service: "checkout-api",
    environment: "production",
    recent_deployment:
      "Rolled out build 2026.04.09.7 with payment routing and feature-flag cleanup changes",
    metric_summary:
      "HTTP 500 rate 0.4% -> 19.2%, p95 latency 420ms -> 1.8s, request volume steady, checkout conversion sharply down",
  },
  {
    label: "Load demo: DB timeout",
    incident_packet:
      "User-facing latency alerts triggered for accounts-api in production. p95 latency increased from 280ms to 3.4s over the last 20 minutes, with intermittent 504s from upstream callers. Application logs show repeated database timeout and connection pool exhaustion messages on profile and account summary queries. No fresh deployment to accounts-api was made today. The database team reports elevated load on the primary cluster after an analytics job started.",
    service: "accounts-api",
    environment: "production",
    recent_deployment: "No application deploy in the last 24 hours",
    metric_summary:
      "p95 latency 280ms -> 3.4s, timeout rate increasing, DB connection pool saturated, intermittent upstream 504s",
  },
  {
    label: "Load demo: queue backlog",
    incident_packet:
      "Background processing alerts fired for notifications-worker. Queue depth has grown from 1.2k to 48k jobs over the last 35 minutes. Worker throughput dropped by roughly 70% after a maintenance restart earlier today. User-triggered emails and push notifications are delayed, but core request traffic is healthy. Logs show repeated retries on a third-party provider call and workers spending longer in retry backoff.",
    service: "notifications-worker",
    environment: "production",
    recent_deployment:
      "Worker pods restarted during routine node maintenance; no new app release",
    metric_summary:
      "Queue depth 1.2k -> 48k, processing throughput down 70%, retry count rising, core API traffic healthy",
  },
];

const genericErrorMessage =
  "Unable to analyze incident. Check the backend connection and try again.";

export function IncidentForm() {
  const [form, setForm] = useState<AnalyzeIncidentRequest>(initialForm);
  const [resultState, setResultState] = useState<ResultState>({
    status: "empty",
  });
  const [validationError, setValidationError] = useState<string | null>(null);

  const isSubmitting = resultState.status === "loading";

  const setField = (
    field: keyof AnalyzeIncidentRequest,
    value: AnalyzeIncidentRequest[keyof AnalyzeIncidentRequest],
  ) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));

    if (
      field === "incident_packet" &&
      validationError &&
      typeof value === "string" &&
      value.trim()
    ) {
      setValidationError(null);
    }
  };

  const loadDemo = (demo: DemoIncident) => {
    setForm({
      incident_packet: demo.incident_packet,
      service: demo.service,
      environment: demo.environment,
      recent_deployment: demo.recent_deployment,
      metric_summary: demo.metric_summary,
    });
    setValidationError(null);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    if (!form.incident_packet.trim()) {
      setValidationError("Add the incident packet before running analysis.");
      setResultState({ status: "empty" });
      return;
    }

    setValidationError(null);
    setResultState({ status: "loading" });

    try {
      const data = await analyzeIncident({
        incident_packet: form.incident_packet.trim(),
        service: form.service?.trim() || null,
        environment: form.environment?.trim() || null,
        recent_deployment: form.recent_deployment?.trim() || null,
        metric_summary: form.metric_summary?.trim() || null,
      });
      setResultState({ status: "success", data });
    } catch (error) {
      setResultState({
        status: "error",
        message: error instanceof Error ? error.message : genericErrorMessage,
      });
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.12fr)_minmax(320px,0.88fr)]">
      <section className="rounded-[24px] border border-border bg-panel-strong p-5 shadow-[var(--shadow)] sm:p-6">
        <div className="flex flex-col gap-2 border-b border-slate-200 pb-5">
          <h2 className="text-lg font-semibold tracking-[-0.02em] text-slate-950">
            Incident input
          </h2>
          <p className="text-sm leading-6 text-muted">
            Capture the incident context and send it to the triage backend.
          </p>
        </div>

        <div className="mt-5 rounded-[20px] border border-slate-200 bg-slate-50/90 p-4">
          <p className="text-sm leading-6 text-slate-600">
            Use a demo packet or enter your own incident details.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {demoIncidents.map((demo) => (
              <button
                key={demo.label}
                className="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-100 focus:outline-none focus:ring-4 focus:ring-slate-200"
                type="button"
                onClick={() => loadDemo(demo)}
              >
                {demo.label}
              </button>
            ))}
          </div>
        </div>

        <form className="mt-5 space-y-5" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-800">
              Incident packet
            </span>
            <textarea
              className="min-h-56 w-full resize-y rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-900 outline-none transition focus:border-accent focus:bg-white focus:ring-4 focus:ring-accent-soft"
              name="incident_packet"
              value={form.incident_packet}
              onChange={(event) =>
                setField("incident_packet", event.target.value)
              }
              placeholder="Paste the incident summary, timeline, logs, and responder notes."
            />
            {validationError ? (
              <p className="mt-2 rounded-xl border border-danger/20 bg-danger-soft px-3 py-2 text-sm text-danger">
                {validationError}
              </p>
            ) : null}
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-800">
                Service
              </span>
              <input
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-accent focus:bg-white focus:ring-4 focus:ring-accent-soft"
                name="service"
                value={form.service ?? ""}
                onChange={(event) => setField("service", event.target.value)}
                placeholder="checkout-api"
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-800">
                Environment
              </span>
              <input
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-accent focus:bg-white focus:ring-4 focus:ring-accent-soft"
                name="environment"
                value={form.environment ?? ""}
                onChange={(event) =>
                  setField("environment", event.target.value)
                }
                placeholder="production"
              />
            </label>
          </div>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-800">
              Recent deployment
            </span>
            <input
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-accent focus:bg-white focus:ring-4 focus:ring-accent-soft"
              name="recent_deployment"
              value={form.recent_deployment ?? ""}
              onChange={(event) =>
                setField("recent_deployment", event.target.value)
              }
              placeholder="Version identifier, time, or config change details"
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-800">
              Metric summary
            </span>
            <input
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-accent focus:bg-white focus:ring-4 focus:ring-accent-soft"
              name="metric_summary"
              value={form.metric_summary ?? ""}
              onChange={(event) =>
                setField("metric_summary", event.target.value)
              }
              placeholder="Error rate, latency, saturation, or traffic shifts"
            />
          </label>

          <div className="flex flex-col gap-3 border-t border-slate-200 pt-5 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm leading-6 text-muted">
              Submit the incident context to generate a structured triage brief.
            </p>
            <button
              className="inline-flex items-center justify-center rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-slate-300 disabled:cursor-not-allowed disabled:bg-slate-400 disabled:hover:bg-slate-400"
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Analyzing incident..." : "Analyze incident"}
            </button>
          </div>
        </form>
      </section>

      <ResultCards resultState={resultState} />
    </div>
  );
}
