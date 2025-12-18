"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { BarChart3, Info, User } from "lucide-react"
import { StatisticsSheet } from "./StatisticsSheet"
import { formatLastUpdate, getBackendBaseUrl, toWebSocketBaseUrl } from "@/lib/backend"

// тип данных одного стола
interface TableData {
  id: number
  occupied: number
  capacity: number
  statusColor?: "green" | "yellow" | "red"
}
// тип данных от бекенда
interface BackendTable {
  table_id: number
  occupied: number
  capacity: number
  status_color: "green" | "yellow" | "red"
}

interface BackendDetailedStatus {
  overall_inside: number
  total_capacity: number
  tables: BackendTable[]
  last_update: string
}

// главный экран занятости столов
export function CafeteriaOccupancy() {
  const [showStatistics, setShowStatistics] = useState(false) // панель статистики открыта тут
  const [lastUpdated, setLastUpdated] = useState<string>("") // время последнего обновления тут
  const [isLoading, setIsLoading] = useState(true)
  const [tables, setTables] = useState<TableData[]>([]) // данные столов тут

  // показываем столы 1 18
  const visibleTables = tables.filter((t) => t.id >= 1 && t.id <= 18)
  const tableById = new Map<number, TableData>(visibleTables.map((t) => [t.id, t]))
  const layoutRows: Array<{ leftId: number | null; rightId: number | null }> = Array.from(
    { length: 10 },
    (_, i) => {
      const rowIndex = i + 1
      const rightId = rowIndex
      const leftId = rowIndex >= 2 && rowIndex <= 9 ? rowIndex + 9 : null
      return { leftId, rightId }
    }
  )

  const renderTile = (table: TableData | undefined, key: string, animationIndex: number) => {
    const baseClasses =
      "rounded-lg p-3 flex flex-col items-center justify-center gap-1 transition-all active:scale-95"

    const colorClass = isLoading
      ? "bg-[#3a435a]/80 animate-pulse"
      : table
      ? `${getTableColor(table)} table-appear`
      : "bg-[#3a435a]/80"

    return (
      <div
        key={key}
        className={`${baseClasses} ${colorClass}`}
        style={!isLoading ? { animationDelay: `${animationIndex * 60}ms` } : undefined}
      >
        {isLoading || !table ? (
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
  }

  // считаем общую загрузку мест
  const totalCapacity = visibleTables.reduce((sum, table) => sum + table.capacity, 0)
  const totalOccupied = visibleTables.reduce((sum, table) => sum + table.occupied, 0)
  const occupancyPercent =
    totalCapacity > 0 ? Math.round((totalOccupied / totalCapacity) * 100) : 0

  // цвет карточки по статусу
  const getTableColor = (table: TableData) => {
    if (table.statusColor === "green") return "bg-emerald-400/80"
    if (table.statusColor === "yellow") return "bg-amber-300/80"
    if (table.statusColor === "red") return "bg-rose-400/80"

    const ratio = table.capacity > 0 ? table.occupied / table.capacity : 0
    if (ratio === 0) return "bg-emerald-400/80"
    if (ratio < 0.5) return "bg-emerald-400/80"
    if (ratio < 1) return "bg-amber-300/80"
    return "bg-rose-400/80"
  }

  // цвет полосы общей загрузки
  const getProgressColor = (percent: number) => {
    if (percent < 33) return "bg-emerald-400/80"
    if (percent < 66) return "bg-amber-300/80"
    return "bg-rose-400/80"
  }

  // загрузка по хттп и вебсокет
  useEffect(() => {
    // СВЯЗЬ ФРОНТЕНДА И БЕКЕНДА: ФОРМИРОВАНИЕ URL
    const backendBaseUrl = getBackendBaseUrl()
    const abortController = new AbortController()
    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let pollingTimer: ReturnType<typeof setInterval> | null = null
    let reconnectAttempt = 0
    let wsConnected = false

    const applyStatus = (payload: BackendDetailedStatus) => {
      setTables(
        (payload.tables || []).map((t) => ({
          id: t.table_id,
          occupied: t.occupied,
          capacity: t.capacity,
          statusColor: t.status_color,
        }))
      )
      setLastUpdated(formatLastUpdate(payload.last_update))
      setIsLoading(false)
    }

    // СВЯЗЬ ФРОНТЕНДА И БЕКЕНДА: HTTP FETCH
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${backendBaseUrl}/api/status/detailed`, {
          signal: abortController.signal,
          cache: "no-store",
        })
        if (!response.ok) return
        const json = (await response.json()) as BackendDetailedStatus
        applyStatus(json)
      } catch {
        // игнорируем ошибку запроса тут
      }
    }

    const scheduleReconnect = () => {
      if (abortController.signal.aborted) return
      if (reconnectTimer) return

      // пауза растет до лимита
      const delay = Math.min(10000, 1000 * Math.pow(2, reconnectAttempt))
      reconnectAttempt += 1

      reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        connectWs()
      }, delay)
    }

    // СВЯЗЬ ФРОНТЕНДА И БЕКЕНДА: WEBSOCKET
    const connectWs = () => {
      try {
        wsConnected = false
        ws = new WebSocket(`${toWebSocketBaseUrl(backendBaseUrl)}/ws/status`)

        ws.onmessage = (event) => {
          try {
            const json = JSON.parse(event.data) as BackendDetailedStatus
            applyStatus(json)
          } catch {
            // игнорируем битый кадр тут
          }
        }

        ws.onopen = () => {
          wsConnected = true
          reconnectAttempt = 0
          // отправляем пинг для канала
          try {
            ws?.send("ping")
          } catch {
            // игнорируем ошибку отправки тут
          }
        }

        ws.onclose = () => {
          wsConnected = false
          scheduleReconnect()
        }

        ws.onerror = () => {
          // ошибка сокета без паники
          wsConnected = false
        }
      } catch {
        // игнорируем ошибку сокета тут
      }
    }

    fetchStatus()
    connectWs()

    // опрос если сокет молчит
    pollingTimer = setInterval(() => {
      if (abortController.signal.aborted) return
      if (wsConnected) return
      fetchStatus()
    }, 3000)

    return () => {
      abortController.abort()
      try {
        ws?.close()
      } catch {
        // игнорируем ошибку закрытия тут
      }

      if (pollingTimer) clearInterval(pollingTimer)
      if (reconnectTimer) clearTimeout(reconnectTimer)
    }
  }, [])

  return (
    <div className="min-h-screen bg-[#1a1d29] pb-20">
      <div className="max-w-[430px] mx-auto px-4 py-6 space-y-4">

        {/* инфо баннер про обновление */}
        <Card className="bg-[#2d3548]/60 border-blue-500/30 p-3">
          <div className="flex items-center gap-2 text-blue-300/90">
            <Info className="w-4 h-4 flex-shrink-0" />
            <p className="text-xs leading-relaxed">
              Данные актуальны на{" "}
              <span className="font-semibold text-blue-100">
                {lastUpdated || "—:—"}
              </span>{" "}
              и обновляются автоматически
            </p>
          </div>
        </Card>

        {/* заголовок приложения по центру */}
        <div className="text-center space-y-1">
          <h1 className="text-3xl font-bold text-white">
            Кафе «Восточное»
          </h1>
        </div>

        {/* количество столов для справки */}
        <div className="text-right text-xs text-gray-400 pr-1 -mt-1 mb-1">
          Всего столов: {visibleTables.length}
        </div>

        {/* карточки загрузки и легенды */}
        <div className="grid grid-cols-2 gap-3">
          {/* карточка общей загрузки тут */}
          <Card className="bg-[#2d3548]/80 border-gray-700/50 p-4">
            <div className="text-center">
              {isLoading ? (
                // скелетон при загрузке тут
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

                  {/* прогресс бар общей загрузки */}
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

          {/* карточка легенды статусов тут */}
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

        {/* карточка схемы столов тут */}
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

          {/* сетка столов по схеме */}
          <div className="grid grid-cols-2 gap-3">
            {layoutRows.flatMap((row, rowIndex) => {
              const animationBase = rowIndex * 2

              const left =
                row.leftId === null
                  ? [
                      <div key={`empty-left-${rowIndex}`} aria-hidden="true" />,
                    ]
                  : [
                      renderTile(
                        tableById.get(row.leftId),
                        `left-${row.leftId}`,
                        animationBase
                      ),
                    ]

              const right =
                row.rightId === null
                  ? [
                      <div key={`empty-right-${rowIndex}`} aria-hidden="true" />,
                    ]
                  : [
                      renderTile(
                        tableById.get(row.rightId),
                        `right-${row.rightId}`,
                        animationBase + 1
                      ),
                    ]

              // порядок левый потом правый
              return [...left, ...right]
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
