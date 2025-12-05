# Streamlit BestellApp - Münster Phoenix (Mobile Version)
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
# MOBILE SELECTBOX (no keyboard)
# ---------------------------
def mobile_select(label, options, key):
    """Mobile-friendly dropdown replacement (no keyboard popup)."""
    if key not in st.session_state:
        st.session_state[key] = options[0]

    btn_label = f"{label}: {st.session_state[key]}"

    # Button that opens the menu
    if st.button(btn_label, key=f"btn_{key}", use_container_width=True):
        st.session_state[f"show_{key}"] = True

    # Popup menu
    if st.session_state.get(f"show_{key}", False):
        st.markdown(
            "<div style='padding:12px; background:#1A1A1A; border-radius:10px; border:1px solid #444;'>",
            unsafe_allow_html=True
        )
        choice = st.radio(f"{label} auswählen:", options, key=f"radio_{key}")
        if st.button("Auswahl übernehmen", key=f"save_{key}", use_container_width=True):
            st.session_state[key] = choice
            st.session_state[f"show_{key}"] = False

        st.markdown("</div>", unsafe_allow_html=True)

    return st.session_state[key]


# ---------------------------
# PRICE LIST
# ---------------------------
PRICES = {
    "Zip Jacke NMS": (65, 70),
    "Kapuzenpulli NMS": (50, 55),
    "Fluffy Hoodie": (48, 48),
    "Kurz Hose Mesh 2k5": (28, 30),
    "Jogging Hose NMS": (45, 50),
    "T-Shirt": (20, 25),
    "T-Shirt Kids": (28, 28),
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

# SIZES
SIZES = ["YS", "YM", "YL", "YXL", "XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL"]

# TEAMS
TEAMS = ["Seniors", "FLINTA*", "U10", "U13", "U16", "U19"]


# ---------------------------
# HELPERS
# ---------------------------
def get_price_for_size(artikel, size):
    base, xxl = PRICES[artikel]
    return xxl if size in ["3XL", "4XL", "5XL"] else base


def connect_to_sheet(sheet_name="Teamwear_Bestellungen"):
    creds_info = st.secrets["gcp_service_account"]

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(credentials)
    return client.open(sheet_name).sheet1


def append_orders_to_sheet(rows):
    try:
        sheet = connect_to_sheet()
        for r in rows:
            sheet.append_row(r)
        return True, None
    except Exception as e:
        return False, str(e)


def append_orders_to_csv(rows, path="orders_local.csv"):
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

    table = Table(data, colWidths=[120, 50, 55, 75, 75, 140])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]))

    story.append(table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>PayPal:</b> https://www.paypal.com/pool/9kwYdJ6jNv?sr=wccr", styles["Normal"]))
    story.append(Paragraph("<b>Verwendungszweck:</b> Name + Team", styles["Normal"]))
    story.append(Paragraph("<b>Bei Problemen:</b> Leonard Kötter – 0173 6121352", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()


# ---------------------------
# UI CONFIG
# ---------------------------
st.set_page_config(page_title="Phoenix Teamwear", layout="centered")

# LOGO
st.image("Münster_Phoenix_Logo_RGB.svg", width=160)
st.markdown("<h1 style='text-align:center;'>🔥 Münster Phoenix – Teamwear</h1>", unsafe_allow_html=True)

# CART SESSION
if "cart" not in st.session_state:
    st.session_state.cart = []

if "customer_info" not in st.session_state:
    st.session_state.customer_info = {}


# ---------------------------
# MOBILE LAYOUT: SINGLE COLUMN FORM
# ---------------------------
st.subheader("Neue Bestellung")
st.markdown(
        """
## Anleitung
Tragt hier alle Artikel ein, die ihr bestellen möchtet. 

#### Paketbestellungen: Abweichende Größen und Extras 
Bitte nutzt das Kommentarfeld „Abweichende Größen und Extras“, wenn etwas vom Standard abweicht.
- Abweichende Größen: Wenn einzelne Artikel von eurer Hauptgröße abweichen, gebt Artikel + gewünschte Größe an.

	- Beispiel: Paket in 3XL, Hose in XXL → "Jogginghose XXL" eintragen  
    
- Extras: Wenn im Paket ein Extra auswählbar ist, tragt eure Wahl dort ein.
	- Beispiele: "Extra: Polo XXL" oder "Extra: Langarm L"

Tipp: Pro Wunsch eine eigene Zeile und klare Bezeichnungen verwenden.
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
        team = mobile_select("Team", TEAMS, "team_select")
        nummer = st.text_input("Jerseynummer oder Initialen")
    else:
        name = st.text_input("Name Spieler*in", st.session_state.customer_info["name"])
        team = mobile_select("Team", TEAMS, "team_select_saved")
        nummer = st.text_input("Rückennummer / Initialen", st.session_state.customer_info["nummer"])

    artikel = mobile_select("Artikel / Paket", list(PRICES.keys()), "artikel_select")
    size = mobile_select("Größe", SIZES, "size_select")
    qty = st.number_input("Menge", 1, step=1)
    additional_sizes = st.text_area("Abweichende Größen & Extras", placeholder="z. B. Hose XXL, Extra Polo")

    submit = st.form_submit_button("➕ Zum Warenkorb hinzufügen")

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

        st.success(f"{qty}× {artikel} hinzugefügt!")


# ---------------------------
# MOBILE CART VIEW – CARD STYLE
# ---------------------------
st.subheader("🛒 Warenkorb")

cart = st.session_state.cart

if not cart:
    st.info("Keine Artikel im Warenkorb.")
else:
    total = 0

    for i, item in enumerate(cart):
        st.markdown(
            f"""
            <div style="
                background:#1A1A1A;
                padding:15px;
                border-radius:12px;
                margin-bottom:12px;
                border:1px solid #333;">
                <b style='color:#F05323;'>{item['artikel']}</b><br>
                Größe: {item['size']}<br>
                Menge: {item['qty']}<br>
                Einzelpreis: {item['price']} €<br>
                <b>Summe: {item['line_total']} €</b><br>
                <i>{item['additional_sizes']}</i>
            </div>
            """,
            unsafe_allow_html=True
        )

        total += item["line_total"]

    st.subheader(f"**Gesamt: {total:.2f} €**")

    st.markdown("---")

    # CSV DOWNLOAD
    df = pd.DataFrame(cart)
    csv = df.to_csv(index=False).encode()
    st.download_button("📦 Angebot als CSV", csv, "Angebot.csv", use_container_width=True)

    # PDF
    if st.button("📄 Rechnung als PDF", use_container_width=True):
        pdf = generate_invoice_pdf(cart, df["name"].iloc[0], df["team"].iloc[0])
        st.download_button("PDF herunterladen", pdf, "Rechnung.pdf", mime="application/pdf")

    # SEND TO SHEETS
    if st.button("📤 Bestellung absenden", use_container_width=True):
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
            st.success("Bestellung übertragen!")
            st.session_state.cart = []
            st.session_state.customer_info = {}
            st.experimental_rerun()
        else:
            st.error(f"Google Sheets Fehler: {err}")


# PAYMENT INFO
st.markdown("""
### Zahlungsinformationen  
💳 **PayPal:** https://www.paypal.com/pool/9kwYdJ6jNv?sr=wccr  
Verwendungszweck: **Name + Team**  
Bei Problemen: **Leonard Kötter – 0173 6121352**  
""")
