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

const initialForm: AnalyzeIncidentRequest = {
  incident_packet: "",
  service: "",
  environment: "",
  recent_deployment: "",
  metric_summary: "",
};

const samplePacket = `Summary: Elevated checkout failures started 8 minutes after the 14:05 UTC production deploy.
Impact: Roughly 22% of checkout requests are returning HTTP 500 and payment completion has dropped sharply.
Signals: Error rate increased on checkout-api pods in us-east-1. Logs show "missing STRIPE_SIGNING_SECRET" during request handling.
Mitigation attempts: Rolled one pod manually and invalidated edge cache with no improvement.
Escalation: Incident commander requests triage on likely cause and first response actions.`;

const genericErrorMessage =
  "Unable to analyze incident. Check the backend connection and try again.";

export function IncidentForm() {
  const [form, setForm] = useState<AnalyzeIncidentRequest>({
    ...initialForm,
    incident_packet: samplePacket,
    service: "checkout-api",
    environment: "production",
    recent_deployment: "Version 2026.04.09-rc3 deployed at 14:05 UTC",
    metric_summary:
      "Checkout success rate down 22%. checkout-api HTTP 500 rate elevated in us-east-1.",
  });
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
            Incident packet
          </h2>
          <p className="text-sm leading-6 text-muted">
            Capture the raw operational context and send it directly to the live
            triage backend.
          </p>
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
              placeholder="Paste the incident summary, logs, timeline, and responder notes."
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
              Submit live incident context to generate a structured triage brief
              from the backend.
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
