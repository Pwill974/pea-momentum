import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION STYLE PRO ---
st.set_page_config(page_title="Tableau de Bord PEA - Institutionnel", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); border: 1px solid #e9ecef; }
    div.stButton > button:first-child { background-color: #007bff; color: white; border-radius: 5px; }
    .status-badge { padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. CONFIGURATION DES ACTIFS ---
assets = {
    "États-Unis (S&P 500)": "IVV",
    "Europe (Stoxx 600)": "VGK",
    "Émergents (MSCI EM)": "EEM",
    "Monde (Socle Principal)": "ACWI"
}

@st.cache_data(ttl=3600)
def load_data():
    dict_data = {}
    all_tickers = list(assets.values()) + ["^VIX"]
    
    for ticker in all_tickers:
        try:
            df_hist = yf.download(ticker, period="2y", progress=False, auto_adjust=True)
            if not df_hist.empty:
                if isinstance(df_hist.columns, pd.MultiIndex):
                    dict_data[ticker] = df_hist['Close'][ticker]
                else:
                    dict_data[ticker] = df_hist['Close']
        except Exception:
            pass
            
    return pd.DataFrame(dict_data).ffill()

data = load_data()

# --- 2. CALCULS STRATÉGIQUES AVANCÉS ---
moms = {}
vix = float(data["^VIX"].iloc[-1]) if "^VIX" in data.columns and not data["^VIX"].empty else 15.0
market_stress = "Crise / Alerte" if vix > 25 else "Opportunité / Calme" if vix < 15 else "Normal"

for name, ticker in assets.items():
    if ticker in data.columns and len(data[ticker]) >= 126:
        current = float(data[ticker].iloc[-1])
        past = float(data[ticker].iloc[-126]) # 6 mois
        
        sma200_series = data[ticker].rolling(200).mean()
        sma200 = float(sma200_series.iloc[-1]) if len(sma200_series) >= 200 else current
        
        score = ((current / past) - 1) * 100
        trend_ok = current > sma200
        
        # Logique des feux tricolores
        if score > 0 and trend_ok:
            status = "🟢 ACHAT FORTE TENDANCE"
        elif score > 0 or trend_ok:
            status = "🟠 PRUDENCE / NEUTRE"
        else:
            status = "🔴 VENTE / SÉCURITÉ"
            
        moms[name] = {
            "Score Momentum (6m)": f"{score:.2f}%",
            "Prix Actuel": f"{current:.2f}$",
            "Au-dessus SMA 200": "Oui" if trend_ok else "Non",
            "Distance SMA 200": f"{(((current / sma200) - 1) * 100):.2f}%",
            "Statut Système": status,
            "_score_raw": score,
            "_trend_raw": trend_ok
        }

# Recherche du vainqueur sur les 3 zones de la poche Momentum (on exclut le Monde global de la compétition)
poche_momentum_assets = {k: v for k, v in moms.items() if k != "Monde (Socle Principal)"}
winner = max(poche_momentum_assets, key=lambda x: poche_momentum_assets[x]["_score_raw"])

# Sécurité VIX interne
signal_final = winner
if vix > 25:
    signal_final = "CASH / SÉCURITÉ COMPTE ESPÈCES"

# --- 3. INTERFACE PRINCIPALE ---
st.title("🏛️ Terminal Quantitaire - PEA Momentum Pro")
st.write(f"Flux d'analyse institutionnel mis à jour le : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
st.markdown("---")

# Métriques du haut
col_sig, col_vix, col_stress = st.columns(3)
with col_sig:
    st.metric("🚨 ACTION STRATÉGIQUE DU MOIS", signal_final)
with col_vix:
    st.metric("📊 INDICE VIX (VOLATILITÉ)", f"{vix:.2f}", delta=market_stress, delta_color="inverse")
with col_stress:
    st.metric("🔥 MEILLEUR MOMENTUM TRÈS COURT TERME", moms[winner]["Score Momentum (6m)"])

# --- 4. ASSISTANT D'ORDRE DE BOURSE (SIDEBAR) ---
st.sidebar.header("🧮 Assistant d'Ordre Fortuneo")
st.sidebar.write("Entrez vos chiffres pour obtenir le script exact de vos achats du mois.")

capital_total = st.sidebar.number_input("Valeur totale actuelle du PEA (€)", value=10000, step=500)
apport_mois = st.sidebar.number_input("Versement ce mois-ci (€)", value=1000, step=100)

total_a_repartir = capital_total + apport_mois
poche_tranquille = total_a_repartir * 0.50
poche_momentum_val = total_a_repartir * 0.50

st.sidebar.markdown("---")
st.sidebar.subheader("📝 Votre feuille de route à copier :")
st.sidebar.info(f"**1. Poche Tranquillité (Achat aveugle) :**\nAlimenter l'ETF MSCI World (WPEA) pour cibler un montant total de **{poche_tranquille:,.0f} €**.")
if signal_final != "CASH / SÉCURITÉ COMPTE ESPÈCES":
    st.sidebar.success(f"**2. Poche Momentum (Suivi) :**\nPlacer l'argent de cette poche sur l'actif : **{signal_final}** pour cibler un montant de **{poche_momentum_val:,.0f} €**.")
else:
    st.sidebar.error(f"**2. Poche Momentum (Alerte Risque) :**\nLaissez **{poche_momentum_val:,.0f} €** non investis sur le Compte Espèces de votre PEA.")

# --- 5. GRAPHIQUE DE PERFORMANCE ---
st.subheader("📈 Graphique de force relative (6 derniers mois)")
fig = go.Figure()
for name, ticker in assets.items():
    if ticker in data.columns and len(data[ticker]) >= 126:
        norm_series = (data[ticker].tail(126) / data[ticker].iloc[-126]) * 100
        is_winner = (name == winner)
        fig.add_trace(go.Scatter(
            x=norm_series.index, 
            y=norm_series, 
            name=name, 
            line=dict(width=3.5 if is_winner else 1.5, color="#28a745" if is_winner else None)
        ))

fig.update_layout(template="plotly_white", hovermode="x unified", height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

# --- 6. TABLEAU DE SYNTHÈSE DES MARCHÉS ---
st.subheader("📋 Matrice de Décision Spécifique")
df_display = pd.DataFrame(moms).T[[ "Prix Actuel", "Score Momentum (6m)", "Au-dessus SMA 200", "Distance SMA 200", "Statut Système"]]
st.table(df_display)
