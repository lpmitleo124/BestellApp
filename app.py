
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors as rl_colors
import os

# Optional Google Sheets
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GS_AVAILABLE = True
except Exception:
    GS_AVAILABLE = False

# ---------------------------
# Configuration / Prices
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
    "Paket 1": (45, 50),
    "Paket 2": (80, 90),
    "Paket 3": (75, 80),
    "Paket 4": (100, 110),
    "Paket 5": (110, 120),
    "Paket 6": (125, 135),
    "Paket 7": (150, 165),
    "Paket 8": (155, 170)
}

COLORS = ["Schwarz", "Weiß", "Orange", "Rot"]

SIZES = ["XS","S","M","L","XL","XXL","3XL","4XL","5XL"]

# ---------------------------
# Helpers
# ---------------------------
def get_price_for_size(artikel, size):
    p = PRICES.get(artikel)
    if not p:
        return 0
    base, xxl = p
    if size in ["3XL","4XL","5XL"]:
        return xxl
    return base

def connect_to_sheet(sheet_name="Teamwear_Bestellungen"):
    """Try to connect to Google Sheets using google_credentials.json in working directory.
    Returns a sheet object (gspread) or raises an exception."""
    creds_file = "google_credentials.json"
    if not GS_AVAILABLE:
        raise RuntimeError("gspread / oauth2client not installed in environment.")
    if not os.path.exists(creds_file):
        raise FileNotFoundError(f"{creds_file} not found. Place your service account JSON in the app folder.")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    return sheet

def append_orders_to_sheet(rows, sheet_name="Teamwear_Bestellungen"):
    try:
        sheet = connect_to_sheet(sheet_name)
        for r in rows:
            sheet.append_row(r)
        return True, None
    except Exception as e:
        return False, str(e)

def append_orders_to_csv(rows, csv_path="orders_local.csv"):
    import csv
    file_exists = os.path.exists(csv_path)
    with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp","Name","Team","Nummer","Artikel","Größe","Farbe","Menge","Einzelpreis","Summe"])
        for r in rows:
            writer.writerow(r)
    return True, None

