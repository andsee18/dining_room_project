"use client"

// Глобальный компонент для отображения ошибок уровня приложения.
// Next.js будет показывать эту страницу, если на уровне всего роута случилась ошибка.
export default function GlobalError({
  error,
  reset,
}: {
  error: Error
  reset: () => void
}) {
  return (
    <html>
      {/* Простой тёмный фон + выравнивание блока ошибки по центру экрана */}
      <body className="min-h-screen bg-[#1a1d29] text-white flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center space-y-4">
          <h1 className="text-2xl font-bold">Произошла ошибка</h1>
          <p className="text-sm text-gray-300">
            Что-то пошло не так при загрузке страницы.
          </p>
          {/* Кнопка "Попробовать ещё раз" — вызывает reset(), который даёт Next.js
              ещё одну попытку заново отрендерить страницу */}
          <button
            onClick={() => reset()}
            className="mt-2 rounded-md bg-white/10 px-4 py-2 text-sm hover:bg-white/20"
          >
            Попробовать ещё раз
          </button>
        </div>
      </body>
    </html>
  )
}
