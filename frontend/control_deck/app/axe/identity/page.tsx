'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  useAxeIdentities,
  useActivateAxeIdentity,
  useDeleteAxeIdentity,
} from '@/hooks/useAxeIdentity';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Plus, Edit2, Trash2, CheckCircle2, Circle, Loader2 } from 'lucide-react';

export default function AXEIdentityPage() {
  const { data: identities, isLoading } = useAxeIdentities();
  const activateMutation = useActivateAxeIdentity();
  const deleteMutation = useDeleteAxeIdentity();

  const [deleteId, setDeleteId] = useState<string | null>(null);

  const handleActivate = async (id: string) => {
    await activateMutation.mutateAsync(id);
  };

  const handleDelete = async () => {
    if (deleteId) {
      await deleteMutation.mutateAsync(deleteId);
      setDeleteId(null);
    }
  };

  return (
    <div className="space-y-4 p-4 md:p-6">
      {/* Header - Mobile optimized */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">AXE Identity</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure AXE&apos;s persona
          </p>
        </div>
        <Link href="/axe/identity/new">
          <Button className="w-full sm:w-auto">
            <Plus className="mr-2 h-4 w-4" />
            New Identity
          </Button>
        </Link>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Identity Grid - Mobile First: 1 col → 2 cols → 3 cols */}
      {!isLoading && identities && identities.length > 0 && (
        <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {identities.map((identity) => (
            <Card
              key={identity.id}
              className={identity.is_active ? 'border-emerald-500 border-2' : ''}
            >
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <CardTitle className="text-lg truncate">
                        {identity.name}
                      </CardTitle>
                      {identity.is_active && (
                        <Badge variant="default" className="bg-emerald-600 shrink-0">
                          <CheckCircle2 className="mr-1 h-3 w-3" />
                          Active
                        </Badge>
                      )}
                    </div>
                    <CardDescription className="mt-1 line-clamp-2">
                      {identity.description || 'No description'}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-3">
                {/* System Prompt Preview - Mobile optimized */}
                <div className="text-xs md:text-sm text-muted-foreground line-clamp-3 bg-secondary/50 p-2 rounded">
                  {identity.system_prompt}
                </div>

                {/* Metadata - Responsive text */}
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span>v{identity.version}</span>
                  <span>•</span>
                  <span>{identity.capabilities.length} capabilities</span>
                </div>

                {/* Actions - Stack on mobile, row on desktop */}
                <div className="flex flex-col sm:flex-row gap-2 pt-2">
                  {!identity.is_active && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full sm:w-auto"
                      onClick={() => handleActivate(identity.id)}
                      disabled={activateMutation.isPending}
                    >
                      <Circle className="mr-1 h-3 w-3" />
                      Activate
                    </Button>
                  )}
                  <Link href={`/axe/identity/${identity.id}/edit`} className="w-full sm:w-auto">
                    <Button variant="outline" size="sm" className="w-full">
                      <Edit2 className="mr-1 h-3 w-3" />
                      Edit
                    </Button>
                  </Link>
                  {!identity.is_active && (
                    <Button
                      variant="destructive"
                      size="sm"
                      className="w-full sm:w-auto"
                      onClick={() => setDeleteId(identity.id)}
                    >
                      <Trash2 className="mr-1 h-3 w-3" />
                      Delete
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && (!identities || identities.length === 0) && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 px-4">
            <p className="text-muted-foreground mb-4 text-center">
              No identities created yet
            </p>
            <Link href="/axe/identity/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create First Identity
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent className="max-w-[90vw] sm:max-w-[425px]">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Identity?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The identity will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex-col sm:flex-row gap-2">
            <AlertDialogCancel className="w-full sm:w-auto">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="w-full sm:w-auto">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
