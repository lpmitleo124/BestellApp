# Streamlit BestellApp - Münster Phoenix
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors as rl_colors
import os

import gspread
from google.oauth2.service_account import Credentials


# ---------------------------
# PRICE LIST
# ---------------------------
PRICES = {
    "Zip Jacke NMS": (65, 70),
    "Kapuzenpulli NMS": (50, 55),
    "Kurz Hose Mesh 2k5": (28, 30),
    "Jogging Hose NMS": (45, 50),
    "T-Shirt": (20, 25),
    "Kapuzenpulli Gildan": (40, 45),
    "Polo": (35, 38),
    "Tank Top": (25, 28),
    "Langarm Shirt": (35, 38),

    # Pakete
    "Paket 1": (45, 50),
    "Paket 2": (80, 90),
    "Paket 3": (75, 80),
    "Paket 4": (100, 110),
    "Paket 5": (110, 120),
    "Paket 6": (125, 135),
    "Paket 7": (150, 165),
    "Paket 8": (155, 170),
}


# AVAILABLE SIZES
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL"]

# Available Teams
TEAMS = ["Seniors", "FLINTA*", "U10", "U13", "U16", "U19"]


# ---------------------------
# HELPERS
# ---------------------------
def get_price_for_size(artikel, size):
    base, xxl = PRICES[artikel]
    return xxl if size in ["3XL", "4XL", "5XL"] else base


def connect_to_sheet(sheet_name="Teamwear_Bestellungen"):
    """Google Sheets modern auth via Streamlit Secrets."""
    creds_info = st.secrets["gcp_service_account"]

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(credentials)
    return client.open(sheet_name).sheet1


def append_orders_to_sheet(rows):
    """Send rows to Google Sheets"""
    try:
        sheet = connect_to_sheet()
        for r in rows:
            sheet.append_row(r)
        return True, None
    except Exception as e:
        return False, str(e)


def append_orders_to_csv(rows, path="orders_local.csv"):
    """Fallback if Google Sheets fails."""
    import csv

    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow([
                "Timestamp", "Name", "Team", "Nummer",
                "Artikel", "Größe", "Farbe", "Menge",
                "Einzelpreis", "Summe", "Zusätzliche Größen"
            ])
        for r in rows:
            w.writerow(r)
    return True, None


def generate_invoice_pdf(cart, customer_name, team):
    """Generates a PDF invoice"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(595, 842))
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Rechnung Münster Phoenix", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Datum: {datetime.now().strftime('%Y-%m-%d')}", styles["Normal"]))
    story.append(Paragraph(f"Spieler*in: {customer_name}", styles["Normal"]))
    story.append(Paragraph(f"Team: {team}", styles["Normal"]))
    story.append(Spacer(1, 18))

    # Table
    data = [["Artikel", "Größe", "Menge", "Einzelpreis (€)", "Summe (€)", "Zusätzliche Größen"]]
    total = 0

    for item in cart:
        data.append([
            item["artikel"],
            item["size"],
            item["qty"],
            f"{item['price']:.2f}",
            f"{item['line_total']:.2f}",
            item["additional_sizes"]
        ])
        total += item["line_total"]

    data.append(["", "", "", "", "Gesamt", f"{total:.2f} €"])

    table = Table(data, colWidths=[140, 50, 60, 55, 90, 90])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
    ]))

    story.append(table)
    story.append(Spacer(1, 20))

    # Payment Info
    story.append(Paragraph("Zahlungsinformationen:", styles["Heading3"]))
    story.append(Paragraph("PayPal: <b>https://www.paypal.com/pool/9kwYdJ6jNv?sr=wccr</b>", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()


# ---------------------------
# STREAMLIT UI
# ---------------------------
st.set_page_config(page_title="Münster Phoenix Teamwear", layout="wide")
st.title("🔥 Münster Phoenix – Teamwear Bestellsystem")

if "cart" not in st.session_state:
    st.session_state.cart = []

if "customer_info" not in st.session_state:
    st.session_state.customer_info = {}

left, right = st.columns([1, 2])


# LEFT: ADD ITEM
with left:
    st.header("Neue Bestellung aufgeben")

    st.markdown(
        """
### Anleitung
Tragt hier alle Artikel ein, die ihr bestellen möchtet. 

<span style="color:red;">**Bei Paketen bitte in das Kommentarfeld "Abweichende Größen" reinschreiben, wenn ihr ein Produkt abweichend von der Hauptgröße haben wollt, also wenn ihr das Paket in 3XL haben wollt aber wisst dass euch die Hose in XXL oder XL besser passt, dann schreibt in das Kommentarfeld _"Jogginghose XXL"_**</span>

Ihr müsst für jeden Artikel alles Neu eintragen. Geht um die Übersichtlichkeit.  

