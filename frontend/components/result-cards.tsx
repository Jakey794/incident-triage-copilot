import type { AnalyzeIncidentResponse } from "@/lib/api";

type ResultState =
  | { status: "empty" }
  | { status: "loading" }
  | { message: string; status: "error" }
  | { data: AnalyzeIncidentResponse; status: "success" };

const severityStyles: Record<AnalyzeIncidentResponse["severity"], string> = {
  "sev-1": "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200",
  "sev-2": "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200",
  "sev-3": "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-200",
  "sev-4": "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200",
};

type MetricCardProps = {
  children: React.ReactNode;
  label: string;
  tone?: "default" | "accent";
};

function MetricCard({ children, label, tone = "default" }: MetricCardProps) {
  return (
    <div
      className={`rounded-[20px] border p-4 ${
        tone === "accent"
          ? "border-teal-200 bg-teal-50/70"
          : "border-slate-200 bg-white"
      }`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
        {label}
      </p>
      <div className="mt-3 text-sm leading-6 text-slate-800">{children}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <section className="rounded-[24px] border border-border bg-[rgba(248,250,252,0.84)] p-5 shadow-[var(--shadow)] sm:p-6">
      <div className="rounded-[22px] border border-dashed border-slate-300 bg-white/70 p-6">
        <div className="h-11 w-11 rounded-2xl bg-slate-100" />
        <h2 className="mt-5 text-lg font-semibold tracking-[-0.02em] text-slate-950">
          Triage brief
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Submit an incident packet to generate the summary, severity, impacted
          service, likely cause, and next actions.
        </p>
      </div>
    </section>
  );
}

function LoadingState() {
  return (
    <section className="rounded-[24px] border border-border bg-[rgba(248,250,252,0.84)] p-5 shadow-[var(--shadow)] sm:p-6">
      <div className="space-y-4">
        <div className="rounded-[22px] border border-slate-200 bg-white p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Analysis in progress
          </p>
          <h2 className="mt-3 text-lg font-semibold tracking-[-0.02em] text-slate-950">
            Building the incident brief
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Pulling together the impact, likely cause, and immediate response
            steps from the submitted context.
          </p>
        </div>
        <div className="space-y-4 animate-pulse">
          <div className="rounded-[20px] border border-slate-200 bg-white p-4">
            <div className="h-3 w-24 rounded-full bg-slate-200" />
            <div className="mt-4 h-4 w-5/6 rounded-full bg-slate-200" />
            <div className="mt-3 h-4 w-4/6 rounded-full bg-slate-100" />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-[20px] border border-slate-200 bg-white p-4">
              <div className="h-3 w-20 rounded-full bg-slate-200" />
              <div className="mt-4 h-8 w-28 rounded-full bg-slate-200" />
            </div>
            <div className="rounded-[20px] border border-slate-200 bg-white p-4">
              <div className="h-3 w-28 rounded-full bg-slate-200" />
              <div className="mt-4 h-5 w-2/3 rounded-full bg-slate-100" />
            </div>
          </div>
          <div className="rounded-[20px] border border-slate-200 bg-white p-4">
            <div className="h-3 w-36 rounded-full bg-slate-200" />
            <div className="mt-4 space-y-3">
              <div className="h-4 w-full rounded-full bg-slate-100" />
              <div className="h-4 w-5/6 rounded-full bg-slate-100" />
              <div className="h-4 w-4/6 rounded-full bg-slate-100" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <section className="rounded-[24px] border border-danger/15 bg-white p-5 shadow-[var(--shadow)] sm:p-6">
      <div className="rounded-[22px] border border-danger/15 bg-danger-soft p-5">
        <div className="inline-flex rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-danger">
          Triage unavailable
        </div>
        <h2 className="mt-4 text-lg font-semibold tracking-[-0.02em] text-slate-950">
          We could not build the incident brief
        </h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">{message}</p>
      </div>
    </section>
  );
}

function SuccessState({ data }: { data: AnalyzeIncidentResponse }) {
  const confidencePercent = Math.round(data.confidence_score * 100);
  const severityLabel = data.severity.toUpperCase();

  return (
    <section className="rounded-[24px] border border-border bg-[rgba(248,250,252,0.84)] p-5 shadow-[var(--shadow)] sm:p-6">
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <MetricCard label="Severity">
            <span
              className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${severityStyles[data.severity]}`}
            >
              {severityLabel}
            </span>
          </MetricCard>

          <MetricCard label="Impacted service">
            <p className="font-medium text-slate-950">
              {data.impacted_service}
            </p>
          </MetricCard>
        </div>

        <MetricCard label="Summary" tone="accent">
          <p>{data.summary}</p>
        </MetricCard>

        <MetricCard label="Root cause">
          <p>{data.likely_root_cause_hypothesis}</p>
        </MetricCard>

        <MetricCard label="Next actions">
          <ul className="space-y-2">
            {data.immediate_next_actions.map((action) => (
              <li key={action} className="flex gap-3">
                <span className="mt-2 h-1.5 w-1.5 rounded-full bg-teal-600/70" />
                <span className="flex-1">{action}</span>
              </li>
            ))}
          </ul>
        </MetricCard>

        <MetricCard label="Confidence">
          <div className="flex items-center gap-4">
            <p className="text-2xl font-semibold tracking-[-0.04em] text-slate-950">
              {confidencePercent}%
            </p>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-teal-600"
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
          </div>
        </MetricCard>
      </div>
    </section>
  );
}

export function ResultCards({ resultState }: { resultState: ResultState }) {
  if (resultState.status === "loading") {
    return <LoadingState />;
  }

  if (resultState.status === "error") {
    return <ErrorState message={resultState.message} />;
  }

  if (resultState.status === "success") {
    return <SuccessState data={resultState.data} />;
  }

  return <EmptyState />;
}
