"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { UploadCloud, FileText, FileSearch, Filter, MapPin, User, Users, Layers, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { uploadDocument, UploadResult } from "@/lib/api";

const ACCEPTED = ".pdf,.docx,.doc,.png,.jpg,.jpeg,.tiff,.bmp,.webp";

const PIPELINE_STEPS = [
  { icon: FileSearch,    label: "Dokument einlesen" },
  { icon: Filter,        label: "Entitäten erkennen" },
  { icon: Filter,        label: "Konfidenz filtern" },
  { icon: MapPin,        label: "Adressen analysieren" },
  { icon: User,          label: "Personen bereinigen" },
  { icon: Users,         label: "Namen propagieren" },
  { icon: Layers,        label: "Überlappungen auflösen" },
  { icon: CheckCircle2,  label: "Fertig" },
] as const;

const STEP_INTERVAL_MS = 1500;
const DONE_PAUSE_MS    = 500;
const LAST_STEP        = PIPELINE_STEPS.length - 1;
const PENULTIMATE_STEP = PIPELINE_STEPS.length - 2;

interface Props {
  onResult: (result: UploadResult) => void;
}

export default function UploadZone({ onResult }: Props) {
  const [dragging, setDragging]   = useState(false);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [fileName, setFileName]   = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopInterval = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  useEffect(() => stopInterval, []); // cleanup on unmount

  const process = useCallback(
    async (file: File) => {
      setError(null);
      setFileName(file.name);
      setStepIndex(0);
      setLoading(true);

      // Advance one step every STEP_INTERVAL_MS, but stop before "Fertig"
      // so the animation waits for the real API result.
      intervalRef.current = setInterval(() => {
        setStepIndex((prev) => {
          if (prev >= PENULTIMATE_STEP) {
            stopInterval();
            return prev; // hold here until API finishes
          }
          return prev + 1;
        });
      }, STEP_INTERVAL_MS);

      let result: UploadResult;
      try {
        result = await uploadDocument(file, "de");
      } catch (e: unknown) {
        stopInterval();
        setError(e instanceof Error ? e.message : "Unbekannter Fehler");
        setLoading(false);
        return;
      }

      // API done — snap to "Fertig"
      stopInterval();
      setStepIndex(LAST_STEP);

      await new Promise((r) => setTimeout(r, DONE_PAUSE_MS));

      setLoading(false);
      onResult(result);
    },
    [onResult]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) process(file);
    },
    [process]
  );

  const currentStep = PIPELINE_STEPS[stepIndex];
  const isDone      = stepIndex === LAST_STEP;

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => !loading && document.getElementById("file-input")?.click()}
      className={[
        "relative flex flex-col items-center justify-center gap-5 rounded-2xl border-2 border-dashed p-16 transition-all duration-200 cursor-pointer",
        dragging
          ? "border-primary bg-primary/5 scale-[1.01]"
          : "border-border hover:border-primary/40 hover:bg-muted/30",
        loading ? "pointer-events-none" : "",
      ].join(" ")}
    >
      <input
        id="file-input"
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) process(f); }}
      />

      {loading ? (
        <div className="flex flex-col items-center gap-6 w-full max-w-xs">
          {/* Icon */}
          <div className={`rounded-full p-4 transition-colors duration-300 ${isDone ? "bg-green-500/15" : "bg-primary/10"}`}>
            <currentStep.icon
              className={`h-8 w-8 transition-colors duration-300 ${isDone ? "text-green-500" : "text-primary"}`}
            />
          </div>

          {/* Step label + filename */}
          <div className="text-center">
            <p className="font-medium text-sm">{currentStep.label}</p>
            <p className="text-xs text-muted-foreground mt-1">{fileName}</p>
          </div>

          {/* Dots */}
          <div className="flex items-center gap-1.5">
            {PIPELINE_STEPS.map((step, i) => (
              <div
                key={step.label}
                className={[
                  "rounded-full transition-all duration-300",
                  i < stepIndex  ? "w-2 h-2 bg-primary"
                  : i === stepIndex ? "w-3 h-3 bg-primary"
                  : "w-2 h-2 bg-muted-foreground/25",
                ].join(" ")}
              />
            ))}
          </div>

          {/* Progress bar */}
          <div className="w-full h-1 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-500 ease-out"
              style={{ width: `${(stepIndex / LAST_STEP) * 100}%` }}
            />
          </div>
        </div>
      ) : (
        <>
          <div className={`rounded-full p-4 transition-colors ${dragging ? "bg-primary/15" : "bg-muted"}`}>
            {fileName
              ? <FileText className="h-8 w-8 text-primary" />
              : <UploadCloud className="h-8 w-8 text-muted-foreground" />
            }
          </div>
          <div className="text-center">
            <p className="font-semibold text-sm">
              {dragging ? "Datei loslassen" : "Datei hierher ziehen"}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              oder klicken zum Auswählen · PDF, DOCX, PNG, JPG
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="rounded-full px-5"
            onClick={(e) => { e.stopPropagation(); document.getElementById("file-input")?.click(); }}
          >
            Datei auswählen
          </Button>
        </>
      )}

      {error && (
        <p className="absolute bottom-4 text-xs text-destructive font-medium">{error}</p>
      )}
    </div>
  );
}
