# start_dashboard_simple.py
"""
Dashboard simple pour visualiser les résultats des tests.
Compatible Windows, fonctionne sans problèmes d'encodage.
"""

import http.server
import socketserver
import json
import os
import threading
import time
import random
from pathlib import Path
from datetime import datetime


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        def do_GET(self):
            if self.path == '/':
                self.path = '/dashboard.html'
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

    def send_api_response(self):
        """Envoie les données de statut en temps réel."""
        # Simuler des données de performance
        data = {
            "timestamp": datetime.now().isoformat(),
            "system_status": "RUNNING",
            "scenarios_completed": random.randint(3, 7),
            "scenarios_total": 7,
            "success_rate": random.uniform(85, 98),
            "queue_sizes": {
                "vip": random.randint(0, 15),
                "standard": random.randint(5, 45)
            },
            "resources": {
                "cpu_usage": random.uniform(30, 85),
                "memory_usage": random.uniform(40, 75),
                "available_cpu": random.uniform(15, 70),
                "available_memory": random.uniform(25, 60)
            },
            "performance": {
                "avg_response_time_vip": random.uniform(1.5, 3.2),
                "avg_response_time_standard": random.uniform(2.1, 4.5),
                "throughput": random.uniform(8, 16),
                "equity_ratio": random.uniform(1.1, 1.4)
            }
        }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_results_response(self):
        """Envoie les résultats des tests."""
        # Lire les résultats des logs si disponibles
        logs_dir = Path("logs/scenarios")
        results = []

        if logs_dir.exists():
            for log_file in logs_dir.glob("*.log"):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "PASSED" in content or "FAILED" in content:
                            results.append({
                                "file": log_file.name,
                                "date": log_file.stat().st_mtime,
                                "summary": self.extract_summary(content)
                            })
                except Exception:
                    continue

        # Données par défaut si pas de logs
        if not results:
            results = [
                {"scenario": "Performance de Base", "status": "PASSED", "success_rate": 95.2, "duration": 3.1},
                {"scenario": "Scalabilité", "status": "PASSED", "success_rate": 93.8, "duration": 5.2},
                {"scenario": "Pics de Charge", "status": "PASSED", "success_rate": 88.4, "duration": 4.7},
                {"scenario": "Dépendances", "status": "PASSED", "success_rate": 100.0, "duration": 6.1},
                {"scenario": "Équité", "status": "PASSED", "success_rate": 96.1, "duration": 4.0},
                {"scenario": "Saturation", "status": "PASSED", "success_rate": 85.3, "duration": 7.2},
                {"scenario": "Récupération", "status": "PASSED", "success_rate": 92.7, "duration": 5.8}
            ]

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(results).encode())

    def send_logs_response(self):
        """Envoie les derniers logs."""
        logs = []

        # Simuler des logs récents
        now = datetime.now()
        for i in range(10):
            logs.append({
                "timestamp": (now.timestamp() - i * 30),
                "level": random.choice(["INFO", "INFO", "INFO", "WARNING"]),
                "message": random.choice([
                    "Demande VIP traitée avec succès",
                    "Allocation de ressources réussie",
                    "Pic de charge détecté",
                    "Équilibrage de charge activé",
                    "Récupération système complète",
                    "Performance nominale atteinte"
                ])
            })

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(logs).encode())

    def extract_summary(self, content):
        """Extrait un résumé du contenu du log."""
        lines = content.split('\n')
        summary = []
        for line in lines:
            if "PASSED" in line or "FAILED" in line or "Taux de réussite" in line:
                summary.append(line.strip())
                if len(summary) >= 3:
                    break
        return summary


