export function getBackendBaseUrl() {
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

export function toWebSocketBaseUrl(httpBaseUrl: string) {
  // переводим хттп в вебсокет
  return httpBaseUrl.replace(/^https:/i, "wss:").replace(/^http:/i, "ws:")
}

export function formatLastUpdate(value: string) {
  if (!value || value === "N/A") return ""
  // режем время для интерфейса
  const parts = value.split(" ")
  const timePart = parts.length >= 2 ? parts[1] : value
  return timePart.slice(0, 5)
}
