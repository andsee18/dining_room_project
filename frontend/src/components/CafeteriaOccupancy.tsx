"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { BarChart3, Info, User } from "lucide-react"
import { StatisticsSheet } from "./StatisticsSheet"

// Тип для описания одного стола
interface TableData {
  id: number
  occupied: number
  capacity: number
}

// Основной компонент приложения — экран с текущей загруженностью столовой
export function CafeteriaOccupancy() {
  const [showStatistics, setShowStatistics] = useState(false) // открыта ли панель статистики
  const [lastUpdated, setLastUpdated] = useState<string>("")  // время последнего обновления
  const [isLoading, setIsLoading] = useState(true)            // имитация состояния "данные загружаются"

  // Временный мок: 15 столов с заполняемостью
  // Позже сюда будут приходить реальные данные с backend/ML
  const tables: TableData[] = [
    { id: 1, occupied: 2, capacity: 4 },
    { id: 2, occupied: 1, capacity: 4 },
    { id: 3, occupied: 3, capacity: 4 },
    { id: 4, occupied: 1, capacity: 4 },
    { id: 5, occupied: 2, capacity: 4 },
    { id: 6, occupied: 0, capacity: 4 },
    { id: 7, occupied: 2, capacity: 4 },
    { id: 8, occupied: 4, capacity: 4 },
    { id: 9, occupied: 2, capacity: 4 },
    { id: 10, occupied: 0, capacity: 4 },
    { id: 11, occupied: 3, capacity: 4 },
    { id: 12, occupied: 0, capacity: 4 },
    { id: 13, occupied: 4, capacity: 4 },
    { id: 14, occupied: 1, capacity: 4 },
    { id: 15, occupied: 2, capacity: 4 },
  ]

  // Суммарное количество мест и занятых мест
  const totalCapacity = tables.reduce((sum, table) => sum + table.capacity, 0)
  const totalOccupied = tables.reduce((sum, table) => sum + table.occupied, 0)
  const occupancyPercent =
    totalCapacity > 0 ? Math.round((totalOccupied / totalCapacity) * 100) : 0

  // Цвет фона для карточки стола в зависимости от доли занятых мест
  const getTableColor = (occupied: number, capacity: number) => {
    const ratio = occupied / capacity
    if (ratio === 0) return "bg-emerald-400/80"  // стол полностью свободен
    if (ratio < 0.5) return "bg-emerald-400/80"  // менее половины мест занято
    if (ratio < 1) return "bg-amber-300/80"      // почти заполнен
    return "bg-rose-400/80"                      // полностью заполнен
  }

  // Цвет прогресс-бара общей загрузки (те же цвета, что и у столов)
  const getProgressColor = (percent: number) => {
    if (percent < 33) return "bg-emerald-400/80" // низкая загрузка
    if (percent < 66) return "bg-amber-300/80"   // средняя
    return "bg-rose-400/80"                      // высокая
  }

  // Обновляем строку "Данные актуальны на ..." каждую минуту
  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      const hours = now.getHours().toString().padStart(2, "0")
      const minutes = now.getMinutes().toString().padStart(2, "0")
      setLastUpdated(`${hours}:${minutes}`)
    }

    updateTime() // выставляем время сразу при первом рендере
    const intervalId = setInterval(updateTime, 60_000) // раз в минуту

    return () => clearInterval(intervalId)
  }, [])

  // Имитация загрузки данных при первом открытии.
  // Потом здесь можно будет ждать реальный ответ от backend.
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false)
    }, 900) // ~0.9 секунды "загрузки"

    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="min-h-screen bg-[#1a1d29] pb-20">
      <div className="max-w-[430px] mx-auto px-4 py-6 space-y-4">

        {/* Инфо-баннер с временем последнего обновления */}
        <Card className="bg-[#2d3548]/60 border-blue-500/30 p-3">
          <div className="flex items-center gap-2 text-blue-300/90">
            <Info className="w-4 h-4 flex-shrink-0" />
            <p className="text-xs leading-relaxed">
              Данные актуальны на{" "}
              <span className="font-semibold text-blue-100">
                {lastUpdated || "—:—"}
              </span>{" "}
              и обновляются каждые 3 минуты
            </p>
          </div>
        </Card>

        {/* Заголовок и количество столов под ним */}
        <div className="text-center space-y-1">
          <h1 className="text-3xl font-bold text-white">
            Кафе «Восточное»
          </h1>
        </div>

        {/* Всего столов — теперь справа над легендой статусов */}
        <div className="text-right text-xs text-gray-400 pr-1 -mt-1 mb-1">
          Всего столов: {tables.length}
        </div>

        {/* Левая карточка — общая загрузка, правая — легенда статусов */}
        <div className="grid grid-cols-2 gap-3">
          {/* Карточка с общей загрузкой */}
          <Card className="bg-[#2d3548]/80 border-gray-700/50 p-4">
            <div className="text-center">
              {isLoading ? (
                // Скелетон во время загрузки
                <div className="flex flex-col items-center gap-3 animate-pulse">
                  <div className="h-9 w-24 rounded-md bg-slate-500/40" />
                  <div className="h-3 w-20 rounded-md bg-slate-500/30" />
                  <div className="mt-1 h-2 w-full max-w-[180px] rounded-full bg-slate-500/30" />
                </div>
              ) : (
                <>
                  <div className="text-4xl font-bold text-white mb-1">
                    {totalOccupied}/{totalCapacity}
                  </div>
                  <div className="text-gray-300 text-sm">Мест занято</div>

                  {/* Прогресс-бар */}
                  <div className="mt-3 h-2 rounded-full bg-gray-900/70 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${getProgressColor(
                        occupancyPercent
                      )}`}
                      style={{ width: `${occupancyPercent}%` }}
                    />
                  </div>

                  <div className="mt-1 text-[11px] text-gray-400">
                    Загрузка: {occupancyPercent}%
                  </div>
                </>
              )}
            </div>
          </Card>

          {/* Карточка-легенда */}
          <Card className="bg-[#2d3548]/80 border-gray-700/50 p-4">
            {isLoading ? (
              <div className="space-y-2 animate-pulse">
                <div className="h-4 w-28 rounded-md bg-slate-500/40" />
                <div className="h-4 w-32 rounded-md bg-slate-500/35" />
                <div className="h-4 w-24 rounded-md bg-slate-500/30" />
              </div>
            ) : (
              <div className="space-y-2 flex flex-col justify-center h-full">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-emerald-400/80" />
                  <span className="text-white text-sm">Свободно</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-amber-300/80" />
                  <span className="text-white text-sm">Есть места</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-rose-400/80" />
                  <span className="text-white text-sm">Занято</span>
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Карточка со схемой посадочных мест */}
        <Card className="bg-[#2d3548]/80 border-gray-700/50 p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-white">Посадочные места</h2>

            <Button
              onClick={() => setShowStatistics(true)}
              variant="ghost"
              size="icon"
              className="text-white hover:bg-white/10"
            >
              <BarChart3 className="w-5 h-5" />
            </Button>
          </div>

          {/* Сетка столов */}
          <div className="grid grid-cols-3 gap-2">
            {tables.map((table, index) => {
              const baseClasses =
                "rounded-lg p-3 flex flex-col items-center justify-center gap-1 transition-all active:scale-95"

              const colorClass = isLoading
                ? "bg-[#3a435a]/80 animate-pulse"
                : `${getTableColor(table.occupied, table.capacity)} table-appear`

              return (
                <div
                  key={table.id}
                  className={`${baseClasses} ${colorClass}`}
                  style={
                    !isLoading
                      ? { animationDelay: `${index * 60}ms` }
                      : undefined
                  }
                >
                  {isLoading ? (
                    <div className="h-4 w-10 rounded-md bg-gray-900/40" />
                  ) : (
                    <>
                      <User className="w-4 h-4 text-gray-800" />
                      <span className="text-gray-900 font-semibold text-base">
                        {table.occupied}/{table.capacity}
                      </span>
                    </>
                  )}
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      <StatisticsSheet
        open={showStatistics}
        onOpenChange={setShowStatistics}
      />
    </div>
  )
}
