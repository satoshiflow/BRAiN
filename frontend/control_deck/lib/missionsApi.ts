const API_BASE =
  process.env.NEXT_PUBLIC_BRAIN_API_URL ?? "http://localhost:8000";

export type MissionStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | string;

export type Mission = {
  id: string;
  name: string;
  description?: string | null;
  status: MissionStatus;
  created_at?: string;
  updated_at?: string;
};

type RawMission = any;

function mapMission(raw: RawMission): Mission {
  return {
    id: String(raw.id ?? raw.mission_id ?? ""),
    name: String(raw.name ?? raw.title ?? "Unnamed Mission"),
    description:
      typeof raw.description === "string" ? raw.description : null,
    status: String(raw.status ?? "PENDING"),
    created_at: raw.created_at ?? raw.createdAt ?? undefined,
    updated_at: raw.updated_at ?? raw.updatedAt ?? undefined,
  };
}

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    const short = text.length > 200 ? text.slice(0, 200) + "…" : text;
    throw new Error(`Request failed: ${res.status} ${res.statusText} – ${short}`);
  }
  return (await res.json()) as T;
}

export async function fetchMissions(): Promise<Mission[]> {
  const res = await fetch(`${API_BASE}/api/missions`, {
    cache: "no-store",
  });
  const data = await handleJson<RawMission[]>(res);
  return Array.isArray(data) ? data.map(mapMission) : [];
}

export async function createMission(payload: {
  name: string;
  description?: string;
}): Promise<Mission> {
  const res = await fetch(`${API_BASE}/api/missions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await handleJson<RawMission>(res);
  return mapMission(data);
}

export async function updateMissionStatus(
  missionId: string,
  status: MissionStatus,
): Promise<Mission> {
  const res = await fetch(
    `${API_BASE}/api/missions/${encodeURIComponent(missionId)}/status`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    },
  );
  const data = await handleJson<RawMission>(res);
  return mapMission(data);
}