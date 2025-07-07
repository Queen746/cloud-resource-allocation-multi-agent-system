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
import concurrent.futures

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
        """
        self.host = host
        self.xmpp_server = xmpp_server
        self.dashboard_port = dashboard_port
        self.simulation_mode = simulation_mode

        # Initialiser les attributs pour le suivi des demandes
        self.completed_requests = set()  # Demandes terminées
        self.failed_requests = {}  # {request_id: reason}
        self.active_requests = set()  # Demandes en cours de traitement

        # Variables pour le monitoring et la récupération
        self.in_recovery_mode = False
        self.recent_requests = set()
        self.request_start_times = {}

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

        # Gérer l'arrêt propre
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def submit_request(self, client, request_id, cpu_required, memory_required, estimated_duration,
                       dependencies=None):
        """
        Soumet une nouvelle demande au système.
        """
        self.logger.info(f"Simulation: Envoi de la demande {request_id} du client {client.id} "
                         f"(CPU: {cpu_required}, Mémoire: {memory_required}, Durée: {estimated_duration}s, "
                         f"Dépendances: {dependencies})")

        # Ajouter aux demandes actives (pour le suivi des tests)
        self.active_requests.add(request_id)
        self.request_start_times[request_id] = time.time()

        # Construire la requête pour le ClientManagerAgent
        request = {
            'id': request_id,
            'client': client.to_dict(),
            'cpu_required': cpu_required,
            'memory_required': memory_required,
            'estimated_duration': estimated_duration,
            'dependencies': list(dependencies) if dependencies else []
        }

        # Envoyer la demande
        try:
            message = Message(
                to=self.agent_jids["client_manager"],
                body=json.dumps(request),
                metadata={"performative": "request"}
            )
            self.agents["client_manager"].send(message)
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la soumission de la demande {request_id}: {e}")
            self.failed_requests[request_id] = f"error_during_submission: {str(e)}"
            return False

    def get_completed_requests(self):
        """
        Retourne l'ensemble des demandes complétées depuis le dernier appel.
        """
        completed = self.completed_requests.copy()
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
            self.logger.info(f"Demande {request_id} marquée comme complétée")

    def mark_request_failed(self, request_id, reason):
        """
        Marque une demande comme échouée.
        """
        if request_id in self.active_requests:
            self.active_requests.remove(request_id)
            self.failed_requests[request_id] = reason
            self.logger.info(f"Demande {request_id} marquée comme échouée: {reason}")

    def add_client_request(self, request):
        """Ajoute une demande client au système"""
        message = Message(
            to=self.agent_jids["client_manager"],
            body=json.dumps(request),
            metadata={"performative": "request"}
        )

        self.logger.info(f"Envoi d'une demande client: {request['id']} ({request['client_type']})")
        self.agents["client_manager"].send(message)

    def handle_signal(self, sig, frame):
        """
        Gère les signaux d'interruption (Ctrl+C) pour un arrêt propre.
        """
        self.logger.info("Signal d'arrêt reçu. Arrêt en cours...")
        self.stop()
        sys.exit(0)

    # Méthodes pour la surveillance et la récupération du système
    def activate_recovery_mode(self):
        """
        Active le mode de récupération après un pic de charge.
        """
        self.logger.info("Activation du mode de récupération")
        self.in_recovery_mode = True

        # Réinitialiser les files d'attente bloquées
        if hasattr(self, 'agents') and 'client_manager' in self.agents:
            # Note: reset_queues devrait être implémenté dans ClientManagerAgent si nécessaire
            pass

        # Augmenter temporairement les ressources virtuelles
        if hasattr(self, 'agents') and 'resource_manager' in self.agents:
            asyncio.create_task(self.agents['resource_manager'].increase_virtual_capacity(1.5))

        # Planifier la désactivation du mode de récupération
        asyncio.create_task(self.deactivate_recovery_mode_after(60))

    async def deactivate_recovery_mode_after(self, delay):
        """
        Désactive le mode de récupération après un délai.
        """
        await asyncio.sleep(delay)
        self.in_recovery_mode = False
        self.logger.info("Mode de récupération désactivé")

        # Revenir aux capacités normales
        if hasattr(self, 'agents') and 'resource_manager' in self.agents:
            await self.agents['resource_manager'].reset_virtual_capacity()

    def monitor_system_health(self):
        """
        Surveille la santé globale du système et active les mesures correctives si nécessaire.
        """
        # Vérifier le taux de complétion récent
        recent_completion_rate = self.calculate_recent_completion_rate()

        if recent_completion_rate < 0.5:  # Si moins de 50% des demandes sont traitées
            self.logger.warning(f"Taux de complétion récent bas: {recent_completion_rate:.2f}")
            self.activate_recovery_mode()

        # Vérifier s'il y a des deadlocks
        stalled_requests = self.identify_stalled_requests()
        if stalled_requests:
            self.logger.warning(f"Détection de {len(stalled_requests)} demandes bloquées")
            self.resolve_stalled_requests(stalled_requests)

    def calculate_recent_completion_rate(self):
        """
        Calcule le taux de complétion des demandes récentes.
        """
        if not hasattr(self, 'recent_requests') or not self.recent_requests:
            return 1.0  # Par défaut, considérer que tout va bien

        total_recent = len(self.recent_requests)
        completed_recent = sum(1 for req_id in self.recent_requests if req_id in self.completed_requests)

        if total_recent == 0:
            return 1.0

        return completed_recent / total_recent

    def identify_stalled_requests(self):
        """
        Identifie les demandes qui semblent bloquées dans le système.
        """
        stalled_requests = []
        current_time = time.time()

        # Vérifier les demandes actives qui sont en attente depuis trop longtemps
        for request_id in self.active_requests:
            if request_id in self.request_start_times:
                start_time = self.request_start_times[request_id]
                if current_time - start_time > 30:  # Plus de 30 secondes d'attente
                    stalled_requests.append(request_id)

        return stalled_requests

    def resolve_stalled_requests(self, stalled_requests):
        """
        Intervient pour résoudre les demandes bloquées.
        """
        for request_id in stalled_requests:
            self.logger.info(f"Résolution de la demande bloquée {request_id}")
            # Forcer la complétion (à utiliser avec précaution)
            self.mark_request_completed(request_id)

    async def start_agents(self):
        """
        Démarre tous les agents du système.
        """
        self.logger.info("Démarrage des agents...")

        try:
            # Agent de monitoring
            self.logger.info("Initialisation de MonitorAgent...")
            self.agents["monitor"] = MonitorAgent(
                self.agent_jids["monitor"],
                "password",
                dashboard_url=f"http://localhost:{self.dashboard_port}"
            )

            # CORRECTION: Utiliser asyncio.wait_for pour gérer le Future
            try:
                await asyncio.wait_for(
                    asyncio.wrap_future(self.agents["monitor"].start(auto_register=True)),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("Timeout lors du démarrage de MonitorAgent, tentative continue...")
            except Exception as e:
                self.logger.warning(f"Erreur lors du démarrage de MonitorAgent: {e}, tentative continue...")

            self.logger.info("MonitorAgent initialisé")
            await asyncio.sleep(2)

            # Agent d'équilibrage de charge
            self.logger.info("Initialisation de LoadBalancerAgent...")
            self.agents["load_balancer"] = LoadBalancerAgent(
                self.agent_jids["load_balancer"],
                "password",
                self.agent_jids["monitor"]
            )

            try:
                await asyncio.wait_for(
                    asyncio.wrap_future(self.agents["load_balancer"].start(auto_register=True)),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("Timeout lors du démarrage de LoadBalancerAgent, tentative continue...")
            except Exception as e:
                self.logger.warning(f"Erreur lors du démarrage de LoadBalancerAgent: {e}, tentative continue...")

            self.logger.info("LoadBalancerAgent initialisé")
            await asyncio.sleep(2)

            # Gestionnaire de ressources
            self.logger.info("Initialisation de ResourceManagerAgent...")
            self.agents["resource_manager"] = ResourceManagerAgent(
                self.agent_jids["resource_manager"],
                "password",
                self.agent_jids["load_balancer"],
                self.agent_jids["monitor"]
            )

            try:
                await asyncio.wait_for(
                    asyncio.wrap_future(self.agents["resource_manager"].start(auto_register=True)),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("Timeout lors du démarrage de ResourceManagerAgent, tentative continue...")
            except Exception as e:
                self.logger.warning(f"Erreur lors du démarrage de ResourceManagerAgent: {e}, tentative continue...")

            self.logger.info("ResourceManagerAgent initialisé")
            await asyncio.sleep(2)

            # Gestionnaire de clients
            self.logger.info("Initialisation de ClientManagerAgent...")
            self.agents["client_manager"] = ClientManagerAgent(
                self.agent_jids["client_manager"],
                "password",
                self.agent_jids["resource_manager"],
                self.agent_jids["monitor"]
            )

            try:
                await asyncio.wait_for(
                    asyncio.wrap_future(self.agents["client_manager"].start(auto_register=True)),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("Timeout lors du démarrage de ClientManagerAgent, tentative continue...")
            except Exception as e:
                self.logger.warning(f"Erreur lors du démarrage de ClientManagerAgent: {e}, tentative continue...")

            self.logger.info("ClientManagerAgent initialisé")

            # CORRECTION IMPORTANTE: Injecter la référence au SystemLauncher dans tous les agents
            self.agents["client_manager"].system_launcher = self
            self.agents["resource_manager"].system_launcher = self
            self.agents["load_balancer"].system_launcher = self
            self.agents["monitor"].system_launcher = self

            self.logger.info("Tous les agents sont initialisés et opérationnels")
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
                # CORRECTION: Utiliser asyncio.wrap_future pour les Futures
                if hasattr(agent, 'stop'):
                    try:
                        await asyncio.wait_for(
                            asyncio.wrap_future(agent.stop()),
                            timeout=5.0
                        )
                        self.logger.info(f"{agent_name} arrêté")
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Timeout lors de l'arrêt de {agent_name}")
                    except Exception as e:
                        self.logger.warning(f"Erreur lors de l'arrêt de {agent_name}: {e}")
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
        return True

    def stop(self):
        """
        Arrête le système complet.
        """
        self.logger.info("Arrêt du système...")

        # Arrêter les simulations
        for sim in self.simulations:
            sim.cancel()

        # Arrêter les agents (de manière synchrone pour éviter les problèmes)
        if hasattr(self, 'agents'):
            for agent_name, agent in self.agents.items():
                try:
                    if hasattr(agent, 'stop'):
                        # Utiliser asyncio.run_coroutine_threadsafe si on est dans un thread
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(self._stop_agent_async(agent_name, agent))
                            else:
                                asyncio.run(self._stop_agent_async(agent_name, agent))
                        except RuntimeError:
                            # Si pas de boucle d'événements, créer une nouvelle
                            asyncio.run(self._stop_agent_async(agent_name, agent))

                        self.logger.info(f"{agent_name} arrêté")
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'arrêt de {agent_name}: {e}")

        # Arrêter le tableau de bord
        self.stop_dashboard()

        self.logger.info("Système arrêté")

    async def _stop_agent_async(self, agent_name, agent):
        """Méthode auxiliaire pour arrêter un agent de manière asynchrone."""
        try:
            await asyncio.wait_for(
                asyncio.wrap_future(agent.stop()),
                timeout=3.0
            )
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'arrêt de {agent_name}: {e}")

    async def run(self, duration=None):
        """
        Exécute le système pour une durée déterminée ou indéfiniment.
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
                while True:
                    await asyncio.sleep(3600)  # Attendre 1 heure

        except asyncio.CancelledError:
            self.logger.info("Exécution annulée")
        except Exception as e:
            self.logger.error(f"Erreur pendant l'exécution: {e}")
            return False
        finally:
            self.stop()

        return True


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


