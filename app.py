import streamlit as st
import sqlite3
import hashlib
import yagmail
import os
try:
    EMAIL_USER = st.secrets["EMAIL_USER"]
    EMAIL_PASS = st.secrets["EMAIL_PASS"]
except Exception:
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")

if not EMAIL_USER or not EMAIL_PASS:
    st.error("Les identifiants email ne sont pas configurés. Vérifiez vos secrets ou variables d'environnement.")
    st.stop()

yag = yagmail.SMTP(EMAIL_USER, EMAIL_PASS)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_password(pw, h):
    return hash_password(pw) == h

def send_email(to: str, subject: str, html: str) -> bool:
    """
    Envoie un email HTML, retourne True si OK, False sinon (et affiche l'erreur).
    """
    try:
        yag.send(to=to, subject=subject, contents=html)
        return True
    except Exception as e:
        st.error(f"Erreur email: {e}")
        return False

# --- DB Connection ---
conn = sqlite3.connect('sales.db', check_same_thread=False)
c = conn.cursor()

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

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title(" Authentification")
    login_tab, register_tab = st.tabs(["Se connecter", "S'inscrire"])

    with login_tab:
        user_input = st.text_input("Utilisateur (username)")
        pw_input = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            row = c.execute(
                "SELECT password, role, email FROM users WHERE username=?", (user_input,)
            ).fetchone()
            if row and verify_password(pw_input, row[0]):
                st.session_state.logged_in = True
                st.session_state.username = user_input
                st.session_state.role = row[1]
                st.session_state.email = row[2]
                st.rerun()
            else:
                st.error("Identifiants invalides")

    with register_tab:
        new_user = st.text_input("Nom d'utilisateur", key="reg_user")
        new_email = st.text_input("Email", key="reg_email")
        new_pw = st.text_input("Mot de passe", type="password", key="reg_pw")
        confirm_pw = st.text_input("Confirmer mot de passe", type="password", key="reg_pw2")
        role = st.selectbox("Rôle", ["client", "sales", "delivery"], key="reg_role")
        if st.button("S'inscrire"):
            if new_pw != confirm_pw:
                st.error("Les mots de passe ne correspondent pas")
            elif c.execute(
                "SELECT 1 FROM users WHERE username=? OR email=?", (new_user, new_email)
            ).fetchone():
                st.error("Utilisateur ou email déjà utilisé")
            else:
                c.execute(
                    "INSERT INTO users (username,email,password,role) VALUES (?,?,?,?)",
                    (new_user, new_email, hash_password(new_pw), role)
                )
                if role == 'client':
                    c.execute(
                        "INSERT OR IGNORE INTO clients (nom,email) VALUES (?,?)",
                        (new_user, new_email)
                    )
                conn.commit()
                st.success("Inscription réussie ! Connectez-vous.")
    st.stop()

# --- After login: sidebar & logout ---
st.sidebar.write(
    f"Connecté : {st.session_state.username} ({st.session_state.role})"
)
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
        prix = st.number_input("Prix (€)", min_value=0.0, key="prod_prix")
        if st.button("Ajouter Produit", key="add_prod"):
            c.execute("INSERT INTO produits (nom,prix) VALUES (?,?)", (nom, prix))
            conn.commit()
            st.success("Produit ajouté !")
        st.markdown("---")
        for pid, name, pr in c.execute("SELECT * FROM produits"):
            cols = st.columns([3,1,1])
            cols[0].write(f"{pid}. {name} — {pr}€")
            if cols[1].button("Modifier", key=f"modp{pid}"):
                up_name = st.text_input("Nom", value=name, key=f"np{pid}")
                up_price = st.number_input("Prix (€)", value=pr, key=f"pp{pid}")
                if st.button("Valider Modif", key=f"cfp{pid}"):
                    c.execute(
                        "UPDATE produits SET nom=?,prix=? WHERE id=?",
                        (up_name, up_price, pid)
                    )
                    conn.commit()
                    st.rerun()
            if cols[2].button("Supprimer", key=f"delp{pid}"):
                c.execute("DELETE FROM produits WHERE id=?", (pid,))
                conn.commit()
                st.rerun()

