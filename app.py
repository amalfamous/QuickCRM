import streamlit as st
import sqlite3
import hashlib
import yagmail

# --- Configuration Email (Secrets Streamlit) ---
EMAIL_USER = st.secrets["EMAIL_USER"]
EMAIL_PASS = st.secrets["EMAIL_PASS"]
yag = yagmail.SMTP(EMAIL_USER, EMAIL_PASS)

# --- Helper functions ---
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()
def verify_password(pw, h):
    return hash_password(pw) == h

def send_email(to, subject, html):
    try:
        yag.send(to=to, subject=subject, contents=html)
        st.info(f"Email envoyé à {to}")
    except Exception as e:
        st.error(f"Erreur email: {e}")

# --- DB Connection ---
conn = sqlite3.connect('sales.db', check_same_thread=False)
c = conn.cursor()

# --- Create tables ---
tables = [
    ("users", "id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE, password TEXT, role TEXT"),
    ("produits", "id INTEGER PRIMARY KEY, nom TEXT, prix REAL"),
    ("clients", "id INTEGER PRIMARY KEY, nom TEXT, email TEXT"),
    ("devis", "id INTEGER PRIMARY KEY, client_id INTEGER, produit_id INTEGER, quantite INTEGER, statut TEXT"),
    ("bon_commandes", "id INTEGER PRIMARY KEY, devis_id INTEGER UNIQUE, statut TEXT"),
    ("factures", "id INTEGER PRIMARY KEY, devis_id INTEGER, montant REAL, statut TEXT"),
    ("livraisons", "id INTEGER PRIMARY KEY, facture_id INTEGER, statut TEXT")
]
for name, schema in tables:
    c.execute(f"CREATE TABLE IF NOT EXISTS {name} ({schema})")
conn.commit()

# --- Authentication ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔒 Authentification")
    tab_login, tab_register = st.tabs(["Se connecter", "S'inscrire"])

    with tab_login:
        user = st.text_input("Utilisateur")
        pw = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            row = c.execute("SELECT password, role, email FROM users WHERE username=?", (user,)).fetchone()
            if row and verify_password(pw, row[0]):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.role = row[1]
                st.session_state.email = row[2]
                st.rerun()

            else:
                st.error("Identifiants invalides")
    with tab_register:
        new_user = st.text_input("Nom d'utilisateur", key="reg_user")
        new_email = st.text_input("Email", key="reg_email")
        new_pw = st.text_input("Mot de passe", type="password", key="reg_pw")
        confirm_pw = st.text_input("Confirmer mot de passe", type="password", key="reg_pw2")
        role = st.selectbox("Rôle", ["client", "sales", "delivery"], key="reg_role")
        if st.button("S'inscrire"):
            if new_pw != confirm_pw:
                st.error("Les mots de passe ne correspondent pas")
            elif c.execute("SELECT 1 FROM users WHERE username=? OR email=?", (new_user, new_email)).fetchone():
                st.error("Utilisateur ou email déjà utilisé")
            else:
                c.execute(
                    "INSERT INTO users (username,email,password,role) VALUES (?,?,?,?)",
                    (new_user, new_email, hash_password(new_pw), role)
                )
                if role == 'client':
                    c.execute("INSERT OR IGNORE INTO clients (nom,email) VALUES (?,?)", (new_user, new_email))
                conn.commit()
                st.success("Inscription réussie ! Connectez-vous.")
    st.stop()

# --- After login ---
st.sidebar.write(f"Connecté : {st.session_state.username} ({st.session_state.role})")
if st.sidebar.button("Déconnexion"):
    st.session_state.clear()
    st.rerun()


# --- Role-based tabs ---
role = st.session_state.role
if role == 'sales':
    tabs = st.tabs(["Produits", "Clients", "Devis", "Bon de Commande", "Factures"])  
elif role == 'delivery':
    tabs = st.tabs(["Livraisons"])
elif role == 'client':
    tabs = st.tabs(["Mes Devis", "Mes BDC", "Mes Factures"])
else:
    st.error("Rôle inconnu")
    st.stop()

# --- Sales: Produits ---
if role == 'sales':
    with tabs[0]:
        st.header("Produits")
        nom = st.text_input("Nom du produit", key="prod_nom")
        prix = st.number_input("Prix", min_value=0.0, key="prod_prix")
        if st.button("Ajouter Produit", key="add_prod"):
            c.execute("INSERT INTO produits (nom,prix) VALUES (?,?)", (nom, prix))
            conn.commit(); st.success("Produit ajouté !")
        st.markdown("---")
        for pid, name, pr in c.execute("SELECT * FROM produits"):
            cols = st.columns([3,1,1])
            cols[0].write(f"{pid}. {name} — {pr}€")
            if cols[1].button("Modifier", key=f"modp{pid}"):
                new_name = st.text_input("Nom", value=name, key=f"np{pid}")
                new_price = st.number_input("Prix", value=pr, key=f"pp{pid}")
                if st.button("Valider Modif", key=f"cfp{pid}"):
                    c.execute("UPDATE produits SET nom=?,prix=? WHERE id=?", (new_name, new_price, pid))
                    conn.commit(); st.rerun()

            if cols[2].button("Supprimer", key=f"delp{pid}"):
                c.execute("DELETE FROM produits WHERE id=?", (pid,)); conn.commit(); st.rerun()


