import type { Metadata } from "next"
import "./globals.css"

// Метаданные страницы: заголовок вкладки и описание для поисковиков / превью
export const metadata: Metadata = {
  title: "Кафе «Восточное»",
  description: "Мониторинг загруженности столовой",
}

// Общий layout для приложения.
// Здесь подключаем глобальные стили и задаём общую разметку html/body.
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="ru">
      {/* antialiased — сглаживание шрифтов, фон задаём здесь один раз */}
      <body className="antialiased bg-[#1a1d29]">
        {children}
      </body>
    </html>
  )
}
