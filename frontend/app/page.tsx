import { IncidentForm } from "@/components/incident-form";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-5 py-8 sm:px-8 sm:py-10 lg:px-10">
      <section className="rounded-[28px] border border-white/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(244,247,248,0.92))] p-6 shadow-[0_18px_50px_rgba(15,23,42,0.08)] backdrop-blur sm:p-8">
        <div className="flex flex-col gap-8">
          <header className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/75 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Incident Triage Copilot
            </div>
            <h1 className="mt-4 max-w-2xl text-3xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-4xl">
              Triage production incidents with fast, structured operational
              context.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600 sm:text-[15px]">
              Review an incident packet, capture the service context, and
              generate a concise response brief from the live triage backend.
            </p>
          </header>

          <IncidentForm />
        </div>
      </section>
    </main>
  );
}
