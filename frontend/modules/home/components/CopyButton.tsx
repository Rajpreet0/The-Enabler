"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

interface CopyButtonProps {
    text: string;
}

const CopyButton: React.FC<CopyButtonProps> = ({text}) => {
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
  )
}

export default CopyButton
