"use client";

import { useMemo, useState } from "react";
import { EntityFound } from "@/lib/api";
import { getEntitiyMeta } from "@/config/entities";

// Represents a Text Segement in Preview-Modus
export interface TextSegment {
  text: string;                   // Normal Text
  entity: EntityFound | null;     // Unanoymized Text Version
}

/**
 * Hook for anonymisien Text based on the found entities (with Position in Text)
 * @param entities - List of all Entites from the backend
 * @param rawText  - Previous Text (raw)
 */
export function useAnonymizer(entities: EntityFound[], rawText: string) {
  // Saves the Indicies of entities which the user selected 
  const [disabled, setDisabled] = useState<Set<number>>(new Set());

  // Uses the Index to toggle an Entity (show/hide)
  const toggle = (index: number) =>
    setDisabled((prev) => {
      const next = new Set(prev);
      if (next.has(index)) { 
          next.delete(index);         // Deactivated -> Activated 
      } else { 
        next.add(index);              // Activated -> Deactivated
      }
      return next;
    });

  // Only the Entites which were not deactivated should be anonymized
  const activeEntities = useMemo(
    () => entities.filter((_, i) => !disabled.has(i)),
    [entities, disabled]
  );

  // Anonymizes all Entites with respect to their designated Labels (e.x "[NAME], [ORT]")
  const anonymizedText = useMemo(() => {
    // From back to the front
    const sorted = [...activeEntities].sort((a, b) => b.start - a.start);
    const chars = [...rawText];
    for (const e of sorted) {
      const label = getEntitiyMeta(e.entity_type).anonymizeLabel;
      // Erases the raw Text and replaces it with the Label
      chars.splice(e.start, e.end - e.start, label);
    }
    return chars.join("");
  }, [activeEntities, rawText]);

  // Takes the original Text and split it into segments
  const previewSegments = useMemo((): TextSegment[] => {
    const sorted = [...activeEntities].sort((a, b) => a.start - b.start);
    const segments: TextSegment[] = [];
    let cursor = 0;
    for (const e of sorted) {
      if (e.start > cursor) segments.push({ text: rawText.slice(cursor, e.start), entity: null });
      segments.push({ text: rawText.slice(e.start, e.end), entity: e });
      cursor = e.end;
    }
    if (cursor < rawText.length) segments.push({ text: rawText.slice(cursor), entity: null });
    return segments;
  }, [activeEntities, rawText]);

  return { disabled, toggle, activeEntities, anonymizedText, previewSegments };
}
