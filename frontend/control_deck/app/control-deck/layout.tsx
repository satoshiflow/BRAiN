import { ModuleRegistryProvider } from "./ModuleRegistryProvider";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <ModuleRegistryProvider>
      {children}
    </ModuleRegistryProvider>
  );
}