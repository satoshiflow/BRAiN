// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

import { redirect } from "next/navigation";
import { auth } from "@/auth";

export default async function Home() {
  const session = await auth();
  
  if (session) {
    // Eingeloggt -> zum Dashboard
    redirect("/dashboard");
  } else {
    // Nicht eingeloggt -> zur Login-Seite
    redirect("/auth/signin");
  }
}
