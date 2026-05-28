import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, date, timedelta
import os

# ─── CONFIG PAGE ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PrintCut Pro — Gestion Découpe",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = "decoupe_activites.db"

# ─── BASE DE DONNÉES ────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS activites (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT    NOT NULL,
            heure_debut TEXT,
            heure_fin   TEXT,
            operateur   TEXT    NOT NULL,
            client      TEXT    NOT NULL,
            type_travail TEXT   NOT NULL,
            description TEXT,
            matiere     TEXT,
            quantite    REAL    NOT NULL,
            unite       TEXT    NOT NULL,
            nb_poses    INTEGER DEFAULT 0,
            statut      TEXT    NOT NULL DEFAULT 'Terminé',
            priorite    TEXT    NOT NULL DEFAULT 'Normale',
            notes       TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    # Seed demo data if empty
    c.execute("SELECT COUNT(*) FROM activites")
    if c.fetchone()[0] == 0:
        _seed_demo(c)
    conn.commit()
    conn.close()


def _seed_demo(c):
    today = date.today()
    demo = [
        (str(today - timedelta(days=6)), "08:00", "10:30", "Moussa K.", "Brakina SA", "Découpe étiquettes", "Étiquettes bières 33cl", "Papier couché", 5000, "unités", 50, "Terminé", "Haute", "Lot urgent"),
        (str(today - timedelta(days=5)), "09:00", "11:00", "Fatou S.", "SONABHY", "Découpe autocollants", "Stickers signalétique", "Vinyle blanc", 1200, "unités", 24, "Terminé", "Normale", ""),
        (str(today - timedelta(days=5)), "14:00", "16:30", "Moussa K.", "LONAB", "Découpe carton", "Boîtes emballage", "Carton 350g", 800, "feuilles", 16, "Terminé", "Normale", ""),
        (str(today - timedelta(days=4)), "08:30", "12:00", "Ibrahim T.", "Coris Bank", "Découpe étiquettes", "Étiquettes adhésives", "Papier couché", 10000, "unités", 100, "Terminé", "Haute", "Travail répété mensuel"),
        (str(today - timedelta(days=3)), "10:00", "11:30", "Fatou S.", "ONEA", "Découpe vinyle", "Panneaux signalétique", "Vinyle bâché", 50, "m²", 10, "Terminé", "Normale", ""),
        (str(today - timedelta(days=2)), "08:00", "09:30", "Ibrahim T.", "Air Burkina", "Découpe étiquettes", "Bagages tags", "Papier synthétique", 3000, "unités", 30, "Terminé", "Urgente", "Vol départ demain"),
        (str(today - timedelta(days=1)), "11:00", "13:00", "Moussa K.", "Ministère Santé", "Découpe autocollants", "Stickers campagne", "Vinyle blanc", 2500, "unités", 50, "Terminé", "Haute", ""),
        (str(today), "08:00", "10:00", "Fatou S.", "Brakina SA", "Découpe étiquettes", "Étiquettes 75cl", "Papier couché", 4000, "unités", 40, "En cours", "Haute", "Suite commande semaine passée"),
        (str(today), "10:30", None, "Ibrahim T.", "Client Privé", "Découpe carton", "Boîtes cadeaux", "Carton 300g", 200, "feuilles", 4, "En attente", "Normale", "Paiement en attente"),
    ]
    c.executemany("""
        INSERT INTO activites
          (date, heure_debut, heure_fin, operateur, client, type_travail, description,
           matiere, quantite, unite, nb_poses, statut, priorite, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, demo)


def get_conn():
    return sqlite3.connect(DB_PATH)


def load_all():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM activites ORDER BY date DESC, id DESC", conn)
    conn.close()
    return df


def insert_activite(data: dict):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO activites
          (date, heure_debut, heure_fin, operateur, client, type_travail, description,
           matiere, quantite, unite, nb_poses, statut, priorite, notes)
        VALUES (:date, :heure_debut, :heure_fin, :operateur, :client, :type_travail,
                :description, :matiere, :quantite, :unite, :nb_poses, :statut, :priorite, :notes)
    """, data)
    conn.commit()
    conn.close()