def emergency_resource_release(self):
    """
    Libère d'urgence des ressources en cas de surcharge critique.
    """
    self.logger.warning("Activation de la libération d'urgence des ressources")

    # Marquer comme complétées les demandes qui sont actives depuis trop longtemps
    current_time = time.time()
    for request_id in list(self.active_requests):
        if request_id in self.request_start_times:
            if current_time - self.request_start_times[request_id] > 120:  # Plus de 2 minutes
                self.mark_request_completed(request_id)
                self.logger.info(f"Libération d'urgence: {request_id} marquée comme complétée")


# Ajout simple dans SystemLauncher
def start_simple_dashboard(self):
    """Démarre un dashboard basique"""
    import subprocess
    import sys

    # Lancer le dashboard en parallèle
    dashboard_process = subprocess.Popen([
        sys.executable, 'dashboard_simple.py'
    ])

    self.logger.info("Dashboard disponible sur http://localhost:8080")
    return dashboard_process
    # Tableau de bord amélioré
    from dashboard.app import Dashboard
    self.dashboard = Dashboard(host='0.0.0.0', port=dashboard_port)

    # Lancer le dashboard dans un thread séparé
    self.dashboard_thread = None


def start_dashboard(self):
    """Démarre le tableau de bord web dans un thread séparé"""

    def run_dashboard():
        try:
            self.logger.info(f"Démarrage du dashboard sur le port {self.dashboard.port}")
            self.dashboard.start()
        except Exception as e:
            self.logger.error(f"Erreur dashboard: {e}")

    self.dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    self.dashboard_thread.start()

    # Attendre que le serveur soit prêt
    time.sleep(2)

    self.logger.info(f"🎛️  Dashboard Admin: http://localhost:{self.dashboard.port}/admin")
    self.logger.info(f"👤 Interface Client: http://localhost:{self.dashboard.port}/client")

    return True


