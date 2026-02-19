'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAxeIdentity, useUpdateAxeIdentity } from '@/hooks/useAxeIdentity';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Save, Loader2 } from 'lucide-react';

export default function EditIdentityPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { data: identity, isLoading } = useAxeIdentity(params.id);
  const updateMutation = useUpdateAxeIdentity();

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    system_prompt: '',
    capabilities: '',
  });

  // Pre-fill form when identity loads
  useEffect(() => {
    if (identity) {
      setFormData({
        name: identity.name,
        description: identity.description || '',
        system_prompt: identity.system_prompt,
        capabilities: identity.capabilities.join(', '),
      });
    }
  }, [identity]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await updateMutation.mutateAsync({
        id: params.id,
        data: {
          name: formData.name,
          description: formData.description || undefined,
          system_prompt: formData.system_prompt,
          capabilities: formData.capabilities
            ? formData.capabilities.split(',').map((c) => c.trim())
            : [],
        },
      });

      router.push('/axe/identity');
    } catch (error) {
      console.error('Failed to update identity:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!identity) {
    return <div className="p-6">Identity not found</div>;
  }

  return (
    <div className="space-y-4 p-4 md:p-6">
      {/* Header - Mobile optimized */}
      <div className="flex items-center gap-3">
        <Link href="/axe/identity">
          <Button variant="ghost" size="icon" className="shrink-0">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold md:text-3xl truncate">Edit Identity</h1>
            <Badge variant="outline">v{identity.version}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Update identity configuration
          </p>
        </div>
      </div>

      {/* Form Card */}
      <Card>
        <CardHeader>
          <CardTitle>Identity Details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name */}
            <div className="space-y-2">
              <Label htmlFor="name">
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="AXE Guardian"
                required
                className="w-full"
              />
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="Security-focused AXE persona"
                rows={2}
                className="w-full resize-none"
              />
            </div>

            {/* System Prompt */}
            <div className="space-y-2">
              <Label htmlFor="system_prompt">
                System Prompt <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="system_prompt"
                value={formData.system_prompt}
                onChange={(e) =>
                  setFormData({ ...formData, system_prompt: e.target.value })
                }
                placeholder="Du bist AXE..."
                rows={8}
                className="w-full resize-y font-mono text-sm"
                required
              />
              <p className="text-xs text-muted-foreground">
                The system prompt defines AXE&apos;s behavior and personality
              </p>
            </div>

            {/* Capabilities */}
            <div className="space-y-2">
              <Label htmlFor="capabilities">Capabilities</Label>
              <Input
                id="capabilities"
                value={formData.capabilities}
                onChange={(e) =>
                  setFormData({ ...formData, capabilities: e.target.value })
                }
                placeholder="monitoring, troubleshooting, admin"
                className="w-full"
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated list of capabilities
              </p>
            </div>

            {/* Actions */}
            <div className="flex flex-col-reverse sm:flex-row gap-3 pt-4">
              <Link href="/axe/identity" className="w-full sm:w-auto">
                <Button type="button" variant="outline" className="w-full">
                  Cancel
                </Button>
              </Link>
              <Button
                type="submit"
                disabled={updateMutation.isPending}
                className="w-full sm:w-auto sm:ml-auto"
              >
                {updateMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Save className="mr-2 h-4 w-4" />
                )}
                Update Identity
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