# --- Sales: Clients ---
if role == 'sales':
    with tabs[1]:
        st.header("Clients")
        cname = st.text_input("Nom du client", key="cli_nom")
        cemail = st.text_input("Email du client", key="cli_email")
        if st.button("Ajouter Client", key="add_cli"):
            c.execute("INSERT INTO clients (nom,email) VALUES (?,?)", (cname, cemail))
            conn.commit()
            st.success("Client ajouté !")
        st.markdown("---")
        for cid, nm, mail in c.execute("SELECT * FROM clients"):
            cols = st.columns([3,1,1])
            cols[0].write(f"{cid}. {nm} — {mail}")
            if cols[1].button("Supprimer", key=f"delc{cid}"):
                c.execute("DELETE FROM clients WHERE id=?", (cid,))
                conn.commit()
                st.rerun()

# --- Sales: Devis ---
if role == 'sales':
    with tabs[2]:
        st.header("Devis")
        # 1) Préparation des mappings client/produit
        clients = c.execute("SELECT id, nom, email FROM clients").fetchall()
        client_ids = [cid for cid,_,_ in clients]
        client_names = {cid: name for cid,name,_ in clients}
        produits = c.execute("SELECT id, nom FROM produits").fetchall()
        prod_ids = [pid for pid,_ in produits]
        prod_names = {pid: name for pid,name in produits}

        # 2) Formulaire de création de devis
        if client_ids and prod_ids:
            cid = st.selectbox("Client", client_ids, format_func=lambda x: client_names[x])
            pid = st.selectbox("Produit", prod_ids, format_func=lambda x: prod_names[x])
            qty = st.number_input("Quantité", min_value=1, key="dv_qty")

            if st.button("Créer & Envoyer Devis", key="send_devis"):
                # Création en base
                c.execute(
                    "INSERT INTO devis (client_id,produit_id,quantite,statut) "
                    "VALUES (?,?,?,'En attente')",
                    (cid, pid, qty)
                )
                conn.commit()
                did = c.lastrowid

                # Préparation du mail
                email_client = next(e for i,n,e in clients if i == cid)
                link = f"http://localhost:8501/?confirm_devis={did}"
                html = (
                    f"<p>Votre devis #{did} est prêt.</p>"
                    f"<p><a href='{link}'>Confirmer le devis</a></p>"
                )

                # Envoi avec feedback
                ok = send_email(email_client, "Votre devis", html)
                if ok:
                    st.success("Devis créé et email envoyé !")
                else:
                    st.warning("Devis créé, mais l’email n’a pas pu être envoyé.")

        st.markdown("---")

        # 3) Confirmation via le lien dans l'URL
        params = st.query_params
        if "confirm_devis" in params:
            did_conf = int(params["confirm_devis"][0])
            c.execute("UPDATE devis SET statut='Confirmé' WHERE id=?", (did_conf,))
            conn.commit()
            st.success(f"Devis #{did_conf} confirmé !")
            # on vide les query params pour éviter de réafficher ce message
            st.experimental_set_query_params()


# --- Sales: Bon de Commande ---
if role == 'sales':
    with tabs[3]:
        st.header("Bon de Commande")
        for bdc_id, devis_id, statut in c.execute("SELECT * FROM bon_commandes"):
            prod, qte = c.execute(
                "SELECT produit_id,quantite FROM devis WHERE id=?", (devis_id,)
            ).fetchone()
            pname = c.execute(
                "SELECT nom FROM produits WHERE id=?", (prod,)
            ).fetchone()[0]
            st.write(f"#{bdc_id} – Devis {devis_id} ({pname}×{qte}) => **{statut}**")
            if statut == 'En attente' and st.button(f"Marquer comme Reçu", key=f"rcv_bdc{bdc_id}"):
                c.execute("UPDATE bon_commandes SET statut='Reçu' WHERE id=?", (bdc_id,))
                conn.commit()
                st.rerun()


