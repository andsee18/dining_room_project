"use client"

import { useEffect, useMemo, useState } from "react"
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

// список дней недели тут
type DayOfWeek = "Пн" | "Вт" | "Ср" | "Чт" | "Пт" | "Сб"

const daysOfWeek: DayOfWeek[] = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]

interface BackendWeeklyStats {
  days: DayOfWeek[]
  hours: string[]
  occupancy: Record<DayOfWeek, number[]>
  total_capacity?: number
}

function getBackendBaseUrl() {
  let url = (process.env.NEXT_PUBLIC_BACKEND_URL || "").trim()
  if (!url) url = "http://127.0.0.1:8000"

  // допускаем адрес без схемы
  if (!/^https?:\/\//i.test(url)) {
    url = `http://${url}`
  }

  // убираем лишние слеши в конце
  url = url.replace(/\/+$/, "")
  return url
}

function createEmptyOccupancy(hoursCount: number): Record<DayOfWeek, number[]> {
  return {
    Пн: Array.from({ length: hoursCount }, () => 0),
    Вт: Array.from({ length: hoursCount }, () => 0),
    Ср: Array.from({ length: hoursCount }, () => 0),
    Чт: Array.from({ length: hoursCount }, () => 0),
    Пт: Array.from({ length: hoursCount }, () => 0),
    Сб: Array.from({ length: hoursCount }, () => 0),
  }
}

// выезжающая панель статистики дней
export function StatisticsSheet({ open, onOpenChange }: StatisticsSheetProps) {
  const [selectedDay, setSelectedDay] = useState<DayOfWeek>("Пн")

  const [hours, setHours] = useState<string[]>(["09", "10", "11", "12", "13", "14", "15", "16"])
  const [occupancyData, setOccupancyData] = useState<Record<DayOfWeek, number[]>>(
    createEmptyOccupancy(8)
  )
  const [totalCapacity, setTotalCapacity] = useState<number>(54)

  useEffect(() => {
    const abortController = new AbortController()
    const backendBaseUrl = getBackendBaseUrl()

    const load = async () => {
      try {
        const response = await fetch(
          `${backendBaseUrl}/api/stats/weekly?days_back=30&start_hour=0&end_hour=23`,
          {
          signal: abortController.signal,
          }
        )
        if (!response.ok) return
        const json = (await response.json()) as BackendWeeklyStats

        if (Array.isArray(json.hours) && json.hours.length > 0) {
          setHours(json.hours)
        }

        if (typeof json.total_capacity === "number" && Number.isFinite(json.total_capacity)) {
          setTotalCapacity(json.total_capacity)
        }

        if (json.occupancy) {
          // дополняем отсутствующие дни тут
          const hoursCount = (json.hours && json.hours.length) || 8
          setOccupancyData({
            ...createEmptyOccupancy(hoursCount),
            ...json.occupancy,
          })
        }
      } catch {
        // игнорируем ошибку запроса тут
      }
    }

    load()
    return () => abortController.abort()
  }, [])

  const data = occupancyData[selectedDay]
  const maxValue = useMemo(() => {
    const all = Object.values(occupancyData).flat()
    const m = all.length ? Math.max(...all) : 0
    return m > 0 ? m : 1
  }, [occupancyData])

  // считаем среднюю загрузку дня
  const avgSeats = data.length ? data.reduce((a, b) => a + b, 0) / data.length : 0
  const avgOccupancyPercent = Math.round((avgSeats / totalCapacity) * 100)
  // час максимальной загрузки дня
  const peakHour = hours[data.indexOf(Math.max(...data))]
  const peakValue = Math.max(...data)

  // цвет столбика по загрузке
  const getBarColor = (value: number) => {
    const percentage = (value / totalCapacity) * 100
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

          {/* выбор дня недели тут */}
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

          {/* сводка по дню тут */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            <div className="bg-[#1a1d29]/60 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-400 mb-1">Средняя загрузка</div>
              <div className="text-xl font-bold text-white">
                {avgOccupancyPercent}%
              </div>
            </div>
            <div className="bg-[#1a1d29]/60 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-400 mb-1">Пик загрузки</div>
              <div className="text-xl font-bold text-white">{peakHour}:00</div>
            </div>
          </div>

          {/* график по часам тут */}
          <div className="bg-[#1a1d29]/40 rounded-xl p-3">
            <div className="relative h-40">
              <div className="absolute inset-0 flex items-end justify-between gap-0.5">
                {data.map((value, index) => {
                  // нормируем высоту столбика тут
                  const height = (value / maxValue) * 100
                  const percentage = Math.round((value / totalCapacity) * 100)
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
                          {/* подпись процента над столбиком */}
                          <div className="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] font-semibold text-white whitespace-nowrap">
                            {percentage}%
                          </div>
                        </div>
                      </div>
                      {/* подпись часа под столбиком */}
                      <span className="text-gray-400 text-[10px] font-medium">
                        {hours[index]}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* легенда цветов для графика */}
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
