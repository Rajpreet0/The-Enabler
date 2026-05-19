"use client";

import { useState } from "react";
import { ArrowLeft, FileText, Eye, Bot, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { UploadResult } from "@/lib/api";
import ExportButton from "@/components/ExportButton";
import CopyButton from "@/modules/home/components/CopyButton";
import { getEntitiyMeta } from "@/config/entities";
import { useAnonymizer } from "@/hooks/useAnonymizer";


interface Props {
  result: UploadResult;
  onReset: () => void;
}

export default function ResultView({ result, onReset }: Props) {
  
  /*-------------- STATES --------------*/
  const [tab, setTab] = useState<"preview" | "anonymized">("preview");
  const rawText = result.raw_text;

  /*-------------- HOOKS --------------*/
  const { disabled, toggle, activeEntities, anonymizedText, previewSegments } =
    useAnonymizer(result.entities_found, rawText);

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
                const meta = getEntitiyMeta(e.entity_type);
                const isDisabled = disabled.has(i);
                return (
                  <button
                    key={i}
                    onClick={() => toggle(i)}
                    className={[
                      "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-all",
                      isDisabled
                        ? "bg-muted text-muted-foreground border-border line-through opacity-50"
                        : meta.color,
                    ].join(" ")}
                  >
                    <span>{meta.label}</span>
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
                const meta = getEntitiyMeta(seg.entity.entity_type);
                return (
                  <mark
                    key={i}
                    className={`rounded px-1 py-0.5 not-italic ${meta.color}`}
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
