import { cleanup, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { CafeteriaOccupancy } from "../CafeteriaOccupancy"

type BackendDetailedStatus = {
  overall_inside: number
  total_capacity: number
  tables: Array<{
    table_id: number
    occupied: number
    capacity: number
    status_color: "green" | "yellow" | "red"
  }>
  last_update: string
}

class FakeWebSocket {
  static instances: FakeWebSocket[] = []

  url: string
  onopen: ((event: unknown) => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: ((event: unknown) => void) | null = null

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
    queueMicrotask(() => this.onopen?.({}))
  }

  send() {
    // пустая отправка для теста
  }

  close() {
    this.onclose?.({})
  }
}

class FakeWebSocketNeverOpen {
  static instances: FakeWebSocketNeverOpen[] = []

  url: string
  onopen: ((event: unknown) => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: ((event: unknown) => void) | null = null

  constructor(url: string) {
    this.url = url
    FakeWebSocketNeverOpen.instances.push(this)
  }

  send() {
    // пустая отправка для теста
  }

  close() {
    this.onclose?.({})
  }
}

describe("CafeteriaOccupancy", () => {
  beforeEach(() => {
    FakeWebSocket.instances = []
    FakeWebSocketNeverOpen.instances = []
    process.env.NEXT_PUBLIC_BACKEND_URL = ""
    ;(globalThis as unknown as { WebSocket: unknown }).WebSocket = FakeWebSocket
  })

  afterEach(() => {
    // тесты независимы друг от друга
    try {
      vi.useRealTimers()
    } catch {
      // игнорируем ошибку таймеров тут
    }
    vi.clearAllMocks()
    cleanup()
  })

  // рендер количества столов из backend
  it("renders tables count from backend fetch", async () => {
    const payload: BackendDetailedStatus = {
      overall_inside: 3,
      total_capacity: 6,
      tables: [
        { table_id: 1, occupied: 0, capacity: 3, status_color: "green" },
        { table_id: 2, occupied: 3, capacity: 3, status_color: "red" },
      ],
      last_update: "2025-12-16 12:34:56",
    }

    ;(globalThis as unknown as { fetch: unknown }).fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })

    render(<CafeteriaOccupancy />)

    await waitFor(() => {
      expect(screen.getByText(/Всего столов:/)).toBeInTheDocument()
    })

    expect(screen.getByText(/Всего столов:\s*2/)).toBeInTheDocument()
  })

  // рендер при ошибке backend
  it("renders basic shell even when backend fetch fails", () => {
    ;(globalThis as unknown as { fetch: unknown }).fetch = vi.fn().mockRejectedValue(new Error("fail"))

    render(<CafeteriaOccupancy />)

    expect(screen.getByRole("heading", { name: "Кафе «Восточное»" })).toBeInTheDocument()
    expect(screen.getByText(/Данные актуальны на/)).toBeInTheDocument()
    expect(screen.getByText("—:—")).toBeInTheDocument()
  })

  // построение websocket url
  it("builds WebSocket URL from NEXT_PUBLIC_BACKEND_URL without scheme", async () => {
    process.env.NEXT_PUBLIC_BACKEND_URL = "127.0.0.1:8123"

    const payload: BackendDetailedStatus = {
      overall_inside: 0,
      total_capacity: 3,
      tables: [{ table_id: 1, occupied: 0, capacity: 3, status_color: "green" }],
      last_update: "2025-12-16 12:00:00",
    }

    //HTTP FETCH
    ;(globalThis as unknown as { fetch: unknown }).fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })

    render(<CafeteriaOccupancy />)

    await screen.findByText(/Всего столов:\s*1/)

    // WEBSOCKET
    const ws = FakeWebSocket.instances[0]
    expect(ws).toBeTruthy()
    expect(ws.url).toBe("ws://127.0.0.1:8123/ws/status")
  })

  // wss если backend https
  it("uses wss:// when backend base url is https://", async () => {
    process.env.NEXT_PUBLIC_BACKEND_URL = "https://example.com:8443/"

    const payload: BackendDetailedStatus = {
      overall_inside: 0,
      total_capacity: 3,
      tables: [{ table_id: 1, occupied: 0, capacity: 3, status_color: "green" }],
      last_update: "2025-12-16 12:00:00",
    }

    ;(globalThis as unknown as { fetch: unknown }).fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })

    render(<CafeteriaOccupancy />)

    await screen.findByText(/Всего столов:\s*1/)

    // EBSOCKET
    const ws = FakeWebSocket.instances[0]
    expect(ws).toBeTruthy()
    expect(ws.url).toBe("wss://example.com:8443/ws/status")
  })

  // не перераспределяет места на клиенте
  it("does not apply client-side redistribution (shows 5/3 as-is)", async () => {
    const payload: BackendDetailedStatus = {
      overall_inside: 5,
      total_capacity: 3,
      tables: [{ table_id: 1, occupied: 5, capacity: 3, status_color: "red" }],
      last_update: "2025-12-16 12:00:00",
    }

    ;(globalThis as unknown as { fetch: unknown }).fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })

    render(<CafeteriaOccupancy />)

    // ждем рендер счетчика столов
    await screen.findByText(/Всего столов:\s*1/)

    // значение внутри элемента спан
    expect(screen.getByText("5/3", { selector: "span" })).toBeInTheDocument()
  })

  // рендер схемы посадки 20 ячеек
  it("renders seating layout with 20 cells and 2 empty placeholders", async () => {
    const tables: BackendDetailedStatus["tables"] = Array.from({ length: 18 }, (_, i) => {
      const id = i + 1
      return { table_id: id, occupied: id % 3, capacity: 3, status_color: "green" as const }
    })

    const payload: BackendDetailedStatus = {
      overall_inside: 0,
      total_capacity: 54,
      tables,
      last_update: "2025-12-16 12:00:00",
    }

    // СВЯЗЬ ФРОНТЕНДА И БЕКЕНДА: HTTP FETCH
    ;(globalThis as unknown as { fetch: unknown }).fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })

    const { container } = render(<CafeteriaOccupancy />)

    await screen.findByText(/Всего столов:\s*18/)

    const seatingHeading = screen.getAllByRole("heading", { name: "Посадочные места" })[0]
    const seatingCard = seatingHeading?.closest("div.rounded-xl.border.shadow-sm")
    expect(seatingCard).toBeTruthy()

    const seatingGrid = seatingCard?.querySelector(".grid.grid-cols-2.gap-3") as
      | HTMLDivElement
      | null
    expect(seatingGrid).toBeTruthy()

    expect(seatingGrid?.children.length).toBe(20)

    const directChildren = Array.from(seatingGrid?.children || [])
    const emptyCells = directChildren.filter((el) => el.getAttribute("aria-hidden") === "true")
    expect(emptyCells.length).toBe(2)

    // пустые ячейки в схеме
    expect(directChildren[0]?.getAttribute("aria-hidden")).toBe("true")
    expect(directChildren[18]?.getAttribute("aria-hidden")).toBe("true")

    // проверяем что есть значения
    expect(container.querySelectorAll("span").length).toBeGreaterThan(0)
  })

  // fallback на http polling если websocket не открыт
  it("falls back to HTTP polling when WebSocket never opens", async () => {
    ;(globalThis as unknown as { WebSocket: unknown }).WebSocket = FakeWebSocketNeverOpen

    // делаем опрос детерминированным тут
    const setIntervalSpy = vi.spyOn(globalThis, "setInterval")
    let intervalCallback: any = null
    setIntervalSpy.mockImplementation((cb: (...args: any[]) => void) => {
      intervalCallback = cb
      // фейковый ид для интервала
      return 123 as unknown as ReturnType<typeof setInterval>
    })

    const payload: BackendDetailedStatus = {
      overall_inside: 0,
      total_capacity: 3,
      tables: [{ table_id: 1, occupied: 0, capacity: 3, status_color: "green" }],
      last_update: "2025-12-16 12:00:00",
    }

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })
    ;(globalThis as unknown as { fetch: unknown }).fetch = fetchMock

    render(<CafeteriaOccupancy />)

    // первый хттп запрос статуса
    await screen.findByText(/Всего столов:\s*1/)
    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(1)

    // повторный запрос при опросе
    expect(typeof intervalCallback).toBe("function")
    intervalCallback()

    await waitFor(() => {
      expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)
    })

    setIntervalSpy.mockRestore()
  })

  // обновления через websocket
  it("applies WebSocket updates", async () => {
    const payload1: BackendDetailedStatus = {
      overall_inside: 0,
      total_capacity: 3,
      tables: [{ table_id: 1, occupied: 0, capacity: 3, status_color: "green" }],
      last_update: "2025-12-16 12:00:00",
    }

    const payload2: BackendDetailedStatus = {
      overall_inside: 3,
      total_capacity: 3,
      tables: [{ table_id: 1, occupied: 3, capacity: 3, status_color: "red" }],
      last_update: "2025-12-16 12:05:00",
    }

    // СВЯЗЬ ФРОНТЕНДА И БЕКЕНДА: HTTP FETCH
    ;(globalThis as unknown as { fetch: unknown }).fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload1,
    })

    render(<CafeteriaOccupancy />)

    await screen.findByText(/Всего столов:\s*1/)

    // СВЯЗЬ ФРОНТЕНДА И БЕКЕНДА: WEBSOCKET
    const ws = FakeWebSocket.instances[0]
    expect(ws).toBeTruthy()

    ws.onmessage?.({ data: JSON.stringify(payload2) })

    await waitFor(() => {
      expect(screen.getByText(/3\/3/, { selector: "span" })).toBeInTheDocument()
    })
  })
})
