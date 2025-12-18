"use client";

import * as React from "react";
import * as SheetPrimitive from "@radix-ui/react-dialog";
import { XIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function Sheet(
  props: React.ComponentProps<typeof SheetPrimitive.Root>
) {
  return <SheetPrimitive.Root {...props} />;
}

function SheetPortal(
  props: React.ComponentProps<typeof SheetPrimitive.Portal>
) {
  return <SheetPrimitive.Portal {...props} />;
}

function SheetOverlay(
  { className, ...props }: React.ComponentProps<typeof SheetPrimitive.Overlay>
) {
  return (
    <SheetPrimitive.Overlay
      className={cn(
        "sheet-overlay fixed inset-0 z-50 bg-black/40 backdrop-blur-sm",
        className
      )}
      {...props}
    />
  );
}

export function SheetContent({
  className,
  children,
  side = "bottom",
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Content> & {
  side?: "top" | "right" | "bottom" | "left";
}) {
  return (
    <SheetPortal>
      <SheetOverlay />

      <SheetPrimitive.Content
        data-side={side}
        className={cn(
          "sheet-content fixed z-50 flex flex-col bg-[#2d3548] text-white shadow-lg rounded-t-3xl",

          // центрирование и адаптивная ширина
          side === "bottom" &&
            "left-1/2 -translate-x-1/2 bottom-0 w-full max-w-[430px] md:max-w-[720px] lg:max-w-[960px]",

          className
        )}
        {...props}
      >
        {/* плавное появление содержимого тут */}
        <div className="sheet-inner px-4 pb-4 pt-2">{children}</div>

        <SheetPrimitive.Close className="absolute top-4 right-4 inline-flex items-center justify-center rounded-full bg-black/30 p-1 text-white opacity-70 transition hover:bg-black/50 hover:opacity-100">
          <XIcon className="w-5 h-5" />
          <span className="sr-only">Закрыть</span>
        </SheetPrimitive.Close>
      </SheetPrimitive.Content>

    </SheetPortal>
  );
}

export function SheetHeader({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div className={cn("flex flex-col gap-1.5 py-2", className)} {...props} />
  );
}

export function SheetTitle({
  className,
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Title>) {
  return (
    <SheetPrimitive.Title
      className={cn("text-foreground font-semibold text-lg", className)}
      {...props}
    />
  );
}
