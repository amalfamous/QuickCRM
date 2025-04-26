import streamlit as st
import sqlite3

# --- Database Setup ---
conn = sqlite3.connect('sales.db', check_same_thread=False)
c = conn.cursor()
# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS produits (id INTEGER PRIMARY KEY, nom TEXT, prix REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY, nom TEXT, email TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS devis (id INTEGER PRIMARY KEY, client_id INTEGER, produit_id INTEGER, quantite INTEGER, statut TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS factures (id INTEGER PRIMARY KEY, devis_id INTEGER, montant REAL, statut TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS livraisons (id INTEGER PRIMARY KEY, facture_id INTEGER, statut TEXT)''')
conn.commit()

# --- UI Tabs ---
tabs = st.tabs(["Produits", "Clients", "Devis", "Factures", "Livraisons"])

# --- Onglet Produits ---
with tabs[0]:
    st.header("Gestion des Produits")

    # Create
    nom = st.text_input("Nom du Produit", key="prod_nom")
    prix = st.number_input("Prix du Produit", min_value=0.0, key="prod_prix")
    if st.button("Ajouter Produit"):
        c.execute("INSERT INTO produits (nom, prix) VALUES (?, ?)", (nom, prix))
        conn.commit()
        st.success("Produit ajouté !")

    st.markdown("---")

    # Read & Update/Delete
    produits = c.execute("SELECT * FROM produits").fetchall()
    st.subheader("Modifier ou Supprimer un Produit")
    ids = [p[0] for p in produits]
    if ids:
        sel = st.selectbox("Choisir ID", ids, key="sel_prod")
        prod = next(p for p in produits if p[0] == sel)
        new_nom = st.text_input("Nom", value=prod[1], key="upd_prod_nom")
        new_prix = st.number_input("Prix", value=prod[2], key="upd_prod_prix")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Mettre à jour Produit"):
                c.execute("UPDATE produits SET nom=?, prix=? WHERE id=?", (new_nom, new_prix, sel))
                conn.commit()
                st.success("Produit mis à jour !")
        with col2:
            if st.button("Supprimer Produit"):
                c.execute("DELETE FROM produits WHERE id=?", (sel,))
                conn.commit()
                st.success("Produit supprimé !")
    else:
        st.info("Aucun produit trouvé.")

# --- Onglet Clients ---
with tabs[1]:
    st.header("Gestion des Clients")

    # Create
    nom_client = st.text_input("Nom du Client", key="cli_nom")
    email_client = st.text_input("Email du Client", key="cli_email")
    if st.button("Ajouter Client"):
        c.execute("INSERT INTO clients (nom, email) VALUES (?, ?)", (nom_client, email_client))
        conn.commit()
        st.success("Client ajouté !")

    st.markdown("---")

    # Read & Update/Delete
    clients = c.execute("SELECT * FROM clients").fetchall()
    st.subheader("Modifier ou Supprimer un Client")
    cids = [c_[0] for c_ in clients]
    if cids:
        selc = st.selectbox("Choisir ID", cids, key="sel_cli")
        cli = next(c_ for c_ in clients if c_[0] == selc)
        new_nom_c = st.text_input("Nom", value=cli[1], key="upd_cli_nom")
        new_email_c = st.text_input("Email", value=cli[2], key="upd_cli_email")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Mettre à jour Client"):
                c.execute("UPDATE clients SET nom=?, email=? WHERE id=?", (new_nom_c, new_email_c, selc))
                conn.commit()
                st.success("Client mis à jour !")
        with col2:
            if st.button("Supprimer Client"):
                c.execute("DELETE FROM clients WHERE id=?", (selc,))
                conn.commit()
                st.success("Client supprimé !")
    else:
        st.info("Aucun client trouvé.")