def create_dashboard_html():
    """Crée le fichier HTML du dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoring Temps Réel - Système Multi-Agents</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
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

        .metric-label {
            color: #64748b;
            font-size: 0.9rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
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

        .chart-container {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
            height: 400px;
        }

        .alert-panel {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
            max-height: 300px;
            overflow-y: auto;
        }

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
    <!-- Header -->
    <div class="dashboard-header">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-8">
                    <h1 class="mb-0">
                        <i class="fas fa-chart-line me-3"></i>
                        Monitoring Temps Réel - Système Multi-Agents
                    </h1>
                    <p class="mb-0 mt-2 opacity-75">Surveillance des performances et de la santé du système</p>
                </div>
                <div class="col-md-4 text-end">
                    <div id="systemStatus">
                        <span class="status-indicator status-idle"></span>
                        <span>Système en Attente</span>
                    </div>
                    <div id="lastUpdate" style="color: rgba(255,255,255,0.8); font-size: 0.85rem; margin-top: 5px;">
                        Dernière mise à jour: --:--:--
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="container-fluid">
        <!-- Source des Données -->
        <div class="row">
            <div class="col-12">
                <div id="dataSourceIndicator" class="data-source simulated-data">
                    <i class="fas fa-info-circle me-2"></i>
                    <strong>Mode:</strong> <span id="dataMode">Simulation (Aucun test actif)</span>
                    <br><small>Lancez vos tests pour voir les vraies métriques en temps réel</small>
                </div>
            </div>
        </div>

        <!-- Métriques Principales -->
        <div class="row">
            <div class="col-lg-3 col-md-6">
                <div class="metric-card">
                    <div class="metric-label">
                        <i class="fas fa-tachometer-alt me-2"></i>
                        Débit Actuel
                    </div>
                    <div class="metric-value text-primary" id="currentThroughput">0.0</div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">req/s</small>
                        <small class="text-muted">Max: <span id="maxThroughput">8.4</span></small>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6">
                <div class="metric-card">
                    <div class="metric-label">
                        <i class="fas fa-clock me-2"></i>
                        Temps de Réponse
                    </div>
                    <div class="metric-value text-success" id="avgResponseTime">0.0</div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">secondes</small>
                        <small class="text-muted">Objectif: 1.8s</small>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6">
                <div class="metric-card">
                    <div class="metric-label">
                        <i class="fas fa-list me-2"></i>
                        Files d'Attente
                    </div>
                    <div class="metric-value text-warning" id="totalQueue">0</div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">VIP: <span id="vipQueue">0</span> | STD: <span id="stdQueue">0</span></small>
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6">
                <div class="metric-card">
                    <div class="metric-label">
                        <i class="fas fa-balance-scale me-2"></i>
                        Ratio d'Équité
                    </div>
                    <div class="metric-value text-info" id="equityRatio">1.00</div>
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">Standard/VIP</small>
                        <small class="text-muted">Optimal: 1.05</small>
                    </div>
                </div>
            </div>
        </div>

        <!-- Graphiques et Alertes -->
        <div class="row">
            <div class="col-lg-8">
                <div class="chart-container">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h5 class="mb-0">
                            <i class="fas fa-chart-area me-2" style="color: var(--primary-color);"></i>
                            Performance en Temps Réel
                        </h5>
                        <button class="btn btn-outline-primary btn-sm" onclick="loadLatestData()">
                            <i class="fas fa-sync-alt me-1"></i>Actualiser
                        </button>
                    </div>
                    <canvas id="performanceChart"></canvas>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="alert-panel">
                    <h5 class="mb-3">
                        <i class="fas fa-bell me-2"></i>
                        Événements Système
                    </h5>
                    <div id="alertsContainer">
                        <div style="text-align: center; color: #6b7280; padding: 20px;">
                            <i class="fas fa-clock" style="font-size: 2rem; margin-bottom: 10px;"></i>
                            <p>En attente de tests...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Résultats des Tests -->
        <div class="row">
            <div class="col-lg-4">
                <div class="metric-card">
                    <h5 class="mb-3">
                        <i class="fas fa-clipboard-check me-2"></i>
                        Test Baseline
                    </h5>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Requêtes Traitées</span>
                        <span><strong id="baselineRequests">291</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Taux de Réussite</span>
                        <span class="text-success"><strong id="baselineSuccess">100%</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Temps Réponse Moyen</span>
                        <span><strong id="baselineResponse">1.84s</strong></span>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Ratio d'Équité</span>
                        <span class="text-success"><strong id="baselineEquity">1.05</strong></span>
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
                        <span><strong id="scalaMax">1000 req</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Taux de Réussite</span>
                        <span class="text-success"><strong id="scalaSuccess">100%</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Débit Maximum</span>
                        <span><strong id="scalaDebit">7.6 req/s</strong></span>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Scalabilité</span>
                        <span class="text-success"><strong>Linéaire</strong></span>
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
                        <span><strong id="spikeRequests">553</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Taux de Réussite</span>
                        <span class="text-success"><strong id="spikeSuccess">100%</strong></span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Pic Géré</span>
                        <span><strong id="spikePeak">8.2 req/s</strong></span>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Récupération</span>
                        <span class="text-success"><strong>Auto</strong></span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let charts = {};
        let realDataMode = false;
        let dataUpdateInterval = null;

        // Métriques par défaut (basées sur vos vrais tests)
        const defaultMetrics = {
            baseline: {
                requests: 291,
                success_rate: 1.0,
                avg_response_time: 1.84,
                equity_ratio: 1.05,
                max_throughput: 5.6
            },
            scalability: {
                max_volume: 1000,
                success_rate: 1.0,
                max_throughput: 7.6
            },
            spike: {
                requests: 553,
                success_rate: 1.0,
                max_throughput: 8.2
            }
        };

        function initializeCharts() {
            const ctx = document.getElementById('performanceChart').getContext('2d');
            charts.performance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Débit (req/s)',
                            data: [],
                            borderColor: '#2563eb',
                            backgroundColor: '#2563eb20',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'Temps Réponse (s)',
                            data: [],
                            borderColor: '#10b981',
                            backgroundColor: '#10b98120',
                            borderWidth: 2,
                            fill: false,
                            tension: 0.4,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 500 },
                    scales: {
                        x: {
                            display: true,
                            title: { display: true, text: 'Temps' }
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: { display: true, text: 'Débit (req/s)' },
                            min: 0,
                            max: 10
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: { display: true, text: 'Temps Réponse (s)' },
                            grid: { drawOnChartArea: false },
                            min: 0,
                            max: 5
                        }
                    }
                }
            });
        }

        async function loadLatestData() {
            try {
                // Essayer de charger les données depuis les fichiers JSON
                const files = [
                    'logs/metrics/baseline_report_latest.json',
                    'logs/metrics/scalability_report_latest.json', 
                    'logs/metrics/spike_report_latest.json'
                ];

                let hasRealData = false;

                for (const file of files) {
                    try {
                        const response = await fetch(file);
                        if (response.ok) {
                            const data = await response.json();
                            processRealData(data);
                            hasRealData = true;
                        }
                    } catch (e) {
                        console.log(`Fichier ${file} non trouvé`);
                    }
                }

                if (hasRealData) {
                    setRealDataMode(true);
                    addEvent('info', 'Données réelles chargées depuis les fichiers de test');
                } else {
                    setRealDataMode(false);
                    addEvent('warning', 'Aucune donnée réelle trouvée - Mode simulation');
                }

            } catch (error) {
                console.error('Erreur lors du chargement des données:', error);
                setRealDataMode(false);
            }

            updateLastUpdate();
        }

        function processRealData(data) {
            // Traiter les données selon le type de test
            if (data.test_type === 'baseline') {
                updateMetric('currentThroughput', data.performance.avg_throughput.toFixed(1));
                updateMetric('avgResponseTime', data.performance.vip_avg_response_time.toFixed(2));
                updateMetric('equityRatio', data.performance.equity_ratio.toFixed(2));
                updateMetric('vipQueue', data.queues.max_vip_queue_size);
                updateMetric('stdQueue', data.queues.max_standard_queue_size);
                updateMetric('totalQueue', data.queues.max_vip_queue_size + data.queues.max_standard_queue_size);

                // Mise à jour graphique si données temporelles disponibles
                if (data.time_series && data.time_series.timestamps) {
                    updateChart(data.time_series);
                }
            } else if (data.test_type === 'spike_test') {
                updateMetric('currentThroughput', data.performance.max_throughput.toFixed(1));
                updateMetric('avgResponseTime', data.summary.avg_response_time.toFixed(2));
                updateMetric('equityRatio', data.performance.equity_ratio.toFixed(2));

                if (data.time_series) {
                    updateChart(data.time_series);
                }
            }
        }

        function updateChart(timeSeries) {
            if (!timeSeries.timestamps) return;

            // Convertir les timestamps en format lisible
            const labels = timeSeries.timestamps.slice(-50).map(ts => 
                new Date(ts * 1000).toLocaleTimeString()
            );

            charts.performance.data.labels = labels;
            charts.performance.data.datasets[0].data = timeSeries.throughput_per_second.slice(-50);

            // Calculer temps de réponse moyen par période
            const responseData = [];
            for (let i = 0; i < labels.length; i++) {
                const avgResp = (timeSeries.response_times_vip[i] + timeSeries.response_times_standard[i]) / 2;
                responseData.push(avgResp || 0);
            }
            charts.performance.data.datasets[1].data = responseData;

            charts.performance.update();
        }

        function setRealDataMode(isReal) {
            realDataMode = isReal;
            const indicator = document.getElementById('dataSourceIndicator');
            const modeText = document.getElementById('dataMode');
            const statusElement = document.getElementById('systemStatus');

            if (isReal) {
                indicator.className = 'data-source real-data';
                modeText.textContent = 'Données Réelles (Tests actifs)';
                indicator.innerHTML = '<i class="fas fa-check-circle me-2"></i><strong>Mode:</strong> <span id="dataMode">Données Réelles (Tests actifs)</span><br><small>Métriques authentiques provenant de vos tests de performance</small>';

                statusElement.innerHTML = '<span class="status-indicator status-online"></span><span>Tests en Cours</span>';
            } else {
                indicator.className = 'data-source simulated-data';
                modeText.textContent = 'Simulation (Aucun test actif)';
                indicator.innerHTML = '<i class="fas fa-info-circle me-2"></i><strong>Mode:</strong> <span id="dataMode">Simulation (Aucun test actif)</span><br><small>Lancez vos tests pour voir les vraies métriques en temps réel</small>';

                statusElement.innerHTML = '<span class="status-indicator status-idle"></span><span>Système en Attente</span>';
            }
        }

        function updateMetric(elementId, value) {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = value;
            }
        }

        function addEvent(type, message) {
            const container = document.getElementById('alertsContainer');
            const eventDiv = document.createElement('div');
            const now = new Date().toLocaleTimeString();

            eventDiv.innerHTML = `
                <div style="padding: 10px; border-left: 4px solid ${type === 'info' ? '#06b6d4' : type === 'warning' ? '#f59e0b' : '#ef4444'}; 
                     background: ${type === 'info' ? '#eff6ff' : type === 'warning' ? '#fffbeb' : '#fef2f2'}; 
                     border-radius: 6px; margin-bottom: 10px;">
                    <strong>${type.toUpperCase()}</strong> - ${message}
                    <br><small style="color: #6b7280;">${now}</small>
                </div>
            `;

            container.insertBefore(eventDiv, container.firstChild);

            // Garder seulement 10 événements
            while (container.children.length > 10) {
                container.removeChild(container.lastChild);
            }
        }

        function updateLastUpdate() {
            document.getElementById('lastUpdate').textContent = 
                'Dernière mise à jour: ' + new Date().toLocaleTimeString();
        }

        function initializeDashboard() {
            // Charger les métriques par défaut
            updateMetric('baselineRequests', defaultMetrics.baseline.requests);
            updateMetric('baselineSuccess', (defaultMetrics.baseline.success_rate * 100).toFixed(0) + '%');
            updateMetric('baselineResponse', defaultMetrics.baseline.avg_response_time + 's');
            updateMetric('baselineEquity', defaultMetrics.baseline.equity_ratio);

            updateMetric('scalaMax', defaultMetrics.scalability.max_volume + ' req');
            updateMetric('scalaSuccess', (defaultMetrics.scalability.success_rate * 100).toFixed(0) + '%');
            updateMetric('scalaDebit', defaultMetrics.scalability.max_throughput + ' req/s');

            updateMetric('spikeRequests', defaultMetrics.spike.requests);
            updateMetric('spikeSuccess', (defaultMetrics.spike.success_rate * 100).toFixed(0) + '%');
            updateMetric('spikePeak', defaultMetrics.spike.max_throughput + ' req/s');

            updateMetric('maxThroughput', defaultMetrics.spike.max_throughput);

            // Essayer de charger les vraies données
            loadLatestData();

            // Vérifier les nouvelles données toutes les 5 secondes
            dataUpdateInterval = setInterval(loadLatestData, 5000);
        }

        // Initialisation
        document.addEventListener('DOMContentLoaded', function() {
            initializeCharts();
            initializeDashboard();

            addEvent('info', 'Dashboard initialisé avec les résultats de vos tests');
            addEvent('info', 'Prêt à afficher les données en temps réel');
        });

        // Nettoyage à la fermeture
        window.addEventListener('beforeunload', function() {
            if (dataUpdateInterval) {
                clearInterval(dataUpdateInterval);
            }
        });
    </script>
</body>
</html>"""

    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html_content)


# Ajoutez cette méthode dans votre classe DashboardHandler dans start_dashboard_simple.py

def do_GET(self):
    if self.path == '/':
        self.path = '/dashboard.html'
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


def start_dashboard(port=8080):
    """Démarre le serveur dashboard."""
    print(f"Création du fichier dashboard...")
    create_dashboard_html()

    print(f"Démarrage du dashboard sur le port {port}...")
    print(f"Accédez à: http://localhost:{port}")
    print("Appuyez sur Ctrl+C pour arrêter")

    try:
        with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard arrêté")
    except Exception as e:
        print(f"Erreur: {e}")
        print(f"Le port {port} est peut-être déjà utilisé. Essayez un autre port:")
        print(f"python start_dashboard_simple.py --port 8081")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dashboard simple pour les tests")
    parser.add_argument("--port", type=int, default=8080,
                        help="Port du serveur (défaut: 8080)")
    args = parser.parse_args()

    start_dashboard(args.port)