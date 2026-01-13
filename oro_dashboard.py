import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time
import requests
import base64

# ================= CONFIG =================
SYMBOL_GOLD = "GC=F"
SYMBOL_SILVER = "SI=F"
INTERVAL = "1h"  # H4 requires resampling from 1h
PERIOD_INTRADAY = "60d" # More data for H4 resampling

# Configuración de la página
st.set_page_config(
    page_title="🪙 Gold Trading Monitor",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 25px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.5);
    }
    
    .buy-signal {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        font-size: 48px;
        font-weight: bold;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 0 30px rgba(56, 239, 125, 0.5);
        animation: pulse 2s infinite;
    }
    
    .sell-signal {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        font-size: 48px;
        font-weight: bold;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 0 30px rgba(245, 87, 108, 0.5);
        animation: pulse 2s infinite;
    }
    
    .wait-signal {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-size: 48px;
        font-weight: bold;
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 0 30px rgba(102, 126, 234, 0.3);
    }
    
    @keyframes pulse {
        0%, 100% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.05);
        }
    }
    
    .price-display {
        font-size: 72px;
        font-weight: bold;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin: 20px 0;
    }
    
    .status-joven {
        color: #38ef7d;
        font-weight: bold;
    }
    
    .status-optimo {
        color: #4facfe;
        font-weight: bold;
    }
    
    .status-tarde {
        color: #f093fb;
        font-weight: bold;
    }
    
    .status-agotado {
        color: #ee0979;
        font-weight: bold;
    }
    
    h1, h2, h3, p, div, span, label {
        color: #4facfe !important;
    }
    
    .stMetric label {
        color: #4facfe !important;
        font-weight: bold !important;
    }
    
    .stMetric value {
        color: #00f2fe !important;
    }
    
    div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-size: 28px !important;
        text-shadow: 0 0 10px rgba(0, 242, 254, 0.3);
    }
    
    .metric-container {
        background: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(79, 172, 254, 0.2);
        text-align: center;
    }
    
    .tooltip-text {
        font-size: 14px;
        color: #8ec5fc !important;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar con configuración
with st.sidebar:
    st.title("⚙️ Configuración")
    
    st.markdown("### Parámetros Técnicos")
    ADR_PERIOD = st.slider("Período ADR", 5, 30, 14)
    EMA_FAST = st.slider("EMA Rápida", 3, 10, 5)
    EMA_SLOW = st.slider("EMA Lenta", 10, 30, 15)
    
    st.markdown("### Umbrales de Señal")
    MIN_EMA_DIST = st.slider("Distancia EMA mínima (%)", 0.0, 0.5, 0.10, 0.01)
    MIN_EMA_SLOPE = st.slider("Pendiente EMA mínima (%)", 0.0, 0.1, 0.03, 0.001)
    MAX_ADR_USE = st.slider("Uso máximo ADR (%)", 0.3, 1.0, 0.60, 0.05)
    
    st.markdown("### Notificaciones Telegram")
    TELEGRAM_TOKEN = st.text_input("Bot Token", value="6075391597:AAFi28sadDJmq0rgvKG1bMnMK5hk8A1JFQU", type="password", help="Obtenlo de @BotFather")
    TELEGRAM_CHAT_ID = st.text_input("Chat ID", value="909954663", help="Obtenlo de @userinfobot")
    ENABLE_TELEGRAM = st.checkbox("Activar Telegram", value=True)
    
    st.markdown("### Actualización")
    REFRESH_INTERVAL = st.slider("Intervalo de actualización (seg)", 30, 300, 60, 30)
    
    if st.button("🔄 Actualizar Ahora", use_container_width=True):
        st.rerun()

# Función para calcular ADR
@st.cache_data(ttl=3600)
def calcular_ADR(symbol, adr_period):
    try:
        df_d = yf.download(symbol, period="3mo", interval="1d", progress=False)
        
        # Asegurar que trabajamos con series simples
        if isinstance(df_d.columns, pd.MultiIndex):
            df_d.columns = df_d.columns.get_level_values(0)
        
        # Calcular el cierre previo
        prev_close = df_d["Close"].shift(1)
        
        # Calcular componentes del True Range
        hl = (df_d["High"] - df_d["Low"]).values
        hpc = abs(df_d["High"] - prev_close).values
        lpc = abs(df_d["Low"] - prev_close).values
        
        # True Range es el máximo de los tres componentes
        tr = np.maximum(hl, np.maximum(hpc, lpc))
        
        # Calcular ADR usando pandas Series para el EWM
        tr_series = pd.Series(tr, index=df_d.index)
        adr = tr_series.ewm(span=adr_period).mean()
        
        return float(adr.iloc[-1])
    except Exception as e:
        st.error(f"Error calculando ADR para {symbol}: {e}")
        return None

def send_telegram_message(message):
    if not ENABLE_TELEGRAM or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        st.error(f"Error enviando Telegram: {e}")

def play_sound():
    # Sonido de campana corto en base64
    audio_html = """
        <audio autoplay>
            <source src="https://www.soundjay.com/buttons/sounds/button-3.mp3" type="audio/mpeg">
        </audio>
    """
    st.components.v1.html(audio_html, height=0)

def play_sound():
    # Sonido de campana corto en base64
    audio_html = """
        <audio autoplay>
            <source src="https://www.soundjay.com/buttons/sounds/button-3.mp3" type="audio/mpeg">
        </audio>
    """
    st.components.v1.html(audio_html, height=0)

def fetch_and_alert(symbol, label):
    """
    Función para obtener datos y enviar alertas. 
    Se ejecuta para ambos activos antes de mostrar las pestañas.
    """
    try:
        df = yf.download(symbol, period=PERIOD_INTRADAY, interval=INTERVAL, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty:
            return None
            
        # Resamplear a H4
        df_h4 = df.resample('4H').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        
        df_h4["EMA5"] = df_h4["Close"].ewm(span=EMA_FAST).mean()
        df_h4["EMA15"] = df_h4["Close"].ewm(span=EMA_SLOW).mean()
        
        ema5 = float(df_h4["EMA5"].iloc[-1])
        ema15 = float(df_h4["EMA15"].iloc[-1])
        close = float(df_h4["Close"].iloc[-1])
        
        # Lógica de Cruce para Alarma (usando Session State específico por símbolo)
        key_ema5 = f"prev_ema5_{symbol}"
        key_ema15 = f"prev_ema15_{symbol}"
        
        if key_ema5 in st.session_state and key_ema15 in st.session_state:
            # Detectar cruce al alza
            if st.session_state[key_ema5] <= st.session_state[key_ema15] and ema5 > ema15:
                # No podemos llamar a play_sound aquí directamente si no es la pestaña activa, 
                # pero el bot de Telegram siempre recibirá el mensaje.
                send_telegram_message(f"🚀 *CRUCE AL ALZA {label} (H4)*\nPrecio: ${close:.2f}\nEMA{EMA_FAST} ha cruzado por encima de EMA{EMA_SLOW}")
                # Guardamos bandera para globos/sonido si el usuario abre esa pestaña
                st.session_state[f"alert_baloons_{symbol}"] = True
            
            # Detectar cruce a la baja
            elif st.session_state[key_ema5] >= st.session_state[key_ema15] and ema5 < ema15:
                send_telegram_message(f"📉 *CRUCE A LA BAJA {label} (H4)*\nPrecio: ${close:.2f}\nEMA{EMA_FAST} ha cruzado por debajo de EMA{EMA_SLOW}")
                st.session_state[f"alert_warning_{symbol}"] = True

        # Actualizar estado previo
        st.session_state[key_ema5] = ema5
        st.session_state[key_ema15] = ema15
        
        return df_h4
    except Exception as e:
        st.error(f"Error procesando alertas para {label}: {e}")
        return None

def display_monitor(df, symbol, label):
    """
    Solo se encarga de mostrar la interfaz visual usando los datos ya procesados.
    """
    if df is None or df.empty:
        st.error(f"No hay datos para mostrar de {label}.")
        return

    # Mostrar alertas visuales si fueron activadas en el procesamiento previo
    if st.session_state.get(f"alert_baloons_{symbol}", False):
        st.balloons()
        play_sound()
        st.session_state[f"alert_baloons_{symbol}"] = False # Resetear
    
    if st.session_state.get(f"alert_warning_{symbol}", False):
        st.warning(f"ALERTA: Cruce de medias a la baja detectado en {label}.")
        play_sound()
        st.session_state[f"alert_warning_{symbol}"] = False # Resetear

    close = float(df["Close"].iloc[-1])
    high = float(df["High"].max())
    low = float(df["Low"].min())
    ema5 = float(df["EMA5"].iloc[-1])
    ema15 = float(df["EMA15"].iloc[-1])
    ema15_prev = float(df["EMA15"].iloc[-2]) if len(df) > 1 else ema15

    # Cálculos
    ema_dist_pct = abs(ema5 - ema15) / close * 100
    ema_slope_pct = abs(ema15 - ema15_prev) / close * 100
    
    adr_val = calcular_ADR(symbol, ADR_PERIOD)
    
    if adr_val:
        consumo_adr = (high - low) / adr_val
        estado_adr, estado_class = ("JOVEN", "status-joven") if consumo_adr < 0.30 else \
                                   ("OPTIMO", "status-optimo") if consumo_adr < 0.60 else \
                                   ("TARDE", "status-tarde") if consumo_adr < 0.80 else \
                                   ("AGOTADO", "status-agotado")
        
        señal_compra = (ema5 > ema15 and ema_dist_pct >= MIN_EMA_DIST and ema_slope_pct >= MIN_EMA_SLOPE and consumo_adr <= MAX_ADR_USE)
        señal_venta = (ema5 < ema15 and ema_dist_pct >= MIN_EMA_DIST and ema_slope_pct >= MIN_EMA_SLOPE and consumo_adr <= MAX_ADR_USE)
        
        st.markdown(f"<div class='price-display'>${close:.2f}</div>", unsafe_allow_html=True)
        
        if señal_compra: st.markdown("<div class='buy-signal'>✅ COMPRAR</div>", unsafe_allow_html=True)
        elif señal_venta: st.markdown("<div class='sell-signal'>📉 VENDER</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='wait-signal'>⏸️ ESPERAR</div>", unsafe_allow_html=True)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(f"EMA {EMA_FAST}", f"${ema5:.2f}")
        col2.metric(f"EMA {EMA_SLOW}", f"${ema15:.2f}")
        col3.metric("Gap EMAs", f"{ema_dist_pct:.3f}%")
        col4.metric("Pendiente Lenta", f"{ema_slope_pct:.3f}%")

        st.markdown("---")
        st.markdown(f"### 📊 Rango Diario Promedio (ADR)")
        c1, c2, c3 = st.columns([1, 1, 2])
        c1.metric("Valor ADR", f"${adr_val:.2f}")
        c2.metric("Consumo Hoy", f"{consumo_adr*100:.1f}%")
        c3.markdown(f"<div style='text-align: center; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 10px;'><span style='font-size: 20px; color: #4facfe;'>Estado: </span><span class='{estado_class}' style='font-size: 24px;'>{estado_adr}</span></div>", unsafe_allow_html=True)
        
        st.progress(min(consumo_adr, 1.0))
        st.markdown("### Acción del Precio con EMAs")
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Precio'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA5'], mode='lines', name=f'EMA {EMA_FAST}', line=dict(color='#38ef7d', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA15'], mode='lines', name=f'EMA {EMA_SLOW}', line=dict(color='#ee0979', width=2)), row=1, col=1)
        
        colors = ['red' if df['Close'].iloc[i] < df['Open'].iloc[i] else 'green' for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volumen', marker_color=colors, opacity=0.5), row=2, col=1)
        fig.update_layout(template='plotly_dark', height=700, showlegend=True, xaxis_rangeslider_visible=False, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)

# Función para obtener datos macro
@st.cache_data(ttl=3600)
def obtener_datos_macro():
    symbols = {
        "DXY": "DX-Y.NYB",
        "US10Y": "^TNX",
        "Oro": "GC=F",
        "Plata": "SI=F",
        "SP500": "^GSPC"
    }
    
    data = {}
    for name, symbol in symbols.items():
        try:
            df = yf.download(symbol, period="6mo", interval="1d", progress=False)
            
            # Asegurar que trabajamos con series simples
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            if not df.empty:
                data[name] = df
        except Exception as e:
            st.warning(f"Error descargando {name}: {e}")
    
    return data

# Header
st.markdown("<h1 style='text-align: center; font-size: 56px; color: #4facfe;'>🪙 MONITOR DE TRADING - ORO</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #4facfe; font-size: 18px;'>Análisis en tiempo real con señales de compra</p>", unsafe_allow_html=True)


# --- PROCESAMIENTO DE ALERTAS (Background) ---
# Esto se ejecuta siempre antes de las pestañas
df_gold = fetch_and_alert(SYMBOL_GOLD, "ORO")
df_silver = fetch_and_alert(SYMBOL_SILVER, "PLATA")

# Tabs principales
tab_intro, tab_oro, tab_plata, tab_macro = st.tabs(["🏠 Inicio / Estrategia", "🥇 Monitor Oro", "🥈 Monitor Plata", "🌍 Contexto Macro"])

with tab_intro:
    st.markdown("## 🧠 Análisis Lógico y Matemático")
    
    col_teoria, col_calc = st.columns([1, 1])
    
    with col_teoria:
        st.markdown("### 📘 Fundamentos Matemáticos")
        
        with st.expander("Ver Demostración Matemática Completa", expanded=True):
            st.markdown("#### 1️⃣ Definición Formal")
            st.latex(r"\mathbb{E}[X] = \sum_{i=1}^{n} x_i \cdot P(X = x_i)")
            st.caption("Donde $X$ es el resultado de una operación.")

            st.markdown("#### 2️⃣ Modelo de Trading")
            st.markdown("""
            Simplificamos sin perder rigor. Cada operación tiene dos estados posibles:
            *   **Ganancia ($G$):** $+R \cdot RR$
            *   **Pérdida ($P$):** $-R$
            """)

            st.markdown("#### 3️⃣ Probabilidades")
            st.latex(r"P_g + P_p = 1 \implies P_p = 1 - P_g")

            st.markdown("#### 4️⃣ Variable Aleatoria")
            st.latex(r"""
            X = \begin{cases} 
            +R \cdot RR & \text{con prob. } P_g \\
            -R & \text{con prob. } 1 - P_g 
            \end{cases}
            """)

            st.markdown("#### 5️⃣ Esperanza Matemática General")
            st.markdown("Aplicando la definición y factorizando el Riesgo ($R$):")
            st.latex(r"\mathbb{E}[X] = R(P_g \cdot RR - (1 - P_g))")
            st.warning("☝️ Esta es la **Fórmula Fundamental del Trading Cuantitativo**.")

            st.markdown("#### 6️⃣ Condición para Ganar Dinero")
            st.markdown("Para ser rentable necesitamos $\mathbb{E}[X] > 0$, lo que implica:")
            st.latex(r"P_g > \frac{1}{RR + 1}")

            st.markdown("#### 7️⃣ Interpretación (Win Rate Mínimo)")
            st.markdown("""
            | Ratio R/R | Win Rate Mínimo |
            | :---: | :---: |
            | **1 : 1** | $50.0\%$ |
            | **2 : 1** | $33.3\%$ |
            | **3 : 1** | $25.0\%$ |
            """)
            st.success("👉 Con un RR de 2:1, solo necesitas acertar el **34%** de las veces para ser rentable.")

        with st.expander("📉 Probabilidad de Ruina (Teoría Formal)"):
            st.markdown("<h4 style='color: #4ECDC4;'>1️⃣ Definición del Problema</h4>", unsafe_allow_html=True)
            st.markdown("Consideramos un capital inicial $C_0$ que evoluciona mediante operaciones independientes $X_i$:")
            st.latex(r"C_n = C_0 + \sum_{i=1}^{n} X_i")
            st.caption("La ruina ocurre si existe algún $n$ tal que $C_n \leq 0$.")

            st.markdown("<h4 style='color: #4ECDC4;'>2️⃣ Teorema Fundamental</h4>", unsafe_allow_html=True)
            st.markdown("Si la esperanza matemática es positiva ($\mathbb{E}[X] > 0$), entonces la probabilidad de ruina es estrictamente menor que 1.")
            st.latex(r"\mathbb{E}[X] = R(P_g \cdot RR - (1 - P_g)) > 0 \implies \text{Ruina no segura}")

            st.markdown("<h4 style='color: #4ECDC4;'>3️⃣ Aproximación de Cramér-Lundberg</h4>", unsafe_allow_html=True)
            st.latex(r"P_{ruina} \approx \left( \frac{1 - P_g}{P_g} \right)^{\frac{C_0}{R}}")

            st.markdown("<h4 style='color: #4ECDC4;'>4️⃣ Aplicación a tu Sistema</h4>", unsafe_allow_html=True)
            st.markdown("""
            *   $P_g = 0.55$
            *   $R = 1\%$ (Capital normalizado $C_0 = 100$ unidades de riesgo)
            """)
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.latex(r"P_{ruina} \approx \left( \frac{0.45}{0.55} \right)^{100} \approx 2.4 \times 10^{-9}")
            st.success("🛡️ **Probabilidad de Ruina:** $\approx 0.00000024\%$ (Virtualmente imposibe si se respeta el plan).")
            

        with st.expander("🚀 Optimización con Criterio de Kelly"):
            st.markdown("<h4 style='color: #FF6B6B;'>1️⃣ Definición</h4>", unsafe_allow_html=True)
            st.markdown("Kelly maximiza el crecimiento logarítmico esperado del capital: $\max \mathbb{E}[\ln(C_{n+1})]$.")
            st.latex(r"f^* = \frac{P_g \cdot RR - (1 - P_g)}{RR}")

            st.markdown("<h4 style='color: #FF6B6B;'>2️⃣ Kelly Aplicado a tu Sistema</h4>", unsafe_allow_html=True)
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.latex(r"P_{ruina} \approx \left( \frac{0.45}{0.55} \right)^{100}")
            st.latex(r"\approx 2.4 \times 10^{-9}")
            st.error("⚠️ **Kelly Completo (32.5%)**: Inoperable psicológica y prácticamente.")

            st.markdown("<h4 style='color: #FF6B6B;'>3️⃣ Kelly Fraccionado (Realidad Profesional)</h4>", unsafe_allow_html=True)
            st.markdown("""
            | Versión | Riesgo Sugerido |
            | :--- | :--- |
            | **Kelly Completo** | $32.5\%$ |
            | **1/2 Kelly** | $16.25\%$ |
            | **1/4 Kelly** | $8.1\%$ |
            | **1/8 Kelly** | $\approx 4\%$ |
            | **...** | ... |
            | **1/32 Kelly** | $\approx 1\%$ |
            """)
            st.info("""
            👉 **Tu riesgo del 1% equivale a "Kelly muy conservador" (1/32).**
            
            Esto garantiza:
            *   ✅ Máxima supervivencia.
            *   ✅ Crecimiento estable.
            *   ✅ Drawdowns controlables.
            """)

    with col_calc:
        st.markdown("### 🧮 Calculadora de Posición")
        
        sub_col1, sub_col2 = st.columns(2)
        with sub_col1:
            calc_capital_val = st.number_input("Capital (€)", value=10000, step=1000)
            calc_risk_pct_val = st.number_input("Riesgo (%)", value=1.0, step=0.1)
        with sub_col2:
            calc_sl_pips_val = st.number_input("Stop Loss (Pips)", value=30, step=5)
            calc_pip_value_val = st.number_input("Valor Pip estándar ($)", value=10.0, disabled=True)

        risk_amount_val = calc_capital_val * (calc_risk_pct_val / 100)
        lots_val = risk_amount_val / (calc_sl_pips_val * calc_pip_value_val)
        
        st.success(f"""
        **Resultados de Gestión:**
        *   Dinero en Riesgo: **€{risk_amount_val:.2f}**
        *   Lotes Recomendados: **{lots_val:.2f} Lotes**
        """)

    st.markdown("---")
    st.markdown("## 🎲 Simulación de Monte Carlo")
    
    sc1, sc2, sc3, sc4 = st.columns(4)
    sim_win_rate_val = sc1.slider("Win Rate (%)", 30, 80, 55) / 100
    sim_rr_val = sc2.slider("Ratio Riesgo/Beneficio", 1.0, 5.0, 2.0)
    sim_trades_val = sc3.slider("Nº de Operaciones", 50, 1000, 300)
    
    if st.button("▶️ Ejecutar Simulación"):
        riesgo_sim_v = calc_capital_val * (calc_risk_pct_val / 100)
        ganancia_sim_v = riesgo_sim_v * sim_rr_val
        equity_curves = []
        final_capitals = []
        
        for _ in range(50):
            cap = calc_capital_val
            curve = [cap]
            for _ in range(sim_trades_val):
                if np.random.rand() < sim_win_rate_val: cap += ganancia_sim_v
                else: cap -= riesgo_sim_v
                curve.append(cap)
                if cap <= 0: break
            equity_curves.append(curve)
            final_capitals.append(cap)
            
        fig_eq = go.Figure()
        for curve in equity_curves:
            fig_eq.add_trace(go.Scatter(y=curve, mode='lines', line=dict(width=1), opacity=0.3, showlegend=False))
        
        avg_c = np.mean([len(c)==len(equity_curves[0]) and c or c+[c[-1]]*(len(equity_curves[0])-len(c)) for c in equity_curves], axis=0)
        fig_eq.add_trace(go.Scatter(y=avg_c, mode='lines', name='Promedio', line=dict(color='#38ef7d', width=3)))
        fig_eq.update_layout(title="Curvas de Equity (50 Simulaciones)", template="plotly_dark", height=400)
        
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(x=final_capitals, marker_color='#4facfe', opacity=0.7))
        fig_hist.update_layout(title="Distribución de Capital Final", template="plotly_dark", height=400)
        
        g1, g2 = st.columns(2)
        g1.plotly_chart(fig_eq, use_container_width=True)
        g2.plotly_chart(fig_hist, use_container_width=True)

with tab_oro:
    display_monitor(df_gold, SYMBOL_GOLD, "ORO")

with tab_plata:
    display_monitor(df_silver, SYMBOL_SILVER, "PLATA")


with tab_macro:
    st.markdown("## Contexto Macroeconómico")
    st.markdown("Análisis de 6 meses de activos correlacionados con el oro")
    
    data_macro = obtener_datos_macro()
    
    if data_macro:
        # Crear gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            if "DXY" in data_macro:
                fig_dxy = go.Figure()
                fig_dxy.add_trace(go.Scatter(
                    x=data_macro["DXY"].index,
                    y=data_macro["DXY"]["Close"],
                    mode='lines',
                    name='DXY',
                    line=dict(color='#4facfe', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(79, 172, 254, 0.2)'
                ))
                fig_dxy.update_layout(
                    title="DXY - Índice del Dólar",
                    template='plotly_dark',
                    height=350,
                    hovermode='x unified',
                    xaxis_tickformat='%d %b %y'
                )
                st.plotly_chart(fig_dxy, use_container_width=True)
            
            if "SP500" in data_macro:
                fig_sp = go.Figure()
                fig_sp.add_trace(go.Scatter(
                    x=data_macro["SP500"].index,
                    y=data_macro["SP500"]["Close"],
                    mode='lines',
                    name='S&P 500',
                    line=dict(color='#11998e', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(17, 153, 142, 0.2)'
                ))
                fig_sp.update_layout(
                    title="S&P 500",
                    template='plotly_dark',
                    height=350,
                    hovermode='x unified',
                    xaxis_tickformat='%d %b %y'
                )
                st.plotly_chart(fig_sp, use_container_width=True)
        
        with col2:
            if "US10Y" in data_macro:
                fig_us10y = go.Figure()
                fig_us10y.add_trace(go.Scatter(
                    x=data_macro["US10Y"].index,
                    y=data_macro["US10Y"]["Close"],
                    mode='lines',
                    name='US10Y',
                    line=dict(color='#ee0979', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(238, 9, 121, 0.2)'
                ))
                fig_us10y.update_layout(
                    title="US10Y - Bono 10 años (Yield %)",
                    template='plotly_dark',
                    height=350,
                    hovermode='x unified',
                    xaxis_tickformat='%d %b %y'
                )
                st.plotly_chart(fig_us10y, use_container_width=True)
            
            if "Plata" in data_macro:
                fig_plata = go.Figure()
                fig_plata.add_trace(go.Scatter(
                    x=data_macro["Plata"].index,
                    y=data_macro["Plata"]["Close"],
                    mode='lines',
                    name='Plata',
                    line=dict(color='#C0C0C0', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(192, 192, 192, 0.2)'
                ))
                fig_plata.update_layout(
                    title="Plata (XAG)",
                    template='plotly_dark',
                    height=350,
                    hovermode='x unified',
                    xaxis_tickformat='%d %b %y'
                )
                st.plotly_chart(fig_plata, use_container_width=True)
    else:
        st.warning("No se pudieron cargar datos macro. Verifica tu conexión.")

# Footer con info de actualización
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"**Última actualización:** {datetime.now().strftime('%H:%M:%S')}")

with col2:
    st.markdown(f"**Próxima actualización:** {REFRESH_INTERVAL}s")

with col3:
    st.markdown("**Símbolo:** GC=F (Gold Futures)")

# Auto-refresh
time.sleep(REFRESH_INTERVAL)
st.rerun()