def generate_invoice_pdf(cart, customer_name, team, filename=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(595, 842))
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Rechnung - Münster Phoenix", styles['Title']))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Datum: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    story.append(Paragraph(f"Kunde: {customer_name}", styles['Normal']))
    story.append(Paragraph(f"Team: {team}", styles['Normal']))
    story.append(Spacer(1, 12))

    data = [["Artikel", "Größe", "Farbe", "Menge", "Einzelpreis (€)", "Summe (€)"]]
    total = 0.0
    for item in cart:
        data.append([item['artikel'], item['size'], item['color'], item['qty'], f"{item['price']:.2f}", f"{item['line_total']:.2f}"])
        total += item['line_total']

    data.append(['', '', '', '', 'Gesamt', f"{total:.2f}"])

    table = Table(data, hAlign='LEFT', colWidths=[140,50,60,40,80,80])
    tbl_style = TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, rl_colors.black),
        ('BACKGROUND', (0,0), (-1,0), rl_colors.lightgrey),
        ('ALIGN', (-2,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
    ])
    table.setStyle(tbl_style)
    story.append(table)
    story.append(Spacer(1,12))
    story.append(Paragraph("Vielen Dank für Ihre Bestellung!", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ---------------------------
# Streamlit App
# ---------------------------
st.set_page_config(page_title="Münster Phoenix Teamwear", layout='wide')
st.title("Münster Phoenix – Teamwear Preisrechner, Angebot & Rechnung")

if 'cart' not in st.session_state:
    st.session_state.cart = []

# Left column: add item
col1, col2 = st.columns([1,2])
with col1:
    st.header("Neue Position hinzufügen")
    with st.form(key='add_item_form', clear_on_submit=True):
        name = st.text_input("Name Spieler*in", key='name_input')
        team = st.text_input("Team / Mannschaft", key='team_input')
        nummer = st.text_input("Rückennummer (optional)", key='num_input')
        artikel = st.selectbox("Artikel oder Paket", list(PRICES.keys()), key='artikel_select')
        size = st.selectbox("Größe", SIZES, index=2, key='size_select')
        color = st.selectbox("Farbe", COLORS, index=0, key='color_select')
        qty = st.number_input("Menge", min_value=1, value=1, step=1, key='qty_input')
        submitted = st.form_submit_button("In den Warenkorb legen")
        if submitted:
            price = get_price_for_size(artikel, size)
            line_total = price * qty
            st.session_state.cart.append({
                'name': name,
                'team': team,
                'nummer': nummer,
                'artikel': artikel,
                'size': size,
                'color': color,
                'qty': qty,
                'price': price,
                'line_total': line_total
            })
            st.success(f"{qty} x {artikel} ({size}, {color}) hinzugefügt — {line_total:.2f} €")

# Right column: cart & actions
with col2:
    st.header("Warenkorb / Angebotsvorschau")
    if len(st.session_state.cart) == 0:
        st.info("Der Warenkorb ist leer. Füge Artikel hinzu.")
    else:
        df = pd.DataFrame(st.session_state.cart)
        df_display = df[['artikel','size','color','qty','price','line_total','name','team','nummer']].rename(columns={
            'artikel':'Artikel','size':'Größe','color':'Farbe','qty':'Menge','price':'Einzelpreis','line_total':'Summe','name':'Spieler','team':'Team','nummer':'Nummer'
        })
        st.dataframe(df_display, use_container_width=True)
        total = df['line_total'].sum()
        st.subheader(f"Gesamtsumme: {total:.2f} €")

        # Actions: Download Angebot CSV
        csv_bytes = df_display.to_csv(index=False).encode('utf-8')
        st.download_button("Angebot (CSV) herunterladen", data=csv_bytes, file_name='angebot.csv', mime='text/csv')

        # Download Rechnung PDF für den aktuellen Warenkorb
        if st.button("Rechnung (PDF) herunterladen"):
            customer_name = df['name'].iloc[0] if 'name' in df.columns else ''
            customer_team = df['team'].iloc[0] if 'team' in df.columns else ''
            pdf = generate_invoice_pdf(st.session_state.cart, customer_name, customer_team)
            st.download_button("PDF herunterladen", data=pdf, file_name='Rechnung.pdf', mime='application/pdf')

        # Submit orders (Google Sheets or local CSV)
        st.markdown("---")
        st.write("Bestellungen absenden (speichert jede Position als einzelne Zeile)")
        col_sub1, col_sub2 = st.columns([1,1])
        with col_sub1:
            if st.button("Absenden → Google Sheets (falls konfiguriert)"):
                rows = []
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for item in st.session_state.cart:
                    rows.append([ts, item['name'], item['team'], item['nummer'], item['artikel'], item['size'], item['color'], item['qty'], f"{item['price']:.2f}", f"{item['line_total']:.2f}"])
                success, err = append_orders_to_sheet(rows)
                if success:
                    st.success("Bestellungen wurden in Google Sheets eingetragen.")
                    st.session_state.cart = []
                else:
                    st.error(f"Fehler beim Schreiben in Google Sheets: {err}")
        with col_sub2:
            if st.button("Absenden → Lokal (CSV)"):
                rows = []
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for item in st.session_state.cart:
                    rows.append([ts, item['name'], item['team'], item['nummer'], item['artikel'], item['size'], item['color'], item['qty'], f"{item['price']:.2f}", f"{item['line_total']:.2f}"])
                ok, err = append_orders_to_csv(rows)
                if ok:
                    st.success("Bestellungen wurden lokal in orders_local.csv gespeichert.")
                    st.session_state.cart = []
                else:
                    st.error(f"Fehler beim Speichern: {err}")

# Admin / Übersicht
st.markdown("---")
st.header("Admin: Bestellungen Übersicht")
# Try to show Google Sheet if available; otherwise show local CSV if exists
shown = False
if GS_AVAILABLE:
    try:
        sheet = connect_to_sheet()
        data = sheet.get_all_records()
        if data:
            df_sheet = pd.DataFrame(data)
            st.subheader('Bestellungen (Google Sheets)')
            st.dataframe(df_sheet)
            shown = True
    except Exception as e:
        st.info("Google Sheets nicht verbunden oder Fehler: " + str(e))
if not shown:
    csv_path = 'orders_local.csv'
    if os.path.exists(csv_path):
        try:
            df_local = pd.read_csv(csv_path)
            st.subheader('Bestellungen (lokal)')
            st.dataframe(df_local)
            shown = True
        except Exception as e:
            st.warning('Fehler beim Laden der lokalen Bestellungen: ' + str(e))

if not shown:
    st.info('Noch keine Bestellungen vorhanden oder Google Sheets nicht verbunden.')