# --- Sales: Clients ---
if role == 'sales':
    with tabs[1]:
        st.header("Clients")
        cname = st.text_input("Nom du client", key="cli_nom")
        cemail = st.text_input("Email du client", key="cli_email")
        if st.button("Ajouter Client", key="add_cli"):
            c.execute("INSERT INTO clients (nom,email) VALUES (?,?)", (cname, cemail))
            conn.commit(); st.success("Client ajouté !")
        st.markdown("---")
        for cid, nm, mail in c.execute("SELECT * FROM clients"):
            cols = st.columns([3,1,1])
            cols[0].write(f"{cid}. {nm} — {mail}")
            if cols[1].button("Modifier", key=f"modc{cid}"):
                up_nm = st.text_input("Nom", value=nm, key=f"nm{cid}")
                up_mail = st.text_input("Email", value=mail, key=f"em{cid}")
                if st.button("Valider", key=f"vc{cid}"):
                    c.execute("UPDATE clients SET nom=?,email=? WHERE id=?", (up_nm, up_mail, cid))
                    conn.commit(); st.rerun()

            if cols[2].button("Supprimer", key=f"delc{cid}"):
                c.execute("DELETE FROM clients WHERE id=?", (cid,)); conn.commit(); st.rerun()


# --- Sales: Devis ---
if role == 'sales':
    with tabs[2]:
        st.header("Devis")
        clients = c.execute("SELECT id,nom,email FROM clients").fetchall()
        produits = c.execute("SELECT id,nom FROM produits").fetchall()
        if clients and produits:
            cid = st.selectbox("Client", [i for i,n,e in clients], format_func=lambda x: dict(clients)[x])
            pid = st.selectbox("Produit", [i for i,n in produits], format_func=lambda x: dict(produits)[x])
            qty = st.number_input("Quantité", min_value=1, key="dv_qty")
            if st.button("Créer & Envoyer Devis", key="send_devis"):
                c.execute(
                    "INSERT INTO devis (client_id,produit_id,quantite,statut) VALUES (?,?,?,'En attente')",
                    (cid, pid, qty)
                )
                conn.commit()
                did = c.lastrowid
                email = next(e for i,n,e in clients if i==cid)
                link = f"{st.request.url}?confirm_devis={did}"
                html = f"<p>Votre devis #{did} est prêt.</p><p><a href='{link}'>Confirmer le devis</a></p>"
                send_email(email, "Votre devis", html)
                st.success("Devis créé et email envoyé !")
        st.markdown("---")
        for did, cid, pid, q, stt in c.execute("SELECT * FROM devis"):
            cname = c.execute("SELECT nom FROM clients WHERE id=?", (cid,)).fetchone()[0]
            pname = c.execute("SELECT nom FROM produits WHERE id=?", (pid,)).fetchone()[0]
            st.write(f"{did}. {cname} – {pname}×{q} => **{stt}**")
        params = st.experimental_get_query_params()
        if "confirm_devis" in params:
            did = int(params["confirm_devis"][0])
            c.execute("UPDATE devis SET statut='Confirmé' WHERE id=?", (did,)); conn.commit()
            st.success(f"Devis #{did} confirmé !")

# --- Sales: Bon de Commande ---
if role == 'sales':
    with tabs[3]:
        st.header("Bon de Commande")
        for bdc_id, devis_id, statut in c.execute("SELECT * FROM bon_commandes"):
            # fetch client and product details
            cid = c.execute("SELECT client_id FROM devis WHERE id=?", (devis_id,)).fetchone()[0]
            prod = c.execute("SELECT produit_id,quantite FROM devis WHERE id=?", (devis_id,)).fetchone()
            pname = c.execute("SELECT nom FROM produits WHERE id=?", (prod[0],)).fetchone()[0]
            st.write(f"#{bdc_id} – Devis {devis_id} ({pname}×{prod[1]}) => **{statut}**")
            if statut == 'En attente' and st.button("Marquer comme Reçu", key=f"rcv_bdc{bdc_id}"):
                c.execute("UPDATE bon_commandes SET statut='Reçu' WHERE id=?", (bdc_id,))
                conn.commit(); st.rerun()


