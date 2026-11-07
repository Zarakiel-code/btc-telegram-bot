import httpx
from typing import Optional

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
BINANCE_URL = "https://data-api.binance.vision/api/v3/klines"


async def get_btc_price() -> Optional[dict]:
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(COINGECKO_URL, params=params)
            r.raise_for_status()
            data = r.json()["bitcoin"]
            return {
                "price": data["usd"],
                "change_24h": data["usd_24h_change"],
                "market_cap": data["usd_market_cap"],
                "volume_24h": data["usd_24h_vol"],
            }
    except (httpx.HTTPError, KeyError) as e:
        print(f"Error CoinGecko: {e}")
        return None


async def get_klines(interval: str = "15m", limit: int = 200) -> Optional[list]:
    """Velas OHLCV de Binance. Devuelve lista de dicts o None si falla."""
    params = {"symbol": "BTCUSDT", "interval": interval, "limit": limit}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(BINANCE_URL, params=params)
            r.raise_for_status()
            return [
                {
                    "open_time": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": k[6],
                }
                for k in r.json()
            ]
    except (httpx.HTTPError, KeyError, IndexError) as e:
        print(f"Error Binance: {e}")
        return None
        
if __name__ == "__main__":
    import asyncio

    print(asyncio.run(get_btc_price()))
    print(asyncio.run(get_klines())[-1])