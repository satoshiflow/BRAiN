"use client";

import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader } from "@/components/shell/page-layout";
import { Card, CardHeader, CardTitle, CardContent, CardDescription, Button, Badge } from "@ui-core/components";
import { 
  Save,
  Moon,
  Sun,
  Globe,
  Bell,
  Shield,
  Database
} from "lucide-react";

export default function SettingsPage() {
  return (
    <DashboardLayout title="Settings" subtitle="Systemkonfiguration">
      <PageContainer>
        <PageHeader
          title="Einstellungen"
          description="Konfiguriere das ControlDeck"
          actions={
            <Button>
              <Save className="h-4 w-4 mr-2" />
              Speichern
            </Button>
          }
        />

        <div className="space-y-6 max-w-2xl">
          {/* Theme Settings */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Moon className="h-5 w-5" />
                Erscheinungsbild
              </CardTitle>
              <CardDescription>
                Passe das Theme und die Farben an
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Theme</p>
                  <p className="text-sm text-muted-foreground">Wähle zwischen Hell und Dunkel</p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    <Sun className="h-4 w-4 mr-2" />
                    Hell
                  </Button>
                  <Button variant="default" size="sm">
                    <Moon className="h-4 w-4 mr-2" />
                    Dunkel
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* API Settings */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                API Konfiguration
              </CardTitle>
              <CardDescription>
                Backend API Endpoints
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">API Base URL</label>
                <input
                  type="text"
                  defaultValue="https://api.brain.falklabs.de"
                  className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">WebSocket URL</label>
                <input
                  type="text"
                  defaultValue="wss://api.brain.falklabs.de/ws"
                  className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
            </CardContent>
          </Card>

          {/* Notifications */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Benachrichtigungen
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Mission Alerts</p>
                  <p className="text-sm text-muted-foreground">Benachrichtigungen bei Mission-Status-Änderungen</p>
                </div>
                <Button variant="outline" size="sm">Aktiviert</Button>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">System Warnings</p>
                  <p className="text-sm text-muted-foreground">Warnungen bei System-Problemen</p>
                </div>
                <Button variant="outline" size="sm">Aktiviert</Button>
              </div>
            </CardContent>
          </Card>

          {/* Security */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Sicherheit
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Session Timeout</p>
                  <p className="text-sm text-muted-foreground">Automatische Abmeldung nach Inaktivität</p>
                </div>
                <Badge variant="default">30 Minuten</Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      </PageContainer>
    </DashboardLayout>
  );
}