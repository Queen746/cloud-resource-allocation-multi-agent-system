import asyncio
import logging
import time
import argparse
import uuid
import random
import json
import os
import signal
import sys
from datetime import datetime
<<<<<<< HEAD
=======

import self

>>>>>>> b68335f (Premier commit)
from tests.load_test import LoadTest
from multiprocessing import Queue
import threading
from spade.message import Message

# Importer les agents
from agents.client_manager_agent import ClientManagerAgent
from agents.resource_manager_agent import ResourceManagerAgent
from agents.load_balancer_agent import LoadBalancerAgent
from agents.monitor_agent import MonitorAgent

# Importer les modèles
from models.client import Client
from models.resource_request import ResourceRequest
from models.enums import ClientType, RequestStatus

# Importer le tableau de bord
from dashboard.app import Dashboard

# Variable globale pour le statut de simulation
simulation_status = {
    'status': 'idle',
    'requests_sent': 0,
    'requests_active': 0,
    'requests_completed': 0,
    'elapsed_time': 0,
    'total_duration': 0
}


class SimulationRunner(threading.Thread):
    def __init__(self, launcher):
        super().__init__()
        self.launcher = launcher
        self.daemon = True
        self.running = True

    def run(self):
        while self.running:
            try:
                # Vérifier s'il y a une simulation à exécuter
                if not SystemLauncher.simulation_queue.empty():
                    simulation = SystemLauncher.simulation_queue.get(block=False)
                    self.execute_simulation(simulation)

                time.sleep(0.5)
            except Exception as e:
                self.launcher.logger.error(f"Erreur dans SimulationRunner: {e}")

    def execute_simulation(self, simulation):
        """Exécute une simulation selon les paramètres fournis"""
        simulation_type = simulation.get('type')

        if simulation_type == 'constant':
            self.execute_constant_load(simulation)
        elif simulation_type == 'burst':
            self.execute_burst_load(simulation)

    def execute_constant_load(self, params):
        """Exécute une simulation de charge constante"""
        duration = params.get('duration', 300)
        request_interval = params.get('request_interval', 5)
        vip_ratio = params.get('vip_ratio', 0.2)

        self.launcher.logger.info(f"Démarrage d'une simulation de charge constante: "
                                  f"durée={duration}s, intervalle={request_interval}s, ratio VIP={vip_ratio}")

        start_time = time.time()
        request_count = 0

        while time.time() - start_time < duration:
            # Déterminer le type de client
            is_vip = random.random() < vip_ratio

            # Créer une demande
            request = self.create_request(is_vip)

            # Envoyer la demande au système
            self.launcher.add_client_request(request)
            request_count += 1

            # Mettre à jour les statistiques
            global simulation_status
            if simulation_status:
                simulation_status['requests_sent'] = request_count

            # Attendre l'intervalle spécifié
            time.sleep(request_interval)

        self.launcher.logger.info(f"Fin de la simulation de charge constante: {request_count} demandes envoyées")

    def execute_burst_load(self, params):
        """Exécute une simulation de pic de charge"""
        burst_size = params.get('burst_size', 10)
        burst_type = params.get('burst_type', 'mixed')
        include_dependencies = params.get('include_dependencies', False)

        self.launcher.logger.info(f"Démarrage d'une simulation de pic de charge: "
                                  f"taille={burst_size}, type={burst_type}, dépendances={include_dependencies}")

        requests = []

        # Créer les demandes du burst
        for i in range(burst_size):
            # Déterminer le type de client selon le paramètre burst_type
            is_vip = False
            if burst_type == 'vip':
                is_vip = True
            elif burst_type == 'mixed':
                is_vip = random.random() < 0.5

            request = self.create_request(is_vip)

            # Ajouter des dépendances si demandé
            if include_dependencies and i > 0 and random.random() < 0.3:
                # 30% de chance d'avoir une dépendance avec une demande précédente
                dependency_idx = random.randint(0, i - 1)
                request['dependencies'] = [requests[dependency_idx]['id']]

            requests.append(request)

        # Envoyer toutes les demandes rapidement
        for request in requests:
            self.launcher.add_client_request(request)
            # Petite pause pour la stabilité du système
            time.sleep(0.1)

        # Mettre à jour les statistiques
        global simulation_status
        if simulation_status:
            simulation_status['requests_sent'] = burst_size

        self.launcher.logger.info(f"Fin de la simulation de pic de charge: {burst_size} demandes envoyées")

    def create_request(self, is_vip):
        """Crée une nouvelle demande de ressources"""
        request_id = f"req-{random.randint(1000, 9999)}"

        return {
            'id': request_id,
            'client_id': f"client-{'vip' if is_vip else 'std'}-{random.randint(100, 999)}",
            'client_type': 'VIP' if is_vip else 'STANDARD',
            'cpu_requested': random.uniform(5, 20),
            'memory_requested': random.uniform(5, 20),
            'estimated_duration': random.uniform(10, 60),
            'arrival_time': time.time(),
            'priority': 100 if is_vip else 10,
            'dependencies': []
        }


