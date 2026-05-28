"""
PrintCut Pro v2 — Gestion découpe avec auth, factures, stats
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, date, timedelta
import os, io

import auth as AUTH
from facture import generer_facture_pdf

# ── Config page ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PrintCut Pro",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = "decoupe_activites.db"

# ── Init DB ────────────────────────────────────────────────────────────────────
def init_db():
    AUTH.init_users_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS activites (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT NOT NULL,
            heure_debut  TEXT,
            heure_fin    TEXT,
            operateur    TEXT NOT NULL,
            client       TEXT NOT NULL,
            type_travail TEXT NOT NULL,
            description  TEXT,
            matiere      TEXT,
            quantite     REAL NOT NULL,
            unite        TEXT NOT NULL,
            nb_poses     INTEGER DEFAULT 0,
            statut       TEXT NOT NULL DEFAULT 'Terminé',
            priorite     TEXT NOT NULL DEFAULT 'Normale',
            notes        TEXT,
            created_by   TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS factures (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            numero           TEXT NOT NULL UNIQUE,
            date_facture     TEXT NOT NULL,
            date_echeance    TEXT,
            activite_id      INTEGER,
            client_nom       TEXT NOT NULL,
            client_adresse   TEXT,
            client_ville     TEXT,
            client_telephone TEXT,
            client_email     TEXT,
            lignes_json      TEXT,
            montant_ht       REAL NOT NULL DEFAULT 0,
            taux_tva         REAL NOT NULL DEFAULT 0.18,
            montant_ttc      REAL NOT NULL DEFAULT 0,
            statut_paiement  TEXT NOT NULL DEFAULT 'En attente',
            moyen_paiement   TEXT,
            notes            TEXT,
            created_by       TEXT,
            created_at       TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("SELECT COUNT(*) FROM activites")
    if c.fetchone()[0] == 0:
        _seed_demo(c)
    conn.commit()
    conn.close()


def _seed_demo(c):
    today = date.today()
    demo = [
        (str(today-timedelta(6)), "08:00","10:30","Moussa K.","Brakina SA","Découpe étiquettes","Étiquettes bières 33cl","Papier couché",5000,"unités",50,"Terminé","Haute","Lot urgent","admin"),
        (str(today-timedelta(5)), "09:00","11:00","Fatou S.","SONABHY","Découpe autocollants","Stickers signalétique","Vinyle blanc",1200,"unités",24,"Terminé","Normale","","admin"),
        (str(today-timedelta(5)), "14:00","16:30","Moussa K.","LONAB","Découpe carton","Boîtes emballage","Carton 350g",800,"feuilles",16,"Terminé","Normale","","admin"),
        (str(today-timedelta(4)), "08:30","12:00","Ibrahim T.","Coris Bank","Découpe étiquettes","Étiquettes adhésives","Papier couché",10000,"unités",100,"Terminé","Haute","Travail répété mensuel","admin"),
        (str(today-timedelta(3)), "10:00","11:30","Fatou S.","ONEA","Découpe vinyle","Panneaux signalétique","Vinyle bâché",50,"m²",10,"Terminé","Normale","","admin"),
        (str(today-timedelta(2)), "08:00","09:30","Ibrahim T.","Air Burkina","Découpe étiquettes","Bagages tags","Papier synthétique",3000,"unités",30,"Terminé","Urgente","Vol départ demain","admin"),
        (str(today-timedelta(1)), "11:00","13:00","Moussa K.","Ministère Santé","Découpe autocollants","Stickers campagne","Vinyle blanc",2500,"unités",50,"Terminé","Haute","","admin"),
        (str(today), "08:00","10:00","Fatou S.","Brakina SA","Découpe étiquettes","Étiquettes 75cl","Papier couché",4000,"unités",40,"En cours","Haute","Suite commande","admin"),
        (str(today), "10:30",None,"Ibrahim T.","Client Privé","Découpe carton","Boîtes cadeaux","Carton 300g",200,"feuilles",4,"En attente","Normale","Paiement en attente","admin"),
    ]
    c.executemany("""INSERT INTO activites
        (date,heure_debut,heure_fin,operateur,client,type_travail,description,matiere,
         quantite,unite,nb_poses,statut,priorite,notes,created_by)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", demo)


def get_conn(): return sqlite3.connect(DB_PATH)

def load_all(user=None):
    conn = get_conn()
    if user and user.get("role") == "operateur":
        df = pd.read_sql(
            "SELECT * FROM activites WHERE operateur=? ORDER BY date DESC, id DESC",
            conn, params=(user["nom_complet"],)
        )
    else:
        df = pd.read_sql("SELECT * FROM activites ORDER BY date DESC, id DESC", conn)
    conn.close()
    return df

def load_factures():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM factures ORDER BY created_at DESC", conn)
    conn.close()
    return df

def insert_activite(data):
    conn = get_conn()
    conn.execute("""INSERT INTO activites
        (date,heure_debut,heure_fin,operateur,client,type_travail,description,matiere,
         quantite,unite,nb_poses,statut,priorite,notes,created_by)
        VALUES(:date,:heure_debut,:heure_fin,:operateur,:client,:type_travail,:description,
               :matiere,:quantite,:unite,:nb_poses,:statut,:priorite,:notes,:created_by)""", data)
    conn.commit(); conn.close()

def delete_activite(act_id):
    conn = get_conn()
    conn.execute("DELETE FROM activites WHERE id=?", (act_id,))
    conn.commit(); conn.close()

