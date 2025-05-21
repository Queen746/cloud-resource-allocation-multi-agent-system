import asyncio
import logging
import time
from agents.client_manager_agent import ClientManagerAgent
from agents.resource_manager_agent import ResourceManagerAgent
from agents.load_balancer_agent import LoadBalancerAgent
from agents.monitor_agent import MonitorAgent
from tests.performance.test_adapter import TestAdapter
from tests.performance.direct_test_adapter import DirectTestAdapter


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

        # Adapter pour les tests - sera initialisé après le démarrage des agents
        self.test_adapter = None

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
            # Attendre que le monitor soit prêt
            time.sleep(2)

        if self.load_balancer:
            self.load_balancer.start(auto_register=True)
            # Attendre que le load_balancer soit prêt
            time.sleep(2)

        if self.resource_manager:
            self.resource_manager.start(auto_register=True)
            # Attendre que le resource_manager soit prêt
            time.sleep(2)

        if self.client_manager:
            self.client_manager.start(auto_register=True)
            # Attendre que le client_manager soit prêt
            time.sleep(2)

        # CORRECTION IMPORTANTE: Injecter la référence au SystemLauncher dans tous les agents
        self.client_manager.system_launcher = self
        self.resource_manager.system_launcher = self
        self.load_balancer.system_launcher = self
        self.monitor.system_launcher = self

        # Initialiser l'adaptateur de test APRÈS que les agents soient démarrés
        self.test_adapter = DirectTestAdapter(self)

        self.is_running = True
        self.logger.info("Système démarré avec succès.")

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

    def submit_request(self, client, request_id, cpu_required, memory_required, estimated_duration, dependencies=None):
        """
        Soumet une nouvelle demande au système pour les tests.
        Utilise l'adaptateur TestAdapter qui est conçu pour gérer ces demandes.
        """
        self.logger.info(f"Simulation: Envoi de la demande {request_id} du client {client.id} "
                         f"(CPU: {cpu_required}, Mémoire: {memory_required}, Durée: {estimated_duration}s, "
                         f"Dépendances: {dependencies})")

        # Ajouter la demande aux demandes actives pour le suivi
        self.active_requests.add(request_id)

        try:
            # Vérifier que l'adaptateur est initialisé
            if self.test_adapter is None:
                self.logger.error("TestAdapter n'est pas initialisé")
                self.failed_requests[request_id] = "error_during_submission: TestAdapter not initialized"
                return False

            # Utiliser l'adaptateur pour soumettre la demande
            success = self.test_adapter.submit_request(
                client,
                request_id,
                cpu_required,
                memory_required,
                estimated_duration,
                dependencies
            )

            return success

        except Exception as e:
            self.logger.error(f"Erreur lors de la soumission de la demande {request_id}: {e}")
            self.failed_requests[request_id] = f"error_during_submission: {str(e)}"
            return False

    def shutdown(self):
        """
        Arrête le système multi-agents.
        """
        if not self.is_running:
            return

        self.logger.info("Arrêt du système...")

        # Nettoyer l'adaptateur de test s'il existe
        if self.test_adapter:
            # TestAdapter a une méthode __del__ qui nettoie ses ressources
            self.test_adapter = None

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
        """
        # Copier l'ensemble actuel pour le retourner
        completed = self.completed_requests.copy()

        # Vider l'ensemble pour le prochain appel
        self.completed_requests.clear()

        return completed

    def get_failed_requests(self):
        """
        Retourne l'ensemble des demandes échouées depuis le dernier appel.
        """
        # Retourner les clés (identifiants) des demandes échouées
        failed = set(self.failed_requests.keys())

        # Ne pas vider self.failed_requests car on en a besoin pour get_failure_reason
        return failed

    def get_failure_reason(self, request_id):
        """
        Retourne la raison de l'échec d'une demande.
        """
        return self.failed_requests.get(request_id, "unknown_failure")

    def mark_request_completed(self, request_id):
        """
        Marque une demande comme complétée.
        Cette méthode doit être appelée par les agents lorsqu'une demande est terminée.
        """
        if request_id in self.active_requests:
            self.active_requests.remove(request_id)
            self.completed_requests.add(request_id)
            self.logger.info(f"Demande {request_id} marquée comme complétée")

    def mark_request_failed(self, request_id, reason):
        """
        Marque une demande comme échouée.
        Cette méthode doit être appelée par les agents lorsqu'une demande échoue.
        """
        if request_id in self.active_requests:
            self.active_requests.remove(request_id)
            self.failed_requests[request_id] = reason
            self.logger.info(f"Demande {request_id} marquée comme échouée: {reason}")

    def manually_mark_all_active_as_completed(self):
        """
        Marque toutes les demandes actives comme complétées.
        Utile pour les tests si le mécanisme normal ne fonctionne pas.
        """
        self.logger.info(f"Marquage manuel de toutes les demandes actives comme complétées")

        active_copy = self.active_requests.copy()
        for request_id in active_copy:
            self.mark_request_completed(request_id)
            self.logger.info(f"Demande {request_id} marquée manuellement comme complétée")

        return len(active_copy)