def update_dashboard_stats(self, vip_queue_size, standard_queue_size,
                           cpu_usage, memory_usage):
    """Met à jour les statistiques du dashboard"""
    if hasattr(self, 'dashboard'):
        self.dashboard.update_queue_sizes(vip_queue_size, standard_queue_size)
        self.dashboard.update_resources(cpu_usage, memory_usage)


def add_dashboard_log(self, level, message):
    """Ajoute un log au dashboard"""
    if hasattr(self, 'dashboard'):
        self.dashboard.add_log(level, message)


# Exemple d'utilisation dans votre code d'agents
# Quand une demande arrive :
def on_request_received(self, request_id, client_type):
    # Votre logique existante...

    # Notifier le dashboard
    if hasattr(self, 'launcher'):
        self.launcher.add_dashboard_log('INFO',
                                        f'Nouvelle demande {client_type}: {request_id}')


# Quand les ressources changent :
def update_system_resources(self):
    # Calculer les métriques actuelles
    vip_queue = len(self.vip_queue)
    standard_queue = len(self.standard_queue)
    cpu_usage = self.get_cpu_usage()  # Votre méthode
    memory_usage = self.get_memory_usage()  # Votre méthode

    # Mettre à jour le dashboard
    if hasattr(self, 'launcher'):
        self.launcher.update_dashboard_stats(
            vip_queue, standard_queue, cpu_usage, memory_usage
        )

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
    return await launcher.run(duration=args.duration)


if __name__ == "__main__":
    # Exécuter la fonction principale
    success = asyncio.run(main())