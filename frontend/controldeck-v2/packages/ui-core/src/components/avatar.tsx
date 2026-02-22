import * as React from "react";
import { cn } from "@ui-core/utils";

interface AvatarProps {
  className?: string;
  children: React.ReactNode;
}

export function Avatar({ className, children }: AvatarProps) {
  return (
    <div
      className={cn(
        "relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full",
        className
      )}
    >
      {children}
    </div>
  );
}

interface AvatarImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src?: string;
  alt?: string;
}

export function AvatarImage({ className, src, alt, ...props }: AvatarImageProps) {
  if (!src) return null;
  return (
    <img
      src={src}
      alt={alt}
      className={cn("aspect-square h-full w-full object-cover", className)}
      {...props}
    />
  );
}

interface AvatarFallbackProps {
  className?: string;
  children: React.ReactNode;
  delayMs?: number;
}

export function AvatarFallback({ className, children }: AvatarFallbackProps) {
  return (
    <div
      className={cn(
        "flex h-full w-full items-center justify-center rounded-full bg-muted",
        className
      )}
    >
      {children}
    </div>
  );
}
