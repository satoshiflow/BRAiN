import { LandingPage } from "@/components/LandingPage";
import { getInitialLang } from "@/content/i18n";

export default function Page({ searchParams }: { searchParams?: Record<string, any> }) {
  const initialLang = getInitialLang(searchParams);
  return <LandingPage initialLang={initialLang} />;
}