class SystemLauncher:
    """
    Point d'entrée du système. Gère le démarrage et l'arrêt des agents,
    et la coordination entre eux.
    """
    simulation_queue = Queue()

    def __init__(self, host="localhost", xmpp_server="localhost", dashboard_port=8080,
                 log_level=logging.INFO, simulation_mode=True):
        """
        Initialise le lanceur du système.

        Args:
            host (str): Nom d'hôte pour les JIDs des agents
            xmpp_server (str): Serveur XMPP pour la communication
            dashboard_port (int): Port pour le tableau de bord web
            log_level (int): Niveau de journalisation
            simulation_mode (bool): Si True, génère des demandes simulées
        """
        self.host = host
        self.xmpp_server = xmpp_server
        self.dashboard_port = dashboard_port
        self.simulation_mode = simulation_mode

        # Configurer la journalisation
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("cloud_mas.log")
            ]
        )
        self.logger = logging.getLogger("SystemLauncher")

        # JIDs des agents
        # Configuration des JIDs pour utiliser le serveur Openfire
        self.agent_jids = {
            "client_manager": "client_manager@localhost",
            "resource_manager": "resource_manager@localhost",
            "load_balancer": "load_balancer@localhost",
            "monitor": "monitor@localhost"
        }

        # Agents (seront initialisés au démarrage)
        self.agents = {}

        # Tableau de bord
        self.dashboard = Dashboard(host='0.0.0.0', port=dashboard_port)

        # Liste des simulations en cours
        self.simulations = []

        # Initialiser le runner de simulation
        self.simulation_runner = SimulationRunner(self)
        self.simulation_runner.start()

        # Gérer l'arrêt propre
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def add_client_request(self, request):
        """Ajoute une demande client au système"""
        # Convertir en format de message pour l'agent ClientManager
        message = Message(
            to=self.agent_jids["client_manager"],
            body=json.dumps(request),
            metadata={"performative": "request"}
        )

        # Envoyer le message
        self.logger.info(f"Envoi d'une demande client: {request['id']} ({request['client_type']})")
        self.agents["client_manager"].send(message)

    def handle_signal(self, sig, frame):
        """
        Gère les signaux d'interruption (Ctrl+C) pour un arrêt propre.
        """
        self.logger.info("Signal d'arrêt reçu. Arrêt en cours...")
        self.stop()
        sys.exit(0)

    async def start_agents(self):
        """
        Démarre tous les agents du système en utilisant le mode auto-register.
        """
        self.logger.info("Démarrage des agents avec auto-register...")

        try:
            # Agent de monitoring
            self.logger.info("Initialisation de MonitorAgent...")
            self.agents["monitor"] = MonitorAgent(
                self.agent_jids["monitor"],
                "password",
                dashboard_url=f"http://localhost:{self.dashboard_port}"  # Enlever /update
            )
            await self.agents["monitor"].start(auto_register=True)
            self.logger.info("MonitorAgent démarré")

            await asyncio.sleep(2)

            # Agent d'équilibrage de charge
            self.logger.info("Initialisation de LoadBalancerAgent...")
            self.agents["load_balancer"] = LoadBalancerAgent(
                self.agent_jids["load_balancer"],
                "password",
                self.agent_jids["monitor"]
            )
            await self.agents["load_balancer"].start()
            self.logger.info("LoadBalancerAgent démarré")

            await asyncio.sleep(2)

            # Gestionnaire de ressources
            self.logger.info("Initialisation de ResourceManagerAgent...")
            self.agents["resource_manager"] = ResourceManagerAgent(
                self.agent_jids["resource_manager"],
                "password",
                self.agent_jids["load_balancer"],
                self.agent_jids["monitor"]
            )
            await self.agents["resource_manager"].start()
            self.logger.info("ResourceManagerAgent démarré")

            await asyncio.sleep(2)

            # Gestionnaire de clients
            self.logger.info("Initialisation de ClientManagerAgent...")
            self.agents["client_manager"] = ClientManagerAgent(
                self.agent_jids["client_manager"],
                "password",
                self.agent_jids["resource_manager"],
                self.agent_jids["monitor"]
            )
            await self.agents["client_manager"].start()
            self.logger.info("ClientManagerAgent démarré")

            self.logger.info("Tous les agents sont démarrés et opérationnels")
            return True

        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage des agents: {e}", exc_info=True)
            await self.stop_agents()
            return False

    async def stop_agents(self):
        """
        Arrête tous les agents du système.
        """
        self.logger.info("Arrêt des agents...")

        for agent_name, agent in self.agents.items():
            try:
                await agent.stop()
                self.logger.info(f"{agent_name} arrêté")
            except Exception as e:
                self.logger.error(f"Erreur lors de l'arrêt de {agent_name}: {e}")

    def start_dashboard(self):
        """
        Démarre le tableau de bord web.
        """
        self.logger.info(f"Démarrage du tableau de bord sur le port {self.dashboard_port}...")
        self.dashboard.start()
        return True

    def stop_dashboard(self):
        """
        Arrête le tableau de bord web.
        """
        self.logger.info("Arrêt du tableau de bord...")
        self.dashboard.stop()

    # Dans system_launcher.py
    async def simulate_clients(self, duration=600, request_interval=5):
        """
        Simule des clients qui envoient des demandes au système.

        Args:
            duration (int): Durée de la simulation en secondes
            request_interval (int): Intervalle entre les demandes en secondes
        """
        if not self.simulation_mode:
            return

        self.logger.info(f"Démarrage de la simulation clients pour {duration}s")

        # Créer des clients simulés
        from models.client import Client
        from models.enums import ClientType

        clients = {
            "vip": [
                Client(client_id=f"vip-{i}", client_type=ClientType.VIP)
                for i in range(1, 6)  # 5 clients VIP
            ],
            "standard": [
                Client(client_id=f"std-{i}", client_type=ClientType.STANDARD)
                for i in range(1, 16)  # 15 clients standard
            ]
        }

        start_time = time.time()
        request_counter = 0

        # Simuler des dépendances
        dependencies = {}  # id -> [liste d'ids dont il dépend]

        try:
            while time.time() - start_time < duration:
                # Sélectionner un client aléatoire
                client_type = random.choice(["vip", "standard"] if random.random() < 0.3 else ["standard"])
                client = random.choice(clients[client_type])

                # Générer une demande
                request_id = f"req-{request_counter}"
                request_counter += 1

                # CPU et mémoire aléatoires
                cpu_required = random.uniform(1.0, 5.0)
                memory_required = random.uniform(1.0, 8.0)

                # Durée d'exécution estimée
                estimated_duration = random.uniform(20, 120)  # 20s à 2min

                # Gérer les dépendances
                request_dependencies = set()

                # 30% de chance d'avoir des dépendances
                if random.random() < 0.3 and dependencies:
                    # Choisir entre 1 et 3 demandes dont dépendre
                    num_deps = min(random.randint(1, 3), len(dependencies))
                    dep_ids = random.sample(list(dependencies.keys()), num_deps)
                    request_dependencies = set(dep_ids)

                # Enregistrer cette demande pour les futures dépendances
                # (sauf si la probabilité indique qu'elle ne devrait pas être une dépendance)
                if random.random() < 0.7:
                    dependencies[request_id] = request_dependencies

                # Informations de log
                self.logger.info(f"Simulation: Envoi de la demande {request_id} du client {client.id} "
                                 f"(CPU: {cpu_required:.1f}, Mémoire: {memory_required:.1f}, "
                                 f"Durée: {estimated_duration:.1f}s, "
                                 f"Dépendances: {request_dependencies})")

                # Envoyer la demande au ClientManagerAgent
                await self.agents["client_manager"].process_simulation_request({
                    "id": request_id,
                    "client": client.to_dict(),  # Utiliser to_dict() pour la sérialisation
                    "cpu_required": cpu_required,
                    "memory_required": memory_required,
                    "estimated_duration": estimated_duration,
                    "dependencies": list(request_dependencies)
                })

                # Pour simuler des pics de charge
                if random.random() < 0.1:  # 10% de chance d'avoir un pic
                    burst_size = random.randint(3, 8)
                    self.logger.info(f"Simulation: Pic de charge avec {burst_size} demandes simultanées")

                    # Envoyer plusieurs demandes rapprochées
                    for i in range(burst_size):
                        # Générer une demande similaire mais différente
                        burst_request_id = f"{request_id}-burst-{i}"

                        # Envoyer directement cette demande
                        await self.agents["client_manager"].process_simulation_request({
                            "id": burst_request_id,
                            "client": client.to_dict(),  # Utiliser to_dict() pour la sérialisation
                            "cpu_required": random.uniform(0.8, 1.2) * cpu_required,
                            "memory_required": random.uniform(0.8, 1.2) * memory_required,
                            "estimated_duration": random.uniform(0.8, 1.2) * estimated_duration,
                            "dependencies": []  # Pas de dépendances pour simplifier
                        })

                        # Court délai pour éviter une saturation totale
                        await asyncio.sleep(0.2)

                # Attendre avant la prochaine demande
                await asyncio.sleep(request_interval * random.uniform(0.5, 1.5))

        except Exception as e:
            self.logger.error(f"Erreur dans la simulation clients: {e}", exc_info=True)

        self.logger.info("Fin de la simulation clients")

    async def start(self):
        """
        Démarre le système complet.
        """
        self.logger.info("Démarrage du système...")

        # Démarrer le tableau de bord
        if not self.start_dashboard():
            self.logger.error("Échec du démarrage du tableau de bord")
            return False

        # Démarrer les agents
        if not await self.start_agents():
            self.logger.error("Échec du démarrage des agents")
            self.stop_dashboard()
            return False

        self.logger.info("Système démarré avec succès")

        # En mode simulation, démarrer la génération de demandes
        if self.simulation_mode:
            self.simulations.append(
                asyncio.create_task(self.simulate_clients())
            )

        return True

    def stop(self):
        """
        Arrête le système complet.
        """
        self.logger.info("Arrêt du système...")

        # Arrêter les simulations
        for sim in self.simulations:
            sim.cancel()

        # Arrêter les agents (sans utiliser asyncio.run)
        if hasattr(self, 'agents'):
            for agent_name, agent in self.agents.items():
                try:
                    # Utiliser une tâche pour arrêter l'agent sans attendre
                    asyncio.create_task(agent.stop())
                    self.logger.info(f"{agent_name} arrêté")
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'arrêt de {agent_name}: {e}")

        # Arrêter le tableau de bord
        self.stop_dashboard()

        self.logger.info("Système arrêté")

    async def run(self, duration=None):
        """
        Exécute le système pour une durée déterminée ou indéfiniment.

        Args:
            duration (int, optional): Durée d'exécution en secondes. Si None, exécute indéfiniment.

        Returns:
            bool: True si l'exécution s'est terminée normalement, False sinon
        """
        if not await self.start():
            return False

        try:
            if duration is not None:
                self.logger.info(f"Exécution du système pour {duration}s")
                await asyncio.sleep(duration)
                self.logger.info(f"Durée de {duration}s écoulée, arrêt du système")
            else:
                self.logger.info("Exécution du système en mode continu")
                # Boucle infinie pour maintenir le programme en vie
                while True:
                    await asyncio.sleep(3600)  # Attendre 1 heure avant de vérifier à nouveau

        except asyncio.CancelledError:
            self.logger.info("Exécution annulée")

        except Exception as e:
            self.logger.error(f"Erreur pendant l'exécution: {e}")
            return False

        finally:
            self.stop()

        return True

    async def run_load_test(self, duration=300, burst_interval=30, burst_size=10):
        """Exécute un test de charge sur le système"""
        self.logger.info(f"Démarrage d'un test de charge pour {duration} secondes")

        # Créer et configurer le testeur
        load_tester = LoadTest(self.agents["client_manager"])

        # Exécuter le test
        results = await load_tester.run_test(
            duration=duration,
            burst_interval=burst_interval,
            burst_size=burst_size
        )

        # Afficher les résultats
        self.logger.info(f"Résultats du test de charge:")
        self.logger.info(f"Demandes envoyées: {results['requests_sent']}")
        self.logger.info(f"Demandes complétées: {results['requests_completed']}")
        self.logger.info(f"Temps d'attente moyen VIP: {results['vip_avg_wait_time']:.2f}s")
        self.logger.info(f"Temps d'attente moyen standard: {results['standard_avg_wait_time']:.2f}s")

        return results

