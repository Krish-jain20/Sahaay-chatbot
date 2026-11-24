// Inline stroke icons: 24px viewBox, 2px stroke, round caps, currentColor (docs/DESIGN.md §6).
type P = { className?: string };
const base = {
  width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
  strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true,
};
export const CheckIcon = ({ className }: P) => <svg {...base} className={className}><path d="M5 12l5 5 9-10" /></svg>;
export const XIcon = ({ className }: P) => <svg {...base} className={className}><path d="M6 6l12 12M18 6L6 18" /></svg>;
export const HelpIcon = ({ className }: P) => (
  <svg {...base} className={className}><circle cx="12" cy="12" r="9" /><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17h.01" /></svg>
);
export const ShieldCheckIcon = ({ className }: P) => (
  <svg {...base} className={className}><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /><path d="M8.5 12l2.5 2.5 4.5-5" /></svg>
);
export const AlertIcon = ({ className }: P) => (
  <svg {...base} className={className}><path d="M12 3l9.5 17h-19z" /><path d="M12 10v4M12 17h.01" /></svg>
);
export const SendIcon = ({ className }: P) => <svg {...base} className={className}><path d="M4 12l16-8-6 16-2.5-6.5z" /></svg>;
export const StopIcon = ({ className }: P) => <svg {...base} className={className}><rect x="6" y="6" width="12" height="12" rx="2" /></svg>;
export const LinkIcon = ({ className }: P) => (
  <svg {...base} className={className}><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" /></svg>
);
export const ChevronDownIcon = ({ className }: P) => <svg {...base} className={className}><path d="M6 9l6 6 6-6" /></svg>;
export const ChatIcon = ({ className }: P) => (
  <svg {...base} className={className}><path d="M4 5h16v11H9l-5 4z" /><path d="M8 9.5h8M8 12.5h5" /></svg>
);
export const ScaleIcon = ({ className }: P) => (
  <svg {...base} className={className}><path d="M12 4v16M6 20h12M5 8h14" /><path d="M5 8l-3 6a3.5 3.5 0 0 0 6 0zM19 8l-3 6a3.5 3.5 0 0 0 6 0z" /></svg>
);
export const FileIcon = ({ className }: P) => (
  <svg {...base} className={className}><path d="M6 3h8l5 5v13H6z" /><path d="M14 3v5h5M9 13h7M9 17h5" /></svg>
);
export const PenIcon = ({ className }: P) => (
  <svg {...base} className={className}><path d="M4 20l1-4L16.5 4.5a2.1 2.1 0 0 1 3 3L8 19z" /><path d="M14.5 6.5l3 3" /></svg>
);
export const ClipboardIcon = ({ className }: P) => (
  <svg {...base} className={className}><rect x="6" y="4" width="12" height="17" rx="2" /><path d="M9 4h6v3H9zM9 12h6M9 16h4" /></svg>
);
export const FolderIcon = ({ className }: P) => (
  <svg {...base} className={className}><path d="M3 6.5A1.5 1.5 0 0 1 4.5 5H10l2 2.5h7.5A1.5 1.5 0 0 1 21 9v9.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z" /></svg>
);
export const LifebuoyIcon = ({ className }: P) => (
  <svg {...base} className={className}><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="3.5" /><path d="M5.6 5.6l3.9 3.9M14.5 14.5l3.9 3.9M18.4 5.6l-3.9 3.9M9.5 14.5l-3.9 3.9" /></svg>
);
export const LockIcon = ({ className }: P) => (
  <svg {...base} className={className}><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3M12 15v2" /></svg>
);
export const ArrowRightIcon = ({ className }: P) => <svg {...base} className={className}><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
export const BookmarkCheckIcon = ({ className }: P) => (
  <svg {...base} className={className}><path d="M6 4h12v17l-6-4-6 4z" /><path d="M9 10l2 2 4-4" /></svg>
);
