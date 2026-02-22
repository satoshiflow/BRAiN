import * as React from "react";
import { cn } from "@ui-core/utils";
import { ChevronDown, User, Settings, Shield, Key, LogOut } from "lucide-react";
import { Button } from "./button";

interface DropdownMenuProps {
  children: React.ReactNode;
  trigger: React.ReactNode;
  align?: "left" | "right";
}

export function DropdownMenu({ children, trigger, align = "right" }: DropdownMenuProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);

  // Close on click outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  return (
    <div ref={containerRef} className="relative">
      <div onClick={() => setIsOpen(!isOpen)}>{trigger}</div>
      
      {isOpen && (
        <div
          className={cn(
            "absolute z-50 mt-2 w-56 rounded-md border border-border bg-popover shadow-lg animate-in fade-in zoom-in-95 duration-100",
            align === "right" ? "right-0" : "left-0"
          )}
        >
          <div className="py-1" onClick={() => setIsOpen(false)}>
            {children}
          </div>
        </div>
      )}
    </div>
  );
}

interface DropdownMenuItemProps {
  children: React.ReactNode;
  onClick?: () => void;
  icon?: React.ReactNode;
  href?: string;
  className?: string;
}

export function DropdownMenuItem({ children, onClick, icon, href, className }: DropdownMenuItemProps) {
  const baseClasses = cn(
    "flex items-center gap-3 w-full px-3 py-2 text-sm text-popover-foreground hover:bg-accent hover:text-accent-foreground cursor-pointer transition-colors",
    className
  );

  const content = (
    <>
      {icon && <span className="w-4 h-4 opacity-70">{icon}</span>}
      <span>{children}</span>
    </>
  );

  if (href) {
    return (
      <a href={href} className={baseClasses} onClick={onClick}>
        {content}
      </a>
    );
  }

  return (
    <button className={cn(baseClasses, "text-left")} onClick={onClick}>
      {content}
    </button>
  );
}

export function DropdownMenuSeparator({ className }: { className?: string }) {
  return <div className={cn("my-1 h-px bg-border", className)} />;
}

export function DropdownMenuLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("px-3 py-2 text-xs font-semibold text-muted-foreground uppercase", className)}>
      {children}
    </div>
  );
}
