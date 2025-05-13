import json
import threading
import queue
import uuid
import time
import random

from flask import Flask, render_template, jsonify, request

# Pour simuler les données AWS si le module n'est pas disponible
try:
    from aws.simulator import AWSResourceSimulator

    aws_simulator = AWSResourceSimulator()
except ImportError:
    # Simulateur AWS de secours
    class SimpleAWSSimulator:
        def get_status_json(self):
            return {
                "instances": {
                    "i-12345678": {"name": "agent-monitor", "state": "running", "type": "t3.medium"},
                    "i-87654321": {"name": "agent-resource-manager", "state": "running", "type": "t3.large"}
                },
                "auto_scaling_groups": {
                    "asg-12345678": {"name": "client-agents", "state": "active", "instances": 3, "desired_capacity": 3}
                },
                "cost": 1.25,
                "uptime": 3600
            }

        def create_instance(self, instance_type, name):
            return {"id": f"i-{uuid.uuid4().hex[:8]}", "type": instance_type, "name": name}

        def create_load_balancer(self, name, instances):
            return {"id": f"lb-{uuid.uuid4().hex[:8]}", "name": name}

        def create_auto_scaling_group(self, name, instance_type, min_size, max_size, desired_capacity):
            return {"id": f"asg-{uuid.uuid4().hex[:8]}", "name": name}

        def simulate_load(self, duration, interval):
            pass


    aws_simulator = SimpleAWSSimulator()

# Données globales
metrics_data = {
    "server_metrics": {},
    "queue_sizes": {"vip": 0, "standard": 0},
    "normalized": {"cpu_percentage": 0, "memory_percentage": 0}
}
queue_history_data = {
    "vip": [],
    "standard": []
}
resource_history_data = {}
events_data = []
alerts_data = []
simulation_queue = queue.Queue()


