import { AppShell } from "@/components/app-shell";
import { Hero } from "@/components/home/hero";
import { HowItWorks } from "@/components/home/how-it-works";
import { PopularServices } from "@/components/home/popular-services";
import { SiteFooter } from "@/components/home/site-footer";
import { ToolsGrid } from "@/components/home/tools-grid";
import { Trust } from "@/components/home/trust";

export default function Home() {
  return (
    <AppShell wide>
      <main className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-10">
        <Hero />
        <HowItWorks />
        <ToolsGrid />
        <PopularServices />
        <Trust />
      </main>
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-10">
        <SiteFooter />
      </div>
    </AppShell>
  );
}