# --- Onglet Devis ---
with tabs[2]:
    st.header("Gestion des Devis")

    # Create
    clients = c.execute("SELECT id, nom FROM clients").fetchall()
    produits = c.execute("SELECT id, nom FROM produits").fetchall()
    if clients and produits:
        id_cli = st.selectbox("Client", [c[0] for c in clients], format_func=lambda x: next(n for i,n in clients if i==x))
        id_prod = st.selectbox("Produit", [p[0] for p in produits], format_func=lambda x: next(n for i,n in produits if i==x))
        qty = st.number_input("Quantité", min_value=1, step=1, key="dev_qty")
        if st.button("Créer Devis"):
            c.execute("INSERT INTO devis (client_id, produit_id, quantite, statut) VALUES (?, ?, ?, 'En attente')", (id_cli, id_prod, qty))
            conn.commit()
            st.success("Devis créé !")

    st.markdown("---")

    # Read & Update/Delete
    devis = c.execute("SELECT * FROM devis").fetchall()
    st.subheader("Modifier ou Supprimer un Devis")
    dids = [d[0] for d in devis]
    if dids:
        seld = st.selectbox("Choisir ID", dids, key="sel_dev")
        d = next(d for d in devis if d[0]==seld)
        new_stat = st.selectbox("Statut", ["En attente","Confirmé","Annulé"], index=["En attente","Confirmé","Annulé"].index(d[4]), key="upd_dev_stat")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Mettre à jour Devis"):
                c.execute("UPDATE devis SET statut=? WHERE id=?", (new_stat, seld))
                conn.commit()
                st.success("Devis mis à jour !")
        with col2:
            if st.button("Supprimer Devis"):
                c.execute("DELETE FROM devis WHERE id=?", (seld,))
                conn.commit()
                st.success("Devis supprimé !")
    else:
        st.info("Aucun devis trouvé.")

# --- Onglet Factures ---
with tabs[3]:
    st.header("Gestion des Factures")

    # Create
    devis_ids = [d[0] for d in c.execute("SELECT * FROM devis WHERE statut='Confirmé'").fetchall()]
    if devis_ids:
        sel_df = st.selectbox("Devis à facturer", devis_ids, key="fact_dev")
        montant = st.number_input("Montant", min_value=0.0, key="fact_montant")
        if st.button("Créer Facture"):
            c.execute("INSERT INTO factures (devis_id, montant, statut) VALUES (?, ?, 'En attente Paiement')", (sel_df, montant))
            conn.commit()
            st.success("Facture créée !")
    st.markdown("---")

    # Read & Update/Delete
    factures = c.execute("SELECT * FROM factures").fetchall()
    st.subheader("Modifier ou Supprimer une Facture")
    fids = [f[0] for f in factures]
    if fids:
        self = st.selectbox("Choisir ID", fids, key="sel_fact")
        f = next(f for f in factures if f[0]==self)
        new_stat_f = st.selectbox("Statut", ["En attente Paiement","Payé","Refusé"], index=["En attente Paiement","Payé","Refusé"].index(f[3]), key="upd_fact_stat")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Mettre à jour Facture"):
                c.execute("UPDATE factures SET statut=? WHERE id=?", (new_stat_f, self))
                conn.commit()
                st.success("Facture mise à jour !")
        with col2:
            if st.button("Supprimer Facture"):
                c.execute("DELETE FROM factures WHERE id=?", (self,))
                conn.commit()
                st.success("Facture supprimée !")
    else:
        st.info("Aucune facture trouvée.")

# --- Onglet Livraisons ---
with tabs[4]:
    st.header("Gestion des Livraisons")

    # Confirm Delivery
    payed = c.execute("SELECT id FROM factures WHERE statut='Payé'").fetchall()
    pid = [p[0] for p in payed]
    if pid:
        sel_liv = st.selectbox("Facture livrée", pid, key="liv_fact")
        if st.button("Confirmer Livraison"):
            c.execute("INSERT INTO livraisons (facture_id, statut) VALUES (?, 'Livré')", (sel_liv,))
            conn.commit()
            st.success("Livraison confirmée !")

    st.markdown("---")

    # Read & Delete
    livraisons = c.execute("SELECT * FROM livraisons").fetchall()
    st.subheader("Supprimer une Livraison")
    lids = [l[0] for l in livraisons]
    if lids:
        sell = st.selectbox("Choisir ID", lids, key="sel_liv_del")
        if st.button("Supprimer Livraison"):
            c.execute("DELETE FROM livraisons WHERE id=?", (sell,))
            conn.commit()
            st.success("Livraison supprimée !")
    else:
        st.info("Aucune livraison trouvée.")