def insert_facture(data):
    import json
    conn = get_conn()
    conn.execute("""INSERT INTO factures
        (numero,date_facture,date_echeance,activite_id,client_nom,client_adresse,client_ville,
         client_telephone,client_email,lignes_json,montant_ht,taux_tva,montant_ttc,
         statut_paiement,moyen_paiement,notes,created_by)
        VALUES(:numero,:date_facture,:date_echeance,:activite_id,:client_nom,:client_adresse,
               :client_ville,:client_telephone,:client_email,:lignes_json,:montant_ht,:taux_tva,
               :montant_ttc,:statut_paiement,:moyen_paiement,:notes,:created_by)""", data)
    conn.commit(); conn.close()

def next_facture_number():
    conn = get_conn()
    year = date.today().year
    c = conn.execute("SELECT COUNT(*) FROM factures WHERE numero LIKE ?", (f"F-{year}-%",))
    n = c.fetchone()[0] + 1
    conn.close()
    return f"F-{year}-{n:04d}"

def update_facture_statut(fid, statut):
    conn = get_conn()
    conn.execute("UPDATE factures SET statut_paiement=? WHERE id=?", (statut, fid))
    conn.commit(); conn.close()

# ── Constantes ─────────────────────────────────────────────────────────────────
TYPES_TRAVAIL = ["Découpe étiquettes","Découpe autocollants","Découpe carton",
                 "Découpe vinyle","Découpe papier","Découpe PVC","Découpe bâche","Autre"]
MATIERES      = ["Papier couché","Papier offset","Papier synthétique","Vinyle blanc",
                 "Vinyle transparent","Vinyle bâché","Carton 250g","Carton 300g",
                 "Carton 350g","PVC rigide","Bâche PVC","Kraft","Autre"]
UNITES        = ["unités","feuilles","m²","mètres","rouleaux"]
STATUTS       = ["Terminé","En cours","En attente","Annulé"]
PRIORITES     = ["Normale","Haute","Urgente"]
OPERATEURS    = ["Moussa K.","Fatou S.","Ibrahim T.","Autre"]
TVA_OPTIONS   = {"18% (standard)":0.18,"0% (exonéré)":0.0,"10%":0.10}
MOYENS_PAIE   = ["Virement bancaire","Espèces","Mobile Money","Chèque",""]
STATUTS_PAIE  = ["En attente","Payé","Partiel","Annulé"]

STATUT_COLOR = {"Terminé":"#22c55e","En cours":"#3b82f6","En attente":"#f59e0b","Annulé":"#ef4444"}
PRIO_ICON    = {"Normale":"🟢","Haute":"🟡","Urgente":"🔴"}

