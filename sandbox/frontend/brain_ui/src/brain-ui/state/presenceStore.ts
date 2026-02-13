import { create } from "zustand";

export type PresenceMode = "circle" | "avatar";
export type PresenceAffect = "neutral" | "alert" | "happy" | "thinking";

type State = {
  mode: PresenceMode;
  affect: PresenceAffect;
  isSpeaking: boolean;
  isCanvasOpen: boolean;
  activeCanvasTab: string | null;
};

type Actions = {
  setMode: (m: PresenceMode) => void;
  setAffect: (a: PresenceAffect) => void;
  setSpeaking: (s: boolean) => void;
  openCanvas: (tab?: string) => void;
  closeCanvas: () => void;
  setActiveCanvasTab: (t: string | null) => void;
  reset: () => void;
};

const initial: State = {
  mode: "circle",
  affect: "neutral",
  isSpeaking: false,
  isCanvasOpen: false,
  activeCanvasTab: "documents"
};

export const usePresenceStore = create<State & Actions>((set) => ({
  ...initial,

  setMode: (mode) => set({ mode }),
  setAffect: (affect) => set({ affect }),
  setSpeaking: (isSpeaking) => set({ isSpeaking }),

  openCanvas: (tab) =>
    set((state) => ({
      isCanvasOpen: true,
      activeCanvasTab: tab ?? state.activeCanvasTab
    })),

  closeCanvas: () => set({ isCanvasOpen: false }),

  setActiveCanvasTab: (t) => set({ activeCanvasTab: t }),

  reset: () => set(initial)
}));
