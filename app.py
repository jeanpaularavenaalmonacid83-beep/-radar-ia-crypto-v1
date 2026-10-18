import time
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

APP_TITLE = "Radar IA Crypto — V1"
INITIAL_SOL = 100.0
FEE_RATE = 0.01          # Supuesto conservador de simulación: 1% por lado
SLIPPAGE_RATE = 0.01     # Supuesto inicial: 1% por lado; no es una cotización real
MAX_TRADE_SOL = 2.0      # Límite de práctica por operación
MIN_LIQUIDITY_USD = 10_000
MIN_VOLUME_24H_USD = 25_000
API_TIMEOUT = 12

st.set_page_config(page_title=APP_TITLE, page_icon="📡", layout="wide")

st.title("📡 Radar IA Crypto")
st.caption("Versión 1 · Simulador solamente · Sin conexión a billeteras · Sin operaciones reales")

st.warning(
    "Este prototipo usa datos públicos cuando están disponibles y también permite una demo. "
    "Las señales no son recomendaciones financieras. Los datos de tokens nuevos/boosted no "
    "representan todo Pump.fun, y el precio de una API no garantiza que una operación se pueda ejecutar."
)

with st.sidebar:
    st.header("⚙️ Parámetros")
    data_mode = st.radio("Fuente de datos", ["Demo (segura)", "Intentar datos en vivo"])
    min_liquidity = st.number_input("Liquidez mínima (USD)", min_value=0, value=MIN_LIQUIDITY_USD, step=2500)
    min_volume = st.number_input("Volumen 24 h mínimo (USD)", min_value=0, value=MIN_VOLUME_24H_USD, step=5000)
    trade_size = st.number_input("Tamaño por compra simulada (SOL)", min_value=0.1, max_value=MAX_TRADE_SOL, value=1.0, step=0.1)
    st.caption("Límite del prototipo: máximo 2 SOL por operación.")
    st.caption("Costos simulados: 1% comisión + 1% deslizamiento por cada lado. Son supuestos ajustables, no costos reales garantizados.")
    if st.button("Reiniciar simulación", use_container_width=True):
        for key in ["cash_sol", "positions", "trades", "seen_prices"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

if "cash_sol" not in st.session_state:
    st.session_state.cash_sol = INITIAL_SOL
if "positions" not in st.session_state:
    st.session_state.positions = {}
if "trades" not in st.session_state:
    st.session_state.trades = []
if "seen_prices" not in st.session_state:
    st.session_state.seen_prices = {}

def demo_tokens():
    # Datos ficticios: sirven para aprender la interfaz, no describen tokens reales.
    return [
        {"name":"Demo Cat", "symbol":"DCAT", "address":"DEMO_DCAT", "priceUsd":0.00042,
         "liquidityUsd":85000, "volume24h":245000, "txns24h":1840, "change24h":18.4, "dexId":"demo",
         "url":"", "createdAt":None, "source":"DEMO FICTICIA"},
        {"name":"Demo Frog", "symbol":"DFROG", "address":"DEMO_DFROG", "priceUsd":0.0012,
         "liquidityUsd":42000, "volume24h":98000, "txns24h":720, "change24h":-7.2, "dexId":"demo",
         "url":"", "createdAt":None, "source":"DEMO FICTICIA"},
        {"name":"Demo Rocket", "symbol":"DROCK", "address":"DEMO_DROCK", "priceUsd":0.00008,
         "liquidityUsd":12000, "volume24h":38000, "txns24h":410, "change24h":34.0, "dexId":"demo",
         "url":"", "createdAt":None, "source":"DEMO FICTICIA"},
        {"name":"Demo Sleepy", "symbol":"DSLP", "address":"DEMO_DSLP", "priceUsd":0.0021,
         "liquidityUsd":7000, "volume24h":18000, "txns24h":85, "change24h":-22.0, "dexId":"demo",
         "url":"", "createdAt":None, "source":"DEMO FICTICIA"},
    ]

def fetch_live_tokens():
    """
    Exploratory discovery path:
    1) Read the latest boosted token list from DexScreener.
    2) Ask for Solana pairs for each token.
    3) Keep pairs whose DEX id looks like pump.fun.
    This is NOT a complete feed of all Pump.fun tokens; boosted-token discovery is biased.
    """
    headers = {"User-Agent": "RadarIACrypto-V1/1.0"}
    resp = requests.get("https://api.dexscreener.com/token-boosts/latest/v1",
                        timeout=API_TIMEOUT, headers=headers)
    resp.raise_for_status()
    items = resp.json()
    if not isinstance(items, list):
        return []
    addresses = []
    for item in items:
        if item.get("chainId") == "solana" and item.get("tokenAddress"):
            addresses.append(item["tokenAddress"])
    # Limit requests to keep the free prototype gentle.
    addresses = list(dict.fromkeys(addresses))[:25]
    results = []
    for address in addresses:
        try:
            pair_resp = requests.get(
                f"https://api.dexscreener.com/token-pairs/v1/solana/{address}",
                timeout=API_TIMEOUT, headers=headers
            )
            if pair_resp.status_code != 200:
                continue
            pairs = pair_resp.json()
            if not isinstance(pairs, list):
                continue
            for p in pairs:
                dex = str(p.get("dexId", "")).lower()
                if "pump" not in dex:
                    continue
                base = p.get("baseToken") or {}
                txns = p.get("txns") or {}
                h24 = txns.get("h24") or {}
                price_change = p.get("priceChange") or {}
                liquidity = p.get("liquidity") or {}
                volume = p.get("volume") or {}
                try:
                    price = float(p.get("priceUsd") or 0)
                except (TypeError, ValueError):
                    price = 0
                if price <= 0:
                    continue
                results.append({
                    "name": base.get("name") or "Unknown",
                    "symbol": base.get("symbol") or "?",
                    "address": base.get("address") or address,
                    "priceUsd": price,
                    "liquidityUsd": float(liquidity.get("usd") or 0),
                    "volume24h": float(volume.get("h24") or 0),
                    "txns24h": int(h24.get("buys") or 0) + int(h24.get("sells") or 0),
                    "change24h": float(price_change.get("h24") or 0),
                    "dexId": p.get("dexId") or "",
                    "url": p.get("url") or "",
                    "createdAt": p.get("pairCreatedAt"),
                    "source": "DEXSCREENER · EXPLORATORIO",
                })
        except (requests.RequestException, ValueError, TypeError):
            continue
    # De-duplicate by token address, keep highest-volume pair per token.
    results.sort(key=lambda x: x["volume24h"], reverse=True)
    unique = {}
    for token in results:
        unique.setdefault(token["address"], token)
    return list(unique.values())

def score_token(t):
    liq = t["liquidityUsd"]
    vol = t["volume24h"]
    txns = t["txns24h"]
    change = t["change24h"]
    score = 0
    if liq >= 100_000: score += 25
    elif liq >= 50_000: score += 20
    elif liq >= 25_000: score += 14
    elif liq >= 10_000: score += 7
    if vol >= 500_000: score += 25
    elif vol >= 150_000: score += 20
    elif vol >= 50_000: score += 14
    elif vol >= 25_000: score += 7
    if txns >= 3000: score += 20
    elif txns >= 1000: score += 15
    elif txns >= 300: score += 10
    elif txns >= 100: score += 5
    # Penaliza movimientos extremos: pueden reflejar manipulación o volatilidad.
    if -15 <= change <= 25: score += 15
    elif -30 <= change < -15 or 25 < change <= 50: score += 8
    if liq > 0 and vol / liq >= 1: score += 15
    elif liq > 0 and vol / liq >= 0.4: score += 8
    return min(score, 100)

def usd_to_sol(usd, sol_usd):
    return usd / sol_usd if sol_usd > 0 else 0

def get_sol_price():
    try:
        r = requests.get("https://api.dexscreener.com/latest/dex/search?q=SOL/USDC",
                         timeout=API_TIMEOUT, headers={"User-Agent":"RadarIACrypto-V1/1.0"})
        r.raise_for_status()
        pairs = r.json().get("pairs") or []
        prices = [float(p.get("priceUsd")) for p in pairs
                  if p.get("chainId") == "solana" and p.get("priceUsd")]
        if prices:
            return prices[0]
    except Exception:
        pass
    return None

col1, col2 = st.columns([1, 1])
with col1:
    refresh = st.button("🔄 Cargar / actualizar tokens", type="primary", use_container_width=True)
with col2:
    st.write("Última consulta:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if "tokens" not in st.session_state or refresh:
    if data_mode == "Demo (segura)":
        st.session_state.tokens = demo_tokens()
        st.session_state.data_note = "Datos ficticios de demostración."
    else:
        with st.spinner("Consultando datos públicos…"):
            try:
                live = fetch_live_tokens()
                st.session_state.tokens = live
                st.session_state.data_note = (
                    "Datos exploratorios de DexScreener. La lista de boosted tokens no cubre todos los tokens."
                    if live else "No se encontraron pares Pump.fun en esta consulta. Prueba de nuevo o usa Demo."
                )
            except Exception as e:
                st.session_state.tokens = []
                st.session_state.data_note = f"No se pudieron cargar datos: {type(e).__name__}. Prueba Demo o vuelve a intentar."

tokens = st.session_state.tokens
st.info(st.session_state.get("data_note", ""))

sol_usd = get_sol_price() if data_mode == "Intentar datos en vivo" else None
if sol_usd:
    st.caption(f"Precio SOL de referencia consultado: ${sol_usd:,.2f} USD. Puede variar y no es precio ejecutable.")
else:
    sol_usd = 150.0
    st.caption("Para demo o si falla la consulta de SOL, se usa $150 USD/SOL como supuesto ficticio para conversiones.")

# Mark scores and apply filters.
prepared = []
for t in tokens:
    t = dict(t)
    t["score"] = score_token(t)
    t["pasa_filtros"] = t["liquidityUsd"] >= min_liquidity and t["volume24h"] >= min_volume
    prepared.append(t)
prepared.sort(key=lambda x: (x["pasa_filtros"], x["score"], x["volume24h"]), reverse=True)

# Mark-to-market positions using most recent observed token price.
for address, pos in list(st.session_state.positions.items()):
    match = next((t for t in prepared if t["address"] == address), None)
    if match:
        pos["last_price_usd"] = match["priceUsd"]

positions = st.session_state.positions
cash = float(st.session_state.cash_sol)
position_value = 0.0
for pos in positions.values():
    px = float(pos.get("last_price_usd", pos["entry_price_usd"]))
    position_value += pos["token_qty"] * px / sol_usd
equity = cash + position_value
realized = sum(t["pnl_sol"] for t in st.session_state.trades if t["side"] == "SELL")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Saldo disponible", f"{cash:.3f} SOL")
m2.metric("Valor cartera", f"{position_value:.3f} SOL")
m3.metric("Patrimonio simulado", f"{equity:.3f} SOL")
m4.metric("P/L realizado", f"{realized:+.3f} SOL")

st.subheader("🔎 Tokens con más actividad")
st.caption("La puntuación es una heurística educativa. No predice rentabilidad ni certifica que un token sea seguro.")
if prepared:
    view_rows = []
    for t in prepared:
        view_rows.append({
            "Token": f'{t["name"]} (${t["symbol"]})',
            "Score": t["score"],
            "Liquidez USD": t["liquidityUsd"],
            "Volumen 24h USD": t["volume24h"],
            "Txns 24h": t["txns24h"],
            "Cambio 24h %": t["change24h"],
            "Filtros": "PASA" if t["pasa_filtros"] else "NO PASA",
            "DEX": t["dexId"],
        })
    st.dataframe(pd.DataFrame(view_rows), use_container_width=True, hide_index=True)
else:
    st.info("No hay tokens para mostrar. Usa Demo o actualiza la consulta de datos en vivo.")

st.subheader("🧪 Simulador de compra / venta")
if prepared:
    options = {f'{t["symbol"]} — {t["name"]} — score {t["score"]}': t for t in prepared}
    selected_label = st.selectbox("Selecciona un token", list(options.keys()))
    selected = options[selected_label]
    st.write(f'Precio observado: **${selected["priceUsd"]:.10f} USD** · Liquidez: **${selected["liquidityUsd"]:,.0f}** · Volumen 24 h: **${selected["volume24h"]:,.0f}**')
    if not selected["pasa_filtros"]:
        st.warning("Este token no cumple los filtros actuales. La compra de práctica sigue bloqueada hasta que los cumpla.")
    buy_col, sell_col = st.columns(2)
    with buy_col:
        st.markdown("**Comprar (simulado)**")
        already_held = selected["address"] in positions
        buy_blocked = already_held or not selected["pasa_filtros"] or cash < trade_size
        if st.button("Comprar con saldo ficticio", disabled=buy_blocked, use_container_width=True):
            spend = min(float(trade_size), MAX_TRADE_SOL, cash)
            effective_sol = spend * (1 - FEE_RATE) * (1 - SLIPPAGE_RATE)
            usd_value = effective_sol * sol_usd
            qty = usd_value / selected["priceUsd"]
            st.session_state.cash_sol -= spend
            st.session_state.positions[selected["address"]] = {
                "name": selected["name"], "symbol": selected["symbol"],
                "token_qty": qty, "cost_sol": spend,
                "entry_price_usd": selected["priceUsd"], "last_price_usd": selected["priceUsd"],
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "address": selected["address"],
            }
            st.session_state.trades.append({
                "time": datetime.now(timezone.utc).isoformat(), "side":"BUY",
                "name":selected["name"], "symbol":selected["symbol"], "address":selected["address"],
                "price_usd":selected["priceUsd"], "amount_sol":spend, "pnl_sol":0.0,
                "notes":f"Fee {FEE_RATE:.1%} + slippage {SLIPPAGE_RATE:.1%} supuesto por lado",
            })
            st.rerun()
        if already_held:
            st.caption("Ya tienes una posición abierta en este token.")
        if not selected["pasa_filtros"]:
            st.caption("Compra bloqueada: no cumple liquidez y volumen mínimos.")
    with sell_col:
        st.markdown("**Vender (simulado)**")
        if selected["address"] in positions:
            if st.button("Vender posición completa", use_container_width=True):
                pos = st.session_state.positions.pop(selected["address"])
                gross_sol = pos["token_qty"] * selected["priceUsd"] / sol_usd
                net_sol = gross_sol * (1 - FEE_RATE) * (1 - SLIPPAGE_RATE)
                pnl = net_sol - pos["cost_sol"]
                st.session_state.cash_sol += net_sol
                st.session_state.trades.append({
                    "time": datetime.now(timezone.utc).isoformat(), "side":"SELL",
                    "name":selected["name"], "symbol":selected["symbol"], "address":selected["address"],
                    "price_usd":selected["priceUsd"], "amount_sol":net_sol, "pnl_sol":pnl,
                    "notes":f"Fee {FEE_RATE:.1%} + slippage {SLIPPAGE_RATE:.1%} supuesto por lado",
                })
                st.rerun()
        else:
            st.caption("No hay posición abierta para este token.")

st.subheader("📦 Posiciones abiertas")
if positions:
    rows = []
    for pos in positions.values():
        last_px = float(pos.get("last_price_usd", pos["entry_price_usd"]))
        value_sol = pos["token_qty"] * last_px / sol_usd
        rows.append({
            "Token": f'{pos["name"]} (${pos["symbol"]})',
            "Costo inicial SOL": pos["cost_sol"],
            "Valor estimado SOL": value_sol,
            "P/L no realizado SOL": value_sol - pos["cost_sol"],
            "Entrada USD": pos["entry_price_usd"],
            "Último precio USD": last_px,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.caption("Todavía no hay posiciones abiertas.")

st.subheader("🧾 Registro de operaciones")
if st.session_state.trades:
    trades_df = pd.DataFrame(st.session_state.trades)
    st.dataframe(trades_df, use_container_width=True, hide_index=True)
    csv = trades_df.to_csv(index=False).encode("utf-8")
    st.download_button("Descargar operaciones CSV", data=csv, file_name="radar_operaciones.csv", mime="text/csv")
else:
    st.caption("Todavía no hay operaciones. Cada compra/venta simulada aparecerá aquí.")

st.subheader("📌 Reglas y limitaciones de V1")
st.markdown("""
- Saldo inicial: **100 SOL ficticios**.
- Tamaño máximo por operación: **2 SOL**.
- Compra bloqueada si no cumple los mínimos de liquidez y volumen o ya existe una posición abierta en el token.
- Supuestos iniciales de costos: **1% de comisión y 1% de deslizamiento por lado**. Son parámetros de prueba, no una estimación fiable de cada operación real.
- No se envían transacciones, no se conecta ninguna billetera y no se solicitan claves privadas.
- La valoración en SOL usa un precio de referencia de SOL/USD; si no se puede obtener, usa el supuesto de demo de $150.
- Los datos de tokens boosted son sesgados y no cubren el universo completo de Pump.fun. La API puede cambiar o limitar solicitudes.
- El historial y la cartera viven en la sesión del navegador/servidor. Para conservarlos de forma persistente en un despliegue futuro se añadirá una base de datos.
""")
st.caption(f"Build local V1 · Actualizado {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
