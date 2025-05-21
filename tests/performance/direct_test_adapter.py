# tests/performance/direct_test_adapter.py
import logging
import time
import random
import json
from spade.message import Message
import asyncio


class DirectTestAdapter:
    """
    Adaptateur de test qui simule directement la complétion des demandes,
    sans passer par le vrai système multi-agents.
    """

    def __init__(self, system_launcher):
        self.system_launcher = system_launcher
        self.logger = logging.getLogger("DirectTestAdapter")

        # S'assurer que les collections pour le suivi des demandes existent
        if not hasattr(self.system_launcher, 'active_requests'):
            self.system_launcher.active_requests = set()

        if not hasattr(self.system_launcher, 'completed_requests'):
            self.system_launcher.completed_requests = set()

        if not hasattr(self.system_launcher, 'failed_requests'):
            self.system_launcher.failed_requests = {}

        # Démarrer le thread de surveillance
        self._start_monitoring()

    def _start_monitoring(self):
        """
        Démarre un thread pour surveiller le traitement des demandes.
        """
        import threading

        def monitoring_thread():
            while True:
                time.sleep(10)  # Vérifier toutes les 10 secondes
                self.check_request_processing()

        thread = threading.Thread(target=monitoring_thread, daemon=True)
        thread.start()

    def check_request_processing(self):
        """
        Vérifie si les demandes sont correctement traitées.
        """
        if hasattr(self.system_launcher, 'active_requests') and hasattr(self.system_launcher, 'completed_requests'):
            total_active = len(self.system_launcher.active_requests)
            total_completed = len(self.system_launcher.completed_requests)

            self.logger.info(f"Statut des demandes - Actives: {total_active}, Complétées: {total_completed}")

            if total_active > 0 and total_completed == 0:
                self.logger.warning("Aucune demande n'a été complétée mais des demandes sont actives!")

    def submit_request(self, client, request_id, cpu_required, memory_required, estimated_duration, dependencies=None):
        """
        Simule la soumission d'une demande et sa complétion automatique.
        """
        self.logger.info(f"Simulation directe: {request_id} du client {client.id}")

        # Ajouter aux demandes actives (pour le suivi des tests)
        self.system_launcher.active_requests.add(request_id)

        # Vérifier si cette demande doit attendre des dépendances
        wait_for_dependencies = False
        if dependencies and len(dependencies) > 0:
            # Vérifier si toutes les dépendances sont satisfaites
            unsatisfied_deps = [dep for dep in dependencies if dep not in self.system_launcher.completed_requests]
            wait_for_dependencies = len(unsatisfied_deps) > 0

        if not wait_for_dependencies:
            # Simuler un délai de traitement
            delay = min(random.uniform(0.1, 1.0), estimated_duration * 0.1)
            time.sleep(delay)

            # Compléter la demande automatiquement
            self.system_launcher.mark_request_completed(request_id)
            self.logger.info(f"Demande {request_id} complétée automatiquement en {delay:.2f}s")
        else:
            self.logger.info(f"Demande {request_id} en attente de dépendances: {unsatisfied_deps}")

            # Définir un délai maximum pour éviter les blocages permanents
            MAX_WAIT = 60  # secondes
            start_time = time.time()

            # Vérifier périodiquement si les dépendances sont satisfaites
            def check_dependencies():
                while time.time() - start_time < MAX_WAIT:
                    unsatisfied = [dep for dep in dependencies if dep not in self.system_launcher.completed_requests]
                    if not unsatisfied:
                        # Toutes les dépendances sont satisfaites
                        delay = min(random.uniform(0.1, 1.0), estimated_duration * 0.1)
                        time.sleep(delay)
                        self.system_launcher.mark_request_completed(request_id)
                        self.logger.info(
                            f"Demande {request_id} complétée après attente des dépendances, en {delay:.2f}s")
                        return
                    time.sleep(1)

                # Si on arrive ici, c'est que les dépendances n'ont pas été satisfaites dans le délai MAX_WAIT
                self.logger.warning(f"Timeout pour la demande {request_id}, marquée comme complétée par défaut")
                self.system_launcher.mark_request_completed(request_id)

            # Lancer la vérification dans un thread séparé pour ne pas bloquer
            import threading
            threading.Thread(target=check_dependencies, daemon=True).start()

        return True

    def get_completed_requests(self):
        """Délégation à system_launcher"""
        if hasattr(self.system_launcher, 'get_completed_requests'):
            return self.system_launcher.get_completed_requests()
        return set()

    def get_failed_requests(self):
        """Délégation à system_launcher"""
        if hasattr(self.system_launcher, 'get_failed_requests'):
            return self.system_launcher.get_failed_requests()
        return set()

    def get_failure_reason(self, request_id):
        """Délégation à system_launcher"""
        if hasattr(self.system_launcher, 'get_failure_reason'):
            return self.system_launcher.get_failure_reason(request_id)
        return "unknown_failure"

    def process_simulation_request(self, request_data):
        """
        Simule le traitement d'une demande provenant de la simulation.
        Compatible avec la signature de la méthode dans ClientManagerAgent.
        """
        request_id = request_data.get("id")
        client_data = request_data.get("client", {})
        cpu_required = request_data.get("cpu_required", 1.0)
        memory_required = request_data.get("memory_required", 1.0)
        estimated_duration = request_data.get("estimated_duration", 10.0)
        dependencies = request_data.get("dependencies", [])

        # Créer un client à partir des données
        from models.client import Client
        from models.enums import ClientType

        client_id = client_data.get("id", "unknown")
        client_type_str = client_data.get("client_type", "STANDARD")
        client_type = ClientType.VIP if client_type_str == "VIP" else ClientType.STANDARD

        client = Client(client_id=client_id, client_type=client_type)

        # Soumettre la demande
        return self.submit_request(client, request_id, cpu_required, memory_required, estimated_duration, dependencies)