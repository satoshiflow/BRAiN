"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { hasRole } from "@/lib/rbac";

export default function ApiKeysPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  // Fix B: RBAC - Admin only for API Keys
  useEffect(() => {
    if (!isLoading && (!user || !hasRole(user.role, 'admin'))) {
      router.push('/dashboard?error=unauthorized');
    }
  }, [user, isLoading, router]);

  if (isLoading || !user || !hasRole(user.role, 'admin')) {
    return null;
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">API Keys</h1>
    </div>
  );
}
