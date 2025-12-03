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

# Detect package items
PACKAGE_KEYS = [k for k in PRICES.keys() if k.lower().startswith("paket")]


# ---------------------------
# HELPERS
# ---------------------------
def normalize_size(size: str) -> str:
    """Normalisiert Größen inkl. Synonyme (XXXL->3XL, etc.)."""
    if not size:
        return ""
    s = str(size).strip().upper().replace(" ", "")
    synonyms = {"XXXL": "3XL", "XXXXL": "4XL", "XXXXXL": "5XL"}
    return synonyms.get(s, s)


def get_price_for_size(artikel, size):
    base, xxl = PRICES[artikel]
    s = normalize_size(size)
    return xxl if s in {"3XL", "4XL", "5XL"} else base


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
                "Artikel", "Größe", "Paket-Details", "Menge",
                "Einzelpreis", "Summe"
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
    data = [["Artikel", "Größe", "Menge", "Einzelpreis (€)", "Summe (€)"]]
    total = 0

    for item in cart:
        artikel_label = item["artikel"]
        if item.get("package_details"):
            artikel_label += f" – {item['package_details']}"
        data.append([
            artikel_label,
            item.get("size", ""),
            item["qty"],
            f"{item['price']:.2f}",
            f"{item['line_total']:.2f}",
        ])
        total += item["line_total"]

    data.append(["", "", "", "Gesamt", f"{total:.2f} €"])

    table = Table(data, colWidths=[220, 60, 60, 80, 100])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
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

# Session defaults
if "cart" not in st.session_state:
    st.session_state.cart = []

