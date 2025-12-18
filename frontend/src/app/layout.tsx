import type { Metadata } from "next"
import "./globals.css"

// метаданные страницы для сео
export const metadata: Metadata = {
  title: "Кафе «Восточное»",
  description: "Мониторинг загруженности столовой",
}

// общий лэйаут для приложения
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="ru">
      {/* сглаживание текста и фон */}
      <body className="antialiased bg-[#1a1d29]">
        {children}
      </body>
    </html>
  )
}
