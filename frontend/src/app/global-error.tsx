"use client"

// глобальный экран ошибок приложения
export default function GlobalError({
  error,
  reset,
}: {
  error: Error
  reset: () => void
}) {
  return (
    <html>
      {/* темный фон и центр */}
      <body className="min-h-screen bg-[#1a1d29] text-white flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center space-y-4">
          <h1 className="text-2xl font-bold">Произошла ошибка</h1>
          <p className="text-sm text-gray-300">
            Что-то пошло не так при загрузке страницы.
          </p>
          {/* кнопка повторной попытки рендера */}
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