def delete_activite(act_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM activites WHERE id=?", (act_id,))
    conn.commit()
    conn.close()


def update_activite(act_id: int, data: dict):
    conn = get_conn()
    conn.execute("""
        UPDATE activites SET
            date=:date, heure_debut=:heure_debut, heure_fin=:heure_fin,
            operateur=:operateur, client=:client, type_travail=:type_travail,
            description=:description, matiere=:matiere, quantite=:quantite,
            unite=:unite, nb_poses=:nb_poses, statut=:statut, priorite=:priorite,
            notes=:notes
        WHERE id=:id
    """, {**data, "id": act_id})
    conn.commit()
    conn.close()


# ─── CONSTANTES ─────────────────────────────────────────────────────────────────
TYPES_TRAVAIL = [
    "Découpe étiquettes", "Découpe autocollants", "Découpe carton",
    "Découpe vinyle", "Découpe papier", "Découpe PVC",
    "Découpe bâche", "Découpe fond perdu", "Autre"
]
MATIERES = [
    "Papier couché", "Papier offset", "Papier synthétique",
    "Vinyle blanc", "Vinyle transparent", "Vinyle bâché",
    "Carton 250g", "Carton 300g", "Carton 350g",
    "PVC rigide", "Bâche PVC", "Kraft", "Autre"
]
UNITES = ["unités", "feuilles", "m²", "mètres", "rouleaux"]
STATUTS = ["Terminé", "En cours", "En attente", "Annulé"]
PRIORITES = ["Normale", "Haute", "Urgente"]
OPERATEURS = ["Moussa K.", "Fatou S.", "Ibrahim T.", "Autre"]

STATUT_COLOR = {
    "Terminé":    "#22c55e",
    "En cours":   "#3b82f6",
    "En attente": "#f59e0b",
    "Annulé":     "#ef4444",
}
PRIORITE_BADGE = {
    "Normale": "🟢",
    "Haute":   "🟡",
    "Urgente": "🔴",
}

# ─── CSS ────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Root ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3, h4 {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
}

/* ── Background ── */
.stApp {
    background: #0d0f14;
    color: #e8eaf0;
}
section[data-testid="stSidebar"] {
    background: #12151d !important;
    border-right: 1px solid #1e2130;
}
section[data-testid="stSidebar"] * {
    color: #c8ccd8 !important;
}

/* ── Metric Cards ── */
[data-testid="metric-container"] {
    background: #161921;
    border: 1px solid #1e2130;
    border-radius: 14px;
    padding: 20px 24px !important;
    transition: border-color .25s;
}
[data-testid="metric-container"]:hover {
    border-color: #ff6b35;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 2rem !important;
    color: #ff6b35 !important;
}
[data-testid="stMetricLabel"] {
    color: #8891a8 !important;
    font-size: .78rem !important;
    text-transform: uppercase;
    letter-spacing: .08em;
}

/* ── Buttons ── */
.stButton > button {
    background: #ff6b35 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: .04em;
    padding: 0.55rem 1.4rem !important;
    transition: all .2s;
}
.stButton > button:hover {
    background: #e85c28 !important;
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(255,107,53,.3);
}
.stButton > button[kind="secondary"] {
    background: #1e2130 !important;
    color: #c8ccd8 !important;
}

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea, .stSelectbox select,
.stNumberInput input, .stDateInput input, .stTimeInput input {
    background: #161921 !important;
    border: 1px solid #1e2130 !important;
    border-radius: 8px !important;
    color: #e8eaf0 !important;
}
.stSelectbox > div > div {
    background: #161921 !important;
    border: 1px solid #1e2130 !important;
    border-radius: 8px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #12151d;
    border-radius: 10px;
    gap: 4px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 7px;
    color: #8891a8;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    padding: 8px 20px;
}
.stTabs [aria-selected="true"] {
    background: #ff6b35 !important;
    color: #fff !important;
}

/* ── Dataframe ── */
.stDataFrame {
    border: 1px solid #1e2130 !important;
    border-radius: 10px;
    overflow: hidden;
}

