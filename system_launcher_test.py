import asyncio
import logging
import time
from agents.client_manager_agent import ClientManagerAgent
from agents.resource_manager_agent import ResourceManagerAgent
from agents.load_balancer_agent import LoadBalancerAgent
from agents.monitor_agent import MonitorAgent


class SystemLauncher:
    """
    Classe de lancement du système multi-agents avec des adaptations pour les tests.
    """

    def __init__(self):
        """
        Initialise le launcher du système.
        """
        self.logger = logging.getLogger("SystemLauncher")

        # Agents du système
        self.client_manager = None
        self.resource_manager = None
        self.load_balancer = None
        self.monitor = None

        # Pour le suivi des demandes dans les tests
        self.completed_requests = set()  # Demandes terminées
        self.failed_requests = {}  # {request_id: reason}
        self.active_requests = set()  # Demandes en cours de traitement

        # Statut du système
        self.is_running = False

    def start(self):
        """
        Démarre le système multi-agents de manière synchrone pour les tests.
        """
        self.logger.info("Démarrage du système...")

        # Initialiser les agents (sans les démarrer)
        self._init_agents()

        # Démarrer les agents en utilisant la méthode synchrone start
        # Ne pas utiliser run_until_complete ou await
        if self.monitor:
            self.monitor.start(auto_register=True)

        if self.load_balancer:
            self.load_balancer.start(auto_register=True)

        if self.resource_manager:
            self.resource_manager.start(auto_register=True)

        if self.client_manager:
            self.client_manager.start(auto_register=True)

        # Attendre que tous les agents soient prêts
        time.sleep(5)

        self.is_running = True
        self.logger.info("Système démarré.")

    def _init_agents(self):
        """
        Initialise les agents du système sans les démarrer.
        """
        # Créer les agents (adapter les JIDs et mots de passe selon votre configuration)
        self.monitor = MonitorAgent(
            "monitor@localhost", "password",
            dashboard_url="http://localhost:8080"
        )

        self.load_balancer = LoadBalancerAgent(
            "load_balancer@localhost", "password",
            monitor_jid="monitor@localhost"
        )

        self.resource_manager = ResourceManagerAgent(
            "resource_manager@localhost", "password",
            load_balancer_jid="load_balancer@localhost",
            monitor_jid="monitor@localhost"
        )

        self.client_manager = ClientManagerAgent(
            "client_manager@localhost", "password",
            resource_manager_jid="resource_manager@localhost",
            monitor_jid="monitor@localhost"
        )

    def shutdown(self):
        """
        Arrête le système multi-agents.
        """
        if not self.is_running:
            return

        self.logger.info("Arrêt du système...")

        # Arrêter les agents dans l'ordre inverse du démarrage
        if self.client_manager:
            self.client_manager.stop()

        if self.resource_manager:
            self.resource_manager.stop()

        if self.load_balancer:
            self.load_balancer.stop()

        if self.monitor:
            self.monitor.stop()

        # Attendre un peu pour s'assurer que tous les agents sont arrêtés
        time.sleep(2)

        self.is_running = False
        self.logger.info("Système arrêté.")

    def get_completed_requests(self):
        """
        Retourne l'ensemble des demandes complétées depuis le dernier appel.

        Returns:
            set: Ensemble des identifiants des demandes complétées
        """
        # Copier l'ensemble actuel pour le retourner
        completed = self.completed_requests.copy()

        # Vider l'ensemble pour le prochain appel
        self.completed_requests.clear()

        return completed

    def get_failed_requests(self):
        """
        Retourne l'ensemble des demandes échouées depuis le dernier appel.

        Returns:
            set: Ensemble des identifiants des demandes échouées
        """
        # Retourner les clés (identifiants) des demandes échouées
        failed = set(self.failed_requests.keys())

        # Ne pas vider self.failed_requests car on en a besoin pour get_failure_reason
        return failed

    def get_failure_reason(self, request_id):
        """
        Retourne la raison de l'échec d'une demande.

        Args:
            request_id (str): Identifiant de la demande échouée

        Returns:
            str: Raison de l'échec, ou None si la demande n'a pas échoué
        """
        return self.failed_requests.get(request_id, "unknown_failure")

    def mark_request_completed(self, request_id):
        """
        Marque une demande comme complétée.
        Cette méthode doit être appelée par les agents lorsqu'une demande est terminée.

        Args:
            request_id (str): Identifiant de la demande complétée
        """
        if request_id in self.active_requests:
            self.active_requests.remove(request_id)
            self.completed_requests.add(request_id)

    def mark_request_failed(self, request_id, reason):
        """
        Marque une demande comme échouée.
        Cette méthode doit être appelée par les agents lorsqu'une demande échoue.

        Args:
            request_id (str): Identifiant de la demande échouée
            reason (str): Raison de l'échec
        """
        if request_id in self.active_requests:
            self.active_requests.remove(request_id)
            self.failed_requests[request_id] = reason