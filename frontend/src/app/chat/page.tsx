import { AppShell } from "@/components/app-shell";
import { Chat } from "@/components/chat/chat";

export default function ChatPage() {
  return (
    <AppShell>
      <main>
        <Chat />
      </main>
    </AppShell>
  );
}
