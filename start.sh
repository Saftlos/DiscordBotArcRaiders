#!/bin/bash

# In das Verzeichnis des Skripts wechseln
cd "$(dirname "$0")"

# Prüfen, ob das Virtual Environment (venv) existiert
if [ ! -d "venv" ]; then
    echo "⚠️  Kein 'venv' Ordner gefunden."
    echo "⚙️  Erstelle Virtual Environment und installiere Abhängigkeiten..."
    
    python3 -m venv venv
    source venv/bin/activate
    
    # Pip upgraden und Requirements installieren
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "✅ Installation abgeschlossen."
else
    # Venv aktivieren
    source venv/bin/activate
fi

# Bot starten
echo "🚀 Starte Arc Raiders Bot..."
python main.py
