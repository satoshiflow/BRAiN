/**
 * Diff Store - Apply/Reject Workflow
 * Manages code diffs from AXE suggestions
 */

import { create } from 'zustand';
import type { AxeDiff } from '../types';
import { useAxeStore } from './axeStore';

interface DiffStore {
  // ============================================================================
  // State
  // ============================================================================
  pendingDiffs: AxeDiff[];
  currentDiff: AxeDiff | null;
  diffHistory: AxeDiff[]; // Applied/rejected diffs

  // ============================================================================
  // Actions
  // ============================================================================
  addDiff: (diff: AxeDiff) => void;
  applyDiff: (diffId: string) => Promise<void>;
  rejectDiff: (diffId: string) => void;
  setCurrentDiff: (diffId: string | null) => void;
  clearDiffs: () => void;
  getDiffById: (diffId: string) => AxeDiff | null;
}

export const useDiffStore = create<DiffStore>((set, get) => ({
  // ============================================================================
  // Initial State
  // ============================================================================
  pendingDiffs: [],
  currentDiff: null,
  diffHistory: [],

  // ============================================================================
  // Add New Diff
  // ============================================================================
  addDiff: (diff) =>
    set((state) => ({
      pendingDiffs: [...state.pendingDiffs, diff],
      currentDiff: diff // Auto-select new diff
    })),

  // ============================================================================
  // Apply Diff
  // ============================================================================
  applyDiff: async (diffId) => {
    const diff = get().pendingDiffs.find((d) => d.id === diffId);
    if (!diff) return;

    // Apply changes to file in axeStore
    useAxeStore.getState().updateFile(diff.fileId, diff.newContent);

    // Mark as applied and move to history
    const appliedDiff = { ...diff, applied: true };

    set((state) => ({
      pendingDiffs: state.pendingDiffs.filter((d) => d.id !== diffId),
      diffHistory: [...state.diffHistory, appliedDiff],
      currentDiff: null
    }));

    // Log event (will be handled by EventTelemetry)
    console.log('Diff applied:', diffId);
  },

  // ============================================================================
  // Reject Diff
  // ============================================================================
  rejectDiff: (diffId) => {
    const diff = get().pendingDiffs.find((d) => d.id === diffId);
    if (!diff) return;

    // Mark as rejected and move to history
    const rejectedDiff = { ...diff, applied: false };

    set((state) => ({
      pendingDiffs: state.pendingDiffs.filter((d) => d.id !== diffId),
      diffHistory: [...state.diffHistory, rejectedDiff],
      currentDiff: null
    }));

    // Log event
    console.log('Diff rejected:', diffId);
  },

  // ============================================================================
  // Set Current Diff
  // ============================================================================
  setCurrentDiff: (diffId) => {
    if (!diffId) {
      set({ currentDiff: null });
      return;
    }

    const diff = get().pendingDiffs.find((d) => d.id === diffId);
    if (diff) {
      set({ currentDiff: diff });
    }
  },

  // ============================================================================
  // Clear All Diffs
  // ============================================================================
  clearDiffs: () =>
    set({
      pendingDiffs: [],
      currentDiff: null
    }),

  // ============================================================================
  // Get Diff by ID
  // ============================================================================
  getDiffById: (diffId) => {
    const pending = get().pendingDiffs.find((d) => d.id === diffId);
    if (pending) return pending;

    const history = get().diffHistory.find((d) => d.id === diffId);
    return history || null;
  }
}));
