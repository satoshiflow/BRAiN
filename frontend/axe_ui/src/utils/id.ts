/**
 * ID Generation Utilities
 */

export function generateSessionId(): string {
  return `axe_session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function generateFileId(): string {
  return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function generateDiffId(): string {
  return `diff_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function generateEventId(): string {
  return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
