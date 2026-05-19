
import { ShieldCheck } from "lucide-react";

const NavBar = () => {
  return (
    <header className="border-b border-border bg-card/60 backdrop-blur-sm sticky top-0 z-10">
        <div className="mx-auto max-w-5xlx px-6 h-14 flex items-center justify-between">
            <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <span className="font-semibold text-sm tracking-tight">The Enabler</span>
            </div>
            <span className="text-xs text-muted-foreground">PII Detection & Masking</span>
        </div>
    </header>
  )
}

export default NavBar
