import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

// shadcn/ui Button, restyled with Sahaay tokens (docs/DESIGN.md §7 Buttons).
const buttonVariants = cva(
  "inline-flex min-h-11 items-center justify-center gap-2 whitespace-nowrap rounded-full px-5 text-[15px] font-semibold transition-colors disabled:pointer-events-none disabled:bg-line disabled:text-ink-3 focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-teal-700/40 focus-visible:ring-offset-2 [&_svg]:size-5 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-teal-700 text-white hover:bg-teal-700/90",
        accent: "bg-marigold-500 text-ink hover:bg-marigold-500/90",
        secondary: "border border-line bg-surface text-ink hover:bg-bg-sunken",
        chip: "border border-teal-700 bg-surface text-teal-700 hover:bg-teal-700 hover:text-white",
        ghost: "text-ink-2 hover:bg-bg-sunken",
      },
      size: {
        default: "",
        icon: "size-11 px-0",
      },
    },
    defaultVariants: { variant: "primary", size: "default" },
  },
);

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return <Comp data-slot="button" className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}

export { Button, buttonVariants };
