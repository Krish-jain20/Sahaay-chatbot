import { LanguageSwitch } from "@/components/language-switch";
import { Logo } from "@/components/logo";

export function TopBar() {
  return (
    <header className="sticky top-0 z-10 border-b border-line bg-bg/95 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-2">
        <Logo />
        <LanguageSwitch />
      </div>
    </header>
  );
}

export function Disclaimer({ text }: { text: string }) {
  return <p className="text-center text-[12.5px] text-ink-3">{text}</p>;
}
