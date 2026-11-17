import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path

# Pad naar CVS bestanden
DATA_DIR = Path(__file__).resolve().parents[1] / "agendapunten_besluitvorming" / "CVS_files"

for csv_file in DATA_DIR.glob("*.csv"):
    variable_name = f"{csv_file.stem}"
    globals()[variable_name] = pd.read_csv(csv_file)

# Rijen met ngative duraties verwijderen
fact_activiteit = fact_activiteit[fact_activiteit.duur_minuten >= 0]
fact_activiteit_besluit = fact_activiteit_besluit[fact_activiteit_besluit.duur_minuten >= 0]

# Omzetten juiste datatypes
fact_activiteit["datum"] = pd.to_datetime(fact_activiteit["datum"])

dim_activiteit["datum"] = pd.to_datetime(dim_activiteit["datum"])
dim_activiteit["aanvangstijd"] = pd.to_datetime(dim_activiteit["aanvangstijd"])
dim_activiteit["eindtijd"] = pd.to_datetime(dim_activiteit["eindtijd"])

dim_fractie["datum_actief"] = pd.to_datetime(dim_fractie["datum_actief"])
dim_fractie["datum_inactief"] = pd.to_datetime(dim_fractie["datum_inactief"])

# normaliseren
dim_besluit['uitkomst'] = dim_besluit['uitkomst'].str.lower()

#---------------------------------------------
# Filters (in sidebar)
#---------------------------------------------

# datum filter
min_date = min(fact_activiteit['datum'])
max_date = max(fact_activiteit['datum'])

all_dates = st.sidebar.checkbox("Alle datums", value=True)

if all_dates:
    datums = (min_date, max_date)
else:
    datums = st.sidebar.date_input(
        'Selecteer de gewenste datums',
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format='DD/MM/YYYY')    

# Besluit soort filter
besluit_soorten = st.sidebar.multiselect(
    "Besluit soorten",
    dim_besluit['uitkomst'].dropna().unique().tolist(),
    default = dim_besluit['uitkomst'].dropna().unique().tolist())

# Fracties filter
nu_fracties = dim_fractie.loc[dim_fractie['datum_inactief'
    ].isna(), 'fractie_norm'].reset_index(drop=True)
oude_fracties = dim_fractie.loc[~dim_fractie['fractie_norm'
    ].isin(nu_fracties), 'fractie_norm'].reset_index(drop=True)

all_fracties = st.sidebar.checkbox("Alle fracties (ook inactieve fracties)", 
                                   value = True)

if all_fracties:
    fracties = dim_fractie['fractie_norm'].dropna().unique().tolist()
else:
    huidige_fracties = st.sidebar.multiselect(
        "Huidige fracties",
        sorted(nu_fracties.tolist()))

    inactieve_fracties = st.sidebar.multiselect(
        "Oude fracties",
        sorted(oude_fracties.tolist()))

    fracties = huidige_fracties + inactieve_fracties

###
# Voorkomen error weergave tijdens instellen filters
###

# Checked of de datumselectie incompleet is
# Geeft aan wat moet gebeuren om dashboard te laden de 
if len(datums) != 2:
    st.warning("Selecteer een startdatum en een einddatum om het dashboard te laden.")

# Checked besluitenfilter leeg is
# Geeft aan wat moet gebeuren om dashboard te laden 
if len(besluit_soorten) == 0:
    st.warning("Selecteer minstens 1 besluitsoort om het dashboard te laden.")

# Checked fractiefilter leeg is
# Geeft aan wat moet gebeuren om dashboard te laden 
if len(fracties) == 0:
    st.warning("Selecteer minstens 1 fractie om het dashboard te laden.")

# Stopt het laden van het dashboard als 1 van de filters incorrect is
if len(datums) != 2 or len(besluit_soorten) == 0 or len(fracties) == 0:
    st.stop()
    
###
# Filters toepassen
###

# ID's selecteren die onder de filter instellingen passen
selected_activiteit_ids = fact_activiteit.loc[
    fact_activiteit['datum'].between(
        pd.to_datetime(datums[0]), pd.to_datetime(datums[1])), 'activiteit_id']

selected_besluit_ids = dim_besluit.loc[
    dim_besluit['uitkomst'].isin(besluit_soorten), 'besluit_id']

selected_fractie_ids = dim_fractie.loc[
    dim_fractie['fractie_norm'].isin(fracties), 'fractie_id']

