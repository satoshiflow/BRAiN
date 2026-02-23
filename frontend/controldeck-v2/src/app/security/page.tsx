"use client"

import { useState, useEffect } from "react"

// API Configuration
const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "https://api.brain.falklabs.de"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@ui-core/components/card"
import { Button } from "@ui-core/components/button"
import { Switch } from "@ui-core/components/switch"
import { Input, Label } from "@ui-core/components/input"
import { Badge } from "@ui-core/components/badge"
import { Alert, AlertDescription } from "@ui-core/components/alert"
import { 
  Shield, 
  Key, 
  Smartphone, 
  History, 
  Lock, 
  AlertTriangle,
  CheckCircle,
  Clock,
  Activity,
  Eye
} from "lucide-react"
import { DashboardLayout } from "@/components/shell/dashboard-layout"

interface SecuritySettings {
  twoFactorEnabled: boolean
  auditLoggingEnabled: boolean
  rateLimitingEnabled: boolean
  sessionTimeout: number
  ipWhitelist: string[]
  lastPasswordChange: string
  loginHistory: LoginEvent[]
}

interface LoginEvent {
  id: string
  timestamp: string
  ip: string
  userAgent: string
  success: boolean
  location?: string
}

interface SecurityStatus {
  totalEvents: number
  failedLogins24h: number
  activeSessions: number
  lastAuditCheck: string
}

