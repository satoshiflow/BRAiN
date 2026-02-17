/**
 * AXE UI TypeScript Type Definitions
 * Complete type system for AXE Assistant Widget
 */

// ============================================================================
// Core Types
// ============================================================================

export type AxeMode = 'assistant' | 'builder' | 'support' | 'debug';
export type AxeTheme = 'dark' | 'light';
export type AxeTrainingMode = 'global' | 'per_app' | 'off';
export type AxeAnonymizationLevel = 'none' | 'pseudonymized' | 'strict';

// ============================================================================
// Widget Configuration
// ============================================================================

export interface AxeWidgetPosition {
  bottom?: number;
  right?: number;
  top?: number;
  left?: number;
}

export interface AxeRateLimits {
  requests_per_minute: number;
  burst: number;
}

export interface AxeTelemetryConfig {
  enabled: boolean;
  anonymization_level: AxeAnonymizationLevel;
  training_mode: AxeTrainingMode;
  training_opt_in?: boolean;
  collect_context_snapshots: boolean;
  upload_interval_ms: number;
}

export interface AxePermissionsConfig {
  can_run_tools: boolean;
  can_trigger_actions: boolean;
  can_access_apis: string[];
}

export interface AxeUiConfig {
  show_context_panel: boolean;
  show_mode_selector: boolean;
  enable_canvas: boolean;
}

export interface AxeConfig {
  app_id: string;
  display_name: string;
  avatar_url?: string;
  theme: AxeTheme;
  position: AxeWidgetPosition;
  default_open: boolean;
  mode: AxeMode;
  training_mode: AxeTrainingMode;
  allowed_scopes: string[];
  knowledge_spaces: string[];
  rate_limits: AxeRateLimits;
  telemetry: AxeTelemetryConfig;
  permissions: AxePermissionsConfig;
  ui: AxeUiConfig;
}

// ============================================================================
// Chat & Messaging
// ============================================================================

export interface AxeMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  context?: Record<string, any>;
  metadata?: {
    model?: string;
    tokens?: number;
    duration_ms?: number;
  };
}

export interface AxeExtraContext {
  [key: string]: any;
}

// ============================================================================
// Files & Code Editor (CANVAS)
// ============================================================================

export interface AxeFile {
  id: string;
  name: string;
  language: string;
  content: string;
  dependencies?: string[];
  path?: string;
  is_dirty?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AxeDiff {
  id: string;
  fileId: string;
  fileName: string;
  language: string;
  oldContent: string;
  newContent: string;
  description: string;
  timestamp: string;
  applied?: boolean;
}

// ============================================================================
// Event Telemetry
// ============================================================================

export type AxeEventType =
  | 'axe_message'
  | 'axe_feedback'
  | 'axe_click'
  | 'axe_context_snapshot'
  | 'axe_error'
  | 'axe_file_open'
  | 'axe_file_save'
  | 'axe_diff_applied'
  | 'axe_diff_rejected';

export interface AxeClientContext {
  user_agent: string;
  screen_width: number;
  screen_height: number;
  locale: string;
  timezone: string;
}

export interface AxeEventBase {
  event_id: string;
  event_type: AxeEventType;
  timestamp: string;
  app_id: string;
  user_id?: string;
  session_id: string;
  mode: AxeMode;
  client?: AxeClientContext;
}

export interface AxeMessageEvent extends AxeEventBase {
  event_type: 'axe_message';
  payload: {
    message: string;
    context?: Record<string, any>;
    training_enabled: boolean;
    anonymization_level: AxeAnonymizationLevel;
  };
}

export interface AxeFeedbackEvent extends AxeEventBase {
  event_type: 'axe_feedback';
  payload: {
    message_id: string;
    feedback: 'positive' | 'negative';
    comment?: string;
  };
}

export interface AxeClickEvent extends AxeEventBase {
  event_type: 'axe_click';
  payload: {
    element: string;
    action: string;
    metadata?: Record<string, any>;
  };
}

export interface AxeContextSnapshotEvent extends AxeEventBase {
  event_type: 'axe_context_snapshot';
  payload: {
    snapshot: Record<string, any>;
  };
}

export interface AxeErrorEvent extends AxeEventBase {
  event_type: 'axe_error';
  payload: {
    error_type: string;
    error_message: string;
    stack_trace?: string;
  };
}

export interface AxeFileEvent extends AxeEventBase {
  event_type: 'axe_file_open' | 'axe_file_save';
  payload: {
    file_id: string;
    file_name: string;
    language: string;
  };
}

export interface AxeDiffEvent extends AxeEventBase {
  event_type: 'axe_diff_applied' | 'axe_diff_rejected';
  payload: {
    diff_id: string;
    file_id: string;
    file_name: string;
  };
}

export type AxeEvent =
  | AxeMessageEvent
  | AxeFeedbackEvent
  | AxeClickEvent
  | AxeContextSnapshotEvent
  | AxeErrorEvent
  | AxeFileEvent
  | AxeDiffEvent;

// ============================================================================
// API Responses
// ============================================================================

export interface AxeApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
}

export interface AxeChatResponse {
  message_id: string;
  content: string;
  role: 'assistant';
  timestamp: string;
  metadata?: {
    model: string;
    tokens: number;
    duration_ms: number;
  };
  suggestions?: string[];
  diff?: AxeDiff;
}

export interface AxeEventsResponse {
  success: boolean;
  events_received: number;
  events_stored: number;
}

// ============================================================================
// Component Props
// ============================================================================

export interface FloatingAxeProps {
  appId: string;
  backendUrl: string;
  mode?: AxeMode;
  theme?: AxeTheme;
  position?: AxeWidgetPosition;
  defaultOpen?: boolean;
  locale?: string;
  userId?: string;
  sessionId?: string;
  extraContext?: AxeExtraContext;
  onEvent?: (event: AxeEvent) => void;
}

export interface AxeWidgetProps {
  position: AxeWidgetPosition;
  defaultOpen: boolean;
  theme: AxeTheme;
  mode: AxeMode;
  locale: string;
}

export interface AxeCanvasProps {
  mode: AxeMode;
  onModeChange: (mode: AxeMode) => void;
  onClose: () => void;
  locale: string;
}

export interface CodeEditorProps {
  language: string;
  value: string;
  onChange: (value: string) => void;
  theme?: 'vs-dark' | 'light';
  readOnly?: boolean;
  height?: string;
}

export interface DiffEditorProps {
  original: string;
  modified: string;
  language: string;
  theme?: 'vs-dark' | 'light';
  readOnly?: boolean;
}

export interface DiffOverlayProps {
  diff: AxeDiff;
  onApply: () => void;
  onReject: () => void;
}
