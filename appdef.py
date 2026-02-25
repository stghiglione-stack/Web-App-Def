import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import urllib.parse

st.set_page_config(page_title="Universal EV Planner PRO", layout="wide", page_icon="⚡")

# --- STILE E TITOLO ---
st.title("⚡ Universal EV Planner & Maps")
st.markdown("Pianifica i tuoi viaggi con la strategia dell'80%: ricariche più veloci e massima salute della batteria.")

# --- SIDEBAR: CONFIGURAZIONE ---
st.sidebar.header("1. Configurazione Auto")
modello_auto = st.sidebar.text_input("Modello Auto:", "Ford Puma Gen-E")
capacita_batteria = st.sidebar.number_input("Batteria Utilizzabile (kWh):", min_value=10.0, value=43.0)
consumo_medio = st.sidebar.number_input("Consumo Medio (kWh/km):", value=0.18)

st.sidebar.header("2. Sicurezza e Costi")
costo_kwh = st.sidebar.number_input("Costo Energia (€/kWh):", value=0.60)
margine_emergenza_km = st.sidebar.slider("Margine Emergenza (Km)", 10, 100, 30)

st.sidebar.header("3. Preferenze Ricarica")
provider_pref = st.sidebar.text_input("Operatore preferito (es: Tutte, Enel X, Tesla):", "Tutte")

st.sidebar.header("4. Parametri CO2")
co2_termica = st.sidebar.number_input("Emissioni benzina (g/km):", value=120)

# --- PROGRAMMAZIONE SETTIMANALE ---
st.header("Pianificazione Settimanale")
giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
dati_input = []

for g in giorni:
    with st.expander(f"📍 {g}"):
        c1, c2, c3 = st.columns([3, 1, 1])
        dest = c1.text_input(f"Destinazione", placeholder="Es: Porto Antico, Genova", key=f"dest_{g}")
        dist_stimata = c2.number_input("Km (Solo andata)", min_value=0, value=0, key=f"km_{g}")
        ar = c3.checkbox("Andata e Ritorno", value=True, key=f"ar_{g}")
        
        km_effettivi = dist_stimata * 2 if ar else dist_stimata
        dati_input.append({"giorno": g, "dest": dest, "km": km_effettivi})

# --- LOGICA DI CALCOLO OTTIMIZZATA ---
livello_batt_kwh = capacita_batteria # Si parte col pieno
risultati = []
totale_costo = 0.0

for i in range(len(giorni)):
    km_oggi = dati_input[i]["km"]
    km_domani = dati_input[i+1]["km"] if i < 6 else 0
    dest_oggi = dati_input[i]["dest"]
    
    energia_consumata_oggi = km_oggi * consumo_medio
    livello_fine = livello_batt_kwh - energia_consumata_oggi
    
    # Check sicurezza: Batteria deve coprire (Km Domani + Emergenza)
    energia_necessaria_sicurezza = (km_domani * consumo_medio) + (margine_emergenza_km * consumo_medio)
    
    azione = "✅ Batteria OK"
    info_ricarica = "-"
    costo_ricarica = 0.0
    
    # Se la batteria scende sotto il margine di sicurezza, suggeriamo ricarica all'80%
    if livello_fine < energia_necessaria_sicurezza:
        azione = "⚡ RICARICA (80%)"
        target_80 = capacita_batteria * 0.8
        energia_da_reintegrare = max(0, target_80 - livello_fine)
        
        costo_ricarica = energia_da_reintegrare * costo_kwh
        totale_costo += costo_ricarica
        
        # Tempi stimati (efficienza 90%)
        min_lenta = int((energia_da_reintegrare / 7) * 60 / 0.9)
        min_fast = int((energia_da_reintegrare / 50) * 60 / 0.9)
        min_ultra = int((energia_da_reintegrare / 110) * 60 / 0.9)
        
        info_ricarica = f"7kW: {min_lenta}m | 50kW: {min_fast}m | >100kW: {min_ultra}m"
        livello_fine = target_80 
    
    # Link Mappe specifico per AUTO elettriche
    if provider_pref.lower() == "tutte":
        filtro_ricerca = "colonnine ricarica auto elettrica"
    else:
        filtro_ricerca = f"colonnine ricarica auto elettrica {provider_pref}"
    
    punto_riferimento = dest_oggi if dest_oggi else "me"
    query_map = urllib.parse.quote(f"{filtro_ricerca} vicino a {punto_riferimento}")
    map_link = f"http://maps.google.com/?q={query_map}"
    
    risultati.append({
        "Giorno": giorni[i],
        "Destinazione": dest_oggi if dest_oggi else "Nessuna",
        "Km": km_oggi,
        "Batt. Finale": f"{int((max(0, livello_fine)/capacita_batteria)*100)}%",
        "Nota": azione,
        "Tempi Ricarica (all'80%)": info_ricarica,
        "Mappa": map_link
    })
    livello_batt_kwh = livello_fine

# --- TABELLA RISULTATI ---
st.subheader("Tabella di Marcia")
df = pd.DataFrame(risultati)

def make_clickable(link):
    if "Nessuna" in link or "vicino a me" in link and "Nessuna" in link:
        return "-"
    return f'<a href="{link}" target="_blank">🔍 Cerca Colonnine</a>'

df['Mappa'] = df['Mappa'].apply(make_clickable)
st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

# --- ANALISI AMBIENTALE E COSTI ---
tot_km = sum(d["km"] for d in dati_input)
co2_sett = (tot_km * co2_termica) / 1000

st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Distanza Totale", f"{tot_km} km")
c2.metric("Spesa Energia (Target 80%)", f"€ {totale_costo:.2f}")
c3.metric("CO2 Risparmiata", f"{co2_sett:.2f} kg", "🌱")

# Grafico Proiezione
st.subheader("📊 Impatto Green")
periodi = ['Settimana', 'Mese', 'Anno']
valori = [co2_sett, co2_sett*4.3, co2_sett*52]
fig = go.Figure(go.Bar(x=periodi, y=valori, marker_color='#2ecc71', text=[f"{v:.1f}kg" for v in valori], textposition='auto'))
fig.update_layout(template="plotly_white", yaxis_title="CO2 risparmiata (kg)")
st.plotly_chart(fig, use_container_width=True)

if st.button("Pulisci tutti i dati"):
    st.rerun()
