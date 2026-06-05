import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION STYLE ---
st.set_page_config(page_title="Momentum Strategy Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; border-radius: 10px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 1. CHARGEMENT DES DONNÉES SÉCURISÉ ---
assets = {
    "USA (S&P 500)": "SPY",
    "EUROPE (Stoxx 600)": "VGK",
    "EMERGING (MSCI EM)": "EEM",
    "MONDE (Socle)": "ACWI"
}

@st.cache_data(ttl=3600)
def load_data():
    dict_data = {}
    all_tickers = list(assets.values()) + ["^VIX"]
    
    # On télécharge chaque actif individuellement pour garantir la réception des prix
    for ticker in all_tickers:
        try:
            ticker_data = yf.Ticker(ticker, session=None)
            df_hist = ticker_data.history(period="2y")
            if not df_hist.empty:
                dict_data[ticker] = df_hist['Close']
        except Exception as e:
            st.error(f"Erreur de téléchargement pour {ticker}")
            
    return pd.DataFrame(dict_data).ffill() # Remplit les éventuelles cases vides par la dernière valeur connue

data = load_data()

# --- 2. LOGIQUE DE CALCUL ---
moms = {}
vix = data["^VIX"].iloc[-1] if "^VIX" in data.columns else 15.0
market_stress = "Élevé" if vix > 25 else "Calme" if vix < 15 else "Normal"

for name, ticker in assets.items():
    if ticker in data.columns:
        current = data[ticker].iloc[-1]
        past = data[ticker].iloc[-126] # Environ 6 mois de bourse
        sma200 = data[ticker].rolling(200).mean().iloc[-1]
        
        moms[name] = {
            "score": ((current / past) - 1) * 100,
            "price": current,
            "trend": current > sma200,
            "dist_sma": ((current / sma200) - 1) * 100
        }
    else:
        # Valeurs de secours au cas où un ticker manque au premier lancement
        moms[name] = {"score": 0.0, "price": 0.0, "trend": False, "dist_sma": 0.0}

winner = max(moms, key=lambda x: moms[x]["score"])

# --- 3. INTERFACE HAUTE (KPIs) ---
st.title("🏆 Stratégie Momentum Pro")
st.write(f"Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')}")

col_sig, col_vix, col_stress = st.columns(3)
with col_sig:
    status_color = "green" if (moms[winner]["score"] > 0 and moms[winner]["trend"]) else "red"
    st.metric("SIGNAL ACTUEL", winner if status_color == "green" else "CASH / SÉCURITÉ")

with col_vix:
    st.metric("INDICE VIX (PEUR)", f"{vix:.2f}", delta=market_stress, delta_color="inverse")

with col_stress:
    st.metric("MOMENTUM GAGNANT", f"{moms[winner]['score']:.2f}%")

# --- 4. GRAPHIQUE INTERACTIF ---
st.subheader("📊 Comparaison de Performance (Normalisée 100)")
fig = go.Figure()
for name, ticker in assets.items():
    if ticker in data.columns:
        norm_series = (data[ticker].tail(126) / data[ticker].iloc[-126]) * 100
        fig.add_trace(go.Scatter(x=norm_series.index, y=norm_series, name=name, line=dict(width=3 if name == winner else 1.5)))

fig.update_layout(template="plotly_white", hovermode="x unified", height=500)
st.plotly_chart(fig, use_container_width=True)

# --- 5. CALCULATEUR RETRAITE ---
st.sidebar.header("🎯 Objectif Retraite")
cap_actuel = st.sidebar.number_input("Capital Actuel (€)", value=10000)
versement_mensuel = st.sidebar.number_input("Versement Mensuel (€)", value=1000)
taux_retrait = 0.04

st.sidebar.markdown("---")
revenu_potentiel = (cap_actuel * taux_retrait) / 12
st.sidebar.write(f"Revenu mensuel générable actuel : **{revenu_potentiel:.2f} € / mois**")

# --- 6. TABLEAU RÉCAPITULATIF ---
st.subheader("📋 État de santé des marchés")
df_status = pd.DataFrame(moms).T
st.table(df_status.style.format({"score": "{:.2f}%", "price": "{:.2f}$", "dist_sma": "{:.2f}%"}))

