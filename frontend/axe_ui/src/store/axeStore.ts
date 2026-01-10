/**
 * AXE Store - Global State Management
 * Main Zustand store for AXE widget state
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AxeConfig, AxeMode, AxeMessage, AxeFile } from '../types';

interface AxeStore {
  // ============================================================================
  // Configuration
  // ============================================================================
  config: AxeConfig | null;
  setConfig: (config: AxeConfig) => void;

  // ============================================================================
  // Session
  // ============================================================================
  sessionId: string;
  userId?: string;
  setSession: (sessionId: string, userId?: string) => void;

  // ============================================================================
  // Widget State
  // ============================================================================
  widgetState: 'minimized' | 'expanded' | 'canvas';
  setWidgetState: (state: 'minimized' | 'expanded' | 'canvas') => void;

  // ============================================================================
  // Mode
  // ============================================================================
  mode: AxeMode;
  setMode: (mode: AxeMode) => void;

  // ============================================================================
  // Chat Messages
  // ============================================================================
  messages: AxeMessage[];
  addMessage: (message: AxeMessage) => void;
  updateMessage: (messageId: string, updates: Partial<AxeMessage>) => void;
  clearMessages: () => void;

  // ============================================================================
  // Files (CANVAS)
  // ============================================================================
  files: AxeFile[];
  activeFileId: string | null;
  addFile: (file: AxeFile) => void;
  updateFile: (fileId: string, content: string) => void;
  deleteFile: (fileId: string) => void;
  setActiveFile: (fileId: string | null) => void;
  getActiveFile: () => AxeFile | null;

  // ============================================================================
  // Context
  // ============================================================================
  extraContext: Record<string, any>;
  updateContext: (context: Record<string, any>) => void;

  // ============================================================================
  // UI State
  // ============================================================================
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
}

export const useAxeStore = create<AxeStore>()(
  persist(
    (set, get) => ({
      // ============================================================================
      // Initial State
      // ============================================================================
      config: null,
      sessionId: '',
      userId: undefined,
      widgetState: 'minimized',
      mode: 'assistant',
      messages: [],
      files: [],
      activeFileId: null,
      extraContext: {},
      isLoading: false,
      error: null,

      // ============================================================================
      // Configuration Actions
      // ============================================================================
      setConfig: (config) => set({ config }),

      // ============================================================================
      // Session Actions
      // ============================================================================
      setSession: (sessionId, userId) => set({ sessionId, userId }),

      // ============================================================================
      // Widget State Actions
      // ============================================================================
      setWidgetState: (widgetState) => {
        set({ widgetState });

        // Auto-switch to builder mode when opening canvas
        if (widgetState === 'canvas' && get().mode !== 'builder') {
          set({ mode: 'builder' });
        }
      },

      // ============================================================================
      // Mode Actions
      // ============================================================================
      setMode: (mode) => {
        set({ mode });

        // Auto-open canvas when switching to builder mode
        if (mode === 'builder' && get().widgetState !== 'canvas') {
          set({ widgetState: 'canvas' });
        }
      },

      // ============================================================================
      // Chat Actions
      // ============================================================================
      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message]
        })),

      updateMessage: (messageId, updates) =>
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === messageId ? { ...msg, ...updates } : msg
          )
        })),

      clearMessages: () => set({ messages: [] }),

      // ============================================================================
      // File Actions
      // ============================================================================
      addFile: (file) =>
        set((state) => ({
          files: [...state.files, file],
          activeFileId: file.id
        })),

      updateFile: (fileId, content) =>
        set((state) => ({
          files: state.files.map((f) =>
            f.id === fileId
              ? {
                  ...f,
                  content,
                  is_dirty: true,
                  updated_at: new Date().toISOString()
                }
              : f
          )
        })),

      deleteFile: (fileId) =>
        set((state) => {
          const remainingFiles = state.files.filter((f) => f.id !== fileId);
          const newActiveId =
            state.activeFileId === fileId
              ? remainingFiles[0]?.id || null
              : state.activeFileId;

          return {
            files: remainingFiles,
            activeFileId: newActiveId
          };
        }),

      setActiveFile: (fileId) => set({ activeFileId: fileId }),

      getActiveFile: () => {
        const state = get();
        if (!state.activeFileId) return null;
        return state.files.find((f) => f.id === state.activeFileId) || null;
      },

      // ============================================================================
      // Context Actions
      // ============================================================================
      updateContext: (context) =>
        set((state) => ({
          extraContext: { ...state.extraContext, ...context }
        })),

      // ============================================================================
      // UI State Actions
      // ============================================================================
      setIsLoading: (loading) => set({ isLoading: loading }),

      setError: (error) => set({ error })
    }),
    {
      name: 'axe-storage', // localStorage key
      partialize: (state) => ({
        // Only persist these fields (don't persist session-specific data)
        messages: state.messages,
        files: state.files,
        mode: state.mode,
        widgetState: state.widgetState
      })
    }
  )
);