defaults = {
    "name_input": "",
    "team_input": "",
    "nummer_input": "",
    "artikel_select": list(PRICES.keys())[0],
    "size_input": "",
    "size_select": "M",
    "package_details_input": "",
    "qty_input": 1,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

left, right = st.columns([1, 2])

# LEFT: ADD ITEM
with left:
    st.header("Neue Bestellung aufgeben")
    st.markdown("""
### Anleitung
Tragt hier alle Artikel ein, die ihr bestellen möchtet. Ihr müsst für jeden Artikel alles Neu eintragen. Geht um die Übersichtlichkeit. 
Seid ihr fertig, dann klickt auf „Bestellung absenden“.
Anschließend überweist mir bitte den fälligen Betrag.

Bei Fragen meldet euch gern:
**Leonard Kötter, +49 173 6121352** 
""")

    # Eingaben in gewünschter Reihenfolge (ohne st.form, damit dynamische Felder sofort reagieren)
    st.session_state.name_input = st.text_input("Name Spieler*in", value=st.session_state.name_input, key="name_input")
    st.session_state.team_input = st.text_input("Team / Mannschaft", value=st.session_state.team_input, key="team_input")
    st.session_state.nummer_input = st.text_input("Rückennummer (optional)", value=st.session_state.nummer_input, key="nummer_input")

    # WICHTIG: Artikel/Paket direkt UNTER Rückennummer
    st.session_state.artikel_select = st.selectbox(
        "Artikel / Paket",
        list(PRICES.keys()),
        index=list(PRICES.keys()).index(st.session_state.artikel_select),
        key="artikel_select"
    )

    is_package = st.session_state.artikel_select in PACKAGE_KEYS

    # Größe + Paket-Details: dynamisch sichtbar
    if is_package:
        st.session_state.size_input = st.text_input(
            "Größe (Paket, optional – 3XL/4XL/5XL oder XXXL/XXXXL/XXXXXL erhöht den Preis)",
            value=st.session_state.size_input,
            key="size_input",
            placeholder="z. B. M oder 3XL/XXXL"
        )
        st.info("Du hast ein Paket gewählt. Bitte gib hier die Paket-Details an (z. B. Inhalte, weitere Größen, Name/Nr., Farbe):")
        st.session_state.package_details_input = st.text_area(
            "Paket-Details",
            value=st.session_state.package_details_input,
            key="package_details_input",
            placeholder="z. B. T-Shirt L, Hose M; Name: Meyer, Nr.: 12"
        )
        size_value = st.session_state.size_input
    else:
        st.session_state.size_select = st.selectbox(
            "Größe",
            SIZES,
            index=SIZES.index(st.session_state.size_select) if st.session_state.size_select in SIZES else 2,
            key="size_select"
        )
        size_value = st.session_state.size_select
        st.session_state.package_details_input = ""

    st.session_state.qty_input = st.number_input("Menge", min_value=1, step=1, value=st.session_state.qty_input, key="qty_input")

    if st.button("Zum Warenkorb hinzufügen"):
        name = st.session_state.name_input.strip()
        team = st.session_state.team_input.strip()
        nummer = st.session_state.nummer_input.strip()
        artikel = st.session_state.artikel_select
        size_norm = normalize_size(size_value)
        package_details = st.session_state.package_details_input if is_package else ""
        qty = int(st.session_state.qty_input)

        price = get_price_for_size(artikel, size_norm)
        total_price = price * qty

        st.session_state.cart.append({
            "name": name,
            "team": team,
            "nummer": nummer,
            "artikel": artikel,
            "size": size_norm,
            "package_details": package_details,
            "qty": qty,
            "price": price,
            "line_total": total_price,
        })

        # Felder leeren nach Hinzufügen
        st.session_state.name_input = ""
        st.session_state.team_input = ""
        st.session_state.nummer_input = ""
        st.session_state.size_input = ""
        st.session_state.qty_input = 1
        st.session_state.package_details_input = ""

        st.success(f"{qty}× {artikel} hinzugefügt")

# RIGHT: CART
with right:
    st.header("🛒 Warenkorb")

    cart = st.session_state.cart
    if not cart:
        st.info("Noch keine Artikel im Warenkorb.")
    else:
        df = pd.DataFrame(cart)
        cols_order = ["name", "team", "nummer", "artikel", "size", "package_details", "qty", "price", "line_total"]
        for c in cols_order:
            if c not in df.columns:
                df[c] = ""
        df = df[cols_order]
        df = df.rename(columns={
            "name": "Name",
            "team": "Team",
            "nummer": "Nummer",
            "artikel": "Artikel",
            "size": "Größe",
            "package_details": "Paket-Details",
            "qty": "Menge",
            "price": "Einzelpreis",
            "line_total": "Summe"
        })

        st.dataframe(df, use_container_width=True)

        total = df["Summe"].sum()
        st.subheader(f"Gesamtbetrag: {total:.2f} €")

        # CSV Angebot
        csv = df.to_csv(index=False).encode()
        st.download_button("Angebot als CSV herunterladen", csv, "angebot.csv")

        # PDF Rechnung
        if st.button("Rechnung als PDF erstellen"):
            raw_df = pd.DataFrame(cart)
            pdf = generate_invoice_pdf(cart, raw_df["name"].iloc[0], raw_df["team"].iloc[0])
            st.download_button("PDF herunterladen", pdf, "Rechnung.pdf", mime="application/pdf")

        st.markdown("---")

        # SEND TO GOOGLE SHEETS
        if st.button("Bestellung absenden"):
            rows = []
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for i in cart:
                rows.append([
                    ts, i["name"], i["team"], i["nummer"],
                    i["artikel"], i.get("size", ""), i.get("package_details", ""),
                    i["qty"], i["price"], i["line_total"],
                ])

            ok, err = append_orders_to_sheet(rows)
            if ok:
                st.success("Erfolgreich an Google Sheets übertragen!")
                st.session_state.cart = []
            else:
                st.error(f"Google Sheets Fehler: {err}")

        # LOCAL CSV FALLBACK
        if st.button("Lokal speichern (CSV)"):
            rows = []
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for i in cart:
                rows.append([
                    ts, i["name"], i["team"], i["nummer"],
                    i["artikel"], i.get("size", ""), i.get("package_details", ""),
                    i["qty"], i["price"], i["line_total"],
                ])
            append_orders_to_csv(rows)
            st.success("Lokal gespeichert (orders_local.csv).")
            st.session_state.cart = []

st.markdown("""
### Zahlungsinformationen
💳 **PayPal:** [https://www.paypal.com/pool/9kwYdJ6jNv?sr=wccr](https://www.paypal.com/pool/9kwYdJ6jNv?sr=wccr)   
Verwendungszweck: **Name und Team eintragen**

Sollte was schieflaufen oder ihr besitzt kein Paypal bitt schreibt mich Leonard Kötter (Tel.: 01736121352) an und wir finden eine Lösung
""")
