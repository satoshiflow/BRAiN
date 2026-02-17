/**
 * React Query hooks for Knowledge Graph Module
 *
 * Semantic knowledge storage and search system
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API_BASE } from "@/lib/api";


// ============================================================================
// Types
// ============================================================================

export interface KnowledgeGraphInfo {
  name: string;
  version: string;
  description: string;
  total_datasets: number;
  total_documents: number;
}

export interface AddDataRequest {
  dataset_id: string;
  data: string | string[];
  metadata?: Record<string, unknown>;
}

export interface AddDataResponse {
  dataset_id: string;
  documents_added: number;
  message: string;
}

export interface CognifyRequest {
  dataset_id: string;
  source_data: string | string[];
  extract_entities?: boolean;
  extract_relationships?: boolean;
}

export interface CognifyResponse {
  dataset_id: string;
  entities_extracted: number;
  relationships_created: number;
  processing_time_ms: number;
}

export interface SearchRequest {
  query: string;
  dataset_id?: string;
  limit?: number;
  threshold?: number;
}

export interface SearchResult {
  id: string;
  content: string;
  score: number;
  metadata?: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_time_ms: number;
}

export interface Dataset {
  id: string;
  name: string;
  description?: string;
  document_count: number;
  created_at: string;
}

export interface ListDatasetsResponse {
  datasets: Dataset[];
  total_datasets: number;
}

// ============================================================================
// API Functions
// ============================================================================

async function fetchKnowledgeGraphInfo(): Promise<KnowledgeGraphInfo> {
  const response = await fetch(`${API_BASE}/api/knowledge-graph/info`);
  if (!response.ok) throw new Error(`Failed to fetch info: ${response.statusText}`);
  return response.json();
}

async function addData(request: AddDataRequest): Promise<AddDataResponse> {
  const response = await fetch(`${API_BASE}/api/knowledge-graph/add`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Failed to add data: ${response.statusText}`);
  return response.json();
}

async function cognify(request: CognifyRequest): Promise<CognifyResponse> {
  const response = await fetch(`${API_BASE}/api/knowledge-graph/cognify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Failed to cognify: ${response.statusText}`);
  return response.json();
}

async function search(request: SearchRequest): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE}/api/knowledge-graph/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`Failed to search: ${response.statusText}`);
  return response.json();
}

async function listDatasets(): Promise<ListDatasetsResponse> {
  const response = await fetch(`${API_BASE}/api/knowledge-graph/datasets`);
  if (!response.ok) throw new Error(`Failed to list datasets: ${response.statusText}`);
  return response.json();
}

async function resetKnowledgeGraph(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/knowledge-graph/reset`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(`Failed to reset: ${response.statusText}`);
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Get knowledge graph system information
 */
export function useKnowledgeGraphInfo() {
  return useQuery<KnowledgeGraphInfo>({
    queryKey: ['knowledge-graph', 'info'],
    queryFn: fetchKnowledgeGraphInfo,
    staleTime: 300_000,
    retry: 2,
  });
}

/**
 * List all datasets
 */
export function useDatasets() {
  return useQuery<ListDatasetsResponse>({
    queryKey: ['knowledge-graph', 'datasets'],
    queryFn: listDatasets,
    refetchInterval: 30_000,
    staleTime: 20_000,
    retry: 2,
  });
}

/**
 * Add data to knowledge graph
 */
export function useAddData() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: addData,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph', 'datasets'] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph', 'info'] });
    },
  });
}

/**
 * Process data into knowledge graph
 */
export function useCognify() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: cognify,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph', 'datasets'] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph', 'info'] });
    },
  });
}

/**
 * Search knowledge graph
 */
export function useSearchKnowledgeGraph() {
  return useMutation({
    mutationFn: search,
  });
}

/**
 * Reset knowledge graph
 */
export function useResetKnowledgeGraph() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resetKnowledgeGraph,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph'] });
    },
  });
}
