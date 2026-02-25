import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import urllib.parse

st.set_page_config(page_title="Universal EV Planner PRO", layout="wide", page_icon="⚡")

# --- FUNZIONE PER PULIRE TUTTI I CAMPI ---
def reset_form():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- SIDEBAR ---
st.sidebar.header("1. Punto di Partenza (Casa)")
# Usiamo una chiave specifica per la sidebar
casa_input = st.sidebar.text_input("Indirizzo di casa/partenza:", value="Genova, Italia", key="casa_sidebar")

st.sidebar.header("2. Configurazione Auto")
modello_auto = st.sidebar.text_input("Modello Auto:", "Ford Puma Gen-E")
capacita_batteria = st.sidebar.number_input("Batteria Utilizzabile (kWh):", min_value=10.0, value=43.0)
consumo_medio = st.sidebar.number_input("Consumo Medio (kWh/km):", value=0.18)

st.sidebar.header("3. Sicurezza e Costi")
costo_kwh = st.sidebar.number_input("Costo Energia (€/kWh):", value=0.60)
margine_emergenza_km = st.sidebar.slider("Margine Emergenza (Km)", 10, 100, 30)

st.sidebar.header("4. Preferenze Ricarica")
provider_pref = st.sidebar.text_input("Operatore (es: Tutte, Enel X, Tesla):", "Tutte")

# --- PROGRAMMAZIONE SETTIMANALE ---
st.header("Pianificazione Settimanale")
giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
dati_input = []

for g in giorni:
    with st.expander(f"📍 {g}"):
        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        
        # TRUCCO: Usiamo il valore della sidebar direttamente come default 'value'
        # Se l'utente non scrive nulla nel campo del giorno, prenderà sempre l'aggiornamento dalla sidebar
        partenza = c1.text_input(
            f"Punto di Partenza", 
            value=casa_input, 
            key=f"start_{g}"
        )
        
        dest = c2.text_input(f"Destinazione", placeholder="Es: Savona, Italia", key=f"dest_{g}")
        dist_stimata = c3.number_input("Km (Solo andata)", min_value=0, key=f"km_{g}")
        ar = c4.checkbox("Andata e Ritorno", value=True, key=f"ar_{g}")
        
        km_effettivi = dist_stimata * 2 if ar else dist_stimata
        dati_input.append({
            "giorno": g, 
            "start": partenza,
            "dest": dest, 
            "km": km_effettivi,
            "ar": ar
        })

# --- LOGICA DI CALCOLO ---
livello_batt_kwh = capacita_batteria
risultati = []
totale_costo = 0.0

for i in range(len(giorni)):
    km_oggi = dati_input[i]["km"]
    km_domani = dati_input[i+1]["km"] if i < 6 else 0
    dest_oggi = dati_input[i]["dest"]
    partenza_oggi = dati_input[i]["start"]
    is_ar = dati_input[i]["ar"]
    
    energia_consumata_oggi = km_oggi * consumo_medio
    livello_fine = livello_batt_kwh - energia_consumata_oggi
    
    energia_necessaria_sicurezza = (km_domani * consumo_medio) + (margine_emergenza_km * consumo_medio)
    
    azione = "✅ Batteria OK"
    info_ricarica = "-"
    
    if livello_fine < energia_necessaria_sicurezza:
        azione = "⚡ RICARICA (80%)"
        target_80 = capacita_batteria * 0.8
        energia_da_reintegrare = max(0, target_80 - livello_fine)
        totale_costo += energia_da_reintegrare * costo_kwh
        
        min_lenta = int((energia_da_reintegrare / 7) * 60 / 0.9)
        min_fast = int((energia_da_reintegrare / 50) * 60 / 0.9)
        min_ultra = int((energia_da_reintegrare / 110) * 60 / 0.9)
        info_ricarica = f"7kW: {min_lenta}m | 50kW: {min_fast}m | >100kW: {min_ultra}m"
        livello_fine = target_80 
    
    # Logica Mappa: A/R -> Cerca vicino a casa | Sola Andata -> Cerca a destinazione
    punto_ricerca = partenza_oggi if is_ar else dest_oggi
    if not punto_ricerca: punto_ricerca = "me"
    
    filtro = "colonnine ricarica auto elettrica" if provider_pref.lower() == "tutte" else f"colonnine ricarica auto elettrica {provider_pref}"
    query = urllib.parse.quote(f"{filtro} vicino a {punto_ricerca}")
    map_link = f"https://www.google.com/maps/search/{query}"
    
    risultati.append({
        "Giorno": giorni[i],
        "Percorso": f"{partenza_oggi} ➔ {dest_oggi}" if dest_oggi else "Nessuno",
        "Km": km_oggi,
        "Batt. Finale": f"{int((max(0, livello_fine)/capacita_batteria)*100)}%",
        "Nota": azione,
        "Ricarica (80%)": info_ricarica,
        "Mappa": map_link
    })
    livello_batt_kwh = livello_fine

# --- TABELLA E GRAFICO ---
st.subheader("Tabella di Marcia")
df = pd.DataFrame(risultati)
def make_clickable(link):
    return f'<a href="{link}" target="_blank">🔍 Trova Colonnine</a>' if "Nessuno" not in link else "-"
df['Mappa'] = df['Mappa'].apply(make_clickable)
st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

# Metriche e Grafico
tot_km = sum(d["km"] for d in dati_input)
co2_sett = (tot_km * 120) / 1000
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Distanza Totale", f"{tot_km} km")
c2.metric("Spesa Energia (80%)", f"€ {totale_costo:.2f}")
c3.metric("CO2 Risparmiata", f"{co2_sett:.2f} kg", "🌱")

st.subheader("📊 Impatto Green nel Tempo")
fig = go.Figure(data=[go.Bar(x=['Settimana', 'Mese', 'Anno'], y=[co2_sett, co2_sett*4.3, co2_sett*52], marker_color='#2ecc71')])
st.plotly_chart(fig, use_container_width=True)

# --- PULSANTE DI RESET ---
st.button("🗑️ Pulisci tutti i dati", on_click=reset_form, use_container_width=True)
