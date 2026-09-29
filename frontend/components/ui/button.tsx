"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const variantStyles = {
  default:
    "bg-blue-600 hover:bg-blue-500 text-white shadow-sm shadow-blue-600/20",
  outline:
    "border border-[var(--color-border)] bg-transparent hover:bg-[var(--color-card)] text-[var(--color-foreground)]",
  ghost: "hover:bg-[var(--color-card)] text-[var(--color-foreground)]",
  destructive:
    "bg-rose-600 hover:bg-rose-500 text-white shadow-sm shadow-rose-600/20",
} as const;

const sizeStyles = {
  sm: "h-8 px-3 text-xs gap-1.5",
  default: "h-9 px-4 text-sm gap-2",
  lg: "h-11 px-6 text-base gap-2.5",
} as const;

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variantStyles;
  size?: keyof typeof sizeStyles;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-lg font-medium transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-background)]",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "active:scale-[0.98]",
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