<<<<<<< HEAD
=======
    self.completed_requests = set()  # Demandes terminées
    self.failed_requests = {}  # {request_id: reason}
    self.active_requests = set()  # Demandes en cours de traitement

    # Ajouter à system_launcher.py

    def submit_request(self, client, request_id, cpu_required, memory_required, estimated_duration, dependencies=None):
        """
        Soumet une nouvelle demande au système.
        Utilisé par les tests de performance.

        Args:
            client (Client): Le client qui soumet la demande
            request_id (str): Identifiant unique de la demande
            cpu_required (float): Quantité de CPU requise
            memory_required (float): Quantité de mémoire requise
            estimated_duration (float): Durée estimée d'exécution (en secondes)
            dependencies (set, optional): Ensemble des IDs de demandes dont dépend cette demande

        Returns:
            bool: True si la demande a été acceptée, False sinon
        """
        self.logger.info(f"Simulation: Envoi de la demande {request_id} du client {client.id} "
                         f"(CPU: {cpu_required}, Mémoire: {memory_required}, Durée: {estimated_duration}s, "
                         f"Dépendances: {dependencies})")

        # Ajouter aux demandes actives (pour le suivi des tests)
        self.active_requests.add(request_id)

        # Simuler l'envoi de la demande au ClientManagerAgent
        try:
            # Si vous utilisez déjà la méthode ClientManagerAgent.add_request, appelez-la directement
            self.client_manager.add_request(client, request_id, cpu_required, memory_required,
                                            estimated_duration, dependencies)
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la soumission de la demande {request_id}: {e}")
            self.failed_requests[request_id] = f"error_during_submission: {str(e)}"
            return False

    def get_completed_requests(self):
        """
        Retourne l'ensemble des demandes complétées depuis le dernier appel.
        """
        # Copier l'ensemble actuel pour le retourner
        completed = self.completed_requests.copy()
        # Vider l'ensemble pour le prochain appel
        self.completed_requests.clear()
        return completed

    def get_failed_requests(self):
        """
        Retourne l'ensemble des demandes échouées.
        """
        return set(self.failed_requests.keys())

    def get_failure_reason(self, request_id):
        """
        Retourne la raison de l'échec d'une demande.
        """
        return self.failed_requests.get(request_id, "unknown_failure")

    def mark_request_completed(self, request_id):
        """
        Marque une demande comme complétée.
        """
        if request_id in self.active_requests:
            self.active_requests.remove(request_id)
            self.completed_requests.add(request_id)

    def mark_request_failed(self, request_id, reason):
        """
        Marque une demande comme échouée.
        """
        if request_id in self.active_requests:
            self.active_requests.remove(request_id)
            self.failed_requests[request_id] = reason