export default function SecurityPage() {
  const [settings, setSettings] = useState<SecuritySettings>({
    twoFactorEnabled: false,
    auditLoggingEnabled: true,
    rateLimitingEnabled: true,
    sessionTimeout: 60,
    ipWhitelist: [],
    lastPasswordChange: "2026-02-22",
    loginHistory: []
  })
  
  const [status, setStatus] = useState<SecurityStatus>({
    totalEvents: 0,
    failedLogins24h: 0,
    activeSessions: 1,
    lastAuditCheck: new Date().toISOString()
  })
  
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  
  // 2FA Setup State
  const [show2FADialog, setShow2FADialog] = useState(false)
  const [twoFactorSetup, setTwoFactorSetup] = useState<{secret: string; qrCode: string} | null>(null)
  const [verificationCode, setVerificationCode] = useState("")

  // Fetch security status
  useEffect(() => {
    fetchSecurityStatus()
    fetchLoginHistory()
  }, [])

  const fetchSecurityStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/security/status`)
      if (res.ok) {
        const data = await res.json()
        setStatus(data)
      }
    } catch (e) {
      console.error("Failed to fetch security status")
    }
  }

  const fetchLoginHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/security/login-history`)
      if (res.ok) {
        const data = await res.json()
        setSettings(prev => ({ ...prev, loginHistory: data.entries || [] }))
      }
    } catch (e) {
      console.error("Failed to fetch login history")
    }
  }

  const toggleSetting = async (key: keyof SecuritySettings, value: boolean | number) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/security/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [key]: value })
      })
      
      if (res.ok) {
        setSettings(prev => ({ ...prev, [key]: value }))
        setMessage(`${key} updated successfully`)
        setTimeout(() => setMessage(""), 3000)
      }
    } catch (e) {
      setMessage("Failed to update setting")
    } finally {
      setLoading(false)
    }
  }

  const setup2FA = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/security/2fa/setup`, { method: "POST" })
      if (res.ok) {
        const data = await res.json()
        setTwoFactorSetup(data)
        setShow2FADialog(true)
      } else {
        setMessage("Failed to setup 2FA")
      }
    } catch (e) {
      setMessage("Error setting up 2FA")
    } finally {
      setLoading(false)
    }
  }
  
  const verify2FA = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/security/2fa/verify?code=${verificationCode}`, { 
        method: "POST" 
      })
      if (res.ok) {
        setSettings(prev => ({ ...prev, twoFactorEnabled: true }))
        setShow2FADialog(false)
        setMessage("2FA enabled successfully!")
        setVerificationCode("")
      } else {
        setMessage("Invalid verification code")
      }
    } catch (e) {
      setMessage("Error verifying 2FA")
    } finally {
      setLoading(false)
    }
  }

  return (
    <DashboardLayout
      title="Security"
      subtitle="Manage your account security and privacy settings"
    >
      <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Security</h1>
          <p className="text-muted-foreground">Manage your account security and privacy settings</p>
        </div>
        <Shield className="h-8 w-8 text-primary" />
      </div>

      {message && (
        <Alert className="bg-green-500/10 border-green-500/20">
          <CheckCircle className="h-4 w-4 text-green-500" />
          <AlertDescription className="text-green-700">{message}</AlertDescription>
        </Alert>
      )}

      {/* Security Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Security Score</p>
                <p className="text-2xl font-bold text-green-600">85/100</p>
              </div>
              <Shield className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Failed Logins (24h)</p>
                <p className="text-2xl font-bold">{status.failedLogins24h}</p>
              </div>
              <AlertTriangle className="h-8 w-8 text-yellow-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Sessions</p>
                <p className="text-2xl font-bold">{status.activeSessions}</p>
              </div>
              <Activity className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Audit Events</p>
                <p className="text-2xl font-bold">{status.totalEvents}</p>
              </div>
              <Eye className="h-8 w-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Authentication Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              Authentication
            </CardTitle>
            <CardDescription>Manage how you sign in to your account</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* 2FA Toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Two-Factor Authentication</Label>
                <p className="text-sm text-muted-foreground">
                  Add an extra layer of security to your account
                </p>
              </div>
              <div className="flex items-center gap-4">
                {settings.twoFactorEnabled && (
                  <Badge variant="muted" className="bg-green-500/10 text-green-600">Active</Badge>
                )}
                <Switch
                  checked={settings.twoFactorEnabled}
                  onCheckedChange={(checked) => {
                    if (checked) setup2FA()
                    else toggleSetting("twoFactorEnabled", checked)
                  }}
                />
              </div>
            </div>

            {/* Session Timeout */}
            <div className="space-y-2">
              <Label>Session Timeout (minutes)</Label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="15"
                  max="240"
                  step="15"
                  value={settings.sessionTimeout}
                  onChange={(e) => toggleSetting("sessionTimeout", parseInt(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm font-medium w-16">{settings.sessionTimeout}m</span>
              </div>
            </div>

            {/* Password Last Changed */}
            <div className="flex items-center justify-between py-2 border-t">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">Last password change</span>
              </div>
              <span className="text-sm text-muted-foreground">{settings.lastPasswordChange}</span>
            </div>
          </CardContent>
        </Card>

        {/* Security Features */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Security Features
            </CardTitle>
            <CardDescription>Enable or disable security protections</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Audit Logging */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Audit Logging</Label>
                <p className="text-sm text-muted-foreground">
                  Log all actions for security review
                </p>
              </div>
              <Switch
                checked={settings.auditLoggingEnabled}
                onCheckedChange={(checked) => toggleSetting("auditLoggingEnabled", checked)}
              />
            </div>

            {/* Rate Limiting */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Rate Limiting</Label>
                <p className="text-sm text-muted-foreground">
                  Protect against brute force attacks (100 req/min)
                </p>
              </div>
              <Switch
                checked={settings.rateLimitingEnabled}
                onCheckedChange={(checked) => toggleSetting("rateLimitingEnabled", checked)}
              />
            </div>

            {/* IP Whitelist */}
            <div className="space-y-2 border-t pt-4">
              <Label className="flex items-center gap-2">
                <Key className="h-4 w-4" />
                IP Whitelist
              </Label>
              <p className="text-sm text-muted-foreground">
                Restrict access to specific IP addresses (optional)
              </p>
              {settings.ipWhitelist.length === 0 ? (
                <p className="text-sm text-muted-foreground italic">No IP restrictions</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {settings.ipWhitelist.map((ip) => (
                    <Badge key={ip} variant="muted">{ip}</Badge>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Login History */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Login History
            </CardTitle>
            <CardDescription>Recent sign-in activity on your account</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {settings.loginHistory.length === 0 ? (
                <p className="text-muted-foreground text-center py-8">No login history available</p>
              ) : (
                settings.loginHistory.map((entry) => (
                  <div
                    key={entry.id}
                    className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-2 h-2 rounded-full ${entry.success ? 'bg-green-500' : 'bg-red-500'}`} />
                      <div>
                        <p className="text-sm font-medium">
                          {entry.success ? 'Successful login' : 'Failed login attempt'}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(entry.timestamp).toLocaleString()} • {entry.ip} • {entry.userAgent}
                        </p>
                      </div>
                    </div>
                    {entry.location && (
                      <Badge variant="outline">{entry.location}</Badge>
                    )}
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* 2FA Setup Card (Conditional) */}
        {!settings.twoFactorEnabled && (
          <Card className="lg:col-span-2 border-primary/50 bg-primary/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Smartphone className="h-5 w-5" />
                Enable Two-Factor Authentication
              </CardTitle>
              <CardDescription>
                Protect your account with an additional layer of security
              </CardDescription>
            </CardHeader>
            <CardContent className="flex items-center justify-between">
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  Requires verification code on login
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  Works with any authenticator app
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  Backup codes for account recovery
                </li>
              </ul>
              <Button onClick={setup2FA} size="lg">
                <Shield className="h-4 w-4 mr-2" />
                Enable 2FA
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
      
      {/* 2FA Setup Dialog */}
      {show2FADialog && twoFactorSetup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-md mx-4">
            <CardHeader>
              <CardTitle>Setup Two-Factor Authentication</CardTitle>
              <CardDescription>
                Scan the QR code with your authenticator app
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* QR Code */}
              <div className="flex justify-center">
                <img 
                  src={twoFactorSetup.qrCode} 
                  alt="2FA QR Code" 
                  className="w-48 h-48 border rounded-lg"
                />
              </div>
              
              {/* Manual Secret */}
              <div className="bg-muted p-3 rounded-lg">
                <p className="text-xs text-muted-foreground mb-1">Manual entry code:</p>
                <code className="text-sm font-mono break-all">{twoFactorSetup.secret}</code>
              </div>
              
              {/* Verification Code Input */}
              <div className="space-y-2">
                <Label>Enter verification code from app</Label>
                <Input
                  type="text"
                  placeholder="123456"
                  maxLength={6}
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  className="text-center text-2xl tracking-widest"
                />
              </div>
              
              {/* Actions */}
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  className="flex-1"
                  onClick={() => {
                    setShow2FADialog(false)
                    setVerificationCode("")
                  }}
                >
                  Cancel
                </Button>
                <Button 
                  className="flex-1"
                  disabled={verificationCode.length !== 6 || loading}
                  onClick={verify2FA}
                >
                  {loading ? "Verifying..." : "Verify & Enable"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </DashboardLayout>
  )
}
