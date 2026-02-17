import { redirect } from "next/navigation";
import { signOut } from "@/auth";

export default async function SignOutPage() {
  await signOut({ redirectTo: "/auth/signin" });
  redirect("/auth/signin");
}
