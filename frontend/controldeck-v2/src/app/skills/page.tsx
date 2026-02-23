"use client"

import { useState, useEffect } from "react"
import { DashboardLayout } from "@/components/shell/dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@ui-core/components/card"
import { Button } from "@ui-core/components/button"
import { Badge } from "@ui-core/components/badge"
import { Input, Label } from "@ui-core/components/input"
import { Alert, AlertDescription } from "@ui-core/components/alert"
import { 
  Plus, 
  Play, 
  Trash2, 
  Code, 
  FileText, 
  MessageSquare, 
  BarChart3, 
  Settings,
  CheckCircle,
  AlertCircle,
  Loader2
} from "lucide-react"

const API_BASE = process.env.NEXT_PUBLIC_BRAIN_API_BASE || "https://api.brain.falklabs.de"

const CATEGORY_ICONS = {
  api: Code,
  file: FileText,
  communication: MessageSquare,
  analysis: BarChart3,
  custom: Settings
}

const CATEGORY_COLORS = {
  api: "bg-blue-500/10 text-blue-500",
  file: "bg-green-500/10 text-green-500",
  communication: "bg-purple-500/10 text-purple-500",
  analysis: "bg-orange-500/10 text-orange-500",
  custom: "bg-gray-500/10 text-gray-500"
}

interface Skill {
  id: string
  name: string
  description?: string
  category: "api" | "file" | "communication" | "analysis" | "custom"
  manifest: any
  handler_path: string
  enabled: boolean
  created_at: string
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [message, setMessage] = useState("")
  
  // Form state
  const [newSkill, setNewSkill] = useState({
    name: "",
    description: "",
    category: "custom",
    handler_path: "",
    manifest: "{\"name\": \"\", \"version\": \"1.0.0\"}"
  })

  useEffect(() => {
    fetchSkills()
    fetchCategories()
  }, [])

  const fetchSkills = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/skills`)
      if (res.ok) {
        const data = await res.json()
        setSkills(data.skills || [])
      }
    } catch (e) {
      console.error("Failed to fetch skills")
    } finally {
      setLoading(false)
    }
  }

  const fetchCategories = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/skills/categories`)
      if (res.ok) {
        const data = await res.json()
        setCategories(data.categories || [])
      }
    } catch (e) {
      console.error("Failed to fetch categories")
    }
  }

  const createSkill = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/skills`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...newSkill,
          manifest: JSON.parse(newSkill.manifest),
          enabled: true
        })
      })
      
      if (res.ok) {
        const skill = await res.json()
        setSkills([skill, ...skills])
        setShowCreateDialog(false)
        setNewSkill({
          name: "",
          description: "",
          category: "custom",
          handler_path: "",
          manifest: "{\"name\": \"\", \"version\": \"1.0.0\"}"
        })
        setMessage("Skill created successfully!")
        setTimeout(() => setMessage(""), 3000)
      } else {
        const err = await res.text()
        setMessage(`Error: ${err}`)
      }
    } catch (e) {
      setMessage("Error creating skill")
    }
  }

  const deleteSkill = async (id: string) => {
    if (!confirm("Delete this skill?")) return
    
    try {
      const res = await fetch(`${API_BASE}/api/skills/${id}`, {
        method: "DELETE"
      })
      
      if (res.ok) {
        setSkills(skills.filter(s => s.id !== id))
        setMessage("Skill deleted")
        setTimeout(() => setMessage(""), 3000)
      }
    } catch (e) {
      setMessage("Error deleting skill")
    }
  }

  const executeSkill = async (skill: Skill) => {
    try {
      setMessage(`Executing ${skill.name}...`)
      const res = await fetch(`${API_BASE}/api/skills/${skill.id}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ parameters: {} })
      })
      
      if (res.ok) {
        const result = await res.json()
        setMessage(`Executed: ${result.output?.message || "Success"}`)
      } else {
        setMessage("Execution failed")
      }
      setTimeout(() => setMessage(""), 5000)
    } catch (e) {
      setMessage("Error executing skill")
    }
  }

  return (
    <DashboardLayout
      title="Skills"
      subtitle="Manage and execute PicoClaw-style skills"
    >
      <div className="container mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Skills</h1>
            <p className="text-muted-foreground">
              {skills.length} skill{skills.length !== 1 ? 's' : ''} available
            </p>
          </div>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Skill
          </Button>
        </div>

        {message && (
          <Alert className={message.includes("Error") ? "bg-red-500/10" : "bg-green-500/10"}>
            {message.includes("Error") ? (
              <AlertCircle className="h-4 w-4 text-red-500" />
            ) : (
              <CheckCircle className="h-4 w-4 text-green-500" />
            )}
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}

        {/* Skills Grid */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : skills.length === 0 ? (
          <Card className="p-12 text-center">
            <Code className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No skills yet</h3>
            <p className="text-muted-foreground mb-4">
              Create your first skill to get started
            </p>
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Skill
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {skills.map((skill) => {
              const Icon = CATEGORY_ICONS[skill.category] || Settings
              return (
                <Card key={skill.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${CATEGORY_COLORS[skill.category]}`}>
                          <Icon className="h-5 w-5" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">{skill.name}</CardTitle>
                          <Badge variant="muted" className="text-xs mt-1">
                            {skill.category}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => executeSkill(skill)}
                          title="Execute"
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => deleteSkill(skill.id)}
                          className="text-destructive hover:text-destructive"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-3">
                      {skill.description || "No description"}
                    </p>
                    <div className="space-y-2 text-xs text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <Code className="h-3 w-3" />
                        <code className="bg-muted px-1 rounded truncate">
                          {skill.handler_path}
                        </code>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>ID: {skill.id.slice(0, 8)}...</span>
                        <span>{new Date(skill.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}

        {/* Create Dialog */}
        {showCreateDialog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <Card className="w-full max-w-lg max-h-[90vh] overflow-y-auto">
              <CardHeader>
                <CardTitle>Create New Skill</CardTitle>
                <CardDescription>
                  Define a new PicoClaw-style skill
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input
                    value={newSkill.name}
                    onChange={(e) => setNewSkill({...newSkill, name: e.target.value})}
                    placeholder="e.g., pdf_converter"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Input
                    value={newSkill.description}
                    onChange={(e) => setNewSkill({...newSkill, description: e.target.value})}
                    placeholder="What does this skill do?"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Category</Label>
                  <select
                    value={newSkill.category}
                    onChange={(e) => setNewSkill({...newSkill, category: e.target.value})}
                    className="w-full h-10 px-3 rounded-md border border-input bg-background"
                  >
                    {categories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
                
                <div className="space-y-2">
                  <Label>Handler Path</Label>
                  <Input
                    value={newSkill.handler_path}
                    onChange={(e) => setNewSkill({...newSkill, handler_path: e.target.value})}
                    placeholder="skills/my_skill/handler.py"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Manifest (JSON)</Label>
                  <textarea
                    value={newSkill.manifest}
                    onChange={(e) => setNewSkill({...newSkill, manifest: e.target.value})}
                    className="w-full h-32 p-3 rounded-md border border-input bg-background font-mono text-sm"
                  />
                </div>
                
                <div className="flex gap-2 pt-4">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => setShowCreateDialog(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    className="flex-1"
                    disabled={!newSkill.name || !newSkill.handler_path}
                    onClick={createSkill}
                  >
                    Create Skill
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
