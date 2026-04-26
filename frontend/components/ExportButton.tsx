"use client";

import { useState } from "react";
import { Download, FileText, File } from "lucide-react";

interface Props {
  text: string;
  filename: string;
}

type Format = "txt" | "pdf";

const FORMATS: { id: Format; label: string; icon: React.ReactNode; ext: string }[] = [
  { id: "txt", label: "TXT",  icon: <FileText className="h-3.5 w-3.5" />, ext: ".txt" },
  { id: "pdf", label: "PDF",  icon: <File className="h-3.5 w-3.5" />,     ext: ".pdf" },
];

export default function ExportButton({ text, filename }: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState<Format | null>(null);

  const baseName = filename.replace(/\.[^.]+$/, "") + "_anonymized";

  const exportTxt = () => {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    trigger(blob, baseName + ".txt");
  };

  const exportPdf = async () => {
    const { jsPDF } = await import("jspdf");
    const doc = new jsPDF({ unit: "mm", format: "a4" });

    const margin = 15;
    const pageWidth = doc.internal.pageSize.getWidth() - margin * 2;
    const lineHeight = 6;
    let y = margin;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);

    const lines = doc.splitTextToSize(text, pageWidth);
    for (const line of lines) {
      if (y + lineHeight > doc.internal.pageSize.getHeight() - margin) {
        doc.addPage();
        y = margin;
      }
      doc.text(line, margin, y);
      y += lineHeight;
    }

    doc.save(baseName + ".pdf");
  };

  const trigger = (blob: Blob, name: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExport = async (format: Format) => {
    setLoading(format);
    setOpen(false);
    try {
      if (format === "txt") exportTxt();
      if (format === "pdf") await exportPdf();
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <Download className="h-3.5 w-3.5" />
        {loading ? `Exportiere ${loading.toUpperCase()}…` : "Exportieren"}
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          {/* Dropdown */}
          <div className="absolute right-0 top-6 z-20 flex flex-col w-36 rounded-lg border border-border bg-card shadow-lg overflow-hidden">
            {FORMATS.map((f) => (
              <button
                key={f.id}
                onClick={() => handleExport(f.id)}
                className="flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-muted transition-colors"
              >
                {f.icon}
                {f.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