Seid ihr fertig, dann klickt auf „Bestellung absenden“.  
Anschließend überweist mir bitte den fälligen Betrag.

Bei Fragen meldet euch gern:
**Leonard Kötter, +49 173 6121352** 
""",
        unsafe_allow_html=True
    )

    with st.form("add_item", clear_on_submit=True):
        if not st.session_state.customer_info:
            name = st.text_input("Name Spieler*in")
            team = st.selectbox("Team", TEAMS)
            nummer = st.text_input("Rückennummer (optional)")
        else:
            name = st.text_input("Name Spieler*in", st.session_state.customer_info["name"])
            team = st.selectbox("Team", TEAMS, index=TEAMS.index(st.session_state.customer_info["team"]))
            nummer = st.text_input("Rückennummer (optional)", st.session_state.customer_info["nummer"])

        artikel = st.selectbox("Artikel / Paket", list(PRICES.keys()))
        size = st.selectbox("Größe", SIZES)
        qty = st.number_input("Menge", 1, step=1)
        additional_sizes = st.text_area("Zusätzliche Größen (falls Paket und unterschiedliche Größen benötigt)", placeholder="z. B. T-Shirt 3XL, Hose XXL;")

        submit = st.form_submit_button("Zum Warenkorb hinzufügen")

        if submit:
            price = get_price_for_size(artikel, size)
            total_price = price * qty

            st.session_state.cart.append({
                "name": name,
                "team": team,
                "nummer": nummer,
                "artikel": artikel,
                "size": size,
                "qty": qty,
                "price": price,
                "line_total": total_price,
                "additional_sizes": additional_sizes
            })

            st.session_state.customer_info = {"name": name, "team": team, "nummer": nummer}

            additional_sizes = ""
            qty = 1

            st.success(f"{qty}× {artikel} hinzugefügt")

# RIGHT: CART
with right:
    st.header("🛒 Warenkorb")

    cart = st.session_state.cart
    if not cart:
        st.info("Noch keine Artikel im Warenkorb.")
    else:
        df = pd.DataFrame(cart)
        st.dataframe(df, use_container_width=True)

        total = df["line_total"].sum()
        st.subheader(f"Gesamtbetrag: {total:.2f} €")

        # CSV Offer
        csv = df.to_csv(index=False).encode()
        st.download_button("Angebot als CSV herunterladen", csv, "angebot.csv")

        # PDF Invoice
        if st.button("Rechnung als PDF erstellen"):
            pdf = generate_invoice_pdf(cart, df["name"].iloc[0], df["team"].iloc[0])
            st.download_button("PDF herunterladen", pdf, "Rechnung.pdf", mime="application/pdf")

        st.markdown("---")

        # Delete items
        if st.button("Artikel aus dem Warenkorb löschen"):
            selected_indices = st.multiselect("Zu löschende Artikel auswählen", range(len(df)), default=[])
            if selected_indices:
                new_cart = [item for i, item in enumerate(st.session_state.cart) if i not in selected_indices]
                st.session_state.cart = new_cart
                st.success("Artikel aus dem Warenkorb entfernt.")
                st.experimental_rerun()

        # SEND TO GOOGLE SHEETS
        if st.button("Bestellung absenden"):
            rows = []
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for i in cart:
                rows.append([
                    ts, i["name"], i["team"], i["nummer"],
                    i["artikel"], i["size"],
                    i["qty"], i["price"], i["line_total"], i["additional_sizes"]
                ])

            ok, err = append_orders_to_sheet(rows)
            if ok:
                st.success("Erfolgreich an Google Sheets übertragen!")
                st.session_state.cart = []
                st.session_state.customer_info = {}
            else:
                st.error(f"Google Sheets Fehler: {err}")

        # LOCAL CSV FALLBACK
        if st.button("Lokal speichern (CSV)"):
            rows = []
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for i in cart:
                rows.append([
                    ts, i["name"], i["team"], i["nummer"],
                    i["artikel"], i["size"],
                    i["qty"], i["price"], i["line_total"], i["additional_sizes"]
                ])
            append_orders_to_csv(rows)
            st.success("Lokal gespeichert (orders_local.csv).")
            st.session_state.cart = []
            st.session_state.customer_info = {}

st.markdown("""
### Zahlungsinformationen
💳 **PayPal:** [https://www.paypal.com/pool/9kwYdJ6jNv?sr=wccr](https://www.paypal.com/pool/9kwYdJ6jNv?sr=wccr)   
Verwendungszweck: **Name und Team eintragen**

Sollte was schieflaufen oder ihr besitzt kein Paypal bitt schreibt mich Leonard Kötter (Tel.: 01736121352) an und wir finden eine Lösung
""")
