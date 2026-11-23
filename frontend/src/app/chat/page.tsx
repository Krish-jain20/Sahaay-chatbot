import { Chat } from "@/components/chat/chat";
import { TopBar } from "@/components/top-bar";

export default function ChatPage() {
  return (
    <>
      <TopBar />
      <main>
        <Chat />
      </main>
    </>
  );
}
