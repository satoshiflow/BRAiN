"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { signIn } from "@/lib/auth-client"
import { Button } from "@ui-core/components/button"
import { Input, Label } from "@ui-core/components/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@ui-core/components/card"
import { Alert, AlertDescription } from "@ui-core/components/alert"
import { Brain, Shield, User, Lock, AlertCircle } from "lucide-react"

// Predefined dummy accounts for quick login
const DUMMY_ACCOUNTS = [
  { email: "admin@brain.local", role: "admin", label: "Admin" },
  { email: "operator@brain.local", role: "operator", label: "Operator" },
  { email: "agent@brain.local", role: "agent", label: "Agent" },
  { email: "tester@brain.local", role: "operator", label: "Tester" },
]

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      const result = await signIn.email({
        email,
        password,
        callbackURL: "/",
      })

      if (result.error) {
        setError(result.error.message || "Invalid credentials")
      } else {
        router.push("/")
        router.refresh()
      }
    } catch (err) {
      setError("An error occurred. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  const quickLogin = (accountEmail: string) => {
    setEmail(accountEmail)
    // Password is same as role for dummy accounts
    const role = accountEmail.split("@")[0]
    setPassword(role === "tester" ? "tester" : role)
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-gradient-to-br from-background via-background to-muted">
      {/* Left side - Branding */}
      <div className="lg:flex-1 flex flex-col justify-center items-center p-8 lg:p-16">
        <div className="text-center lg:text-left max-w-md">
          <div className="flex items-center justify-center lg:justify-start gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center">
              <Brain className="w-7 h-7 text-primary-foreground" />
            </div>
            <span className="text-3xl font-bold tracking-tight">BRAiN</span>
          </div>
          <h1 className="text-4xl lg:text-5xl font-bold mb-4 tracking-tight">
            Control Deck
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            Enterprise Futuristic Control System
          </p>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Shield className="w-4 h-4" />
            <span>Invitation only access</span>
          </div>
        </div>
      </div>

      {/* Right side - Login form */}
      <div className="lg:flex-1 flex flex-col justify-center items-center p-8 lg:p-16">
        <Card className="w-full max-w-md border-border/50 shadow-2xl">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold text-center">Welcome back</CardTitle>
            <CardDescription className="text-center">
              Sign in to access the control deck
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="flex items-center gap-2">
                  <User className="w-4 h-4" />
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="h-11"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="flex items-center gap-2">
                  <Lock className="w-4 h-4" />
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="h-11"
                />
              </div>

              <Button
                type="submit"
                className="w-full h-11 text-base font-medium"
                disabled={loading}
              >
                {loading ? "Signing in..." : "Sign in"}
              </Button>
            </form>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">
                  Quick login (Demo)
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {DUMMY_ACCOUNTS.map((account) => (
                <Button
                  key={account.email}
                  variant="outline"
                  size="sm"
                  onClick={() => quickLogin(account.email)}
                  className="text-xs"
                >
                  {account.label}
                </Button>
              ))}
            </div>

            <p className="text-xs text-center text-muted-foreground">
              Passwords: admin | operator | agent | tester
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
