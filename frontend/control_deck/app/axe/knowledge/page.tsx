// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  useKnowledgeDocuments,
  useKnowledgeStats,
  useDeleteKnowledgeDocument,
} from '@/hooks/useAxeKnowledge';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Plus, Search, Edit2, Trash2, Loader2 } from 'lucide-react';
import { DocumentCategory } from '@/lib/axeKnowledgeApi';

// Category color mapping
const CATEGORY_COLORS: Record<DocumentCategory, string> = {
  system: 'bg-blue-500',
  domain: 'bg-purple-500',
  procedure: 'bg-green-500',
  faq: 'bg-yellow-500',
  reference: 'bg-orange-500',
  custom: 'bg-gray-500',
};

export default function KnowledgePage() {
  const [category, setCategory] = useState<DocumentCategory | undefined>();
  const [searchQuery, setSearchQuery] = useState('');

  const { data: documents, isLoading } = useKnowledgeDocuments({
    category,
    search_query: searchQuery || undefined,
    enabled_only: true,
  });

  const { data: stats } = useKnowledgeStats();
  const deleteMutation = useDeleteKnowledgeDocument();

  const handleDelete = async (id: string) => {
    if (confirm('Delete this document?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  return (
    <div className="space-y-4 p-4 md:p-6">
      {/* Header - Mobile optimized */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">Knowledge Documents</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage AXE&apos;s knowledge base
          </p>
        </div>
        <Link href="/axe/knowledge/new">
          <Button className="w-full sm:w-auto">
            <Plus className="mr-2 h-4 w-4" />
            New Document
          </Button>
        </Link>
      </div>

      {/* Stats Cards - Responsive grid */}
      {stats && Object.keys(stats).length > 0 && (
        <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
          {Object.entries(stats).map(([cat, count]) => (
            <Card key={cat}>
              <CardContent className="p-3 sm:p-4">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-3 h-3 rounded-full ${
                      CATEGORY_COLORS[cat as DocumentCategory]
                    }`}
                  />
                  <div>
                    <p className="text-xs text-muted-foreground capitalize">
                      {cat}
                    </p>
                    <p className="text-lg font-bold">{count}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Filters - Stack on mobile */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Category Filter */}
        <Select
          value={category}
          onValueChange={(val) =>
            setCategory(val === 'all' ? undefined : (val as DocumentCategory))
          }
        >
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            <SelectItem value="system">System</SelectItem>
            <SelectItem value="domain">Domain</SelectItem>
            <SelectItem value="procedure">Procedure</SelectItem>
            <SelectItem value="faq">FAQ</SelectItem>
            <SelectItem value="reference">Reference</SelectItem>
            <SelectItem value="custom">Custom</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Mobile: Cards */}
      {!isLoading && documents && documents.length > 0 && (
        <div className="block md:hidden space-y-3">
          {documents.map((doc) => (
            <Card key={doc.id}>
              <CardContent className="p-4">
                <div className="space-y-3">
                  <div>
                    <h3 className="font-medium truncate">{doc.name}</h3>
                    <div className="flex flex-wrap gap-2 mt-2">
                      <Badge className={CATEGORY_COLORS[doc.category]}>
                        {doc.category}
                      </Badge>
                      <Badge variant="outline">Score: {doc.importance_score}</Badge>
                      <Badge variant="secondary">v{doc.version}</Badge>
                    </div>
                  </div>
                  {doc.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {doc.description}
                    </p>
                  )}
                  {doc.tags && doc.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {doc.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <div className="flex gap-2 pt-2">
                    <Link href={`/axe/knowledge/${doc.id}/edit`} className="flex-1">
                      <Button variant="outline" size="sm" className="w-full">
                        <Edit2 className="mr-1 h-3 w-3" />
                        Edit
                      </Button>
                    </Link>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(doc.id)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Desktop: Table */}
      {!isLoading && documents && documents.length > 0 && (
        <div className="hidden md:block">
          <Card>
            <CardContent className="p-0">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-4">Name</th>
                    <th className="text-left p-4">Category</th>
                    <th className="text-left p-4">Score</th>
                    <th className="text-left p-4">Version</th>
                    <th className="text-left p-4">Updated</th>
                    <th className="text-right p-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id} className="border-b last:border-0 hover:bg-secondary/50">
                      <td className="p-4">
                        <div>
                          <div className="font-medium">{doc.name}</div>
                          {doc.description && (
                            <div className="text-sm text-muted-foreground line-clamp-1">
                              {doc.description}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="p-4">
                        <Badge className={CATEGORY_COLORS[doc.category]}>
                          {doc.category}
                        </Badge>
                      </td>
                      <td className="p-4">{doc.importance_score}</td>
                      <td className="p-4">v{doc.version}</td>
                      <td className="p-4 text-sm text-muted-foreground">
                        {new Date(doc.updated_at).toLocaleDateString()}
                      </td>
                      <td className="p-4">
                        <div className="flex justify-end gap-2">
                          <Link href={`/axe/knowledge/${doc.id}/edit`}>
                            <Button variant="ghost" size="sm">
                              <Edit2 className="h-4 w-4" />
                            </Button>
                          </Link>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(doc.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && (!documents || documents.length === 0) && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 px-4">
            <p className="text-muted-foreground mb-4 text-center">
              No documents found
            </p>
            <Link href="/axe/knowledge/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Document
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