>>>>>>> b68335f (Premier commit)

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    """
    parser = argparse.ArgumentParser(description="Système multi-agents pour la gestion des demandes cloud")

    # Mode
    parser.add_argument("--no-sim", action="store_true", help="Désactiver le mode simulation")
    parser.add_argument("--duration", type=int, default=None, help="Durée d'exécution en secondes")

    # Réseau
    parser.add_argument("--host", type=str, default="localhost", help="Nom d'hôte pour les JIDs")
    parser.add_argument("--xmpp-server", type=str, default="localhost", help="Serveur XMPP")
    parser.add_argument("--port", type=int, default=8080, help="Port pour le tableau de bord web")

    # Journalisation
    parser.add_argument("--debug", action="store_true", help="Activer le mode debug")

    # Test de charge
    parser.add_argument("--test", action="store_true", help="Exécuter un test de charge")
    parser.add_argument("--burst-interval", type=int, default=30, help="Intervalle entre pics")
    parser.add_argument("--burst-size", type=int, default=10, help="Taille des pics")

    return parser.parse_args()


async def main():
    """
    Fonction principale.
    """
    args = parse_arguments()

    # Configurer le niveau de journalisation
    log_level = logging.DEBUG if args.debug else logging.INFO

    # Créer et exécuter le lanceur
    launcher = SystemLauncher(
        host=args.host,
        xmpp_server=args.xmpp_server,
        dashboard_port=args.port,
        log_level=log_level,
        simulation_mode=not args.no_sim
    )

    # Exécuter le système
    if args.test:
        await launcher.start()
        await launcher.run_load_test(
            duration=args.duration or 300,
            burst_interval=args.burst_interval,
            burst_size=args.burst_size
        )
        await launcher.stop()
        return True
    else:
        return await launcher.run(duration=args.duration)


if __name__ == "__main__":
    # Exécuter la fonction principale
    success = asyncio.run(main())

    # Code de sortie
<<<<<<< HEAD
    sys.exit(0 if success else 1)
=======
    sys.exit(0 if success else 1)
>>>>>>> b68335f (Premier commit)
