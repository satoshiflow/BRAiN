"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';


import Link from "next/link";
import { ArrowLeft, Globe } from "lucide-react";
import { SpecBuilder } from "@/components/webgenesis/SpecBuilder";

export default function NewSitePage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <header className="flex flex-col gap-4">
        <Link
          href="/webgenesis"
          className="inline-flex w-fit items-center gap-2 text-sm text-neutral-400 transition-colors hover:text-neutral-200"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Sites
        </Link>

        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-blue-900/20 p-3">
            <Globe className="h-8 w-8 text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">Create New Site</h1>
            <p className="mt-1 text-sm text-neutral-400">
              Build a new website with the WebsiteSpec Builder
            </p>
          </div>
        </div>
      </header>

      {/* SpecBuilder Wizard */}
      <SpecBuilder />
    </div>
  );
}
