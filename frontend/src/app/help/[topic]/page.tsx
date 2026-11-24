import { redirect } from "next/navigation";

// The three old pages (complaints, scams, terms) are now sections of one Help and rights page.
export default async function OldHelpTopic({ params }: { params: Promise<{ topic: string }> }) {
  const { topic } = await params;
  redirect(["complaints", "scams", "terms"].includes(topic) ? `/help#${topic}` : "/help");
}
