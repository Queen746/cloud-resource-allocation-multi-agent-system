# dashboard/app.py - Version mise à jour pour intégrer les nouvelles interfaces

from flask import Flask, render_template, jsonify, request, send_from_directory
import json
import time
import threading
import logging
from datetime import datetime


class Dashboard:
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.app = Flask(__name__,
                         template_folder='templates',
                         static_folder='static')

        # Données simulées pour les tests
        self.system_data = {
            'agents': {
                'client_manager': {'status': 'online', 'last_seen': time.time()},
                'resource_manager': {'status': 'online', 'last_seen': time.time()},
                'load_balancer': {'status': 'online', 'last_seen': time.time()},
                'monitor': {'status': 'online', 'last_seen': time.time()}
            },
            'queues': {
                'vip_size': 3,
                'standard_size': 8,
                'vip_wait_time': 0.8,
                'standard_wait_time': 4.2
            },
            'resources': {
                'cpu_available': 85.2,
                'memory_available': 76.8,
                'throughput': 127,
                'response_time': 2.4,
                'success_rate': 98.7
            },
            'logs': []
        }

        self.setup_routes()
        self.logger = logging.getLogger("Dashboard")

    def setup_routes(self):
        """Configure les routes Flask"""

        @self.app.route('/')
        def index():
            """Page d'accueil - redirige vers le dashboard admin"""
            return render_template('admin_dashboard.html')

        @self.app.route('/admin')
        def admin_dashboard():
            """Dashboard administrateur"""
            return render_template('admin_dashboard.html')

        @self.app.route('/client')
        def client_interface():
            """Interface client"""
            return render_template('client_interface.html')

        # API pour les données en temps réel
        @self.app.route('/api/system_status')
        def get_system_status():
            """Retourne l'état du système"""
            return jsonify(self.system_data)

        @self.app.route('/api/agents_status')
        def get_agents_status():
            """Retourne l'état des agents"""
            return jsonify(self.system_data['agents'])

        @self.app.route('/api/queue_metrics')
        def get_queue_metrics():
            """Retourne les métriques des files d'attente"""
            return jsonify(self.system_data['queues'])

        @self.app.route('/api/resource_metrics')
        def get_resource_metrics():
            """Retourne les métriques des ressources"""
            return jsonify(self.system_data['resources'])

        @self.app.route('/api/logs')
        def get_logs():
            """Retourne les logs système"""
            return jsonify(self.system_data['logs'][-50:])  # Derniers 50 logs

        # API pour soumettre des demandes (simulation)
        @self.app.route('/api/submit_request', methods=['POST'])
        def submit_request():
            """Traite une nouvelle demande client"""
            data = request.get_json()

            # Simuler la soumission
            request_id = f"REQ-{int(time.time())}"

            # Ajouter aux logs
            self.add_log('INFO', f'Nouvelle demande reçue: {request_id}')

            # Simuler l'ajout aux files d'attente
            if data.get('priority') == 'high':
                self.system_data['queues']['vip_size'] += 1
            else:
                self.system_data['queues']['standard_size'] += 1

            return jsonify({
                'success': True,
                'request_id': request_id,
                'message': 'Demande soumise avec succès'
            })

        # API pour les simulations du dashboard admin
        @self.app.route('/api/start_simulation', methods=['POST'])
        def start_simulation():
            """Démarre une simulation"""
            self.add_log('INFO', 'Simulation démarrée')
            return jsonify({'success': True})

        @self.app.route('/api/stop_simulation', methods=['POST'])
        def stop_simulation():
            """Arrête une simulation"""
            self.add_log('INFO', 'Simulation arrêtée')
            return jsonify({'success': True})

        @self.app.route('/api/reset_metrics', methods=['POST'])
        def reset_metrics():
            """Remet à zéro les métriques"""
            self.system_data['queues']['vip_size'] = 0
            self.system_data['queues']['standard_size'] = 0
            self.add_log('INFO', 'Métriques réinitialisées')
            return jsonify({'success': True})

    def add_log(self, level, message):
        """Ajoute un log au système"""
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'level': level,
            'message': message
        }
        self.system_data['logs'].append(log_entry)

        # Limiter à 100 logs
        if len(self.system_data['logs']) > 100:
            self.system_data['logs'] = self.system_data['logs'][-100:]

    def update_queue_sizes(self, vip_size, standard_size):
        """Met à jour les tailles des files d'attente"""
        self.system_data['queues']['vip_size'] = vip_size
        self.system_data['queues']['standard_size'] = standard_size

    def update_resources(self, cpu_usage, memory_usage):
        """Met à jour les ressources système"""
        self.system_data['resources']['cpu_available'] = 100 - cpu_usage
        self.system_data['resources']['memory_available'] = 100 - memory_usage

    def start(self):
        """Démarre le serveur Flask"""
        try:
            self.logger.info(f"Démarrage du dashboard sur http://{self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port, debug=False, threaded=True)
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage du dashboard: {e}")

    def stop(self):
        """Arrête le serveur Flask"""
        self.logger.info("Arrêt du dashboard")
        # Flask n'a pas de méthode stop() simple, on peut forcer l'arrêt
        import os
        import signal
        os.kill(os.getpid(), signal.SIGINT)


# Fonction utilitaire pour tester le dashboard en standalone
if __name__ == "__main__":
    dashboard = Dashboard(host='0.0.0.0', port=8080)
    dashboard.start()