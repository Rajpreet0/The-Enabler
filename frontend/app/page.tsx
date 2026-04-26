"use client";

import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import UploadZone from "@/components/UploadZone";
import ResultView from "@/components/ResultView";
import { UploadResult } from "@/lib/api";

export default function Home() {
  const [result, setResult] = useState<UploadResult | null>(null);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Navbar */}
      <header className="border-b border-border bg-card/60 backdrop-blur-sm sticky top-0 z-10">
        <div className="mx-auto max-w-5xl px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <span className="font-semibold text-sm tracking-tight">The Enabler</span>
          </div>
          <span className="text-xs text-muted-foreground">PII Detection & Masking</span>
        </div>
      </header>

      <main className="flex-1">
        {result ? (
          /* Result view — full width with padding */
          <div className="mx-auto max-w-5xl px-6 py-10">
            <ResultView result={result} onReset={() => setResult(null)} />
          </div>
        ) : (
          /* Hero + Upload */
          <div className="mx-auto max-w-2xl px-6 py-20 flex flex-col items-center gap-10">
            <div className="text-center flex flex-col gap-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary self-center">
                <ShieldCheck className="h-3.5 w-3.5" />
                DSGVO-konform
              </div>
              <h1 className="text-4xl font-bold tracking-tight">
                Dokumente anonymisieren
              </h1>
              <p className="text-muted-foreground text-base leading-relaxed">
                Lade ein Dokument hoch — Personen, Adressen, IBANs und mehr
                werden automatisch erkannt und maskiert.
              </p>
            </div>

            <div className="w-full">
              <UploadZone onResult={setResult} />
            </div>

            <div className="flex items-center gap-6 text-xs text-muted-foreground">
              <span>PDF · DOCX · PNG · JPG</span>
              <span>·</span>
              <span>Lokal verarbeitet</span>
              <span>·</span>
              <span>Keine Datenspeicherung</span>
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-border py-4">
        <div className="mx-auto max-w-5xl px-6 text-center text-xs text-muted-foreground">
          The Enabler — PII Detection powered by Microsoft Presidio
        </div>
      </footer>
    </div>
  );
}
