import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import urllib.parse

st.set_page_config(page_title="Universal EV Planner PRO", layout="wide", page_icon="⚡")

# --- STILE E TITOLO ---
st.title("⚡ Universal EV Planner & Maps")
st.markdown("Pianifica i tuoi viaggi: calcolo km dalla tua abitazione e ricerca colonnine intelligente.")

# --- SIDEBAR: CONFIGURAZIONE ---
st.sidebar.header("1. Punto di Partenza (Casa)")
# Punto di partenza predefinito ma modificabile
casa_default = st.sidebar.text_input("Indirizzo di casa/partenza:", "Genova, Italia")

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
        partenza = c1.text_input(f"Punto di Partenza", value=casa_default, key=f"start_{g}")
        dest = c2.text_input(f"Destinazione", placeholder="Es: Savona, Italia", key=f"dest_{g}")
        dist_stimata = c3.number_input("Km (Solo andata)", min_value=0, value=0, key=f"km_{g}")
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
    costo_ricarica = 0.0
    
    if livello_fine < energia_necessaria_sicurezza:
        azione = "⚡ RICARICA (80%)"
        target_80 = capacita_batteria * 0.8
        energia_da_reintegrare = max(0, target_80 - livello_fine)
        costo_ricarica = energia_da_reintegrare * costo_kwh
        totale_costo += costo_ricarica
        
        min_lenta = int((energia_da_reintegrare / 7) * 60 / 0.9)
        min_fast = int((energia_da_reintegrare / 50) * 60 / 0.9)
        min_ultra = int((energia_da_reintegrare / 110) * 60 / 0.9)
        info_ricarica = f"7kW: {min_lenta}m | 50kW: {min_fast}m | >100kW: {min_ultra}m"
        livello_fine = target_80 
    
    # --- LOGICA MAPPA INTELLIGENTE ---
    # Se A/R -> Cerca vicino alla partenza (ritorno a casa)
    # Se Sola Andata -> Cerca vicino alla destinazione
    punto_ricerca = partenza_oggi if is_ar else dest_oggi
    if not punto_ricerca or punto_ricerca == "": punto_ricerca = "me"
    
    if provider_pref.lower() == "tutte":
        filtro_ricerca = "colonnine ricarica auto elettrica"
    else:
        filtro_ricerca = f"colonnine ricarica auto elettrica {provider_pref}"
    
    query_map = urllib.parse.quote(f"{filtro_ricerca} vicino a {punto_ricerca}")
    map_link = f"https://www.google.com/maps/search/{query_map}"
    
    risultati.append({
        "Giorno": giorni[i],
        "Percorso": f"{partenza_oggi} ➔ {dest_oggi}" if dest_oggi else "Nessuno",
        "Tipo": "A/R" if is_ar else "Solo Andata",
        "Km": km_oggi,
        "Batt. Finale": f"{int((max(0, livello_fine)/capacita_batteria)*100)}%",
        "Nota": azione,
        "Tempi Ricarica (80%)": info_ricarica,
        "Mappa": map_link
    })
    livello_batt_kwh = livello_fine

# --- TABELLA E GRAFICI ---
st.subheader("Tabella di Marcia")
df = pd.DataFrame(risultati)

def make_clickable(link):
    if "Nessuno" in link: return "-"
    return f'<a href="{link}" target="_blank">🔍 Colonnine a fine viaggio</a>'

df['Mappa'] = df['Mappa'].apply(make_clickable)
st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

# (Statistiche CO2 e Distanza rimangono invariate...)
tot_km = sum(d["km"] for d in dati_input)
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Distanza Totale", f"{tot_km} km")
c2.metric("Spesa Energia (Target 80%)", f"€ {totale_costo:.2f}")
st.info("I link 'Mappa' cercheranno colonnine alla fine del tuo percorso (casa per A/R, destinazione per sola andata).")
