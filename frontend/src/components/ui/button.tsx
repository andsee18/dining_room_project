import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

// Описываем варианты кнопки (цвет, размер) через библиотеку cva.
// Это удобно: можно использовать variant/size как пропсы, а классы формируются автоматически.
const buttonVariants = cva(
  // Базовые классы для любой кнопки
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 outline-none",
  {
    variants: {
      // Варианты оформления кнопки
      variant: {
        default: "bg-primary text-primary-foreground shadow-xs hover:bg-primary/90",
        outline:
          "border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
      },
      // Варианты размеров
      size: {
        sm: "h-8 rounded-md gap-1.5 px-3",
        icon: "size-9",
      },
    },
    // Значения по умолчанию
    defaultVariants: {
      variant: "default",
      size: "sm",
    },
  }
)

// Универсальный компонент Button.
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
  // Если asChild = true — вместо <button> используем Slot (пробрасывает стили в дочерний элемент)
  const Comp = asChild ? Slot : "button"
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}
