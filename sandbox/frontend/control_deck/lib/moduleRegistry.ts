export type UIModuleRoute = {
  path: string;
  label: string;
  icon?: string;
};

export type UIModuleManifest = {
  name: string;
  label: string;
  category?: string;
  routes: UIModuleRoute[];
};

export async function fetchModuleManifests(): Promise<UIModuleManifest[]> {
  const res = await fetch("/api/modules/ui-manifests");
  if (!res.ok) {
    throw new Error("Failed to load module manifests");
  }
  return res.json();
}