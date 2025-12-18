import * as React from "react"
import { cn } from "@/lib/utils"

// Простой компонент Card — обёртка с фоном, рамкой и скруглением.
// Используем для всех карточек интерфейса (баннер, статистика, легенда и т.д.).
export function Card({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "bg-card text-card-foreground rounded-xl border shadow-sm",
        className
      )}
      {...props}
    />
  )
}