selected_zaak_ids = set(bridge_zaak_actor.loc[
    bridge_zaak_actor['fractie_id'].isin(selected_fractie_ids), 'zaak_id'])

# Centrale feitentabel filteren
f_fact_activiteit_besluit = fact_activiteit_besluit[
    fact_activiteit_besluit['besluit_id'].isin(selected_besluit_ids)
    & fact_activiteit_besluit['zaak_id'].isin(selected_zaak_ids)
    & fact_activiteit_besluit['activiteit_id'].isin(selected_activiteit_ids)].copy()

# ID's selecteren die rekening houden met interactie filters
actual_besluit_ids = set(f_fact_activiteit_besluit['besluit_id'])
actual_zaak_ids = set(f_fact_activiteit_besluit['zaak_id'])
actual_activiteit_ids = set(f_fact_activiteit_besluit['activiteit_id'])

# Alle tabellen filteren
f_dim_activiteit = dim_activiteit[
    dim_activiteit['activiteit_id'].isin(actual_activiteit_ids)].copy()

f_fact_activiteit = fact_activiteit[
    fact_activiteit['activiteit_id'].isin(actual_activiteit_ids)].copy()

f_dim_besluit = dim_besluit[
    dim_besluit['besluit_id'].isin(actual_besluit_ids)].copy()

f_bridge_besluit_zaak = bridge_besluit_zaak[
    bridge_besluit_zaak['besluit_id'].isin(actual_besluit_ids)
    & bridge_besluit_zaak['zaak_id'].isin(actual_zaak_ids)].copy()

f_dim_zaak = dim_zaak[
    dim_zaak['zaak_id'].isin(actual_zaak_ids)].copy()

f_bridge_zaak_actor = bridge_zaak_actor[
    bridge_zaak_actor['zaak_id'].isin(actual_zaak_ids)
    & bridge_zaak_actor['fractie_id'].isin(selected_fractie_ids)].copy()

f_dim_fractie = dim_fractie[
    dim_fractie['fractie_id'].isin(selected_fractie_ids)].copy()

#---------------------------------------------
# Title and such
#---------------------------------------------

st.title("Besluiten via stemming")

#---------------------------------------------
# Cards
#---------------------------------------------

def format_besluit_perc(uitkomst):
    percentage = perc_besluiten.get(uitkomst)

    if percentage is None or pd.isna(percentage):
        return "-"
    return f"{percentage:.1f}%"
    
def format_besluit_duur(uitkomst):
    duur = gemiddelde_duur.loc[
        gemiddelde_duur['uitkomst'] == uitkomst, 'duur_minuten']

    if duur.empty or pd.isna(duur.iloc[0]):
        return "-"
    return f"{duur.iloc[0] / 60:.1f} uur"

# Eerste twee cards naast elkaar
col1, col2 = st.columns([1.2, 2.8])

# Percentage van soort besluit
with col1: 
    st.metric("**Totaal aantal besluiten**",
          f_dim_besluit['uitkomst'].notna().sum(), border = True)


perc_besluiten = (f_dim_besluit['uitkomst'].value_counts(normalize=True) * 100)

# Totaal aantal besluiten
with col2:
    with st.container(border=True):
        st.markdown(
            "<h4 style='text-align: center;'>Algemene besluitpercentages</h4>", 
            unsafe_allow_html=True)

        col_1, col_2, col_3 = st.columns(3)

        col_1.metric("Aangenomen", format_besluit_perc("aangenomen"))
        col_2.metric("Verworpen", format_besluit_perc("verworpen"))
        col_3.metric("Aangehouden", format_besluit_perc("aangehouden"))

# Gemiddelde tijd per besluit
duratie_besluiten = f_dim_besluit.merge(
    f_fact_activiteit_besluit[['besluit_id', 'duur_minuten']], 
    on='besluit_id', how='left')

gemiddelde_duur = (
    duratie_besluiten.groupby('uitkomst')['duur_minuten'].mean().reset_index())

with st.container(border=True):
    st.markdown(
        "<h4 style='text-align: center;'>Gemiddelde tijd per soort besluit</h4>",
        unsafe_allow_html=True)

    col_1, col_2, col_3 = st.columns(3)

    col_1.metric("Aangenomen", format_besluit_duur("aangenomen"))
    col_2.metric("Verworpen", format_besluit_duur("verworpen"))
    col_3.metric("Aangehouden", format_besluit_duur("aangehouden"))

#---------------------------------------------
# Dashboard graphs
#---------------------------------------------
