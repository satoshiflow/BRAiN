// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import { redirect } from "next/navigation";

export default function FleetManagementPage() {
  redirect("/fleet");
}