# --- Sales: Factures ---
if role == 'sales':
    with tabs[4]:
        st.header("Factures")
        # seuls les devis confirmés et BDC reçus
        devis_ok = [row[0] for row in c.execute(
            "SELECT d.id FROM devis d "
            "JOIN bon_commandes b ON d.id=b.devis_id "
            "WHERE d.statut='Confirmé' AND b.statut='Reçu'"
        )]

        if devis_ok:
            did_fact = st.selectbox("Devis à facturer", devis_ok)
            amount = st.number_input("Montant (€)", min_value=0.0, key="fc_amt")
            if st.button("Créer & Envoyer Facture", key="send_fact"):
                c.execute(
                    "INSERT INTO factures (devis_id,montant,statut) VALUES (?,?, 'En attente Paiement')",
                    (did_fact, amount)
                )
                conn.commit()
                fid = c.lastrowid

                email = c.execute(
                    "SELECT c.email FROM clients c "
                    "JOIN devis d ON c.id=d.client_id WHERE d.id=?",
                    (did_fact,)
                ).fetchone()[0]
                pay_link = f"http://localhost:8501/?pay_invoice={fid}"
                html = (
                    f"<p>Facture #{fid} – Montant : {amount}€</p>"
                    f"<p><a href='{pay_link}'>Payer la facture</a></p>"
                )
                ok = send_email(email, "Votre facture", html)
                if ok:
                    st.success("Facture créée et email envoyée !")
                else:
                    st.warning("Facture créée, mais l’email n’a pas pu être envoyé.")

        st.markdown("---")

        # affichage et traitement du paiement
        params = st.query_params
        for fid, did_f, amt, stt in c.execute("SELECT * FROM factures"):
            st.write(f"{fid}. devis#{did_f} – {amt}€ => **{stt}**")

        if "pay_invoice" in params:
            fid_pay = int(params["pay_invoice"][0])
            c.execute("UPDATE factures SET statut='Payé' WHERE id=?", (fid_pay,))
            c.execute(
                "INSERT INTO livraisons (facture_id,statut) VALUES (?, 'En attente Livraison')",
                (fid_pay,)
            )
            conn.commit()
            st.success(f"Facture #{fid_pay} payée ! Bon de livraison généré.")
            st.experimental_set_query_params()

# --- Delivery: Livraisons ---
if role == 'delivery':
    with tabs[0]:
        st.header("Livraisons")
        for lid, fid_l, stt in c.execute("SELECT * FROM livraisons"):
            st.write(f"{lid}. facture#{fid_l} => **{stt}**")
            if stt != 'Livré' and st.button(f"Confirmer Livraison", key=f"deliv{lid}"):
                c.execute("UPDATE livraisons SET statut='Livré' WHERE id=?", (lid,))
                conn.commit()
                st.rerun()

# --- Client: Mes Devis, Mes BDC, Mes Factures ---
if role == 'client':
    cid = c.execute("SELECT id FROM clients WHERE email=?", (st.session_state.email,)).fetchone()[0]

    with tabs[0]:
        st.header("Mes Devis")
        for did, _, pid_c, q_c, stt_c in c.execute("SELECT * FROM devis WHERE client_id=?", (cid,)):
            pname_c = c.execute("SELECT nom FROM produits WHERE id=?", (pid_c,)).fetchone()[0]
            st.write(f"{did}. {pname_c}×{q_c} => **{stt_c}**")
            if stt_c == 'En attente' and st.button(f"Confirmer Devis", key=f"conf{did}"):
                c.execute("UPDATE devis SET statut='Confirmé' WHERE id=?", (did,))
                conn.commit()
                st.rerun()

    with tabs[1]:
        st.header("Mes Bon de Commande")
        devis_conf = [d[0] for d in c.execute("SELECT id FROM devis WHERE client_id=? AND statut='Confirmé'", (cid,))]
        for did_b in devis_conf:
            exists = c.execute("SELECT 1 FROM bon_commandes WHERE devis_id=?", (did_b,)).fetchone()
            if not exists and st.button(f"Créer & Envoyer BDC #{did_b}", key=f"bdc{did_b}"):
                c.execute("INSERT INTO bon_commandes (devis_id,statut) VALUES (?, 'En attente')", (did_b,))
                conn.commit()
                sales_emails = [r[0] for r in c.execute("SELECT email FROM users WHERE role='sales'")]
                html = f"<p>Bon de commande pour devis #{did_b} envoyé.</p>"
                for mail in sales_emails:
                    send_email(mail, "Nouveau Bon de Commande", html)
                st.success(f"BDC #{did_b} envoyé !")
            elif exists:
                bdc = c.execute("SELECT id, statut FROM bon_commandes WHERE devis_id=?", (did_b,)).fetchone()
                st.write(f"#{bdc[0]} pour Devis {did_b} => **{bdc[1]}**")

    with tabs[2]:
        st.header("Mes Factures")
        for fid_c, did_fi, amt_c, stt_f in c.execute("SELECT * FROM factures WHERE devis_id IN (SELECT id FROM devis WHERE client_id=?)", (cid,)):
            st.write(f"{fid_c}. devis#{did_fi} – {amt_c}€ => **{stt_f}**")

conn.close()
