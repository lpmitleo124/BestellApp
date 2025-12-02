
# Teamwear Streamlit App (Münster Phoenix)

Diese App ist ein kompletter Preisrechner + Warenkorb + Angebots- und Rechnungs-Export.
Die App unterstützt das Speichern von Bestellungen in **Google Sheets** (empfohlen) oder lokal in einer CSV-Datei als Fallback.

## Features
- Preise für Einzelartikel & Pakete (XS-XXL und 3XL-5XL)
- Farbauswahl: **Schwarz, Weiß, Orange, Rot**
- Warenkorb (mehrere Positionen hinzufügen)
- Angebot (CSV) herunterladen
- Rechnung (PDF) herunterladen
- Bestellungen senden an Google Sheets (wenn `google_credentials.json` vorhanden) oder lokal speichern (orders_local.csv)
- Admin-Übersicht (zeigt Google Sheets oder lokale CSV)

## Setup (kurz)
1. Python 3.8+ installieren.
2. In dein Projektverzeichnis wechseln.
3. Virtuelle Umgebung erstellen (optional):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # mac/linux
   .\.venv\Scripts\activate  # windows
   ```
4. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```
5. Google Sheets (optional):
   - Service Account in Google Cloud erstellen (Anleitung weiter unten).
   - JSON-Schlüssel herunterladen und in `google_credentials.json` umbenennen.
   - Google Sheet erstellen mit Namen `Teamwear_Bestellungen` und die Service Account E-Mail als Bearbeiter hinzufügen.

6. App starten:
   ```bash
   streamlit run app.py
   ```

## Hinweise zu Google Sheets
- Falls `google_credentials.json` fehlt oder nicht korrekt ist, bleibt die App funktional und speichert Bestellungen lokal in `orders_local.csv`.
- `google_credentials.json.sample` ist als Beispiel enthalten — **keine echten Credentials** in das Projekt kopieren.

## Dateien in diesem Repo
- `app.py` – die Streamlit App
- `requirements.txt` – benötigte Python-Pakete
- `google_credentials.json.sample` – Platzhalter / Beispielname
- `README.md` – diese Anleitung
