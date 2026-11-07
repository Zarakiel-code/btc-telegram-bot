import pandas as pd
import asyncio
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from api import get_klines

def cal_indicators(k: list) -> dict:
    closes = pd.Series([v["close"] for v in k])
    
    rsi = RSIIndicator(close=closes, window=14).rsi().iloc[-1]
    sma20 = SMAIndicator(close=closes, window=20).sma_indicator().iloc[-1]
    sma50 = SMAIndicator(close=closes, window=50).sma_indicator().iloc[-1]
    precio = closes.iloc[-1]
    
    return {
        "precio": precio,
        "rsi": round(rsi, 2),
        "sma20": round(sma20, 2),
        "sma50": round(sma50, 2),
        "dist_sma20": round((precio - sma20) / sma20 * 100, 2),
        "dist_sma50": round((precio - sma50) / sma50 * 100, 2),
        "tendencia": "alcista" if sma20 > sma50 else "bajista",
    }
    
if __name__ == "__main__":
        
        async def main() -> None:
        	velas = await get_klines()
        	if velas is None:
        	   print(" get_klines devolvió None")
        	else:
        	   resultado = cal_indicators(velas)
        	   print(resultado)
        	   
        asyncio.run(main())
        	   