# ── CSS ────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
h1,h2,h3,h4{font-family:'Syne',sans-serif!important;font-weight:700!important;}
.stApp{background:#0d0f14;color:#e8eaf0;}
section[data-testid="stSidebar"]{background:#12151d!important;border-right:1px solid #1e2130;}
section[data-testid="stSidebar"] *{color:#c8ccd8!important;}
[data-testid="metric-container"]{background:#161921;border:1px solid #1e2130;border-radius:14px;padding:20px 24px!important;transition:border-color .25s;}
[data-testid="metric-container"]:hover{border-color:#ff6b35;}
[data-testid="stMetricValue"]{font-family:'Syne',sans-serif!important;font-size:2rem!important;color:#ff6b35!important;}
[data-testid="stMetricLabel"]{color:#8891a8!important;font-size:.78rem!important;text-transform:uppercase;letter-spacing:.08em;}
.stButton>button{background:#ff6b35!important;color:#fff!important;border:none!important;border-radius:8px!important;font-family:'Syne',sans-serif!important;font-weight:600!important;letter-spacing:.04em;padding:0.55rem 1.4rem!important;transition:all .2s;}
.stButton>button:hover{background:#e85c28!important;transform:translateY(-1px);box-shadow:0 6px 20px rgba(255,107,53,.3);}
.stTextInput input,.stTextArea textarea,.stNumberInput input,.stDateInput input{background:#161921!important;border:1px solid #1e2130!important;border-radius:8px!important;color:#e8eaf0!important;}
.stSelectbox>div>div{background:#161921!important;border:1px solid #1e2130!important;border-radius:8px!important;}
.stTabs [data-baseweb="tab-list"]{background:#12151d;border-radius:10px;gap:4px;padding:4px;}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:7px;color:#8891a8;font-family:'Syne',sans-serif;font-weight:600;padding:8px 20px;}
.stTabs [aria-selected="true"]{background:#ff6b35!important;color:#fff!important;}
.stDataFrame{border:1px solid #1e2130!important;border-radius:10px;overflow:hidden;}
hr{border-color:#1e2130;}
.sec-head{display:flex;align-items:center;gap:12px;padding:14px 20px;background:#161921;border-left:4px solid #ff6b35;border-radius:0 10px 10px 0;margin-bottom:18px;}
.sec-head span{font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;color:#e8eaf0;letter-spacing:.02em;}
.act-card{background:#161921;border:1px solid #1e2130;border-radius:12px;padding:14px 18px;margin-bottom:8px;transition:border-color .2s,transform .15s;}
.act-card:hover{border-color:#ff6b35;transform:translateY(-1px);}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:.72rem;font-weight:600;letter-spacing:.05em;}
.badge-T{background:#22c55e22;color:#22c55e;}
.badge-C{background:#3b82f622;color:#3b82f6;}
.badge-A{background:#f59e0b22;color:#f59e0b;}
.badge-X{background:#ef444422;color:#ef4444;}
.badge-P{background:#ff6b3522;color:#ff6b35;}
/* Login */
.login-wrap{max-width:420px;margin:80px auto 0;background:#161921;border:1px solid #1e2130;border-radius:18px;padding:40px 36px;}
.login-logo{font-family:'Syne',sans-serif;font-size:2.2rem;font-weight:800;color:#ff6b35;text-align:center;margin-bottom:4px;}
.login-sub{text-align:center;color:#8891a8;font-size:.85rem;margin-bottom:28px;}
/* User card */
.usr-card{background:#161921;border:1px solid #1e2130;border-radius:10px;padding:12px 16px;margin-bottom:8px;display:flex;align-items:center;gap:14px;}
.usr-avatar{width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.2rem;font-weight:700;flex-shrink:0;}
/* Facture card */
.fac-card{background:#161921;border:1px solid #1e2130;border-radius:12px;padding:16px 20px;margin-bottom:10px;}
</style>
"""

# ── Helpers ────────────────────────────────────────────────────────────────────
def sh(icon, text):
    st.markdown(f'<div class="sec-head"><span style="font-size:1.3rem">{icon}</span><span>{text}</span></div>', unsafe_allow_html=True)

def badge(label):
    cls = {"Terminé":"T","En cours":"C","En attente":"A","Annulé":"X","Payé":"T","Partiel":"P"}.get(label,"A")
    return f'<span class="badge badge-{cls}">{label}</span>'

def duree(hd, hf):
    try:
        d = datetime.strptime(hf,"%H:%M") - datetime.strptime(hd,"%H:%M")
        m = int(d.total_seconds()/60)
        return f"{m//60}h{m%60:02d}"
    except: return "—"

# ── Page: Login ────────────────────────────────────────────────────────────────
def page_login():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("""
<div class="login-wrap">
  <div class="login-logo">✂️ PrintCut Pro</div>
  <div class="login-sub">Système de gestion — Machine de découpe</div>
</div>
""", unsafe_allow_html=True)

    col = st.columns([1,2,1])[1]
    with col:
        with st.form("login_form"):
            username = st.text_input("👤 Identifiant", placeholder="votre identifiant")
            password = st.text_input("🔒 Mot de passe", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Connexion →", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Veuillez remplir tous les champs.")
            else:
                user = AUTH.authenticate(username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error("❌ Identifiant ou mot de passe incorrect.")

        st.markdown("""
<div style="margin-top:24px;padding:14px;background:#0d0f14;border-radius:8px;font-size:.78rem;color:#555;line-height:1.7">
<b style="color:#8891a8">Comptes par défaut :</b><br>
admin / Admin@2024! &nbsp;·&nbsp; manager / Manager@2024! &nbsp;·&nbsp; operateur / Operateur@2024!
</div>
""", unsafe_allow_html=True)

# ── Page: Dashboard ─────────────────────────────────────────────────────────────
def page_dashboard(df, user):
    st.markdown(f"<h1 style='font-size:1.9rem;margin-bottom:2px'>✂️ Tableau de bord</h1>"
                f"<p style='color:#8891a8;font-size:.88rem'>Bonjour, <b style='color:#ff6b35'>{user['nom_complet']}</b> — {date.today().strftime('%A %d %B %Y').capitalize()}</p>",
                unsafe_allow_html=True)

    tod = str(date.today())
    df_t = df[df["date"]==tod]
    df_w = df[df["date"]>=str(date.today()-timedelta(6))]
    df_m = df[df["date"]>=str(date.today().replace(day=1))]

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Aujourd'hui",   len(df_t))
    c2.metric("Cette semaine", len(df_w))
    c3.metric("Ce mois",       len(df_m))
    c4.metric("Qté semaine",   f"{df_w['quantite'].sum():,.0f}")
    c5.metric("Taux terminé",  f"{(df_w[df_w['statut']=='Terminé'].shape[0]/max(len(df_w),1)*100):.0f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    l, r = st.columns([3,2])
    with l:
        sh("📊","Activités — 14 derniers jours")
        df14 = df[df["date"]>=str(date.today()-timedelta(13))]
        if not df14.empty:
            cnt = df14.groupby("date").size().reset_index(name="n")
            fig = px.bar(cnt,x="date",y="n",color_discrete_sequence=["#ff6b35"],labels={"date":"","n":"Activités"})
            fig.update_layout(plot_bgcolor="#161921",paper_bgcolor="#161921",font_color="#8891a8",
                              xaxis=dict(gridcolor="#1e2130"),yaxis=dict(gridcolor="#1e2130"),
                              margin=dict(l=0,r=0,t=10,b=0),height=240)
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig,use_container_width=True)
    with r:
        sh("🍩","Répartition types")
        if not df_w.empty:
            tc = df_w["type_travail"].value_counts().reset_index()
            tc.columns=["type","nb"]
            fig2 = px.pie(tc,names="type",values="nb",hole=.55,color_discrete_sequence=px.colors.sequential.Oranges_r)
            fig2.update_layout(plot_bgcolor="#161921",paper_bgcolor="#161921",font_color="#8891a8",
                               legend=dict(font_size=9,bgcolor="#161921"),
                               margin=dict(l=0,r=0,t=10,b=0),height=240)
            st.plotly_chart(fig2,use_container_width=True)

    sh("📅",f"Activités du jour")
    if df_t.empty:
        st.info("Aucune activité enregistrée aujourd'hui.")
    else:
        for _,row in df_t.iterrows():
            d_str = duree(row.get("heure_debut",""),row.get("heure_fin",""))
            st.markdown(f"""<div class="act-card">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <span style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem">{row['type_travail']} — {row['client']}</span>
    <span>{PRIO_ICON.get(row['priorite'],'')} {badge(row['statut'])}</span>
  </div>
  <div style="margin-top:6px;font-size:.8rem;color:#8891a8;display:flex;gap:16px;flex-wrap:wrap">
    <span>👤 {row['operateur']}</span>
    <span>🕐 {row.get('heure_debut','?')} → {row.get('heure_fin','?')} ({d_str})</span>
    <span>📦 {row['quantite']:,.0f} {row['unite']}</span>
    <span>🧱 {row.get('matiere','—')}</span>
    {"<span>💬 "+row['notes']+"</span>" if row.get('notes') else ""}
  </div>
</div>""", unsafe_allow_html=True)

# ── Page: Saisie ────────────────────────────────────────────────────────────────
def page_saisie(user):
    sh("➕","Enregistrer une activité de découpe")
    with st.form("form_act", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        with c1: f_date  = st.date_input("📅 Date", value=date.today())
        with c2: f_deb   = st.text_input("🕐 Heure début", placeholder="08:30")
        with c3: f_fin   = st.text_input("🕑 Heure fin",   placeholder="10:00")
        c4,c5 = st.columns(2)
        with c4: f_op     = st.selectbox("👤 Opérateur", OPERATEURS)
        with c5: f_client = st.text_input("🏢 Client *")
        c6,c7 = st.columns(2)
        with c6: f_type   = st.selectbox("⚙️ Type de travail", TYPES_TRAVAIL)
        with c7: f_mat    = st.selectbox("🧱 Matière", MATIERES)
        f_desc = st.text_input("📝 Description", placeholder="Description du travail")
        c8,c9,c10,c11 = st.columns(4)
        with c8:  f_qte   = st.number_input("📦 Quantité *", min_value=0.0, step=100.0)
        with c9:  f_unit  = st.selectbox("Unité", UNITES)
        with c10: f_poses = st.number_input("Nb poses", min_value=0, step=1)
        with c11: f_stat  = st.selectbox("✅ Statut", STATUTS)
        c12,c13 = st.columns(2)
        with c12: f_prio  = st.selectbox("🚦 Priorité", PRIORITES)
        with c13: f_notes = st.text_input("💬 Notes")
        ok = st.form_submit_button("💾 Enregistrer", use_container_width=True)

    if ok:
        errs = []
        if not f_client.strip(): errs.append("Client obligatoire.")
        if f_qte <= 0:           errs.append("Quantité > 0 requise.")
        for h,l in [(f_deb,"Heure début"),(f_fin,"Heure fin")]:
            if h:
                try: datetime.strptime(h,"%H:%M")
                except: errs.append(f"{l} : format HH:MM attendu.")
        if errs:
            for e in errs: st.error(e)
        else:
            insert_activite({
                "date":str(f_date),"heure_debut":f_deb or None,"heure_fin":f_fin or None,
                "operateur":f_op,"client":f_client.strip(),"type_travail":f_type,
                "description":f_desc,"matiere":f_mat,"quantite":f_qte,"unite":f_unit,
                "nb_poses":f_poses,"statut":f_stat,"priorite":f_prio,"notes":f_notes,
                "created_by":user["username"],
            })
            st.success("✅ Activité enregistrée !")
            st.balloons()

# ── Page: Historique ────────────────────────────────────────────────────────────
def page_historique(df, user):
    sh("📋","Historique des activités")
    with st.expander("🔍 Filtres", expanded=True):
        fc1,fc2,fc3,fc4 = st.columns(4)
        with fc1: dmin = st.date_input("Du",  date.today()-timedelta(30))
        with fc2: dmax = st.date_input("Au",  date.today())
        with fc3: fops = st.multiselect("Opérateur", sorted(df["operateur"].unique()))
        with fc4: fsts = st.multiselect("Statut", STATUTS)
        fc5,fc6 = st.columns(2)
        with fc5: ftyp = st.multiselect("Type", TYPES_TRAVAIL)
        with fc6: fcli = st.text_input("Recherche client", placeholder="Nom…")

    mask = (df["date"]>=str(dmin)) & (df["date"]<=str(dmax))
    if fops: mask &= df["operateur"].isin(fops)
    if fsts: mask &= df["statut"].isin(fsts)
    if ftyp: mask &= df["type_travail"].isin(ftyp)
    if fcli: mask &= df["client"].str.contains(fcli,case=False,na=False)
    filt = df[mask].copy()

    st.markdown(f"<span style='color:#8891a8;font-size:.82rem'>{len(filt)} activité(s)</span>", unsafe_allow_html=True)
    if filt.empty:
        st.info("Aucun résultat.")
        return

    filt["Durée"] = filt.apply(lambda r: duree(r.get("heure_debut",""),r.get("heure_fin","")), axis=1)
    show = filt[["date","operateur","client","type_travail","quantite","unite","statut","priorite","Durée"]].rename(columns={
        "date":"Date","operateur":"Opérateur","client":"Client","type_travail":"Type",
        "quantite":"Quantité","unite":"Unité","statut":"Statut","priorite":"Priorité"
    }).reset_index(drop=True)
    st.dataframe(show, use_container_width=True, height=380)

    csv = filt.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Export CSV", data=csv,
                       file_name=f"decoupe_{dmin}_{dmax}.csv", mime="text/csv")

    if AUTH.has_perm(user,"historique"):
        st.markdown("---")
        sh("🗑️","Supprimer une activité")
        labels = [f"#{r['id']} — {r['date']} — {r['client']} — {r['type_travail']}" for _,r in filt.iterrows()]
        id_map = dict(zip(labels, filt["id"].tolist()))
        col1,col2 = st.columns([3,1])
        with col1: sel = st.selectbox("Activité à supprimer", options=labels)
        with col2:
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("🗑️ Supprimer"):
                delete_activite(id_map[sel])
                st.success("Supprimé."); st.rerun()

# ── Page: Statistiques ──────────────────────────────────────────────────────────
def page_stats(df):
    sh("📈","Statistiques & Analyses")
    period = st.selectbox("Période", ["7 derniers jours","30 derniers jours","Ce mois-ci","Tout"])
    today = date.today()
    if   period=="7 derniers jours":   dfp = df[df["date"]>=str(today-timedelta(6))]
    elif period=="30 derniers jours":  dfp = df[df["date"]>=str(today-timedelta(29))]
    elif period=="Ce mois-ci":         dfp = df[df["date"]>=str(today.replace(day=1))]
    else:                              dfp = df.copy()
    if dfp.empty: st.info("Pas de données."); return

    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Total activités",   len(dfp))
    k2.metric("Terminées",         len(dfp[dfp["statut"]=="Terminé"]))
    k3.metric("Quantité totale",   f"{dfp['quantite'].sum():,.0f}")
    k4.metric("Poses total",       f"{dfp['nb_poses'].sum():,.0f}")

    st.markdown("<br>",unsafe_allow_html=True)
    r1,r2 = st.columns(2)
    with r1:
        st.markdown("#### Statuts")
        sc = dfp["statut"].value_counts().reset_index(); sc.columns=["s","n"]
        fig = px.pie(sc,names="s",values="n",hole=.5,
                     color_discrete_sequence=[STATUT_COLOR.get(s,"#888") for s in sc["s"]])
        fig.update_layout(plot_bgcolor="#161921",paper_bgcolor="#161921",font_color="#8891a8",
                          height=260,margin=dict(l=0,r=0,t=20,b=0),legend=dict(bgcolor="#161921"))
        st.plotly_chart(fig,use_container_width=True)
    with r2:
        st.markdown("#### Quantités par type")
        tq = dfp.groupby("type_travail")["quantite"].sum().sort_values().reset_index()
        fig2 = px.bar(tq,x="quantite",y="type_travail",orientation="h",
                      color_discrete_sequence=["#ff6b35"],labels={"quantite":"Quantité","type_travail":""})
        fig2.update_layout(plot_bgcolor="#161921",paper_bgcolor="#161921",font_color="#8891a8",
                           height=260,margin=dict(l=0,r=0,t=20,b=0),
                           xaxis=dict(gridcolor="#1e2130"),yaxis=dict(gridcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig2,use_container_width=True)

    r3,r4 = st.columns(2)
    with r3:
        st.markdown("#### Top clients")
        tc = dfp.groupby("client").agg(nb=("id","count"),qte=("quantite","sum")).sort_values("nb",ascending=False).head(8).reset_index()
        fig3 = px.bar(tc,x="client",y="nb",color="qte",color_continuous_scale="Oranges",
                      labels={"nb":"Nb jobs","client":"","qte":"Quantité"})
        fig3.update_layout(plot_bgcolor="#161921",paper_bgcolor="#161921",font_color="#8891a8",
                           height=280,margin=dict(l=0,r=0,t=20,b=0),
                           xaxis=dict(tickangle=-30),yaxis=dict(gridcolor="#1e2130"),
                           coloraxis_colorbar=dict(bgcolor="#161921"))
        st.plotly_chart(fig3,use_container_width=True)
    with r4:
        st.markdown("#### Matières utilisées")
        mt = dfp["matiere"].value_counts().reset_index(); mt.columns=["m","n"]
        fig4 = px.pie(mt.head(8),names="m",values="n",color_discrete_sequence=px.colors.sequential.Oranges_r)
        fig4.update_layout(plot_bgcolor="#161921",paper_bgcolor="#161921",font_color="#8891a8",
                           height=280,margin=dict(l=0,r=0,t=20,b=0),legend=dict(bgcolor="#161921",font_size=9))
        st.plotly_chart(fig4,use_container_width=True)

    st.markdown("#### Tableau de performance opérateurs")
    op = dfp.groupby("operateur").agg(
        Activités=("id","count"),
        Terminés=("statut",lambda x:(x=="Terminé").sum()),
        Qté=("quantite","sum"),Clients=("client","nunique"),Poses=("nb_poses","sum")
    ).reset_index()
    op["Taux"] = (op["Terminés"]/op["Activités"]*100).round(1).astype(str)+"%"
    st.dataframe(op.rename(columns={"operateur":"Opérateur"}), use_container_width=True, hide_index=True)

# ── Page: Factures ──────────────────────────────────────────────────────────────
def page_factures(df_act, user):
    tab1, tab2 = st.tabs(["📄 Créer une facture", "📚 Mes factures"])

    with tab1:
        sh("📄","Nouvelle facture / reçu")
        st.markdown("<p style='color:#8891a8;font-size:.85rem'>Renseignez les informations pour générer un document PDF professionnel.</p>", unsafe_allow_html=True)

        c1,c2 = st.columns(2)
        with c1:
            st.markdown("##### 🏢 Votre imprimerie (émetteur)")
            em_nom  = st.text_input("Nom de l'imprimerie *", value="Mon Imprimerie SARL")
            em_adr  = st.text_input("Adresse", value="Avenue de la Nation, Secteur 4")
            em_vil  = st.text_input("Ville", value="Ouagadougou, Burkina Faso")
            em_tel  = st.text_input("Téléphone", value="+226 XX XX XX XX")
            em_mail = st.text_input("Email", value="contact@imprimerie.bf")
            em_rccm = st.text_input("RCCM (optionnel)")
            em_ifu  = st.text_input("IFU (optionnel)")
        with c2:
            st.markdown("##### 👤 Client")
            cli_nom = st.text_input("Nom du client *")
            cli_adr = st.text_input("Adresse client")
            cli_vil = st.text_input("Ville client")
            cli_tel = st.text_input("Téléphone client")
            cli_mail= st.text_input("Email client")

        st.markdown("##### 📋 Lignes de facturation")
        st.caption("Ajoutez autant de lignes que nécessaire.")

        if "facture_lignes" not in st.session_state:
            st.session_state.facture_lignes = [{"description":"","qte":1,"unite":"unités","pu":0.0}]

        lignes = st.session_state.facture_lignes
        to_remove = []
        for i, lg in enumerate(lignes):
            lc1,lc2,lc3,lc4,lc5 = st.columns([4,1.2,1.5,2,0.6])
            with lc1: lg["description"] = st.text_input(f"Description #{i+1}", value=lg["description"], key=f"ld{i}", label_visibility="collapsed" if i>0 else "visible", placeholder="Description du service")
            with lc2: lg["qte"]  = st.number_input("Qté", value=float(lg["qte"]),  min_value=0.0, key=f"lq{i}", label_visibility="collapsed" if i>0 else "visible")
            with lc3: lg["unite"]= st.selectbox("Unité",  UNITES, index=UNITES.index(lg["unite"]) if lg["unite"] in UNITES else 0, key=f"lu{i}", label_visibility="collapsed" if i>0 else "visible")
            with lc4: lg["pu"]   = st.number_input("P.U. FCFA", value=float(lg["pu"]), min_value=0.0, step=500.0, key=f"lp{i}", label_visibility="collapsed" if i>0 else "visible")
            with lc5:
                st.markdown("<br>",unsafe_allow_html=True)
                if st.button("✕", key=f"rm{i}"): to_remove.append(i)

        for i in reversed(to_remove):
            lignes.pop(i)
            st.rerun()

        if st.button("+ Ajouter une ligne"):
            lignes.append({"description":"","qte":1,"unite":"unités","pu":0.0})
            st.rerun()

        # Calcul en direct
        ht = sum(float(lg["qte"])*float(lg["pu"]) for lg in lignes)
        tva_lbl = st.selectbox("TVA", list(TVA_OPTIONS.keys()))
        tva_rate = TVA_OPTIONS[tva_lbl]
        tva_amt  = ht * tva_rate
        ttc      = ht + tva_amt

        col_t1,col_t2,col_t3 = st.columns(3)
        col_t1.metric("Montant HT",  f"{ht:,.0f} FCFA")
        col_t2.metric(f"TVA {tva_lbl}", f"{tva_amt:,.0f} FCFA")
        col_t3.metric("Total TTC",   f"{ttc:,.0f} FCFA")

        st.markdown("##### ⚙️ Options")
        co1,co2,co3 = st.columns(3)
        with co1: stat_p  = st.selectbox("Statut paiement", STATUTS_PAIE)
        with co2: moyen_p = st.selectbox("Moyen de paiement", MOYENS_PAIE)
        with co3: echeance= st.text_input("Échéance", placeholder="Ex: 30 jours, À réception")
        f_notes = st.text_area("Notes / Conditions", height=70)

        lien_act = None
        if not df_act.empty:
            acts = ["Aucune"] + [f"#{r['id']} — {r['date']} — {r['client']} — {r['type_travail']}" for _,r in df_act.iterrows()]
            sel_act = st.selectbox("Lier à une activité (optionnel)", acts)
            if sel_act != "Aucune":
                lien_act = int(sel_act.split("—")[0].replace("#","").strip())

        if st.button("🖨️ Générer le PDF et enregistrer", use_container_width=True):
            errs = []
            if not em_nom.strip():  errs.append("Nom de l'imprimerie obligatoire.")
            if not cli_nom.strip(): errs.append("Nom du client obligatoire.")
            if not any(float(lg["pu"])>0 for lg in lignes): errs.append("Au moins une ligne doit avoir un prix.")
            if errs:
                for e in errs: st.error(e)
            else:
                import json
                num = next_facture_number()
                today_str = str(date.today())
                pdf_data = {
                    "numero_facture": num,
                    "date_facture":   today_str,
                    "date_echeance":  echeance or "À réception",
                    "emetteur": {"nom":em_nom,"adresse":em_adr,"ville":em_vil,
                                 "telephone":em_tel,"email":em_mail,"rccm":em_rccm,"ifu":em_ifu},
                    "client":   {"nom":cli_nom,"adresse":cli_adr,"ville":cli_vil,
                                 "telephone":cli_tel,"email":cli_mail},
                    "lignes":        lignes,
                    "taux_tva":      tva_rate,
                    "notes":         f_notes,
                    "statut_paiement": stat_p,
                    "moyen_paiement":  moyen_p,
                }
                pdf_bytes = generer_facture_pdf(pdf_data)
                insert_facture({
                    "numero":num,"date_facture":today_str,"date_echeance":echeance or "À réception",
                    "activite_id":lien_act,"client_nom":cli_nom,"client_adresse":cli_adr,
                    "client_ville":cli_vil,"client_telephone":cli_tel,"client_email":cli_mail,
                    "lignes_json":json.dumps(lignes),"montant_ht":ht,"taux_tva":tva_rate,
                    "montant_ttc":ttc,"statut_paiement":stat_p,"moyen_paiement":moyen_p,
                    "notes":f_notes,"created_by":user["username"],
                })
                st.success(f"✅ Facture **{num}** générée !")
                st.download_button(
                    label=f"📥 Télécharger {num}.pdf",
                    data=pdf_bytes,
                    file_name=f"{num}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.session_state.facture_lignes = [{"description":"","qte":1,"unite":"unités","pu":0.0}]

    with tab2:
        sh("📚","Historique des factures")
        df_fac = load_factures()
        if df_fac.empty:
            st.info("Aucune facture générée.")
            return
        for _,row in df_fac.iterrows():
            stat_col = {"Payé":"#22c55e","En attente":"#f59e0b","Partiel":"#ff6b35","Annulé":"#ef4444"}.get(row["statut_paiement"],"#888")
            st.markdown(f"""<div class="fac-card">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div>
      <span style="font-family:Syne,sans-serif;font-weight:700;font-size:1rem">{row['numero']}</span>
      <span style="color:#8891a8;font-size:.82rem;margin-left:12px">📅 {row['date_facture']}</span>
    </div>
    <span style="color:{stat_col};font-weight:600;font-size:.82rem">{row['statut_paiement']}</span>
  </div>
  <div style="margin-top:6px;font-size:.82rem;color:#8891a8;display:flex;gap:20px;flex-wrap:wrap">
    <span>👤 {row['client_nom']}</span>
    <span>💰 HT : {row['montant_ht']:,.0f} FCFA</span>
    <span>💵 TTC : {row['montant_ttc']:,.0f} FCFA</span>
    {f"<span>💳 {row['moyen_paiement']}</span>" if row.get('moyen_paiement') else ""}
  </div>
</div>""", unsafe_allow_html=True)

            col_r1,col_r2,col_r3 = st.columns([2,1,1])
            with col_r2:
                new_st = st.selectbox("Statut", STATUTS_PAIE,
                                      index=STATUTS_PAIE.index(row["statut_paiement"]) if row["statut_paiement"] in STATUTS_PAIE else 0,
                                      key=f"fst{row['id']}", label_visibility="collapsed")
                if new_st != row["statut_paiement"]:
                    update_facture_statut(row["id"], new_st)
                    st.rerun()
            with col_r3:
                # Régénérer PDF à la volée
                import json
                try:
                    lignes_data = json.loads(row["lignes_json"]) if row["lignes_json"] else []
                except: lignes_data = []
                if lignes_data:
                    pdf_bytes = generer_facture_pdf({
                        "numero_facture":   row["numero"],
                        "date_facture":     row["date_facture"],
                        "date_echeance":    row.get("date_echeance","À réception"),
                        "emetteur":         {"nom":"Mon Imprimerie SARL","adresse":"","ville":"Ouagadougou","telephone":"","email":""},
                        "client":           {"nom":row["client_nom"],"adresse":row.get("client_adresse",""),
                                             "ville":row.get("client_ville",""),"telephone":row.get("client_telephone",""),
                                             "email":row.get("client_email","")},
                        "lignes":           lignes_data,
                        "taux_tva":         row["taux_tva"],
                        "notes":            row.get("notes",""),
                        "statut_paiement":  row["statut_paiement"],
                        "moyen_paiement":   row.get("moyen_paiement",""),
                    })
                    st.download_button("📥 PDF", data=pdf_bytes,
                                       file_name=f"{row['numero']}.pdf",
                                       mime="application/pdf",
                                       key=f"dl{row['id']}")

# ── Page: Gestion utilisateurs ──────────────────────────────────────────────────
def page_users(current_user):
    sh("👥","Gestion des utilisateurs")
    users = AUTH.get_all_users()

    # Liste
    for u in users:
        role_info = AUTH.ROLES.get(u["role"], {"label":u["role"],"color":"#888","icon":"👤"})
        actif_dot = "🟢" if u["actif"] else "🔴"
        ll = u.get("last_login","Jamais") or "Jamais"
        st.markdown(f"""<div class="usr-card">
  <div class="usr-avatar" style="background:{role_info['color']}22;color:{role_info['color']}">{role_info['icon']}</div>
  <div style="flex:1">
    <div style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem">{u['nom_complet']}
      <span style="font-size:.78rem;color:#8891a8;margin-left:8px">@{u['username']}</span>
    </div>
    <div style="font-size:.78rem;color:#8891a8;margin-top:3px">
      {actif_dot} {role_info['label']} · {u.get('email','—')} · Dernière connexion : {ll[:16] if ll!='Jamais' else 'Jamais'}
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    tab_c, tab_e, tab_p = st.tabs(["➕ Créer un compte","✏️ Modifier","🔑 Mot de passe"])

    with tab_c:
        sh("➕","Nouveau compte")
        with st.form("form_create_user", clear_on_submit=True):
            uc1,uc2 = st.columns(2)
            with uc1: nu_user = st.text_input("Identifiant *", placeholder="ex: jean.dupont")
            with uc2: nu_nom  = st.text_input("Nom complet *")
            uc3,uc4 = st.columns(2)
            with uc3: nu_mail = st.text_input("Email")
            with uc4: nu_role = st.selectbox("Rôle", list(AUTH.ROLES.keys()),
                                              format_func=lambda r: AUTH.ROLES[r]["label"])
            uc5,uc6 = st.columns(2)
            with uc5: nu_pwd1 = st.text_input("Mot de passe *", type="password")
            with uc6: nu_pwd2 = st.text_input("Confirmer *",    type="password")
            st.caption("✅ Min 8 caractères, 1 majuscule, 1 chiffre.")
            if st.form_submit_button("Créer le compte", use_container_width=True):
                if nu_pwd1 != nu_pwd2:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    ok, msg = AUTH.create_user(nu_user, nu_nom, nu_mail, nu_role, nu_pwd1)
                    st.success(msg) if ok else st.error(msg)
                    if ok: st.rerun()

    with tab_e:
        sh("✏️","Modifier un utilisateur")
        umap = {f"@{u['username']} — {u['nom_complet']}": u for u in users}
        sel = st.selectbox("Choisir", list(umap.keys()))
        u = umap[sel]
        if u["username"] == current_user["username"]:
            st.warning("Vous ne pouvez pas modifier votre propre compte ici.")
        else:
            with st.form("form_edit_user"):
                eu1,eu2 = st.columns(2)
                with eu1: e_nom  = st.text_input("Nom complet", value=u["nom_complet"])
                with eu2: e_mail = st.text_input("Email",       value=u.get("email","") or "")
                eu3,eu4 = st.columns(2)
                with eu3: e_role = st.selectbox("Rôle", list(AUTH.ROLES.keys()),
                                                index=list(AUTH.ROLES.keys()).index(u["role"]),
                                                format_func=lambda r: AUTH.ROLES[r]["label"])
                with eu4: e_actif= st.checkbox("Compte actif", value=bool(u["actif"]))
                if st.form_submit_button("Enregistrer", use_container_width=True):
                    ok, msg = AUTH.update_user(u["id"], e_nom, e_mail, e_role, e_actif)
                    st.success(msg) if ok else st.error(msg)
                    if ok: st.rerun()

    with tab_p:
        sh("🔑","Changer le mot de passe")
        umap2 = {f"@{u['username']} — {u['nom_complet']}": u for u in users}
        sel2  = st.selectbox("Utilisateur", list(umap2.keys()), key="pwsel")
        u2    = umap2[sel2]
        with st.form("form_pwd"):
            pp1 = st.text_input("Nouveau mot de passe", type="password")
            pp2 = st.text_input("Confirmer",            type="password")
            if st.form_submit_button("Modifier le mot de passe", use_container_width=True):
                if pp1 != pp2:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    ok, msg = AUTH.change_password(u2["id"], pp1)
                    st.success(msg) if ok else st.error(msg)

# ── Sidebar ────────────────────────────────────────────────────────────────────
def render_sidebar(user):
    with st.sidebar:
        role = AUTH.ROLES.get(user["role"], {"label":user["role"],"color":"#888","icon":"👤"})
        st.markdown(f"""
<div style="padding:18px 10px 10px">
  <div style="font-family:Syne,sans-serif;font-size:1.25rem;font-weight:800;color:#ff6b35">✂️ PrintCut Pro</div>
  <div style="font-size:.72rem;color:#555;margin-top:2px">Gestion Machine Découpe</div>
  <div style="margin-top:14px;padding:10px;background:#1e2130;border-radius:8px">
    <div style="font-family:Syne,sans-serif;font-weight:700;font-size:.88rem;color:#e8eaf0">{role['icon']} {user['nom_complet']}</div>
    <div style="font-size:.72rem;color:{role['color']};margin-top:2px">{role['label']}</div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.markdown("---")

        perms = AUTH.PERMISSIONS.get(user["role"], set())
        nav = []
        if "dashboard"      in perms: nav.append(("🏠 Tableau de bord",   "dashboard"))
        if "saisie"         in perms: nav.append(("➕ Saisir activité",    "saisie"))
        if "mes_activites"  in perms: nav.append(("📋 Mes activités",      "historique"))
        if "historique"     in perms and "mes_activites" not in perms:
                                       nav.append(("📋 Historique",         "historique"))
        if "statistiques"   in perms: nav.append(("📈 Statistiques",       "statistiques"))
        if "factures"       in perms: nav.append(("🧾 Factures / Reçus",   "factures"))
        if "gestion_users"  in perms: nav.append(("👥 Utilisateurs",       "users"))

        if "page" not in st.session_state: st.session_state.page = "dashboard"
        for label, key in nav:
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Déconnexion", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

        st.markdown(f"<p style='font-size:.7rem;color:#333;padding:0 8px;margin-top:10px'>"
                    f"🗓️ {date.today().strftime('%d/%m/%Y')}<br>Base SQLite locale</p>",
                    unsafe_allow_html=True)

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    init_db()
    st.markdown(CSS, unsafe_allow_html=True)

    if "user" not in st.session_state:
        page_login()
        return

    user = st.session_state.user
    render_sidebar(user)
    df   = load_all(user)
    page = st.session_state.get("page","dashboard")

    if   page == "dashboard":    page_dashboard(df, user)
    elif page == "saisie":       page_saisie(user)
    elif page == "historique":   page_historique(df, user)
    elif page == "statistiques": page_stats(df)
    elif page == "factures":     page_factures(df, user)
    elif page == "users":
        if AUTH.has_perm(user,"gestion_users"):
            page_users(user)
        else:
            st.error("⛔ Accès non autorisé.")

if __name__ == "__main__":
    main()
