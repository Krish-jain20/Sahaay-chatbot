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
