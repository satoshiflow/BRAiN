"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { hasRole } from "@/lib/rbac";

export default function SkillsCreatorPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  // Fix B: RBAC - Operator or higher required for Skills Creator
  useEffect(() => {
    if (!isLoading && (!user || !hasRole(user.role, 'operator'))) {
      router.push('/dashboard?error=unauthorized');
    }
  }, [user, isLoading, router]);

  if (isLoading || !user || !hasRole(user.role, 'operator')) {
    return null;
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Skills Creator</h1>
    </div>
  );
}
