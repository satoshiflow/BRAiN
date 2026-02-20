"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import { useState } from "react";
import {
  useKnowledgeGraphInfo,
  useDatasets,
  useAddData,
  useCognify,
  useSearchKnowledgeGraph,
} from "@/hooks/useKnowledgeGraph";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, Database, Search, Sparkles, FileText } from "lucide-react";

export default function KnowledgeGraphPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [dataToAdd, setDataToAdd] = useState("");
  const [searchResults, setSearchResults] = useState<any>(null);

  const { data: info, isLoading: infoLoading } = useKnowledgeGraphInfo();
  const { data: datasets, isLoading: datasetsLoading } = useDatasets();

  const addData = useAddData();
  const cognify = useCognify();
  const searchKG = useSearchKnowledgeGraph();

  const handleSearch = () => {
    if (searchQuery.trim()) {
      searchKG.mutate(
        { query: searchQuery, limit: 10 },
        {
          onSuccess: (data) => setSearchResults(data),
        }
      );
    }
  };

  const handleAddData = () => {
    if (datasetId.trim() && dataToAdd.trim()) {
      addData.mutate({
        dataset_id: datasetId.trim(),
        data: dataToAdd.split("\n").filter((l) => l.trim()),
      });
      setDataToAdd("");
    }
  };

  return (
    <div className="flex-1 space-y-6 p-8 pt-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Knowledge Graph</h2>
          <p className="text-muted-foreground">
            Semantic knowledge storage and intelligent search
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          <Database className="mr-1 h-3 w-3" />
          {info?.version || "v1.0.0"}
        </Badge>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Datasets</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {infoLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <div className="text-2xl font-bold">{info?.total_datasets || 0}</div>
                <p className="text-xs text-muted-foreground">Knowledge bases</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {infoLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <div className="text-2xl font-bold">{info?.total_documents || 0}</div>
                <p className="text-xs text-muted-foreground">Stored documents</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System</CardTitle>
            <Sparkles className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{info?.name || "KG System"}</div>
            <p className="text-xs text-muted-foreground">{info?.description || "Ready"}</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="search" className="space-y-4">
        <TabsList>
          <TabsTrigger value="search">Search</TabsTrigger>
          <TabsTrigger value="add">Add Data</TabsTrigger>
          <TabsTrigger value="cognify">Cognify</TabsTrigger>
          <TabsTrigger value="datasets">Datasets</TabsTrigger>
        </TabsList>

        {/* Search Tab */}
        <TabsContent value="search" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Search Knowledge</CardTitle>
              <CardDescription>Semantic search across all datasets</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <div className="flex-1 space-y-2">
                  <Label htmlFor="search-query">Search Query</Label>
                  <Input
                    id="search-query"
                    placeholder="What do you want to know?"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  />
                </div>
                <div className="flex items-end">
                  <Button onClick={handleSearch} disabled={!searchQuery.trim() || searchKG.isPending}>
                    {searchKG.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Search className="mr-2 h-4 w-4" />
                    )}
                    Search
                  </Button>
                </div>
              </div>

              {/* Search Results */}
              {searchResults && (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Found {searchResults.total_results} results in {searchResults.search_time_ms}ms
                  </p>
                  {searchResults.results.map((result: any, index: number) => (
                    <div key={index} className="rounded-lg border p-3 hover:bg-accent">
                      <div className="flex items-start justify-between">
                        <p className="text-sm">{result.content}</p>
                        <Badge variant="secondary">{(result.score * 100).toFixed(0)}%</Badge>
                      </div>
                      {result.metadata && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          {JSON.stringify(result.metadata)}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Add Data Tab */}
        <TabsContent value="add" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Add Data to Knowledge Graph</CardTitle>
              <CardDescription>Add new documents to a dataset</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="dataset-id">Dataset ID</Label>
                <Input
                  id="dataset-id"
                  placeholder="e.g., technical_docs"
                  value={datasetId}
                  onChange={(e) => setDatasetId(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="data">Data (one item per line)</Label>
                <Textarea
                  id="data"
                  placeholder="Enter documents or text chunks, one per line..."
                  rows={8}
                  value={dataToAdd}
                  onChange={(e) => setDataToAdd(e.target.value)}
                />
              </div>

              <Button
                onClick={handleAddData}
                disabled={!datasetId.trim() || !dataToAdd.trim() || addData.isPending}
                className="w-full"
              >
                {addData.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Adding...
                  </>
                ) : (
                  <>
                    <FileText className="mr-2 h-4 w-4" />
                    Add Data
                  </>
                )}
              </Button>

              {addData.isSuccess && (
                <div className="rounded-lg bg-green-500/10 p-4 text-sm text-green-500">
                  Data added successfully!
                </div>
              )}

              {addData.isError && (
                <div className="rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
                  Error: {addData.error.message}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Cognify Tab */}
        <TabsContent value="cognify" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Cognify Data</CardTitle>
              <CardDescription>
                Process data into knowledge graph with entity and relationship extraction
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg bg-muted p-4 text-center text-sm text-muted-foreground">
                Cognify functionality - extract entities and relationships from raw data
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Datasets Tab */}
        <TabsContent value="datasets" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Datasets</CardTitle>
              <CardDescription>All knowledge bases in the system</CardDescription>
            </CardHeader>
            <CardContent>
              {datasetsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : datasets && datasets.datasets.length > 0 ? (
                <div className="space-y-2">
                  {datasets.datasets.map((dataset) => (
                    <div
                      key={dataset.id}
                      className="flex items-center justify-between rounded-lg border p-3 hover:bg-accent"
                    >
                      <div>
                        <p className="font-medium">{dataset.name || dataset.id}</p>
                        {dataset.description && (
                          <p className="text-sm text-muted-foreground">{dataset.description}</p>
                        )}
                        <p className="text-xs text-muted-foreground">
                          Created: {new Date(dataset.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold">{dataset.document_count}</p>
                        <p className="text-xs text-muted-foreground">documents</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  No datasets found
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
