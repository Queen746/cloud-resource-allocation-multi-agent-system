# start_monitoring_dashboard.py
"""
Serveur simple pour lancer le dashboard de monitoring.
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path


def start_dashboard_server(port=8080):
    """Démarre le serveur du dashboard."""

    # Vérifier si le fichier HTML existe
    dashboard_file = "monitoring_dashboard.html"
    if not os.path.exists(dashboard_file):
        print(f"❌ Erreur: Le fichier '{dashboard_file}' n'existe pas!")
        print("💡 Assurez-vous d'avoir sauvegardé le code HTML du dashboard.")
        return

    print(f"🚀 Démarrage du serveur dashboard...")
    print(f"📊 Dashboard disponible sur: http://localhost:{port}")
    print(f"🔄 Le dashboard se met à jour automatiquement toutes les 3 secondes")
    print(f"⏹️  Appuyez sur Ctrl+C pour arrêter")
    print("=" * 60)

    try:
        # Créer le serveur HTTP
        with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
            print(f"✅ Serveur démarré avec succès sur le port {port}")

            # Ouvrir automatiquement le navigateur
            webbrowser.open(f"http://localhost:{port}/monitoring_dashboard.html")

            # Démarrer le serveur
            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\n⏹️  Serveur arrêté par l'utilisateur")
    except OSError as e:
        if e.errno == 10048:  # Port déjà utilisé sur Windows
            print(f"❌ Erreur: Le port {port} est déjà utilisé")
            print(f"💡 Essayez un autre port: python start_monitoring_dashboard.py --port 8081")
        else:
            print(f"❌ Erreur: {e}")
    except Exception as e:
        print(f"💥 Erreur inattendue: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Serveur Dashboard Monitoring")
    parser.add_argument("--port", type=int, default=8080, help="Port du serveur (défaut: 8080)")
    args = parser.parse_args()

    start_dashboard_server(args.port)