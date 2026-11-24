import {
  BagIcon,
  BoltIcon,
  BuildingIcon,
  CapIcon,
  DropIcon,
  FileIcon,
  LockIcon,
  PenIcon,
  ReceiptIcon,
  ScaleIcon,
  SendIcon,
  ShieldCheckIcon,
  UsersIcon,
} from "@/components/icons";

const MAP: Record<string, (p: { className?: string }) => React.ReactElement> = {
  pen: PenIcon,
  file: FileIcon,
  cap: CapIcon,
  users: UsersIcon,
  bag: BagIcon,
  scale: ScaleIcon,
  send: SendIcon,
  bolt: BoltIcon,
  drop: DropIcon,
  receipt: ReceiptIcon,
  shield: ShieldCheckIcon,
  lock: LockIcon,
  building: BuildingIcon,
};

export function DraftIcon({ name, className }: { name: string; className?: string }) {
  const Icon = MAP[name] ?? PenIcon;
  return <Icon className={className} />;
}
