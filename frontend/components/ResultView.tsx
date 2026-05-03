"use client";

import { useMemo, useState } from "react";
import { ArrowLeft, FileText, Copy, Check, Eye, Bot, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { UploadResult, EntityFound } from "@/lib/api";
import ExportButton from "@/components/ExportButton";

const ENTITY_META: Record<string, { label: string; color: string }> = {
  PERSON:        { label: "Person",  color: "bg-red-100 text-red-700 border-red-200" },
  EMAIL_ADDRESS: { label: "E-Mail",  color: "bg-blue-100 text-blue-700 border-blue-200" },
  PHONE_NUMBER:  { label: "Telefon", color: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  LOCATION:      { label: "Ort",     color: "bg-green-100 text-green-700 border-green-200" },
  IBAN_CODE:     { label: "IBAN",    color: "bg-purple-100 text-purple-700 border-purple-200" },
  ORGANIZATION:  { label: "Firma",   color: "bg-orange-100 text-orange-700 border-orange-200" },
  ADDRESS:       { label: "Adresse", color: "bg-amber-100 text-amber-700 border-amber-200" },
};

const ANONYMIZE_LABELS: Record<string, string> = {
  PERSON:        "[PERSON]",
  EMAIL_ADDRESS: "[EMAIL]",
  PHONE_NUMBER:  "[TELEFON]",
  LOCATION:      "[ORT]",
  IBAN_CODE:     "[IBAN]",
  ORGANIZATION:  "[FIRMA]",
  ADDRESS:       "[ADRESSE]",
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Kopiert" : "Kopieren"}
    </button>
  );
}

interface Props {
  result: UploadResult;
  onReset: () => void;
}

export default function ResultView({ result, onReset }: Props) {
  const [tab, setTab] = useState<"preview" | "anonymized">("preview");

  // Jede einzelne Entity kann per Index deaktiviert werden
  const [disabled, setDisabled] = useState<Set<number>>(new Set());

  const toggle = (index: number) =>
    setDisabled((prev) => {
      const next = new Set(prev);
      if (next.has(index)) { next.delete(index); } else { next.add(index); }
      return next;
    });

  const activeEntities = result.entities_found.filter((_, i) => !disabled.has(i));

  const rawText = result.raw_text;

  // Anonymisierter Text: aktive Entities durch Labels ersetzen
  const anonymizedText = useMemo(() => {
    const sorted = [...activeEntities].sort((a, b) => b.start - a.start);
    const chars = [...rawText];
    for (const e of sorted) {
      const label = ANONYMIZE_LABELS[e.entity_type] ?? `[${e.entity_type}]`;
      chars.splice(e.start, e.end - e.start, label);
    }
    return chars.join("");
  }, [activeEntities, rawText]);

  // JSX-Segmente für Preview
  const previewSegments = useMemo(() => {
    const sorted = [...activeEntities].sort((a, b) => a.start - b.start);
    const segments: { text: string; entity: EntityFound | null }[] = [];
    let cursor = 0;
    for (const e of sorted) {
      if (e.start > cursor) segments.push({ text: rawText.slice(cursor, e.start), entity: null });
      segments.push({ text: rawText.slice(e.start, e.end), entity: e });
      cursor = e.end;
    }
    if (cursor < rawText.length) segments.push({ text: rawText.slice(cursor), entity: null });
    return segments;
  }, [activeEntities, rawText]);

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Neues Dokument
        </button>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <FileText className="h-4 w-4" />
          <span>{result.filename}</span>
        </div>
      </div>

      {/* Entity Badges — abwählbar per X */}
      <Card className="border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
            Erkannte PII — {activeEntities.length} von {result.entities_found.length} aktiv
          </CardTitle>
        </CardHeader>
        <CardContent>
          {result.entities_found.length === 0 ? (
            <p className="text-sm text-muted-foreground">Keine PII gefunden.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {result.entities_found.map((e, i) => {
                const meta = ENTITY_META[e.entity_type];
                const isDisabled = disabled.has(i);
                return (
                  <button
                    key={i}
                    onClick={() => toggle(i)}
                    className={[
                      "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-all",
                      isDisabled
                        ? "bg-muted text-muted-foreground border-border line-through opacity-50"
                        : (meta?.color ?? "bg-muted text-foreground border-border"),
                    ].join(" ")}
                  >
                    <span>{meta?.label ?? e.entity_type}</span>
                    <span className="opacity-40">·</span>
                    <span className="font-mono font-normal">{e.original}</span>
                    <X className="h-3 w-3 ml-0.5 opacity-60" />
                  </button>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tab switcher */}
      <div className="flex items-center justify-between">
        <div className="flex rounded-lg border border-border bg-muted/40 p-1 gap-1">
          <button
            onClick={() => setTab("preview")}
            className={[
              "flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium transition-all",
              tab === "preview" ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            <Eye className="h-3.5 w-3.5" />
            Preview
          </button>
          <button
            onClick={() => setTab("anonymized")}
            className={[
              "flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium transition-all",
              tab === "anonymized" ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            <Bot className="h-3.5 w-3.5" />
            Für KI
          </button>
        </div>
        <div className="flex items-center gap-4">
          <CopyButton text={tab === "preview" ? rawText : anonymizedText} />
          <ExportButton text={anonymizedText} filename={result.filename} />
        </div>
      </div>

      {/* Text Output */}
      <Card className="border-border">
        <CardContent className="pt-5">
          {tab === "preview" ? (
            <pre className="whitespace-pre-wrap text-sm font-sans leading-7">
              {previewSegments.map((seg, i) => {
                if (!seg.entity) return <span key={i}>{seg.text}</span>;
                const meta = ENTITY_META[seg.entity.entity_type];
                return (
                  <mark
                    key={i}
                    className={`rounded px-1 py-0.5 not-italic ${meta?.color ?? "bg-muted"}`}
                  >
                    {seg.text}
                  </mark>
                );
              })}
            </pre>
          ) : (
            <pre className="whitespace-pre-wrap text-sm font-sans leading-7">
              {anonymizedText}
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