class Dashboard:
    def __init__(self, host='0.0.0.0', port=8080):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.server = None
        self.running = False

        # Configuration des routes
        self._setup_routes()

        # Initialiser la simulation AWS
        self.initialize_aws_simulation()

    def _setup_routes(self):
        """
        Configure les routes de l'application Flask.
        """

        # Route principale
        @self.app.route('/')
        def index_page():
            return render_template('index.html')

        # Route pour la page de simulation
        @self.app.route('/simulation')
        def simulation_page():
            return render_template('simulation.html')

        # API - Métriques
        @self.app.route('/api/metrics', methods=['GET', 'POST'])
        def metrics_endpoint():
            global metrics_data
            if request.method == 'POST':
                try:
                    data = request.get_json()
                    print(f"Données reçues: {data}")
                    metrics_data = data
                    return jsonify({"status": "success"})
                except Exception as e:
                    print(f"Erreur: {e}")
                    return jsonify({"status": "error", "message": str(e)})
            return jsonify(metrics_data)

        # API - Historique des files d'attente
        @self.app.route('/api/queue_history', methods=['GET', 'POST'])
        def queue_history_endpoint():
            global queue_history_data
            if request.method == 'POST':
                try:
                    data = request.get_json()
                    queue_history_data = {
                        "vip": data.get("vip", []),
                        "standard": data.get("standard", [])
                    }
                    return jsonify({"status": "success"})
                except Exception as e:
                    return jsonify({"status": "error", "message": str(e)})
            return jsonify(queue_history_data)

        # API - Historique des ressources
        @self.app.route('/api/resource_history', methods=['GET', 'POST'])
        def resource_history_endpoint():
            global resource_history_data
            if request.method == 'POST':
                data = request.get_json()
                if data:
                    resource_history_data = data
                return jsonify({"status": "success"})
            return jsonify(resource_history_data)

        # API - Événements
        @self.app.route('/api/events', methods=['GET', 'POST'])
        def events_endpoint():
            global events_data
            if request.method == 'POST':
                data = request.get_json()
                if data and "events" in data:
                    events_data = data["events"]
                return jsonify({"status": "success"})
            return jsonify(events_data)

        # API - Alertes
        @self.app.route('/api/alerts', methods=['GET', 'POST'])
        def alerts_endpoint():
            global alerts_data
            if request.method == 'POST':
                data = request.get_json()
                if data and "alerts" in data:
                    alerts_data = data["alerts"]
                return jsonify({"status": "success"})
            return jsonify(alerts_data)

        # Variable locale pour AWS data
        aws_data = {
            "instances": {
                "i-12345678": {"name": "agent-monitor", "state": "running", "type": "t3.medium"},
                "i-87654321": {"name": "agent-resource-manager", "state": "running", "type": "t3.large"},
                "i-11223344": {"name": "agent-load-balancer", "state": "running", "type": "t3.large"},
                "i-44332211": {"name": "agent-client-manager", "state": "running", "type": "t3.medium"}
            },
            "auto_scaling_groups": {
                "asg-12345678": {
                    "name": "client-agents",
                    "state": "active",
                    "instances": ["i-asg-1", "i-asg-2", "i-asg-3"],
                    "desired_capacity": 3
                }
            },
            "uptime": int(time.time()) - int(time.time() - 3600),
            "total_cost": round(random.uniform(1.0, 5.0), 2)
        }

        # API - Simulation AWS
        @self.app.route('/api/aws_simulation', methods=['GET'])
        def aws_simulation_endpoint():
            try:
                return jsonify(aws_simulator.get_status_json())
            except:
                return jsonify(aws_data)

        # Variable locale pour le statut de simulation
        simulation_status_data = {
            'status': 'idle',
            'requests_sent': 0,
            'requests_active': 0,
            'requests_completed': 0,
            'elapsed_time': 0,
            'total_duration': 0,
            'start_time': 0
        }

        # API - Statut de la simulation
        @self.app.route('/api/simulation/status', methods=['GET'])
        def simulation_status_endpoint():
            # Mettre à jour le temps écoulé si la simulation est en cours
            if simulation_status_data['status'] == 'running':
                elapsed = time.time() - simulation_status_data['start_time']
                simulation_status_data['elapsed_time'] = elapsed

                # Simuler l'avancement
                simulation_status_data['requests_sent'] = min(100, int(elapsed * 2))
                simulation_status_data['requests_completed'] = min(80, int(elapsed * 1.5))
                simulation_status_data['requests_active'] = simulation_status_data['requests_sent'] - \
                                                            simulation_status_data['requests_completed']

                # Vérifier si la simulation est terminée
                if elapsed >= simulation_status_data['total_duration']:
                    simulation_status_data['status'] = 'completed'
                    simulation_status_data['elapsed_time'] = simulation_status_data['total_duration']
                    simulation_status_data['requests_active'] = 0
                    simulation_status_data['requests_completed'] = simulation_status_data['requests_sent']

            return jsonify(simulation_status_data)

        # API - Démarrer une simulation
        @self.app.route('/api/simulation/start', methods=['POST'])
        def start_simulation_endpoint():
            try:
                data = request.get_json()
                simulation_type = data.get('type')

                # Initialiser l'état de la simulation
                simulation_status_data['status'] = 'running'
                simulation_status_data['type'] = simulation_type
                simulation_status_data['start_time'] = time.time()
                simulation_status_data['requests_sent'] = 0
                simulation_status_data['requests_active'] = 0
                simulation_status_data['requests_completed'] = 0

                if simulation_type == 'constant':
                    duration = int(data.get('duration', 300))
                    request_interval = float(data.get('requestInterval', 5))
                    vip_ratio = float(data.get('vipRatio', 0.2))

                    simulation_status_data['total_duration'] = duration

                    # Démarrer la simulation de démonstration
                    self.start_demo_simulation(duration)

                    return jsonify({
                        'status': 'started',
                        'simulation_id': str(uuid.uuid4())
                    })

                elif simulation_type == 'burst':
                    burst_size = int(data.get('burstSize', 10))
                    burst_type = data.get('burstType', 'mixed')
                    include_dependencies = data.get('includeDependencies', False)

                    simulation_status_data['total_duration'] = 60

                    # Démarrer la simulation de démonstration
                    self.start_demo_simulation(60)

                    return jsonify({
                        'status': 'started',
                        'simulation_id': str(uuid.uuid4())
                    })

                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Type de simulation non reconnu'
                    })

            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                })

    def initialize_aws_simulation(self):
        """Initialise la simulation AWS avec des ressources de base"""

        def start_simulation():
            try:
                # Créer des instances
                instance1 = aws_simulator.create_instance(instance_type="t3.medium", name="agent-monitor")
                instance2 = aws_simulator.create_instance(instance_type="t3.large", name="agent-resource-manager")
                instance3 = aws_simulator.create_instance(instance_type="t3.large", name="agent-load-balancer")
                instance4 = aws_simulator.create_instance(instance_type="t3.medium", name="agent-client-manager")

                # Créer un load balancer
                lb = aws_simulator.create_load_balancer("system-lb", [instance1, instance2, instance3, instance4])

                # Créer un Auto Scaling Group pour les agents clients
                asg = aws_simulator.create_auto_scaling_group(
                    name="client-agents",
                    instance_type="t3.small",
                    min_size=2,
                    max_size=5,
                    desired_capacity=3
                )

                # Lancer la simulation de charge (1h)
                aws_simulator.simulate_load(3600, 30)
            except Exception as e:
                print(f"Erreur lors de l'initialisation AWS: {e}")

        # Lancer dans un thread séparé
        t = threading.Thread(target=start_simulation)
        t.daemon = True
        t.start()

    def start_demo_simulation(self, duration):
        """Démarre une simulation de démonstration pour animer le tableau de bord"""

        def run_simulation():
            global metrics_data, events_data
            start_time = time.time()
            total_requests = int(duration / 2)  # Environ 1 requête toutes les 2 secondes

            for i in range(total_requests):
                if i % 10 == 0 and metrics_data:
                    # Mise à jour des métriques périodiquement
                    server_id = f"server-{(i % 5) + 1}"
                    if server_id in metrics_data.get("server_metrics", {}):
                        # Ajouter de la charge CPU et mémoire
                        cpu_inc = (5 + (i % 10)) * 0.5  # Variation entre 2.5 et 7.5
                        mem_inc = (3 + (i % 8)) * 0.6  # Variation entre 1.8 et 6.0

                        metrics_data["server_metrics"][server_id]["cpu_used"] += cpu_inc
                        metrics_data["server_metrics"][server_id]["memory_used"] += mem_inc

                # Attendre un peu
                time.sleep(0.1)

                # Vérifier si le temps est écoulé
                if time.time() - start_time >= duration:
                    break

        # Lancer dans un thread séparé
        t = threading.Thread(target=run_simulation)
        t.daemon = True
        t.start()

    def start(self):
        """
        Démarre le serveur web dans un thread séparé.
        """
        if self.running:
            return False

        def run_server():
            self.app.run(host=self.host, port=self.port)

        self.server = threading.Thread(target=run_server)
        self.server.daemon = True
        self.server.start()

        self.running = True
        print(f"Dashboard started on http://{self.host}:{self.port}/")
        return True

    def stop(self):
        """
        Arrête le serveur web.
        """
        if not self.running:
            return False

        self.running = False
        print("Dashboard stopped")
        return True