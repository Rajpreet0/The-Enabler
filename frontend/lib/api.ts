const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface EntityFound {
  entity_type: string;
  start: number;
  end: number;
  score: number;
  original: string;
}

export interface UploadResult {
  filename: string;
  content_type: string;
  raw_text: string;
  preview: string;
  anonymized: string;
  entities_found: EntityFound[];
}

export async function uploadDocument(
  file: File,
  language: "de" | "en" = "de"
): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/upload?language=${language}`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Upload fehlgeschlagen");
  }

  return res.json();
}
