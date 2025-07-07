#!/usr/bin/env python3
# start_dashboard_advanced.py
"""
Script pour démarrer le dashboard avancé avec connexion aux vrais tests.
Version améliorée qui se connecte aux données réelles.
"""

import os
import sys
import webbrowser
import time
import json
import threading
import http.server
import socketserver
from pathlib import Path
from datetime import datetime


class AdvancedDashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Handler avancé qui sert les données de test réelles."""

    def do_GET(self):
        if self.path == '/':
            self.path = '/monitoring_dashboard.html'
        elif self.path == '/api/metrics':
            self.send_real_metrics()
            return
        elif self.path == '/api/status':
            self.send_system_status()
            return
        elif self.path.startswith('/logs/'):
            self.serve_log_files()
            return

        return super().do_GET()

    def send_real_metrics(self):
        """Envoie les vraies métriques des tests."""
        try:
            # Chercher les derniers rapports de test
            metrics_dir = Path("logs/metrics")
            latest_data = {}

            if metrics_dir.exists():
                # Charger le rapport baseline le plus récent
                baseline_files = list(metrics_dir.glob("baseline_report_*.json"))
                if baseline_files:
                    latest_baseline = max(baseline_files, key=lambda f: f.stat().st_mtime)
                    with open(latest_baseline, 'r', encoding='utf-8') as f:
                        baseline_data = json.load(f)
                        latest_data['baseline'] = baseline_data

                # Charger le rapport de scalabilité
                scala_files = list(metrics_dir.glob("scalability_report_*.json"))
                if scala_files:
                    latest_scala = max(scala_files, key=lambda f: f.stat().st_mtime)
                    with open(latest_scala, 'r', encoding='utf-8') as f:
                        scala_data = json.load(f)
                        latest_data['scalability'] = scala_data

                # Charger le rapport de pics
                spike_files = list(metrics_dir.glob("spike_report_*.json"))
                if spike_files:
                    latest_spike = max(spike_files, key=lambda f: f.stat().st_mtime)
                    with open(latest_spike, 'r', encoding='utf-8') as f:
                        spike_data = json.load(f)
                        latest_data['spike'] = spike_data

            # Réponse avec vraies données ou simulation
            response_data = {
                'real_data': len(latest_data) > 0,
                'timestamp': datetime.now().isoformat(),
                'data': latest_data if latest_data else self.get_simulation_data()
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, default=str).encode())

        except Exception as e:
            print(f"Erreur lors de l'envoi des métriques: {e}")
            self.send_error(500)

    def get_simulation_data(self):
        """Retourne des données de simulation basées sur vos vrais résultats."""
        return {
            'baseline': {
                'summary': {
                    'total_requests': 291,
                    'completed_requests': 291,
                    'success_rate': 1.0,
                    'avg_response_time': 1.84,
                    'max_throughput': 5.6
                },
                'performance': {
                    'equity_ratio': 1.05,
                    'vip_avg_response_time': 1.87,
                    'standard_avg_response_time': 1.84
                }
            },
            'scalability': {
                'results': [
                    {'volume': 1000, 'success_rate': 1.0, 'throughput': 7.6}
                ]
            },
            'spike': {
                'summary': {
                    'total_requests': 553,
                    'success_rate': 1.0,
                    'max_throughput': 8.2
                }
            }
        }

    def send_system_status(self):
        """Envoie le statut du système."""
        try:
            # Vérifier l'état des tests
            logs_dir = Path("logs/scenarios")
            recent_tests = 0

            if logs_dir.exists():
                # Compter les rapports récents (moins de 1 heure)
                one_hour_ago = time.time() - 3600
                for report_file in logs_dir.glob("scenario_*.json"):
                    if report_file.stat().st_mtime > one_hour_ago:
                        recent_tests += 1

            status_data = {
                'system_active': recent_tests > 0,
                'tests_running': recent_tests,
                'last_update': datetime.now().isoformat(),
                'scenarios_available': ['baseline', 'scalability', 'spike_load'],
                'status': 'ACTIVE' if recent_tests > 0 else 'IDLE'
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(status_data).encode())

        except Exception as e:
            print(f"Erreur status: {e}")
            self.send_error(500)

    def serve_log_files(self):
        """Sert les fichiers de log directement."""
        try:
            # Retirer '/logs/' du chemin
            file_path = self.path[6:]  # Enlever '/logs/'
            full_path = Path("logs") / file_path

            if full_path.exists() and full_path.is_file():
                self.send_response(200)
                if full_path.suffix == '.json':
                    self.send_header('Content-type', 'application/json')
                else:
                    self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                with open(full_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)

        except Exception as e:
            print(f"Erreur fichier log: {e}")
            self.send_error(500)


def create_advanced_dashboard():
    """Crée le dashboard avancé avec le HTML corrigé."""

    # Récupérer le HTML du dashboard corrigé depuis les artifacts
    dashboard_html = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoring Temps Réel - Système Multi-Agents</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <!-- Insérer ici le CSS et JavaScript du dashboard corrigé -->
    <style>
        :root {
            --primary-color: #2563eb;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            --info-color: #06b6d4;
        }
        body {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .dashboard-header {
            background: linear-gradient(135deg, var(--primary-color) 0%, #1e40af 100%);
            color: white;
            padding: 20px 0;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .metric-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
            position: relative;
            overflow: hidden;
        }
        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--primary-color);
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin: 10px 0;
        }
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-online { background: var(--success-color); }
        .status-idle { background: #6b7280; }
        .status-warning { background: var(--warning-color); }
        .status-error { background: var(--danger-color); }
        .data-source {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 15px;
            font-size: 0.9rem;
        }
        .real-data { border-left: 4px solid var(--success-color); }
        .simulated-data { border-left: 4px solid var(--warning-color); }
    </style>
</head>
<body>
    <div class="dashboard-header">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-8">
                    <h1 class="mb-0">
                        <i class="fas fa-chart-line me-3"></i>
                        Monitoring Temps Réel - Système Multi-Agents
                    </h1>
                    <p class="mb-0 mt-2 opacity-75">Dashboard Avancé avec Connexion aux Tests Réels</p>
                </div>
                <div class="col-md-4 text-end">
                    <div id="systemStatus">
                        <span class="status-indicator status-idle"></span>
                        <span>Chargement...</span>
                    </div>
                    <div id="lastUpdate" style="color: rgba(255,255,255,0.8); font-size: 0.85rem; margin-top: 5px;">
                        Dernière mise à jour: --:--:--
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="container-fluid">
        <div class="row">
            <div class="col-12">
                <div id="dataSourceIndicator" class="data-source simulated-data">
                    <i class="fas fa-info-circle me-2"></i>
                    <strong>Mode:</strong> <span id="dataMode">Chargement...</span>
                    <br><small>Connexion aux données de test en cours...</small>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-lg-3 col-md-6">
                <div class="metric-card">
                    <div style="color: #64748b; font-size: 0.9rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">
                        <i class="fas fa-tachometer-alt me-2"></i>
                        Débit Actuel
                    </div>
                    <div class="metric-value text-primary" id="currentThroughput">--</div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">req/s</small>
                        <small class="text-muted">Max testé: 8.4</small>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6">
                <div class="metric-card">
                    <div style="color: #64748b; font-size: 0.9rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">
                        <i class="fas fa-clock me-2"></i>
                        Temps de Réponse
                    </div>
                    <div class="metric-value text-success" id="avgResponseTime">--</div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">secondes</small>
                        <small class="text-muted">Objectif: 1.84s</small>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6">
                <div class="metric-card">
                    <div style="color: #64748b; font-size: 0.9rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">
                        <i class="fas fa-balance-scale me-2"></i>
                        Ratio d'Équité
                    </div>
                    <div class="metric-value text-info" id="equityRatio">--</div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">Standard/VIP</small>
                        <small class="text-muted">Optimal: 1.05</small>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6">
                <div class="metric-card">
                    <div style="color: #64748b; font-size: 0.9rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">
                        <i class="fas fa-check-circle me-2"></i>
                        Taux de Réussite
                    </div>
                    <div class="metric-value text-success" id="successRate">--</div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">Global</small>
                        <small class="text-muted">Objectif: 100%</small>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-lg-4">
                <div class="metric-card">
                    <h5 class="mb-3">
                        <i class="fas fa-clipboard-check me-2"></i>
                        Test Baseline
                    </h5>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Requêtes Traitées</span>
                        <span><strong id="baselineRequests">--</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Taux de Réussite</span>
                        <span class="text-success"><strong id="baselineSuccess">--</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Temps Réponse</span>
                        <span><strong id="baselineResponse">--</strong></span>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Équité</span>
                        <span class="text-success"><strong id="baselineEquity">--</strong></span>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="metric-card">
                    <h5 class="mb-3">
                        <i class="fas fa-expand-arrows-alt me-2"></i>
                        Test Scalabilité
                    </h5>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Volume Maximum</span>
                        <span><strong id="scalaMax">--</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Taux de Réussite</span>
                        <span class="text-success"><strong id="scalaSuccess">--</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Débit Maximum</span>
                        <span><strong id="scalaDebit">--</strong></span>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Scalabilité</span>
                        <span class="text-success"><strong id="scalaStatus">--</strong></span>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="metric-card">
                    <h5 class="mb-3">
                        <i class="fas fa-mountain me-2"></i>
                        Test Pics de Charge
                    </h5>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Requêtes Traitées</span>
                        <span><strong id="spikeRequests">--</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Taux de Réussite</span>
                        <span class="text-success"><strong id="spikeSuccess">--</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Pic Géré</span>
                        <span><strong id="spikePeak">--</strong></span>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Récupération</span>
                        <span class="text-success"><strong id="spikeRecovery">--</strong></span>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-12">
                <div class="metric-card">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="mb-0">
                            <i class="fas fa-rocket me-2"></i>
                            Commandes pour Lancer les Tests
                        </h5>
                        <button class="btn btn-primary btn-sm" onclick="loadData()">
                            <i class="fas fa-sync-alt me-1"></i>Actualiser
                        </button>
                    </div>

                    <div class="row">
                        <div class="col-md-6">
                            <div class="alert alert-success">
                                <h6><i class="fas fa-play-circle me-2"></i>Tous les Scénarios</h6>
                                <code>python tests/performance/run_all_scenarios.py --all</code>
                                <p class="mb-0 mt-2">Lance les 3 scénarios complets avec rapports</p>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="alert alert-info">
                                <h6><i class="fas fa-cog me-2"></i>Scénario Spécifique</h6>
                                <code>python tests/performance/scenarios/scenario_1_baseline.py</code>
                                <p class="mb-0 mt-2">Lance un scénario individuel</p>
                            </div>
                        </div>
                    </div>

                    <div class="alert alert-warning">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>Note:</strong> Le dashboard se met à jour automatiquement quand vous lancez vos tests.
                        Les métriques passent de "simulation" à "données réelles" pendant l'exécution.
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let realDataMode = false;
        let updateInterval = null;

        async function loadData() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();

                setRealDataMode(data.real_data);

                if (data.real_data && data.data) {
                    updateMetricsFromReal(data.data);
                } else {
                    updateMetricsFromSimulation(data.data);
                }

                updateLastUpdate();

            } catch (error) {
                console.error('Erreur chargement:', error);
                setRealDataMode(false);
            }
        }

        function updateMetricsFromReal(data) {
            if (data.baseline) {
                const baseline = data.baseline;
                updateElement('currentThroughput', baseline.summary.max_throughput.toFixed(1));
                updateElement('avgResponseTime', baseline.summary.avg_response_time.toFixed(2));
                updateElement('equityRatio', baseline.performance.equity_ratio.toFixed(2));
                updateElement('successRate', (baseline.summary.success_rate * 100).toFixed(1) + '%');

                updateElement('baselineRequests', baseline.summary.total_requests);
                updateElement('baselineSuccess', (baseline.summary.success_rate * 100).toFixed(0) + '%');
                updateElement('baselineResponse', baseline.summary.avg_response_time.toFixed(2) + 's');
                updateElement('baselineEquity', baseline.performance.equity_ratio.toFixed(2));
            }

            if (data.scalability) {
                const scala = data.scalability;
                const maxResult = scala.results[scala.results.length - 1];
                updateElement('scalaMax', maxResult.volume + ' req');
                updateElement('scalaSuccess', (maxResult.success_rate * 100).toFixed(0) + '%');
                updateElement('scalaDebit', maxResult.throughput.toFixed(1) + ' req/s');
                updateElement('scalaStatus', 'Linéaire');
            }

            if (data.spike) {
                const spike = data.spike;
                updateElement('spikeRequests', spike.summary.total_requests);
                updateElement('spikeSuccess', (spike.summary.success_rate * 100).toFixed(0) + '%');
                updateElement('spikePeak', spike.summary.max_throughput.toFixed(1) + ' req/s');
                updateElement('spikeRecovery', 'Auto');
            }
        }

        function updateMetricsFromSimulation(data) {
            if (data.baseline) {
                const baseline = data.baseline;
                updateElement('currentThroughput', baseline.summary.max_throughput.toFixed(1));
                updateElement('avgResponseTime', baseline.summary.avg_response_time.toFixed(2));
                updateElement('equityRatio', baseline.performance.equity_ratio.toFixed(2));
                updateElement('successRate', (baseline.summary.success_rate * 100).toFixed(1) + '%');

                updateElement('baselineRequests', baseline.summary.total_requests);
                updateElement('baselineSuccess', (baseline.summary.success_rate * 100).toFixed(0) + '%');
                updateElement('baselineResponse', baseline.summary.avg_response_time.toFixed(2) + 's');
                updateElement('baselineEquity', baseline.performance.equity_ratio.toFixed(2));
            }

            // Valeurs par défaut pour les autres
            updateElement('scalaMax', '1000 req');
            updateElement('scalaSuccess', '100%');
            updateElement('scalaDebit', '7.6 req/s');
            updateElement('scalaStatus', 'Linéaire');

            updateElement('spikeRequests', '553');
            updateElement('spikeSuccess', '100%');
            updateElement('spikePeak', '8.2 req/s');
            updateElement('spikeRecovery', 'Auto');
        }

        function setRealDataMode(isReal) {
            realDataMode = isReal;
            const indicator = document.getElementById('dataSourceIndicator');
            const modeText = document.getElementById('dataMode');
            const statusElement = document.getElementById('systemStatus');

            if (isReal) {
                indicator.className = 'data-source real-data';
                modeText.textContent = 'Données Réelles (Tests détectés)';
                indicator.innerHTML = '<i class="fas fa-check-circle me-2"></i><strong>Mode:</strong> <span id="dataMode">Données Réelles (Tests détectés)</span><br><small>Métriques authentiques de vos tests de performance</small>';

                statusElement.innerHTML = '<span class="status-indicator status-online"></span><span>Tests Actifs</span>';
            } else {
                indicator.className = 'data-source simulated-data';
                modeText.textContent = 'Simulation (Résultats de référence)';
                indicator.innerHTML = '<i class="fas fa-info-circle me-2"></i><strong>Mode:</strong> <span id="dataMode">Simulation (Résultats de référence)</span><br><small>Affichage des résultats de vos tests précédents</small>';

                statusElement.innerHTML = '<span class="status-indicator status-idle"></span><span>En Attente</span>';
            }
        }

        function updateElement(id, value) {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        }

        function updateLastUpdate() {
            document.getElementById('lastUpdate').textContent = 
                'Dernière mise à jour: ' + new Date().toLocaleTimeString();
        }

        // Initialisation
        document.addEventListener('DOMContentLoaded', function() {
            loadData();

            // Mise à jour automatique toutes les 5 secondes
            updateInterval = setInterval(loadData, 5000);
        });

        // Nettoyage
        window.addEventListener('beforeunload', function() {
            if (updateInterval) {
                clearInterval(updateInterval);
            }
        });
    </script>
</body>
</html>"""

    # Sauvegarder le dashboard
    dashboard_file = Path("monitoring_dashboard.html")
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(dashboard_html)

    print(f"✅ Dashboard avancé créé: {dashboard_file}")
    return dashboard_file


