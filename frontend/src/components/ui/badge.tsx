import * as React from "react";
import { Slot } from "@radix-ui/react-slot@1.1.2";
import { cva, type VariantProps } from "class-variance-authority@0.7.1";

import { cn } from "./utils";

const badgeVariants = cva(
  "inline-flex items-center justify-center rounded-md border px-2 py-0.5 text-xs font-medium w-fit whitespace-nowrap shrink-0 [&>svg]:size-3 gap-1 [&>svg]:pointer-events-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive transition-[color,box-shadow] overflow-hidden",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground [a&]:hover:bg-primary/90",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground [a&]:hover:bg-secondary/90",
        destructive:
          "border-transparent bg-destructive text-white [a&]:hover:bg-destructive/90 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40 dark:bg-destructive/60",
        outline:
          "[a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

const colorMap: Record<string, string> = {
  red: "border-red-200 bg-red-100 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300",
  orange: "border-orange-200 bg-orange-100 text-orange-700 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-300",
  yellow: "border-yellow-200 bg-yellow-100 text-yellow-700 dark:border-yellow-800 dark:bg-yellow-950 dark:text-yellow-300",
  green: "border-green-200 bg-green-100 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300",
  teal: "border-teal-200 bg-teal-100 text-teal-700 dark:border-teal-800 dark:bg-teal-950 dark:text-teal-300",
  blue: "border-blue-200 bg-blue-100 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300",
  purple: "border-purple-200 bg-purple-100 text-purple-700 dark:border-purple-800 dark:bg-purple-950 dark:text-purple-300",
  pink: "border-pink-200 bg-pink-100 text-pink-700 dark:border-pink-800 dark:bg-pink-950 dark:text-pink-300",
  gray: "border-gray-200 bg-gray-100 text-gray-700 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300",
};

function Badge({
  className,
  variant,
  color,
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & {
    asChild?: boolean;
    color?: string;
  }) {
  const Comp = asChild ? Slot : "span";

  return (
    <Comp
      data-slot="badge"
      className={cn(
        badgeVariants({ variant: color ? "outline" : variant }),
        !color && variant === "outline" && "text-foreground",
        color && colorMap[color],
        className,
      )}
      {...props}
    />
  );
}

export { Badge, badgeVariants };
