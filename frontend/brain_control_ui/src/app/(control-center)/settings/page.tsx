"use client";

import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";

export default function SettingsOverviewPage() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Wähle einen Bereich, um die Konfiguration von BRAiN anzupassen.
      </p>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {/* LLM Settings */}
        <Link href="/settings/llm" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle>LLM Settings</CardTitle>
              <CardDescription>
                Host, Model, Token-Limits und LLM-Test.
              </CardDescription>
            </CardHeader>
            <CardContent>
              Konfiguriere die zentrale AI-Engine (Ollama / LM Studio / Gateway).
            </CardContent>
          </Card>
        </Link>

        {/* Agent Settings */}
        <Link href="/settings/agents" className="block">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
            <CardHeader>
              <CardTitle>Agent Settings</CardTitle>
              <CardDescription>
                Verwaltung und Status der aktiven Agenten.
              </CardDescription>
            </CardHeader>
            <CardContent>
              Überblick über Agenten, Health und laufende Missionen.
            </CardContent>
          </Card>
        </Link>

        {/* Platzhalter: System Settings (später) */}
        <Card className="opacity-70">
          <CardHeader>
            <CardTitle>System Settings</CardTitle>
            <CardDescription>
              Cluster, Ressourcen, Limits & Sicherheit.
            </CardDescription>
          </CardHeader>
          <CardContent>
            Coming Soon – hier landen später globale System-Optionen.
          </CardContent>
        </Card>
      </div>
    </div>
  );
}