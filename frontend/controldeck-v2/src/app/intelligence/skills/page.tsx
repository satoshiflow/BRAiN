"use client";

import { useRouter } from "next/navigation";
import { Button } from "@ui-core/components";
import { Plus, Puzzle } from "lucide-react";

export default function SkillsPage() {
  const router = useRouter();

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Skills</h1>
          <p className="text-muted-foreground mt-1">Manage agent skills and capabilities</p>
        </div>
        <Button onClick={() => router.push("/intelligence/skills/creator")}>
          <Plus className="h-4 w-4 mr-2" />
          Create Skill
        </Button>
      </div>
      
      {/* Skills List Table - Placeholder */}
      <div className="border rounded-lg p-8 text-center text-muted-foreground">
        <Puzzle className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>Skills list will be implemented here</p>
        <p className="text-sm mt-2">Table with all skills + Creator button above</p>
      </div>
    </div>
  );
}
