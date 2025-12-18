import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

// Утилита для объединения классов.
// Сначала склеиваем классы через clsx, потом twMerge убирает конфликты Tailwind
// (например, если случайно задать два разных padding'а).
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