/* ── Dividers ── */
hr { border-color: #1e2130; }

/* ── Section headers ── */
.section-header {
    display: flex; align-items: center; gap: 12px;
    padding: 16px 20px;
    background: #161921;
    border-left: 4px solid #ff6b35;
    border-radius: 0 10px 10px 0;
    margin-bottom: 20px;
}
.section-header span {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #e8eaf0;
    letter-spacing: .02em;
}

/* ── Activity card ── */
.act-card {
    background: #161921;
    border: 1px solid #1e2130;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    transition: border-color .2s, transform .15s;
}
.act-card:hover {
    border-color: #ff6b35;
    transform: translateY(-1px);
}
.act-card-title {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: #e8eaf0;
}
.act-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: .05em;
}
.badge-termine  { background:#22c55e22; color:#22c55e; }
.badge-en-cours { background:#3b82f622; color:#3b82f6; }
.badge-attente  { background:#f59e0b22; color:#f59e0b; }
.badge-annule   { background:#ef444422; color:#ef4444; }

/* ── Toast-like success ── */
.stSuccess {
    background: #22c55e22 !important;
    border-left: 4px solid #22c55e !important;
    border-radius: 8px !important;
}

/* ── Sidebar nav ── */
.sidebar-nav-item {
    padding: 10px 14px;
    border-radius: 8px;
    cursor: pointer;
    transition: background .15s;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    font-size: .92rem;
    color: #8891a8;
}
.sidebar-nav-item:hover { background: #1e2130; color: #e8eaf0; }
.sidebar-nav-item.active { background: #ff6b3522; color: #ff6b35; }

/* ── Table alternating rows ── */
.styled-table { width:100%; border-collapse:collapse; font-size:.85rem; }
.styled-table th {
    background:#1e2130; color:#8891a8;
    text-transform:uppercase; letter-spacing:.07em;
    font-size:.72rem; padding:10px 14px; text-align:left;
}
.styled-table td { padding:10px 14px; border-bottom:1px solid #1a1d28; color:#c8ccd8; }
.styled-table tr:hover td { background:#1a1d28; }
</style>
""", unsafe_allow_html=True)


# ─── HELPERS ────────────────────────────────────────────────────────────────────
def section_title(icon, text):
    st.markdown(
        f'<div class="section-header"><span style="font-size:1.3rem">{icon}</span>'
        f'<span>{text}</span></div>',
        unsafe_allow_html=True,
    )


def statut_badge(statut):
    cls_map = {
        "Terminé": "termine",
        "En cours": "en-cours",
        "En attente": "attente",
        "Annulé": "annule",
    }
    return (f'<span class="act-badge badge-{cls_map.get(statut,"")}">'
            f'{statut}</span>')


def compute_duree(h_debut, h_fin):
    try:
        fmt = "%H:%M"
        d = datetime.strptime(h_fin, fmt) - datetime.strptime(h_debut, fmt)
        mins = int(d.total_seconds() / 60)
        return f"{mins//60}h{mins%60:02d}"
    except Exception:
        return "—"


# ─── PAGES ──────────────────────────────────────────────────────────────────────

def page_dashboard(df):
    st.markdown(
        "<h1 style='font-size:2rem;margin-bottom:4px'>✂️ PrintCut Pro</h1>"
        "<p style='color:#8891a8;margin-top:0;font-size:.95rem'>"
        "Tableau de bord — Machine de découpe</p>",
        unsafe_allow_html=True,
    )

    today_str = str(date.today())
    df_today  = df[df["date"] == today_str]
    df_week   = df[df["date"] >= str(date.today() - timedelta(days=6))]
    df_month  = df[df["date"] >= str(date.today().replace(day=1))]

    # KPI row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Activités aujourd'hui",  len(df_today))
    col2.metric("Cette semaine",          len(df_week))
    col3.metric("Ce mois",                len(df_month))
    col4.metric("Qté totale (semaine)",   f"{df_week['quantite'].sum():,.0f}")
    col5.metric("Taux terminé (sem.)",
                f"{(df_week[df_week['statut']=='Terminé'].shape[0]/max(len(df_week),1)*100):.0f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([3, 2])

    # ── Bar chart activités / jour ──
    with left:
        section_title("📊", "Activités des 14 derniers jours")
        df_14 = df[df["date"] >= str(date.today() - timedelta(days=13))]
        if not df_14.empty:
            counts = df_14.groupby("date").size().reset_index(name="nb")
            fig = px.bar(
                counts, x="date", y="nb",
                color_discrete_sequence=["#ff6b35"],
                labels={"date": "", "nb": "Activités"},
            )
            fig.update_layout(
                plot_bgcolor="#161921", paper_bgcolor="#161921",
                font_color="#8891a8",
                xaxis=dict(gridcolor="#1e2130", tickfont_size=11),
                yaxis=dict(gridcolor="#1e2130", tickfont_size=11),
                margin=dict(l=0, r=0, t=10, b=0),
                height=250,
            )
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas de données sur les 14 derniers jours.")

    # ── Donut types de travail ──
    with right:
        section_title("🍩", "Répartition par type")
        if not df_week.empty:
            type_counts = df_week["type_travail"].value_counts().reset_index()
            type_counts.columns = ["type", "nb"]
            fig2 = px.pie(
                type_counts, names="type", values="nb", hole=.55,
                color_discrete_sequence=px.colors.sequential.Oranges_r,
            )
            fig2.update_layout(
                plot_bgcolor="#161921", paper_bgcolor="#161921",
                font_color="#8891a8",
                legend=dict(font_size=10, bgcolor="#161921"),
                margin=dict(l=0, r=0, t=10, b=0),
                height=250,
            )
            fig2.update_traces(textfont_size=11)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Pas de données cette semaine.")

    # ── Activités du jour ──
    section_title("📅", f"Activités du jour — {date.today().strftime('%A %d %B %Y').capitalize()}")
    if df_today.empty:
        st.info("Aucune activité enregistrée aujourd'hui.")
    else:
        for _, row in df_today.iterrows():
            duree = compute_duree(row.get("heure_debut",""), row.get("heure_fin",""))
            st.markdown(f"""
<div class="act-card">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <span class="act-card-title">{row['type_travail']} — {row['client']}</span>
    <span style="display:flex;gap:8px;align-items:center">
      {PRIORITE_BADGE.get(row['priorite'],'')}
      {statut_badge(row['statut'])}
    </span>
  </div>
  <div style="margin-top:8px;font-size:.82rem;color:#8891a8;display:flex;gap:20px;flex-wrap:wrap">
    <span>👤 {row['operateur']}</span>
    <span>🕐 {row.get('heure_debut','?')} → {row.get('heure_fin','?')} ({duree})</span>
    <span>📦 {row['quantite']:,.0f} {row['unite']}</span>
    <span>🧱 {row.get('matiere','—')}</span>
    {"<span>📝 " + row['notes'] + "</span>" if row.get('notes') else ""}
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Quantités par opérateur ──
    section_title("👷", "Performance opérateurs (cette semaine)")
    if not df_week.empty:
        agg = df_week[df_week["statut"]=="Terminé"].groupby("operateur").agg(
            nb_jobs=("id","count"),
            qte_totale=("quantite","sum"),
        ).reset_index().sort_values("nb_jobs", ascending=False)
        fig3 = make_subplots(specs=[[{"secondary_y": True}]])
        fig3.add_trace(go.Bar(
            x=agg["operateur"], y=agg["nb_jobs"],
            name="Nb jobs", marker_color="#ff6b35",
        ), secondary_y=False)
        fig3.add_trace(go.Scatter(
            x=agg["operateur"], y=agg["qte_totale"],
            name="Qté totale", mode="lines+markers",
            line=dict(color="#60a5fa", width=2),
            marker=dict(size=8),
        ), secondary_y=True)
        fig3.update_layout(
            plot_bgcolor="#161921", paper_bgcolor="#161921",
            font_color="#8891a8",
            legend=dict(bgcolor="#161921"),
            height=270,
            margin=dict(l=0, r=0, t=10, b=0),
        )
        fig3.update_yaxes(gridcolor="#1e2130", secondary_y=False)
        fig3.update_yaxes(gridcolor="#1e2130", secondary_y=True)
        st.plotly_chart(fig3, use_container_width=True)


def page_saisie():
    section_title("➕", "Enregistrer une activité de découpe")

    with st.form("form_activite", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            f_date = st.date_input("📅 Date", value=date.today())
        with c2:
            f_debut = st.text_input("🕐 Heure début (HH:MM)", placeholder="08:30")
        with c3:
            f_fin   = st.text_input("🕑 Heure fin (HH:MM)", placeholder="10:00")

        c4, c5 = st.columns(2)
        with c4:
            f_op = st.selectbox("👤 Opérateur", OPERATEURS)
        with c5:
            f_client = st.text_input("🏢 Client *", placeholder="Nom du client")

        c6, c7 = st.columns(2)
        with c6:
            f_type = st.selectbox("⚙️ Type de travail *", TYPES_TRAVAIL)
        with c7:
            f_matiere = st.selectbox("🧱 Matière", MATIERES)

        f_desc = st.text_input("📝 Description du travail", placeholder="Ex: Étiquettes bières 33cl — format 70x40mm")

        c8, c9, c10, c11 = st.columns(4)
        with c8:
            f_qte = st.number_input("📦 Quantité *", min_value=0.0, step=100.0)
        with c9:
            f_unite = st.selectbox("Unité", UNITES)
        with c10:
            f_poses = st.number_input("🗂️ Nb poses", min_value=0, step=1, value=0)
        with c11:
            f_statut = st.selectbox("✅ Statut", STATUTS)

        c12, c13 = st.columns(2)
        with c12:
            f_prio = st.selectbox("🚦 Priorité", PRIORITES)
        with c13:
            f_notes = st.text_input("💬 Notes", placeholder="Remarques, consignes...")

        submitted = st.form_submit_button("💾 Enregistrer l'activité", use_container_width=True)

    if submitted:
        errors = []
        if not f_client.strip():
            errors.append("Le champ **Client** est obligatoire.")
        if f_qte <= 0:
            errors.append("La **Quantité** doit être supérieure à 0.")
        for h, label in [(f_debut, "Heure début"), (f_fin, "Heure fin")]:
            if h and len(h) == 5:
                try:
                    datetime.strptime(h, "%H:%M")
                except ValueError:
                    errors.append(f"**{label}** : format invalide (HH:MM attendu).")
        if errors:
            for e in errors:
                st.error(e)
        else:
            insert_activite({
                "date": str(f_date),
                "heure_debut": f_debut or None,
                "heure_fin":   f_fin or None,
                "operateur":   f_op,
                "client":      f_client.strip(),
                "type_travail": f_type,
                "description": f_desc,
                "matiere":     f_matiere,
                "quantite":    f_qte,
                "unite":       f_unite,
                "nb_poses":    f_poses,
                "statut":      f_statut,
                "priorite":    f_prio,
                "notes":       f_notes,
            })
            st.success("✅ Activité enregistrée avec succès !")
            st.balloons()


def page_historique(df):
    section_title("📋", "Historique des activités")

    # ── Filtres ──
    with st.expander("🔍 Filtres", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            f_date_min = st.date_input("Du", value=date.today() - timedelta(days=30))
        with fc2:
            f_date_max = st.date_input("Au", value=date.today())
        with fc3:
            f_ops = st.multiselect("Opérateur", options=sorted(df["operateur"].unique()))
        with fc4:
            f_statuts = st.multiselect("Statut", options=STATUTS)

        fc5, fc6, fc7 = st.columns(3)
        with fc5:
            f_types = st.multiselect("Type de travail", options=TYPES_TRAVAIL)
        with fc6:
            f_client_search = st.text_input("Recherche client", placeholder="Nom…")
        with fc7:
            f_prios = st.multiselect("Priorité", options=PRIORITES)

    # Appliquer filtres
    mask = (
        (df["date"] >= str(f_date_min)) &
        (df["date"] <= str(f_date_max))
    )
    if f_ops:       mask &= df["operateur"].isin(f_ops)
    if f_statuts:   mask &= df["statut"].isin(f_statuts)
    if f_types:     mask &= df["type_travail"].isin(f_types)
    if f_prios:     mask &= df["priorite"].isin(f_prios)
    if f_client_search:
        mask &= df["client"].str.contains(f_client_search, case=False, na=False)

    filtered = df[mask].copy()
    st.markdown(f"<span style='color:#8891a8;font-size:.85rem'>{len(filtered)} activité(s) trouvée(s)</span>",
                unsafe_allow_html=True)

    if filtered.empty:
        st.info("Aucune activité ne correspond aux filtres sélectionnés.")
        return

    # ── Affichage tableau ──
    filtered["Durée"] = filtered.apply(
        lambda r: compute_duree(r.get("heure_debut",""), r.get("heure_fin","")), axis=1
    )
    display_cols = ["date","operateur","client","type_travail",
                    "quantite","unite","statut","priorite","Durée"]
    rename = {
        "date": "Date", "operateur": "Opérateur", "client": "Client",
        "type_travail": "Type", "quantite": "Quantité", "unite": "Unité",
        "statut": "Statut", "priorite": "Priorité",
    }
    st.dataframe(
        filtered[display_cols].rename(columns=rename).reset_index(drop=True),
        use_container_width=True, height=400,
    )

    # ── Export CSV ──
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exporter CSV",
        data=csv,
        file_name=f"decoupe_{f_date_min}_{f_date_max}.csv",
        mime="text/csv",
    )

    # ── Suppression ──
    st.markdown("---")
    section_title("🗑️", "Supprimer une activité")
    col_del1, col_del2 = st.columns([2, 1])
    with col_del1:
        ids_options = filtered["id"].tolist()
        labels = [
            f"#{r['id']} — {r['date']} — {r['client']} — {r['type_travail']}"
            for _, r in filtered.iterrows()
        ]
        id_map = dict(zip(labels, ids_options))
        sel_label = st.selectbox("Choisir l'activité à supprimer", options=labels)
    with col_del2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Supprimer", type="secondary"):
            delete_activite(id_map[sel_label])
            st.success("Activité supprimée.")
            st.rerun()


def page_statistiques(df):
    section_title("📈", "Statistiques & Analyses")

    # Sélecteur de période
    period = st.selectbox(
        "Période d'analyse",
        ["7 derniers jours", "30 derniers jours", "Ce mois-ci", "Tout l'historique"],
    )
    today = date.today()
    if period == "7 derniers jours":
        df_p = df[df["date"] >= str(today - timedelta(days=6))]
    elif period == "30 derniers jours":
        df_p = df[df["date"] >= str(today - timedelta(days=29))]
    elif period == "Ce mois-ci":
        df_p = df[df["date"] >= str(today.replace(day=1))]
    else:
        df_p = df.copy()

    if df_p.empty:
        st.info("Pas de données pour cette période.")
        return

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total activités",          len(df_p))
    k2.metric("Activités terminées",       len(df_p[df_p["statut"]=="Terminé"]))
    k3.metric("Quantité totale découpée",  f"{df_p['quantite'].sum():,.0f}")
    k4.metric("Nombre de poses total",     f"{df_p['nb_poses'].sum():,.0f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Ligne 1 ──
    r1c1, r1c2 = st.columns(2)

    with r1c1:
        st.markdown("#### Statuts des travaux")
        stat_counts = df_p["statut"].value_counts().reset_index()
        stat_counts.columns = ["statut","nb"]
        colors = [STATUT_COLOR.get(s,"#888") for s in stat_counts["statut"]]
        fig = px.pie(stat_counts, names="statut", values="nb", hole=.5,
                     color_discrete_sequence=colors)
        fig.update_layout(
            plot_bgcolor="#161921", paper_bgcolor="#161921",
            font_color="#8891a8", height=280,
            margin=dict(l=0,r=0,t=20,b=0),
            legend=dict(bgcolor="#161921"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with r1c2:
        st.markdown("#### Types de travaux")
        type_q = df_p.groupby("type_travail")["quantite"].sum().sort_values(ascending=True).reset_index()
        fig2 = px.bar(type_q, x="quantite", y="type_travail", orientation="h",
                      color_discrete_sequence=["#ff6b35"],
                      labels={"quantite":"Quantité totale","type_travail":""})
        fig2.update_layout(
            plot_bgcolor="#161921", paper_bgcolor="#161921",
            font_color="#8891a8", height=280,
            margin=dict(l=0,r=0,t=20,b=0),
            xaxis=dict(gridcolor="#1e2130"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Ligne 2 ──
    r2c1, r2c2 = st.columns(2)

    with r2c1:
        st.markdown("#### Top clients (par nombre de jobs)")
        top_clients = df_p.groupby("client").agg(
            nb_jobs=("id","count"),
            qte=("quantite","sum")
        ).sort_values("nb_jobs", ascending=False).head(8).reset_index()
        fig3 = px.bar(top_clients, x="client", y="nb_jobs",
                      color="qte",
                      color_continuous_scale="Oranges",
                      labels={"nb_jobs":"Nb jobs","client":"","qte":"Quantité"})
        fig3.update_layout(
            plot_bgcolor="#161921", paper_bgcolor="#161921",
            font_color="#8891a8", height=300,
            margin=dict(l=0,r=0,t=20,b=0),
            xaxis=dict(tickangle=-30),
            yaxis=dict(gridcolor="#1e2130"),
            coloraxis_colorbar=dict(bgcolor="#161921"),
        )
        st.plotly_chart(fig3, use_container_width=True)

    with r2c2:
        st.markdown("#### Répartition matières utilisées")
        mat = df_p["matiere"].value_counts().reset_index()
        mat.columns = ["matiere","nb"]
        fig4 = px.pie(mat.head(8), names="matiere", values="nb",
                      color_discrete_sequence=px.colors.sequential.Oranges_r)
        fig4.update_layout(
            plot_bgcolor="#161921", paper_bgcolor="#161921",
            font_color="#8891a8", height=300,
            margin=dict(l=0,r=0,t=20,b=0),
            legend=dict(bgcolor="#161921", font_size=10),
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ── Activités / jour (courbe) ──
    st.markdown("#### Évolution quotidienne des activités")
    daily = df_p.groupby("date").agg(
        nb_jobs=("id","count"),
        qte_totale=("quantite","sum"),
    ).reset_index()
    fig5 = make_subplots(specs=[[{"secondary_y": True}]])
    fig5.add_trace(go.Bar(
        x=daily["date"], y=daily["nb_jobs"],
        name="Nb activités", marker_color="#ff6b3566",
        marker_line_color="#ff6b35", marker_line_width=1,
    ), secondary_y=False)
    fig5.add_trace(go.Scatter(
        x=daily["date"], y=daily["qte_totale"],
        name="Quantité totale", mode="lines+markers",
        line=dict(color="#60a5fa", width=2),
        marker=dict(size=7, color="#60a5fa"),
    ), secondary_y=True)
    fig5.update_layout(
        plot_bgcolor="#161921", paper_bgcolor="#161921",
        font_color="#8891a8",
        legend=dict(bgcolor="#161921"),
        height=300,
        margin=dict(l=0,r=0,t=20,b=0),
    )
    fig5.update_yaxes(gridcolor="#1e2130")
    st.plotly_chart(fig5, use_container_width=True)

    # ── Tableau récapitulatif par opérateur ──
    st.markdown("#### Tableau de performance par opérateur")
    op_stats = df_p.groupby("operateur").agg(
        nb_activites=("id","count"),
        nb_termines=("statut", lambda x: (x=="Terminé").sum()),
        qte_totale=("quantite","sum"),
        nb_clients=("client","nunique"),
        nb_poses=("nb_poses","sum"),
    ).reset_index()
    op_stats["taux_terme"] = (op_stats["nb_termines"]/op_stats["nb_activites"]*100).round(1).astype(str)+"%"
    op_stats = op_stats.rename(columns={
        "operateur":"Opérateur","nb_activites":"Activités",
        "nb_termines":"Terminés","qte_totale":"Qté totale",
        "nb_clients":"Clients","nb_poses":"Poses","taux_terme":"Taux terminé"
    })
    st.dataframe(op_stats, use_container_width=True, hide_index=True)


# ─── MAIN ────────────────────────────────────────────────────────────────────────
def main():
    init_db()
    inject_css()

    # ── Sidebar ──
    with st.sidebar:
        st.markdown(
            "<div style='padding:20px 10px 10px'>"
            "<p style='font-family:Syne,sans-serif;font-size:1.3rem;"
            "font-weight:800;color:#ff6b35;margin:0'>✂️ PrintCut Pro</p>"
            "<p style='font-size:.75rem;color:#555;margin:0;margin-top:2px'>"
            "Gestion Machine Découpe</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        pages = {
            "🏠 Tableau de bord":   "dashboard",
            "➕ Saisir une activité": "saisie",
            "📋 Historique":         "historique",
            "📈 Statistiques":       "stats",
        }
        if "page" not in st.session_state:
            st.session_state.page = "dashboard"

        for label, key in pages.items():
            active = "active" if st.session_state.page == key else ""
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()

        st.markdown("---")
        st.markdown(
            "<p style='font-size:.72rem;color:#444;padding:0 10px;line-height:1.5'>"
            f"🗓️ {date.today().strftime('%d/%m/%Y')}<br>"
            "Base de données locale SQLite</p>",
            unsafe_allow_html=True,
        )

    # ── Contenu ──
    df = load_all()
    page = st.session_state.page

    if page == "dashboard":
        page_dashboard(df)
    elif page == "saisie":
        page_saisie()
    elif page == "historique":
        page_historique(df)
    elif page == "stats":
        page_statistiques(df)


if __name__ == "__main__":
    main()
