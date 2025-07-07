# debug_dashboard.py - Script pour diagnostiquer les problèmes

import os
import sys
import traceback


def check_structure():
    """Vérifie la structure des dossiers"""
    print("🔍 Vérification de la structure des dossiers...")

    required_files = [
        'dashboard/',
        'dashboard/templates/',
        'dashboard/templates/admin_dashboard.html',
        'dashboard/templates/client_interface.html'
    ]

    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ MANQUANT: {file_path}")

    print()


def check_imports():
    """Vérifie les imports nécessaires"""
    print("🔍 Vérification des imports...")

    try:
        import flask
        print(f"✅ Flask {flask.__version__}")
    except ImportError:
        print("❌ Flask non installé - Exécutez: pip install flask")
        return False

    try:
        import json
        print("✅ JSON")
    except ImportError:
        print("❌ JSON manquant")
        return False

    print()
    return True


def test_simple_flask():
    """Test Flask minimal"""
    print("🧪 Test Flask minimal...")

    try:
        from flask import Flask
        app = Flask(__name__)

        @app.route('/')
        def home():
            return "<h1>✅ Flask fonctionne !</h1><p>Si vous voyez ceci, Flask est OK.</p>"

        print("✅ Flask minimal créé avec succès")
        print("🚀 Démarrage sur http://localhost:5000")
        print("🛑 Appuyez sur Ctrl+C pour arrêter\n")

        app.run(host='0.0.0.0', port=5000, debug=True)

    except Exception as e:
        print(f"❌ Erreur Flask: {e}")
        traceback.print_exc()


def main():
    print("🔧 DIAGNOSTIC DASHBOARD")
    print("=" * 40)

    check_structure()

    if not check_imports():
        print("⚠️  Installez Flask d'abord: pip install flask")
        return

    print("🤔 Voulez-vous tester Flask minimal ? (y/n)")
    choice = input().lower().strip()

    if choice in ['y', 'yes', 'o', 'oui']:
        test_simple_flask()
    else:
        print("📋 Diagnostic terminé. Vérifiez les points marqués ❌ ci-dessus.")


if __name__ == "__main__":
    main()