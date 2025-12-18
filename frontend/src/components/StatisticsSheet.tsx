"use client"

import { useState } from "react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"

interface StatisticsSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// Дни недели, для которых у нас есть статистика
type DayOfWeek = "Пн" | "Вт" | "Ср" | "Чт" | "Пт" | "Сб"

const daysOfWeek: DayOfWeek[] = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]

// Тестовые данные загруженности по дням недели.
// Каждый массив — значения по часам (соответствуют массиву hours ниже).
const occupancyData: Record<DayOfWeek, number[]> = {
  Пн: [10, 18, 25, 35, 48, 52, 45, 30],
  Вт: [8, 15, 22, 38, 50, 58, 48, 28],
  Ср: [12, 20, 28, 40, 52, 56, 50, 32],
  Чт: [15, 22, 30, 42, 54, 60, 52, 35],
  Пт: [18, 25, 32, 45, 55, 60, 55, 38],
  Сб: [5, 10, 18, 25, 35, 42, 35, 22],
}

// Подписи по часам — ось X на графике
const hours = ["09", "10", "11", "12", "13", "14", "15", "16"]

// Выезжающая панель со статистикой загруженности по дням/часам
export function StatisticsSheet({ open, onOpenChange }: StatisticsSheetProps) {
  const [selectedDay, setSelectedDay] = useState<DayOfWeek>("Пн")

  const data = occupancyData[selectedDay]
  const maxValue = Math.max(...Object.values(occupancyData).flat())

  // Средняя загрузка за день (в процентах от максимума 60 мест)
  const avgOccupancy = Math.round(data.reduce((a, b) => a + b, 0) / data.length)
  // Час, на который приходится пик загруженности
  const peakHour = hours[data.indexOf(Math.max(...data))]
  // maxValue пока не используем в UI, но он нужен для нормировки высоты столбцов
  const peakValue = Math.max(...data) // оставлен на будущее, если захотим показать

  // Цвет столбика на графике в зависимости от процента занятости
  const getBarColor = (value: number) => {
    const percentage = (value / 60) * 100
    if (percentage < 33) return "bg-emerald-400/80"
    if (percentage < 66) return "bg-amber-300/80"
    return "bg-rose-400/80"
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="bottom"
        className="bg-[#2d3548] border-t border-gray-700/50 text-white h-[75vh] rounded-t-3xl max-w-[430px] mx-auto left-1/2 -translate-x-1/2"
      >
        <div className="px-4">
          <SheetHeader className="mb-4">
            <SheetTitle className="text-xl font-bold text-center text-white">
              Загруженность
            </SheetTitle>
          </SheetHeader>

          {/* Переключатель дней недели */}
          <div className="flex gap-1.5 justify-center mb-4 flex-wrap">
            {daysOfWeek.map((day) => (
              <Button
                key={day}
                onClick={() => setSelectedDay(day)}
                variant={selectedDay === day ? "default" : "outline"}
                size="sm"
                className={`px-3 py-1.5 rounded-lg transition-colors text-sm ${
                  selectedDay === day
                    ? "bg-[#4a5568] text-white"
                    : "bg-transparent border-gray-600 text-gray-300 hover:bg-[#3a4558] hover:text-white"
                }`}
              >
                {day}
              </Button>
            ))}
          </div>

          {/* Краткая сводка по выбранному дню */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            <div className="bg-[#1a1d29]/60 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-400 mb-1">Средняя загрузка</div>
              <div className="text-xl font-bold text-white">
                {avgOccupancy}%
              </div>
            </div>
            <div className="bg-[#1a1d29]/60 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-400 mb-1">Пик загрузки</div>
              <div className="text-xl font-bold text-white">{peakHour}:00</div>
            </div>
          </div>

          {/* Простейший "ручной" bar chart */}
          <div className="bg-[#1a1d29]/40 rounded-xl p-3">
            <div className="relative h-40">
              <div className="absolute inset-0 flex items-end justify-between gap-0.5">
                {data.map((value, index) => {
                  // Нормируем высоту столбика относительно максимального значения
                  const height = (value / maxValue) * 100
                  const percentage = Math.round((value / 60) * 100)
                  return (
                    <div
                      key={index}
                      className="flex flex-col items-center flex-1 gap-1.5"
                    >
                      <div className="relative w-full flex items-end justify-center h-32">
                        <div
                          className={`${getBarColor(
                            value
                          )} w-full rounded-t transition-all duration-300 active:opacity-80 relative group`}
                          style={{
                            height: `${height}%`,
                            minHeight: height > 0 ? "12px" : "0",
                          }}
                        >
                          {/* Подпись над столбиком: процент загруженности */}
                          <div className="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] font-semibold text-white whitespace-nowrap">
                            {percentage}%
                          </div>
                        </div>
                      </div>
                      {/* Подпись по оси X — час */}
                      <span className="text-gray-400 text-[10px] font-medium">
                        {hours[index]}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Легенда по цветам для графика */}
          <div className="flex justify-center gap-4 mt-4 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-emerald-400/80" />
              <span className="text-gray-300">&lt;33%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-amber-300/80" />
              <span className="text-gray-300">33-66%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-rose-400/80" />
              <span className="text-gray-300">&gt;66%</span>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
