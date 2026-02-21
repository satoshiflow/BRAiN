import * as React from "react";
import { cn } from "@ui-core/utils";
import { X } from "lucide-react";
import { Button } from "./button";

// Dialog/Modal Component
interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
  className?: string;
}

function Dialog({ open, onOpenChange, children, className }: DialogProps) {
  // Close on ESC
  React.useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity animate-in fade-in duration-200"
        onClick={() => onOpenChange(false)}
      />
      
      {/* Dialog Content */}
      <div
        className={cn(
          "relative z-10 w-full max-w-lg rounded-lg border border-border bg-card p-6 shadow-lg",
          "animate-in zoom-in-95 fade-in duration-200",
          className
        )}
      >
        {children}
      </div>
    </div>
  );
}

// Dialog Header
interface DialogHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

function DialogHeader({ children, className, ...props }: DialogHeaderProps) {
  return (
    <div className={cn("flex flex-col space-y-1.5 text-center sm:text-left", className)} {...props}>
      {children}
    </div>
  );
}

// Dialog Title
interface DialogTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
}

function DialogTitle({ children, className, ...props }: DialogTitleProps) {
  return (
    <h2 className={cn("text-lg font-semibold leading-none tracking-tight", className)} {...props}>
      {children}
    </h2>
  );
}

// Dialog Description
interface DialogDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode;
}

function DialogDescription({ children, className, ...props }: DialogDescriptionProps) {
  return (
    <p className={cn("text-sm text-muted-foreground", className)} {...props}>
      {children}
    </p>
  );
}

// Dialog Footer
interface DialogFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

function DialogFooter({ children, className, ...props }: DialogFooterProps) {
  return (
    <div className={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 mt-6", className)} {...props}>
      {children}
    </div>
  );
}

// Drawer Component
interface DrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
  position?: "left" | "right";
  width?: number | string;
  className?: string;
}

function Drawer({
  open,
  onOpenChange,
  children,
  position = "right",
  width = 480,
  className,
}: DrawerProps) {
  // Close on ESC
  React.useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [open, onOpenChange]);

  // Prevent body scroll when open
  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;

  const widthStyle = typeof width === "number" ? `${width}px` : width;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity animate-in fade-in duration-300"
        onClick={() => onOpenChange(false)}
      />

      {/* Drawer Content */}
      <div
        className={cn(
          "absolute top-0 h-full bg-card shadow-xl",
          "transition-transform duration-300 ease-out",
          position === "right" ? "right-0" : "left-0",
          "animate-in",
          position === "right" ? "slide-in-from-right" : "slide-in-from-left",
          className
        )}
        style={{ width: widthStyle }}
      >
        {children}
      </div>
    </div>
  );
}

// Drawer Header
interface DrawerHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  onClose?: () => void;
}

function DrawerHeader({ children, onClose, className, ...props }: DrawerHeaderProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between px-6 py-4 border-b border-border",
        className
      )}
      {...props}
    >
      <div className="flex-1">{children}</div>
      {onClose && (
        <Button variant="ghost" size="icon" onClick={onClose} className="ml-4">
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}

// Drawer Title
interface DrawerTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
}

function DrawerTitle({ children, className, ...props }: DrawerTitleProps) {
  return (
    <h2 className={cn("text-lg font-semibold", className)} {...props}>
      {children}
    </h2>
  );
}

// Drawer Content
interface DrawerContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

function DrawerContent({ children, className, ...props }: DrawerContentProps) {
  return (
    <div className={cn("flex-1 overflow-auto p-6", className)} {...props}>
      {children}
    </div>
  );
}

// Drawer Footer
interface DrawerFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

function DrawerFooter({ children, className, ...props }: DrawerFooterProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-end gap-3 px-6 py-4 border-t border-border",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

// Simple Modal Hook
function useModal(defaultOpen = false) {
  const [open, setOpen] = React.useState(defaultOpen);
  return {
    open,
    onOpenChange: setOpen,
    onOpen: () => setOpen(true),
    onClose: () => setOpen(false),
  };
}

export {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  Drawer,
  DrawerHeader,
  DrawerTitle,
  DrawerContent,
  DrawerFooter,
  useModal,
};
export type { DialogProps, DrawerProps };