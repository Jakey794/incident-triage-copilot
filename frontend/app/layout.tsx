import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const siteUrl = "https://incident-triage-copilot.vercel.app";
const siteTitle = "Incident Triage Copilot";
const siteDescription =
  "Turn incident alerts, logs, metrics, and deployment context into a structured operational triage brief.";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  applicationName: siteTitle,
  title: {
    default: siteTitle,
    template: `%s | ${siteTitle}`,
  },
  description: siteDescription,
  alternates: {
    canonical: "/",
  },
  authors: [{ name: "Jacob Allan", url: "https://github.com/Jakey794" }],
  creator: "Jacob Allan",
  publisher: "Jacob Allan",
  category: "developer tools",
  keywords: [
    "incident response",
    "incident triage",
    "AI operations",
    "site reliability engineering",
    "FastAPI",
    "Next.js",
  ],
  openGraph: {
    type: "website",
    locale: "en_CA",
    url: "/",
    siteName: siteTitle,
    title: siteTitle,
    description: siteDescription,
  },
  twitter: {
    card: "summary_large_image",
    title: siteTitle,
    description: siteDescription,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full">{children}</body>
    </html>
  );
}
