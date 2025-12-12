"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    setMounted(true);
    const root = document.documentElement;
    const stored = window.localStorage.getItem("brain-theme");
    if (stored === "light") {
      root.classList.remove("dark");
      setIsDark(false);
    } else {
      root.classList.add("dark");
      setIsDark(true);
    }
  }, []);

  if (!mounted) return null;

  const toggle = () => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.remove("dark");
      window.localStorage.setItem("brain-theme", "light");
      setIsDark(false);
    } else {
      root.classList.add("dark");
      window.localStorage.setItem("brain-theme", "dark");
      setIsDark(true);
    }
  };

  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      onClick={toggle}
      className="h-8 w-8 rounded-full border-border bg-background/80"
      aria-label="Theme umschalten"
    >
      {isDark ? (
        <Sun className="h-4 w-4" />
      ) : (
        <Moon className="h-4 w-4" />
      )}
    </Button>
  );
}
