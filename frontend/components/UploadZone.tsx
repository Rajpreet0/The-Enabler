"use client";

import { useCallback, useState } from "react";
import { UploadCloud, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { uploadDocument, UploadResult } from "@/lib/api";

const ACCEPTED = ".pdf,.docx,.doc,.png,.jpg,.jpeg,.tiff,.bmp,.webp";

interface Props {
  onResult: (result: UploadResult) => void;
}

export default function UploadZone({ onResult }: Props) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const process = useCallback(
    async (file: File) => {
      setError(null);
      setFileName(file.name);
      setLoading(true);
      try {
        const result = await uploadDocument(file, "de");
        onResult(result);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Unbekannter Fehler");
      } finally {
        setLoading(false);
      }
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
        <>
          <div className="rounded-full bg-primary/10 p-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
          <div className="text-center">
            <p className="font-medium text-sm">Analysiere Dokument…</p>
            <p className="text-xs text-muted-foreground mt-1">{fileName}</p>
          </div>
        </>
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
