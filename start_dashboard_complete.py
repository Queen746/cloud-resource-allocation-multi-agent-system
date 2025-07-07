#!/usr/bin/env python3
"""
Dashboard complet pour visualiser les résultats des tests de performance
du système multi-agents.
"""

import http.server
import socketserver
import webbrowser
import threading
import time
import json
import random
from datetime import datetime
from pathlib import Path


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_dashboard_html()
            return
        elif self.path == '/api/status':
            self.send_api_response()
            return
        elif self.path == '/api/results':
            self.send_results_response()
            return
        elif self.path == '/api/logs':
            self.send_logs_response()
            return
        elif self.path == '/api/real-data':  # 🆕 NOUVELLE ROUTE
            self.send_real_data_response()
            return

        return super().do_GET()

    def send_dashboard_html(self):
        """Génère et envoie le HTML du dashboard."""
        html_content = self.create_dashboard_html()

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def send_real_data_response(self):
        """🆕 Envoie les vraies données de vos tests."""
        try:
            real_data = {}

            # 1. Charger le rapport global le plus récent
            global_reports_dir = Path("logs/global_reports")
            if global_reports_dir.exists():
                global_files = list(global_reports_dir.glob("global_performance_report_*.json"))
                if global_files:
                    latest_global = max(global_files, key=lambda f: f.stat().st_mtime)
                    with open(latest_global, 'r', encoding='utf-8') as f:
                        real_data['global'] = json.load(f)

            # 2. Charger les rapports de scénarios les plus récents
            scenarios_dir = Path("logs/scenarios")
            if scenarios_dir.exists():
                scenario_files = list(scenarios_dir.glob("scenario_*.json"))
                real_data['scenarios'] = []

                for scenario_file in scenario_files:
                    try:
                        with open(scenario_file, 'r', encoding='utf-8') as f:
                            scenario_data = json.load(f)
                            real_data['scenarios'].append(scenario_data)
                    except Exception as e:
                        print(f"Erreur lecture {scenario_file}: {e}")

            # 3. Marquer comme données réelles
            real_data['data_source'] = 'real'
            real_data['last_update'] = datetime.now().isoformat()
            real_data['available'] = len(real_data.get('scenarios', [])) > 0

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(real_data, default=str).encode())

        except Exception as e:
            # En cas d'erreur, renvoyer des données par défaut
            error_data = {
                'data_source': 'simulated',
                'available': False,
                'error': str(e),
                'last_update': datetime.now().isoformat()
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_data).encode())

    def send_api_response(self):
        """Envoie des données simulées pour l'API."""
        data = {
            'status': 'running',
            'throughput': random.uniform(12, 16),
            'response_time': random.uniform(0.8, 1.5),
            'equity_ratio': random.uniform(1.1, 1.4),
            'timestamp': datetime.now().isoformat()
        }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_results_response(self):
        """Envoie des résultats simulés."""
        data = {
            'baseline': {'success_rate': 100, 'avg_response_time': 1.30},
            'scalability': {'max_volume': 1000, 'consistency': 0.98},
            'spike_test': {'max_throughput': 14.6, 'recovery_time': 15}
        }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_logs_response(self):
        """Envoie des logs simulés."""
        logs = [
            {'level': 'INFO', 'message': 'Système démarré', 'timestamp': datetime.now().isoformat()},
            {'level': 'SUCCESS', 'message': 'Tests baseline terminés avec succès',
             'timestamp': datetime.now().isoformat()},
            {'level': 'WARNING', 'message': 'Test de scalabilité en cours...', 'timestamp': datetime.now().isoformat()}
        ]

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(logs).encode())

    def create_dashboard_html(self):
        """Crée le HTML complet du dashboard."""
        return '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Dashboard Multi-Agents - Tests de Performance</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .header {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 1rem 2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }

        .header h1 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }

        .header p {
            opacity: 0.9;
            font-size: 1.1rem;
        }

        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 2rem;
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }

        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }

        .card h3 {
            margin-bottom: 1rem;
            font-size: 1.3rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .metric {
            background: rgba(255, 255, 255, 0.05);
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            border-left: 4px solid #4CAF50;
        }

        .metric-label {
            font-size: 0.9rem;
            opacity: 0.8;
            margin-bottom: 0.5rem;
        }

        .metric-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #4CAF50;
        }

        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }

        .status-online { background: #4CAF50; }
        .status-warning { background: #FF9800; }
        .status-error { background: #f44336; }

        .chart-container {
            grid-column: span 2;
            height: 400px;
            position: relative;
        }

        #performanceChart {
            width: 100%;
            height: 100%;
        }

        .logs-container {
            grid-column: span 1;
            max-height: 400px;
            overflow-y: auto;
        }

        .log-entry {
            background: rgba(255, 255, 255, 0.05);
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            border-left: 3px solid transparent;
            font-family: 'Consolas', monospace;
            font-size: 0.9rem;
        }

        .log-entry.info { border-left-color: #2196F3; }
        .log-entry.success { border-left-color: #4CAF50; }
        .log-entry.warning { border-left-color: #FF9800; }
        .log-entry.error { border-left-color: #f44336; }

        .test-results {
            grid-column: span 3;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
        }

        .test-result-card {
            background: rgba(255, 255, 255, 0.08);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .test-result-card h4 {
            margin-bottom: 1rem;
            color: #4CAF50;
            font-size: 1.2rem;
        }

        .result-metric {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .result-metric:last-child {
            border-bottom: none;
        }

        .data-mode {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: bold;
        }

        .data-mode.real {
            background: #4CAF50;
            color: white;
        }

        .data-mode.simulated {
            background: #FF9800;
            color: white;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        .loading {
            animation: pulse 2s infinite;
        }

        .last-update {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.1);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.8rem;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="data-mode simulated" id="dataMode">📊 Mode Simulation</div>

    <div class="header">
        <h1>🚀 Dashboard Multi-Agents - Tests de Performance</h1>
        <p>Surveillance en temps réel des performances du système</p>
    </div>

    <div class="main-grid">
        <!-- Métriques temps réel -->
        <div class="card">
            <h3>📊 Métriques Temps Réel</h3>
            <div class="metric">
                <div class="metric-label">Débit Actuel</div>
                <div class="metric-value" id="currentThroughput">14.6 req/s</div>
            </div>
            <div class="metric">
                <div class="metric-label">Temps Réponse Moyen</div>
                <div class="metric-value" id="avgResponseTime">1.24s</div>
            </div>
            <div class="metric">
                <div class="metric-label">Ratio d'Équité</div>
                <div class="metric-value" id="equityRatio">1.31</div>
            </div>
        </div>

        <!-- État du système -->
        <div class="card">
            <h3>🏥 État du Système</h3>
            <div class="metric">
                <div class="metric-label">Statut Général</div>
                <div class="metric-value" id="systemStatus">
                    <span class="status-indicator status-warning"></span>
                    <span>En attente de tests...</span>
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">Score Global</div>
                <div class="metric-value" id="globalScore">93.3/100</div>
            </div>
            <div class="metric">
                <div class="metric-label">Débit Maximum</div>
                <div class="metric-value" id="maxThroughput">14.6</div>
            </div>
        </div>

        <!-- Alertes et notifications -->
        <div class="card">
            <h3>🔔 Alertes & Notifications</h3>
            <div class="metric">
                <div class="metric-label">Dernière Alerte</div>
                <div class="metric-value" id="lastAlert" style="font-size: 1rem;">Système stable</div>
            </div>
            <div class="metric">
                <div class="metric-label">Tests Actifs</div>
                <div class="metric-value" id="activeTests">0</div>
            </div>
        </div>

        <!-- Graphique de performance -->
        <div class="card chart-container">
            <h3>📈 Performance en Temps Réel</h3>
            <canvas id="performanceChart"></canvas>
        </div>

        <!-- Logs en temps réel -->
        <div class="card logs-container">
            <h3>📝 Logs Temps Réel</h3>
            <div id="logsContainer">
                <div class="log-entry info">
                    <strong>INFO</strong> - Dashboard démarré
                </div>
                <div class="log-entry warning">
                    <strong>WAIT</strong> - En attente des données de tests...
                </div>
            </div>
        </div>

        <!-- Résultats des tests -->
        <div class="card test-results">
            <h3>🧪 Résultats des Tests</h3>

            <div class="test-result-card">
                <h4>📊 Test Baseline</h4>
                <div class="result-metric">
                    <span>Requêtes traitées:</span>
                    <span id="baselineRequests">291</span>
                </div>
                <div class="result-metric">
                    <span>Taux de réussite:</span>
                    <span id="baselineSuccess">100%</span>
                </div>
                <div class="result-metric">
                    <span>Temps réponse:</span>
                    <span id="baselineResponse">1.30s</span>
                </div>
                <div class="result-metric">
                    <span>Équité:</span>
                    <span id="baselineEquity">1.26</span>
                </div>
            </div>

            <div class="test-result-card">
                <h4>📈 Test Scalabilité</h4>
                <div class="result-metric">
                    <span>Volume maximum:</span>
                    <span id="scalabilityVolume">1000</span>
                </div>
                <div class="result-metric">
                    <span>Consistance:</span>
                    <span id="scalabilityConsistency">En cours...</span>
                </div>
                <div class="result-metric">
                    <span>Dépendances:</span>
                    <span id="scalabilityDeps">Gestion OK</span>
                </div>
            </div>

            <div class="test-result-card">
                <h4>⚡ Test Pics de Charge</h4>
                <div class="result-metric">
                    <span>Requêtes traitées:</span>
                    <span id="spikeRequests">553</span>
                </div>
                <div class="result-metric">
                    <span>Taux de réussite:</span>
                    <span id="spikeSuccess">100%</span>
                </div>
                <div class="result-metric">
                    <span>Pic atteint:</span>
                    <span id="spikePeak">14.6 req/s</span>
                </div>
                <div class="result-metric">
                    <span>Récupération:</span>
                    <span id="spikeRecovery">< 30s</span>
                </div>
            </div>
        </div>
    </div>

    <div class="last-update" id="lastUpdate">
        Dernière mise à jour: En cours...
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <script>
        // Variables globales
        let charts = {};
        let isRealDataMode = false;
        let updateInterval;

        // Initialisation
        document.addEventListener('DOMContentLoaded', function() {
            initializeCharts();
            loadLatestData();
            startDataUpdates();
        });

        function initializeCharts() {
            const ctx = document.getElementById('performanceChart').getContext('2d');

            charts.performance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Débit (req/s)',
                        data: [],
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y'
                    }, {
                        label: 'Temps Réponse (s)',
                        data: [],
                        borderColor: '#2196F3',
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: 'white' }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: 'white' },
                            grid: { color: 'rgba(255, 255, 255, 0.1)' }
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            ticks: { color: 'white' },
                            grid: { color: 'rgba(255, 255, 255, 0.1)' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            ticks: { color: 'white' },
                            grid: { drawOnChartArea: false }
                        }
                    }
                }
            });
        }

        async function loadLatestData() {
            try {
                const response = await fetch('/api/real-data');
                const data = await response.json();

                if (data.available && data.data_source === 'real') {
                    setRealDataMode(true);

                    if (data.global && data.global.summary) {
                        const summary = data.global.summary;
                        updateMetric('currentThroughput', (summary.max_throughput || 14.6).toFixed(1));
                        updateMetric('avgResponseTime', (summary.avg_response_time || 1.24).toFixed(2));
                        updateMetric('equityRatio', (summary.avg_equity || 1.31).toFixed(2));

                        const statusElement = document.getElementById('systemStatus');
                        const successRate = (summary.success_rate * 100).toFixed(0);
                        statusElement.innerHTML = `<span class="status-indicator status-online"></span><span>Tests Terminés - ${successRate}% Réussite</span>`;

                        addEvent('success', `Données réelles chargées - Score: ${data.global.evaluation?.score || '93.3'}/100`);
                    }

                    if (data.scenarios) {
                        for (const scenario of data.scenarios) {
                            if (scenario.scenario_name) {
                                if (scenario.scenario_name.includes('baseline')) {
                                    updateMetric('baselineRequests', scenario.summary?.total_requests || 291);
                                    updateMetric('baselineSuccess', ((scenario.summary?.success_rate || 1.0) * 100).toFixed(0) + '%');
                                    updateMetric('baselineResponse', (scenario.summary?.avg_response_time || 1.30).toFixed(2) + 's');
                                    updateMetric('baselineEquity', (scenario.performance?.equity_ratio || 1.26).toFixed(2));
                                }

                                if (scenario.scenario_name.includes('spike')) {
                                    updateMetric('spikeRequests', scenario.summary?.total_requests || 553);
                                    updateMetric('spikeSuccess', ((scenario.summary?.success_rate || 1.0) * 100).toFixed(0) + '%');
                                    updateMetric('spikePeak', (scenario.performance?.max_throughput || 14.6).toFixed(1) + ' req/s');
                                    updateMetric('maxThroughput', (scenario.performance?.max_throughput || 14.6).toFixed(1));
                                }
                            }
                        }
                    }

                } else {
                    setRealDataMode(false);
                    addEvent('info', 'Mode simulation - Utilisez vos résultats de référence');
                }

            } catch (error) {
                console.error('Erreur chargement données:', error);
                setRealDataMode(false);
                addEvent('warning', 'Erreur chargement - Mode simulation activé');
            }

            updateLastUpdate();
        }

        function setRealDataMode(isReal) {
            isRealDataMode = isReal;
            const modeElement = document.getElementById('dataMode');

            if (isReal) {
                modeElement.textContent = '🎯 Données Réelles';
                modeElement.className = 'data-mode real';
            } else {
                modeElement.textContent = '📊 Mode Simulation';
                modeElement.className = 'data-mode simulated';
            }
        }

        function updateMetric(elementId, value) {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = value;
            }
        }

        function addEvent(type, message) {
            const container = document.getElementById('logsContainer');
            const timestamp = new Date().toLocaleTimeString();

            const logEntry = document.createElement('div');
            logEntry.className = `log-entry ${type}`;
            logEntry.innerHTML = `<strong>${type.toUpperCase()}</strong> [${timestamp}] - ${message}`;

            container.insertBefore(logEntry, container.firstChild);

            // Garder seulement les 10 derniers logs
            while (container.children.length > 10) {
                container.removeChild(container.lastChild);
            }
        }

        function updateLastUpdate() {
            const element = document.getElementById('lastUpdate');
            element.textContent = `Dernière mise à jour: ${new Date().toLocaleTimeString()}`;
        }

        function startDataUpdates() {
            // Charger les données toutes les 5 secondes
            updateInterval = setInterval(() => {
                if (!isRealDataMode) {
                    // Mode simulation - générer des données factices
                    simulateData();
                } else {
                    // Mode réel - recharger les données
                    loadLatestData();
                }
            }, 5000);
        }

        function simulateData() {
            // Simulation de données pour l'aperçu
            const now = new Date().toLocaleTimeString();
            const throughput = 12 + Math.random() * 4;
            const responseTime = 0.8 + Math.random() * 0.7;

            // Mettre à jour le graphique
            if (charts.performance.data.labels.length >= 20) {
                charts.performance.data.labels.shift();
                charts.performance.data.datasets[0].data.shift();
                charts.performance.data.datasets[1].data.shift();
            }

            charts.performance.data.labels.push(now);
            charts.performance.data.datasets[0].data.push(throughput);
            charts.performance.data.datasets[1].data.push(responseTime);
            charts.performance.update('none');

            updateLastUpdate();
        }

        // Arrêter les mises à jour quand la page se ferme
        window.addEventListener('beforeunload', () => {
            if (updateInterval) {
                clearInterval(updateInterval);
            }
        });
    </script>
</body>
</html>'''


def start_dashboard(port=8080):
    """Démarre le serveur dashboard sur le port spécifié."""
    # Essayer plusieurs ports automatiquement
    max_attempts = 10
    original_port = port

    for attempt in range(max_attempts):
        try:
            with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
                dashboard_url = f"http://localhost:{port}"

                print("=" * 80)
                print("🚀 DASHBOARD MULTI-AGENTS - TESTS DE PERFORMANCE")
                print("=" * 80)
                print(f"📊 Dashboard disponible sur: {dashboard_url}")
                print(f"🔄 Rechargement automatique: Activé")
                print(f"📁 Recherche de données dans: logs/")
                print("🎯 Mode: Détection automatique (Réel/Simulation)")
                print("-" * 80)
                print("💡 FONCTIONNALITÉS:")
                print("   ✅ Métriques temps réel")
                print("   ✅ Graphiques de performance")
                print("   ✅ Logs en direct")
                print("   ✅ Résultats des tests")
                print("   ✅ Détection automatique des rapports")
                print("-" * 80)
                print("🛑 Appuyez sur Ctrl+C pour arrêter")
                print("=" * 80)

                # Ouvrir automatiquement dans le navigateur
                def open_browser():
                    time.sleep(1)
                    webbrowser.open(dashboard_url)

                threading.Thread(target=open_browser, daemon=True).start()

                # Démarrer le serveur
                httpd.serve_forever()

        except OSError as e:
            if "Address already in use" in str(e) or "10048" in str(e):
                port += 1
                if attempt < max_attempts - 1:
                    print(f"⚠️ Port {port - 1} occupé, essai du port {port}...")
                    continue
                else:
                    print(f"❌ Impossible de trouver un port libre après {max_attempts} tentatives")
                    print(f"💡 Essayez manuellement: python start_dashboard_complete.py --port {port + 10}")
                    return
            else:
                print(f"❌ Erreur serveur: {e}")
                return
        except KeyboardInterrupt:
            print("\n🛑 Dashboard arrêté par l'utilisateur")
            return

    print(f"❌ Erreur inattendue")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dashboard Multi-Agents pour tests de performance")
    parser.add_argument('--port', type=int, default=8080, help='Port du serveur (défaut: 8080)')

    args = parser.parse_args()
    start_dashboard(args.port)