import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchKnowledgeDocuments,
  fetchKnowledgeDocument,
  fetchTopDocuments,
  fetchCategoryStats,
  createKnowledgeDocument,
  updateKnowledgeDocument,
  deleteKnowledgeDocument,
  KnowledgeDocument,
  KnowledgeDocumentCreate,
  KnowledgeDocumentUpdate,
  DocumentCategory,
} from "@/lib/axeKnowledgeApi";

// Query Keys Structure
const knowledgeKeys = {
  all: ["axe-knowledge"] as const,
  lists: () => [...knowledgeKeys.all, "list"] as const,
  list: (filters: KnowledgeFilters = {}) =>
    [...knowledgeKeys.lists(), filters] as const,
  top: (limit: number) => [...knowledgeKeys.all, "top", limit] as const,
  stats: () => [...knowledgeKeys.all, "stats"] as const,
  detail: (id: string) => [...knowledgeKeys.all, "detail", id] as const,
};

type KnowledgeFilters = {
  category?: DocumentCategory;
  enabled_only?: boolean;
  tags?: string[];
  search_query?: string;
};

// 1. List documents with filters
export function useKnowledgeDocuments(filters?: KnowledgeFilters) {
  return useQuery({
    queryKey: knowledgeKeys.list(filters),
    queryFn: () => fetchKnowledgeDocuments(filters),
    staleTime: 30_000,
  });
}

// 2. Get top documents (for preview/dashboard)
export function useTopKnowledgeDocuments(limit: number = 5) {
  return useQuery({
    queryKey: knowledgeKeys.top(limit),
    queryFn: () => fetchTopDocuments(limit),
    staleTime: 60_000,
  });
}

// 3. Get category statistics
export function useKnowledgeStats() {
  return useQuery({
    queryKey: knowledgeKeys.stats(),
    queryFn: fetchCategoryStats,
    staleTime: 120_000, // 2min - stats change slowly
  });
}

// 4. Get single document
export function useKnowledgeDocument(id: string) {
  return useQuery({
    queryKey: knowledgeKeys.detail(id),
    queryFn: () => fetchKnowledgeDocument(id),
    enabled: !!id,
  });
}

// 5. Create document mutation
export function useCreateKnowledgeDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: KnowledgeDocumentCreate) =>
      createKnowledgeDocument(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() });
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.stats() });
    },
  });
}

// 6. Update document mutation
export function useUpdateKnowledgeDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: KnowledgeDocumentUpdate }) =>
      updateKnowledgeDocument(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() });
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.stats() });
    },
  });
}

// 7. Delete document mutation
export function useDeleteKnowledgeDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteKnowledgeDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() });
      queryClient.invalidateQueries({ queryKey: knowledgeKeys.stats() });
    },
  });
}
