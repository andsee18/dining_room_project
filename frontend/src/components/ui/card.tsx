import * as React from "react"
import { cn } from "@/lib/utils"

// компонент карточки для интерфейса
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
