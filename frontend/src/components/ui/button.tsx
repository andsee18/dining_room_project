import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

// варианты кнопки через варианты классов
const buttonVariants = cva(
  // базовые классы кнопки тут
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 outline-none",
  {
    variants: {
      // варианты оформления кнопки тут
      variant: {
        default: "bg-primary text-primary-foreground shadow-xs hover:bg-primary/90",
        outline:
          "border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
      },
      // варианты размеров кнопки тут
      size: {
        sm: "h-8 rounded-md gap-1.5 px-3",
        icon: "size-9",
      },
    },
    // дефолтные варианты кнопки тут
    defaultVariants: {
      variant: "default",
      size: "sm",
    },
  }
)

// компонент кнопки для интерфейса
export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  // слот вместо кнопки тут
  const Comp = asChild ? Slot : "button"
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}