def start_advanced_dashboard(port=8080):
    """Démarre le serveur dashboard avancé."""

    print("🚀 DASHBOARD AVANCÉ - SYSTÈME MULTI-AGENTS")
    print("=" * 50)

    # Créer le dashboard HTML
    dashboard_file = create_advanced_dashboard()

    try:
        # Démarrer le serveur
        with socketserver.TCPServer(("", port), AdvancedDashboardHandler) as httpd:
            print(f"🌐 Serveur démarré sur http://localhost:{port}")
            print(f"📊 Dashboard: {dashboard_file}")
            print("🔄 Connexion automatique aux tests en cours")
            print("\n💡 FONCTIONNALITÉS:")
            print("   • Détection automatique des tests en cours")
            print("   • Passage automatique simulation ↔ données réelles")
            print("   • Métriques basées sur vos vrais résultats")
            print("   • Mise à jour toutes les 5 secondes")

            # Ouvrir le navigateur
            time.sleep(1)
            url = f"http://localhost:{port}"
            webbrowser.open(url)
            print(f"\n🌐 Dashboard ouvert: {url}")
            print("\nCtrl+C pour arrêter")
            print("=" * 50)

            httpd.serve_forever()

    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} déjà utilisé. Essayez:")
            print(f"python start_dashboard_advanced.py --port {port + 1}")
        else:
            print(f"❌ Erreur: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n🛑 Dashboard arrêté")
        return 0


def main():
    """Fonction principale."""
    import argparse

    parser = argparse.ArgumentParser(description="Dashboard avancé pour tests de performance")
    parser.add_argument("--port", type=int, default=8080, help="Port du serveur (défaut: 8080)")
    args = parser.parse_args()

    # Vérifier qu'on est dans le bon répertoire
    if not Path("tests").exists():
        print("❌ Veuillez lancer depuis le répertoire racine du projet")
        print("   (là où se trouve le dossier tests/)")
        return 1

    return start_advanced_dashboard(args.port)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)