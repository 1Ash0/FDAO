import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FDAO — Feedback-Driven Agent Optimizer",
  description: "LLM agent improves via reward-guided in-context reflection. No weight updates.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <nav style={{
          position: "sticky", top: 0, zIndex: 50,
          height: 52,
          background: "rgba(4,5,14,0.85)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          borderBottom: "1px solid rgba(91,138,255,0.12)",
          boxShadow: "0 1px 40px rgba(91,138,255,0.06)",
          display: "flex", alignItems: "center",
          padding: "0 32px",
        }}>
          {/* Brand */}
          <Link href="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 10, marginRight: 40 }}>
            {/* animated pulse dot */}
            <span style={{ position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{
                position: "absolute",
                width: 14, height: 14, borderRadius: "50%",
                background: "rgba(91,138,255,0.3)",
                animation: "pulse-ring 2s ease-out infinite",
              }} />
              <span style={{
                width: 8, height: 8, borderRadius: "50%",
                background: "var(--accent)",
                boxShadow: "0 0 12px rgba(91,138,255,1), 0 0 28px rgba(91,138,255,0.5)",
                display: "block",
              }} />
            </span>
            <span style={{ fontSize: 15, fontWeight: 800, color: "var(--text)", letterSpacing: "-0.03em" }}>
              fdao
            </span>
          </Link>

          <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Link href="/"            className="nav-link">playground</Link>
            <Link href="/experiments" className="nav-link">experiments</Link>
            <Link href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="nav-link">api</Link>
          </div>

          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
            <span className="mono" style={{
              fontSize: 9, color: "rgba(91,138,255,0.7)",
              border: "1px solid rgba(91,138,255,0.2)",
              background: "rgba(91,138,255,0.06)",
              borderRadius: 5, padding: "3px 8px",
              letterSpacing: "0.1em", textTransform: "uppercase",
            }}>
              NeurIPS 2026
            </span>
          </div>
        </nav>

        {children}
      </body>
    </html>
  );
}
