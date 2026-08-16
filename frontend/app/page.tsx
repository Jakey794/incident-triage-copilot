import { IncidentForm } from "@/components/incident-form";

const structuredData = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "Incident Triage Copilot",
  url: "https://incident-triage-copilot.vercel.app",
  description:
    "Turn incident alerts, logs, metrics, and deployment context into a structured operational triage brief.",
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Any",
  isAccessibleForFree: true,
  author: {
    "@type": "Person",
    name: "Jacob Allan",
    url: "https://github.com/Jakey794",
  },
  codeRepository: "https://github.com/Jakey794/incident-triage-copilot",
  programmingLanguage: ["TypeScript", "Python"],
};

export default function Home() {
  return (
    <>
      <script type="application/ld+json">
        {JSON.stringify(structuredData)}
      </script>
      <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-6 sm:px-8 sm:py-10 lg:px-10">
        <section className="rounded-[24px] border border-white/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(244,247,248,0.92))] p-4 shadow-[0_18px_50px_rgba(15,23,42,0.08)] backdrop-blur sm:rounded-[28px] sm:p-8">
          <div className="flex flex-col gap-8">
            <header className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/75 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Incident Triage Copilot
              </div>
              <h1 className="mt-4 max-w-2xl text-3xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-4xl">
                Triage incidents with a fast, structured operational brief.
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600 sm:text-[15px]">
                Review the packet, capture the service context, and generate a
                concise incident brief from the live triage backend.
              </p>
              <p className="mt-4 max-w-2xl rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
                Public demo: use sample or sanitized data only. Do not submit
                secrets, personal data, or confidential incident details.
              </p>
            </header>

            <IncidentForm />
          </div>
        </section>
        <footer className="flex flex-col gap-2 px-2 py-6 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
          <p>Open-source incident response demo · MIT licensed</p>
          <a
            className="font-medium text-teal-800 underline decoration-teal-300 underline-offset-4 hover:text-teal-950"
            href="https://github.com/Jakey794/incident-triage-copilot"
            rel="noreferrer"
            target="_blank"
          >
            View source on GitHub
          </a>
        </footer>
      </main>
    </>
  );
}
