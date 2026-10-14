/**
 * hunter_ksa1 bot - opt-in, unsigned, read-only Binance CLOSED candles preview.
 * NO account credentials, API order endpoints, NDSP sources, or trade actions.
 * Use only behind loopback SSH. Not intended as a licensed public data feed.
 */
const endpoints = Object.freeze({
  spot: ["https://api.binance.com", "/api/v3/time", "/api/v3/klines"],
  usdm_futures: ["https://fapi.binance.com", "/fapi/v1/time", "/fapi/v1/klines"],
});
const symbols = new Set(["BTCUSDT", "ETHUSDT", "XRPUSDT", "APTUSDT"]);
const intervals = new Map([["5m", 300_000], ["15m", 900_000]]);
const maxBody = 500_000;

export class MarketUnavailable extends Error {
  constructor(code) {
    super(code);
    this.name = "MarketUnavailable";
    this.code = code;
  }
}

export function allowedRequest({ market, symbol, interval }) {
  if (!Object.hasOwn(endpoints, market) ||
      !symbols.has(symbol) || !intervals.has(interval)) {
    throw new MarketUnavailable("MARKET_PREVIEW_UNSUPPORTED_SELECTION");
  }
  return { market, symbol, interval };
}

function fail(code) {
  throw new MarketUnavailable(code);
}

async function fetchJson(fetcher, url) {
  let reply;
  try {
    reply = await fetcher(url, {
      method: "GET",
      redirect: "error",
      signal: AbortSignal.timeout(5000),
      headers: { Accept: "application/json" },
    });
  } catch {
    fail("MARKET_PREVIEW_PROVIDER_UNAVAILABLE");
  }
  if (!reply || reply.status !== 200) {
    fail("MARKET_PREVIEW_PROVIDER_UNAVAILABLE");
  }
  if (Number(reply.headers.get("content-length") || 0) > maxBody) {
    fail("MARKET_PREVIEW_PAYLOAD_TOO_LARGE");
  }
  let text;
  try {
    text = await reply.text();
  } catch {
    fail("MARKET_PREVIEW_PROVIDER_UNAVAILABLE");
  }
  if (text.length > maxBody) fail("MARKET_PREVIEW_PAYLOAD_TOO_LARGE");
  try {
    return JSON.parse(text);
  } catch {
    fail("MARKET_PREVIEW_RESPONSE_INVALID");
  }
}

function positiveNumber(input, allowZero = false) {
  if (typeof input !== "string" || !/^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(input)) {
    fail("MARKET_PREVIEW_CANDLE_INVALID");
  }
  const n = Number(input);
  if (!Number.isFinite(n) || n < 0 || (!allowZero && n === 0)) {
    fail("MARKET_PREVIEW_CANDLE_INVALID");
  }
  return n;
}

/** Two hardcoded unsigned HTTP GETs, no dynamic URL host or user-supplied path. */
export async function readClosedCandles(selection, fetcher = fetch) {
  const { market, symbol, interval } = allowedRequest(selection);
  const [origin, timePath, candlesPath] = endpoints[market];
  const server = await fetchJson(fetcher, origin + timePath);
  const serverTime = server?.serverTime;
  const duration = intervals.get(interval);
  if (!Number.isSafeInteger(serverTime) || serverTime < 1_600_000_000_000) {
    fail("MARKET_PREVIEW_PROVIDER_CLOCK_INVALID");
  }
  const url = new URL(candlesPath, origin);
  url.searchParams.set("symbol", symbol);
  url.searchParams.set("interval", interval);
  url.searchParams.set("limit", "8");
  const rows = await fetchJson(fetcher, url.href);
  if (!Array.isArray(rows) || rows.length < 2 || rows.length > 8) {
    fail("MARKET_PREVIEW_CANDLES_INVALID");
  }
  const closed = [];
  let priorOpen = null;
  for (const row of rows) {
    if (!Array.isArray(row) || row.length < 7) {
      fail("MARKET_PREVIEW_CANDLE_INVALID");
    }
    const [opened, rawOpen, rawHigh, rawLow, rawClose, rawVolume, closeTime] = row;
    if (!Number.isSafeInteger(opened) || opened < 1_600_000_000_000 ||
        opened % duration !== 0 || closeTime !== opened + duration - 1 ||
        (priorOpen !== null && opened !== priorOpen + duration)) {
      fail("MARKET_PREVIEW_CANDLE_TIMING_INVALID");
    }
    priorOpen = opened;
    if (closeTime >= serverTime) continue; // open/unconfirmed bar: never display
    const open = positiveNumber(rawOpen);
    const high = positiveNumber(rawHigh);
    const low = positiveNumber(rawLow);
    const close = positiveNumber(rawClose);
    const volume = positiveNumber(rawVolume, true);
    if (low > Math.min(open, close) || high < Math.max(open, close) || high < low) {
      fail("MARKET_PREVIEW_CANDLE_OHLC_INVALID");
    }
    closed.push({ openTimeMs: opened, closeTimeMs: closeTime, open, high, low, close, volume });
  }
  if (!closed.length) fail("MARKET_PREVIEW_NO_CLOSED_CANDLES");
  const age = serverTime - (closed.at(-1).closeTimeMs + 1);
  if (age < 0 || age > 2 * duration) fail("MARKET_PREVIEW_STALE_CANDLES");
  return {
    status: "READ_ONLY_OK",
    contract: "HUNTER_CLOSED_CANDLES_PREVIEW_V1",
    source: "BINANCE_PUBLIC_REST",
    market, symbol, interval, serverTimeMs: serverTime,
    candles: closed.slice(-5),
    execution_authorized: false,
    orders_sent: 0,
  };
}
