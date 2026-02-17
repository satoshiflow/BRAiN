"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import type { UIModuleManifest } from "@/lib/moduleRegistry";
import { fetchModuleManifests } from "@/lib/moduleRegistry";

type Ctx = {
  modules: UIModuleManifest[];
  loading: boolean;
  error?: string;
};

const ModuleRegistryContext = createContext<Ctx>({
  modules: [],
  loading: true,
});

export const useModuleRegistry = () => useContext(ModuleRegistryContext);

export const ModuleRegistryProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [state, setState] = useState<Ctx>({ modules: [], loading: true });

  useEffect(() => {
    fetchModuleManifests()
      .then((modules) => setState({ modules, loading: false }))
      .catch((err) =>
        setState({ modules: [], loading: false, error: String(err) }),
      );
  }, []);

  return (
    <ModuleRegistryContext.Provider value={state}>
      {children}
    </ModuleRegistryContext.Provider>
  );
};