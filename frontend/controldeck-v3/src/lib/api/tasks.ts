import { fetchJson } from "./client";

export type TaskStatus =
  | "pending"
  | "scheduled"
  | "claimed"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "timeout"
  | "retrying";

export interface TaskRecord {
  id: string;
  task_id: string;
  name: string;
  description?: string | null;
  task_type: string;
  category?: string | null;
  tags: string[];
  status: TaskStatus;
  priority: number;
  payload: Record<string, unknown>;
  config: Record<string, unknown>;
  tenant_id?: string | null;
  mission_id?: string | null;
  skill_run_id?: string | null;
  correlation_id?: string | null;
  claimed_by?: string | null;
  claimed_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  result?: Record<string, unknown> | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  items: TaskRecord[];
  total: number;
  by_status: Record<string, number>;
}

export const taskApi = {
  list: (taskType: string, limit = 20) =>
    fetchJson<TaskListResponse>(`/api/tasks?task_type=${encodeURIComponent(taskType)}&limit=${limit}`),
};
