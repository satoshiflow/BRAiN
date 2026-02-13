import { redirect } from "next/navigation";

export default function SupervisorRedirect() {
  redirect("/agents/supervisor");
}