# --- Sales: Factures ---
if role == 'sales':
    with tabs[4]:
        st.header("Factures")
        # only devis with BDC reçus
        devis_ok = [row[0] for row in c.execute(
            "SELECT d.id FROM devis d JOIN bon_commandes b ON d.id=b.devis_id WHERE d.statut='Confirmé' AND b.statut='Reçu'"
        )]
        if devis_ok:
            did = st.selectbox("Devis à facturer", devis_ok, key="fact_dev")
            amount = st.number_input("Montant", min_value=0.0, key="fc_amt")
            if st.button("Créer & Envoyer Facture", key="send_fact"):
                c.execute(
                    "INSERT INTO factures (devis_id,montant,statut) VALUES (?,?, 'En attente Paiement')",
                    (did, amount)
                )
                conn.commit()
                fid = c.lastrowid
                email = c.execute(
                    "SELECT c.email FROM clients c JOIN devis d ON c.id=d.client_id WHERE d.id=?", (did,)
                ).fetchone()[0]
                pay_link = f"{st.request.url}?pay_invoice={fid}"
                html = f"<p>Facture #{fid} – Montant: {amount}€</p><p><a href='{pay_link}'>Payer la facture</a></p>"
                send_email(email, "Votre facture", html)
                st.success("Facture créée et email envoyée !")
        st.markdown("---")
        for fid, did, amt, stt in c.execute("SELECT * FROM factures"):
            st.write(f"{fid}. devis#{did} – {amt}€ => **{stt}**")
        params = st.experimental_get_query_params()
        if "pay_invoice" in params:
            fid = int(params["pay_invoice"][0])
            c.execute("UPDATE factures SET statut='Payé' WHERE id=?", (fid,)); conn.commit()
            # Création bon de livraison
            c.execute("INSERT INTO livraisons (facture_id,statut) VALUES (?, 'En attente Livraison')", (fid,))
            conn.commit()
            st.success(f"Facture #{fid} payée ! Bon de livraison généré.")

# --- Delivery: Livraisons ---
if role == 'delivery':
    with tabs[0]:
        st.header("Livraisons")
        for lid, fid, stt in c.execute("SELECT * FROM livraisons"):
            st.write(f"{lid}. facture#{fid} => **{stt}**")
            if st.button("Confirmer Livraison", key=f"deliv{lid}") and stt != 'Livré':
                c.execute("UPDATE livraisons SET statut='Livré' WHERE id=?", (lid,))
                conn.commit(); st.rerun()


# --- Client: Mes Devis, Mes BDC, Mes Factures ---
if role == 'client':
    cid = c.execute("SELECT id FROM clients WHERE email=?", (st.session_state.email,)).fetchone()[0]
    # Mes Devis
    with tabs[0]:
        st.header("Mes Devis")
        for did, _, pid, q, stt in c.execute("SELECT * FROM devis WHERE client_id=?", (cid,)):
            pname = c.execute("SELECT nom FROM produits WHERE id=?", (pid,)).fetchone()[0]
            st.write(f"{did}. {pname}×{q} => **{stt}**")
            if stt == 'En attente' and st.button("Confirmer Devis", key=f"conf{did}"):
                c.execute("UPDATE devis SET statut='Confirmé' WHERE id=?", (did,)); conn.commit(); st.rerun()

    # Mes BDC
    with tabs[1]:
        st.header("Mes Bon de Commande")
        devis_conf = [d[0] for d in c.execute("SELECT id FROM devis WHERE client_id=? AND statut='Confirmé'", (cid,))]
        for did in devis_conf:
            exists = c.execute("SELECT 1 FROM bon_commandes WHERE devis_id=?", (did,)).fetchone()
            if not exists:
                if st.button(f"Créer & Envoyer BDC #{did}", key=f"bdc{did}"):
                    c.execute("INSERT INTO bon_commandes (devis_id,statut) VALUES (?, 'En attente')", (did,))
                    conn.commit()
                    # notify sales
                    sales_emails = [r[0] for r in c.execute("SELECT email FROM users WHERE role='sales'")]  
                    html = f"<p>Bon de commande pour devis #{did} envoyé.</p>"
                    for mail in sales_emails:
                        send_email(mail, "Nouveau Bon de Commande", html)
                    st.success(f"BDC #{did} envoyé !")
            else:
                b = c.execute("SELECT id,statut FROM bon_commandes WHERE devis_id=?", (did,)).fetchone()
                st.write(f"#{b[0]} pour Devis {did} => **{b[1]}**")
    # Mes Factures
    with tabs[2]:
        st.header("Mes Factures")
        for fid, did, amt, stt in c.execute(
            "SELECT * FROM factures WHERE devis_id IN (SELECT id FROM devis WHERE client_id=?)", (cid,)
        ):
            st.write(f"{fid}. devis#{did} – {amt}€ => **{stt}**")

conn.close()