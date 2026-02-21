"use client";

import { useState } from "react";
import { DashboardLayout } from "@/components/shell/dashboard-layout";
import { PageContainer, PageHeader } from "@/components/shell/page-layout";
import { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardContent,
  Button,
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
  Badge,
  Input,
  Label
} from "@ui-core/components";
import { AlertTriangle, Info, CheckCircle, XCircle } from "lucide-react";

export default function ModalsPage() {
  // Dialogs
  const alertModal = useModal();
  const confirmModal = useModal();
  const formModal = useModal();
  
  // Drawers
  const detailDrawer = useModal();
  const formDrawer = useModal();
  const settingsDrawer = useModal();

  const [formData, setFormData] = useState({ name: "", email: "" });

  return (
    <DashboardLayout title="Modals & Drawers" subtitle="Dialog and Drawer Components">
      <PageContainer>
        <PageHeader
          title="Modal & Drawer System"
          description="Interactive overlay components for BRAiN ControlDeck v2"
        />

        {/* Dialogs Section */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Dialogs (Center Modals)</h2>
          <Card>
            <CardContent className="p-6">
              <div className="flex flex-wrap gap-4">
                <Button onClick={alertModal.onOpen} variant="destructive">
                  <AlertTriangle className="h-4 w-4 mr-2" />
                  Alert Dialog
                </Button>
                <Button onClick={confirmModal.onOpen} variant="outline">
                  <Info className="h-4 w-4 mr-2" />
                  Confirm Dialog
                </Button>
                <Button onClick={formModal.onOpen}>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Form Dialog
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Drawers Section */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Drawers (Slide-over Panels)</h2>
          <Card>
            <CardContent className="p-6">
              <div className="flex flex-wrap gap-4">
                <Button onClick={detailDrawer.onOpen} variant="secondary">
                  Detail Drawer
                </Button>
                <Button onClick={formDrawer.onOpen} variant="outline">
                  Form Drawer
                </Button>
                <Button onClick={settingsDrawer.onOpen}>
                  Settings Drawer
                </Button>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Usage Guide */}
        <Card className="bg-secondary/30">
          <CardHeader>
            <CardTitle className="text-base">Usage Guide</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div>
              <h4 className="font-medium text-foreground mb-1">Dialogs</h4>
              <ul className="list-disc list-inside space-y-1">
                <li>Use for confirmations, alerts, and small forms</li>
                <li>Centered on screen with backdrop blur</li>
                <li>Max width: 512px (max-w-lg)</li>
                <li>Close with ESC, backdrop click, or close button</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-foreground mb-1">Drawers</h4>
              <ul className="list-disc list-inside space-y-1">
                <li>Use for detail views, settings, and complex forms</li>
                <li>Slide in from right (default) or left</li>
                <li>Default width: 480px</li>
                <li>Better for content-heavy interactions</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-foreground mb-1">useModal Hook</h4>
              <code className="bg-muted px-2 py-1 rounded text-xs">
                const &#123; open, onOpen, onClose, onOpenChange &#125; = useModal()
              </code>
            </div>
          </CardContent>
        </Card>

        {/* Alert Dialog */}
        <Dialog open={alertModal.open} onOpenChange={alertModal.onOpenChange}>
          <DialogHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-danger" />
              <DialogTitle>Delete Mission?</DialogTitle>
            </div>
            <DialogDescription>
              This action cannot be undone. This will permanently delete the mission
              and remove the data from our servers.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={alertModal.onClose}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={alertModal.onClose}>
              Delete
            </Button>
          </DialogFooter>
        </Dialog>

        {/* Confirm Dialog */}
        <Dialog open={confirmModal.open} onOpenChange={confirmModal.onOpenChange}>
          <DialogHeader>
            <div className="flex items-center gap-2">
              <Info className="h-5 w-5 text-info" />
              <DialogTitle>Restart Worker?</DialogTitle>
            </div>
            <DialogDescription>
              Are you sure you want to restart the mission worker? Active missions
              will be interrupted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={confirmModal.onClose}>
              Cancel
            </Button>
            <Button onClick={confirmModal.onClose}>
              Restart
            </Button>
          </DialogFooter>
        </Dialog>

        {/* Form Dialog */}
        <Dialog open={formModal.open} onOpenChange={formModal.onOpenChange}>
          <DialogHeader>
            <DialogTitle>Create New Mission</DialogTitle>
            <DialogDescription>
              Enter the details for your new mission.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Mission Name</Label>
              <Input
                id="name"
                placeholder="e.g., Deploy v2.1"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">Mission Type</Label>
              <select className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                <option>Deploy</option>
                <option>Backup</option>
                <option>Health Check</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={formModal.onClose}>
              Cancel
            </Button>
            <Button onClick={formModal.onClose}>
              Create Mission
            </Button>
          </DialogFooter>
        </Dialog>

        {/* Detail Drawer */}
        <Drawer open={detailDrawer.open} onOpenChange={detailDrawer.onOpenChange} width={480}>
          <DrawerHeader onClose={detailDrawer.onClose}>
            <div>
              <DrawerTitle>Mission Details</DrawerTitle>
              <p className="text-sm text-muted-foreground">ID: m-001-deploy-v2-1</p>
            </div>
          </DrawerHeader>
          <DrawerContent>
            <div className="space-y-6">
              <div>
                <h4 className="text-sm font-medium mb-2">Status</h4>
                <Badge variant="success">Running</Badge>
              </div>
              <div>
                <h4 className="text-sm font-medium mb-2">Progress</h4>
                <div className="w-full bg-muted rounded-full h-2">
                  <div className="bg-success h-2 rounded-full" style={{ width: "65%" }} />
                </div>
                <p className="text-sm text-muted-foreground mt-1">65% complete</p>
              </div>
              <div>
                <h4 className="text-sm font-medium mb-2">Agent</h4>
                <p className="text-sm">picofred</p>
              </div>
              <div>
                <h4 className="text-sm font-medium mb-2">Created</h4>
                <p className="text-sm">Feb 21, 2024 at 10:30 AM</p>
              </div>
              <div>
                <h4 className="text-sm font-medium mb-2">Logs</h4>
                <div className="bg-muted/50 rounded p-3 font-mono text-xs space-y-1">
                  <p>[10:30:01] Mission started</p>
                  <p>[10:30:05] Preparing deployment...</p>
                  <p>[10:30:12] Uploading assets...</p>
                  <p>[10:30:45] Configuring services...</p>
                </div>
              </div>
            </div>
          </DrawerContent>
          <DrawerFooter>
            <Button variant="outline" onClick={detailDrawer.onClose}>
              Close
            </Button>
            <Button variant="destructive">
              Cancel Mission
            </Button>
          </DrawerFooter>
        </Drawer>

        {/* Form Drawer */}
        <Drawer open={formDrawer.open} onOpenChange={formDrawer.onOpenChange} width={480}>
          <DrawerHeader onClose={formDrawer.onClose}>
            <DrawerTitle>New Agent Configuration</DrawerTitle>
          </DrawerHeader>
          <DrawerContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Agent Name</Label>
                <Input placeholder="e.g., Worker 03" />
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <select className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option>Mission Worker</option>
                  <option>Event Processor</option>
                  <option>Backup Agent</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Capabilities</Label>
                <div className="flex flex-wrap gap-2">
                  {["deploy", "backup", "health", "logs"].map((cap) => (
                    <Badge key={cap} variant="secondary" className="cursor-pointer">
                      {cap}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label>Priority</Label>
                <input type="range" min="1" max="10" className="w-full" />
              </div>
            </div>
          </DrawerContent>
          <DrawerFooter>
            <Button variant="outline" onClick={formDrawer.onClose}>
              Cancel
            </Button>
            <Button onClick={formDrawer.onClose}>
              Save Configuration
            </Button>
          </DrawerFooter>
        </Drawer>

        {/* Settings Drawer */}
        <Drawer open={settingsDrawer.open} onOpenChange={settingsDrawer.onOpenChange} width={400}>
          <DrawerHeader onClose={settingsDrawer.onClose}>
            <DrawerTitle>Quick Settings</DrawerTitle>
          </DrawerHeader>
          <DrawerContent>
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">Auto-refresh</h4>
                  <p className="text-sm text-muted-foreground">Update dashboard every 5s</p>
                </div>
                <div className="h-6 w-11 bg-primary rounded-full relative cursor-pointer">
                  <div className="absolute right-1 top-1 h-4 w-4 bg-white rounded-full" />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">Notifications</h4>
                  <p className="text-sm text-muted-foreground">Show mission alerts</p>
                </div>
                <div className="h-6 w-11 bg-primary rounded-full relative cursor-pointer">
                  <div className="absolute right-1 top-1 h-4 w-4 bg-white rounded-full" />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">Dark Mode</h4>
                  <p className="text-sm text-muted-foreground">Use dark theme</p>
                </div>
                <div className="h-6 w-11 bg-muted rounded-full relative cursor-pointer">
                  <div className="absolute left-1 top-1 h-4 w-4 bg-white rounded-full" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Refresh Interval</Label>
                <select className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option>5 seconds</option>
                  <option>10 seconds</option>
                  <option>30 seconds</option>
                  <option>1 minute</option>
                </select>
              </div>
            </div>
          </DrawerContent>
          <DrawerFooter>
            <Button onClick={settingsDrawer.onClose}>
              Save Settings
            </Button>
          </DrawerFooter>
        </Drawer>
      </PageContainer>
    </DashboardLayout>
  );
}