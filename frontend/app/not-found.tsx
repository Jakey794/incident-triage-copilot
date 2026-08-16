import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Page not found",
  description: "The requested Incident Triage Copilot page could not be found.",
};

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl items-center px-5 py-10 sm:px-8">
      <section className="w-full rounded-[28px] border border-white/60 bg-white/90 p-8 text-center shadow-[var(--shadow)] sm:p-12">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-teal-700">
          Error 404
        </p>
        <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-4xl">
          Page not found
        </h1>
        <p className="mx-auto mt-4 max-w-lg text-sm leading-7 text-slate-600 sm:text-base">
          The page you requested does not exist. Return to the incident triage
          workspace to load a demo or analyze a sanitized incident packet.
        </p>
        <Link
          className="mt-7 inline-flex min-h-11 items-center justify-center rounded-2xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-slate-300"
          href="/"
        >
          Return to the triage workspace
        </Link>
      </section>
    </main>
  );
}
