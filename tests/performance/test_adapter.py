# tests/performance/test_adapter.py

import logging
import asyncio
import time
import threading
from models.client import Client
from models.enums import ClientType
from models.resource_request import ResourceRequest


class TestAdapter:
    """
    Adaptateur pour les tests de performance.
    Fournit une interface unifiée pour interagir avec le système.
    """

    def __init__(self, system_launcher):
        """
        Initialise l'adaptateur de test.

        Args:
            system_launcher: Instance du SystemLauncher
        """
        self.system_launcher = system_launcher
        self.logger = logging.getLogger("TestAdapter")

        # S'assurer que les collections pour le suivi des demandes existent
        if not hasattr(self.system_launcher, 'active_requests'):
            self.system_launcher.active_requests = set()

        if not hasattr(self.system_launcher, 'completed_requests'):
            self.system_launcher.completed_requests = set()

        if not hasattr(self.system_launcher, 'failed_requests'):
            self.system_launcher.failed_requests = {}

        # Créer et démarrer la boucle d'événements dans un thread séparé
        self._loop = None
        self._thread = None
        self._start_event_loop()

    def _start_event_loop(self):
        """
        Démarre une boucle d'événements asyncio dans un thread séparé.
        """
        self._loop = asyncio.new_event_loop()

        def run_event_loop():
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_event_loop, daemon=True)
        self._thread.start()

    def submit_request(self, client, request_id, cpu_required, memory_required, estimated_duration, dependencies=None):
        """
        Soumet une nouvelle demande au système.

        Args:
            client: Client qui soumet la demande
            request_id (str): Identifiant unique de la demande
            cpu_required (float): Quantité de CPU requise
            memory_required (float): Quantité de mémoire requise
            estimated_duration (float): Durée estimée d'exécution (en secondes)
            dependencies (set, optional): Ensemble des IDs de demandes dont dépend cette demande

        Returns:
            bool: True si la demande a été acceptée, False sinon
        """
        try:
            # Vérifier si le client_manager existe
            if not hasattr(self.system_launcher, 'client_manager') or not self.system_launcher.client_manager:
                raise AttributeError("client_manager is not available")

            # Créer les données de la demande
            request_data = {
                "client": self._client_to_dict(client),
                "id": request_id,
                "cpu_required": cpu_required,
                "memory_required": memory_required,
                "estimated_duration": estimated_duration,
                "dependencies": list(dependencies) if dependencies else []
            }

            # Tracer la soumission
            self.logger.info(f"Soumission de la demande {request_id} du client {client.id} "
                             f"(CPU: {cpu_required}, Mémoire: {memory_required}, Durée: {estimated_duration}s)")

            # Soumettre la demande au ClientManagerAgent de façon synchrone via asyncio.run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(
                self.system_launcher.client_manager.process_simulation_request(request_data),
                self._loop
            )

            # Attendre le résultat (avec un timeout)
            future.result(timeout=5)

            # Activer le suivi de la demande
            self.system_launcher.active_requests.add(request_id)

            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la soumission de la demande {request_id}: {e}")

            # Enregistrer l'échec
            if hasattr(self.system_launcher, 'failed_requests'):
                self.system_launcher.failed_requests[request_id] = f"error_during_submission: {str(e)}"

            return False

    def _client_to_dict(self, client):
        """
        Convertit un client en dictionnaire.
        Gère les cas où client.to_dict() n'est pas disponible.

        Args:
            client: Client à convertir

        Returns:
            dict: Dictionnaire représentant le client
        """
        if hasattr(client, 'to_dict') and callable(getattr(client, 'to_dict')):
            return client.to_dict()

        # Conversion manuelle
        return {
            "id": client.id,
            "client_type": client.client_type.name
        }

    def get_completed_requests(self):
        """
        Retourne l'ensemble des demandes complétées depuis le dernier appel.

        Returns:
            set: Ensemble des identifiants des demandes complétées
        """
        if hasattr(self.system_launcher, 'get_completed_requests'):
            return self.system_launcher.get_completed_requests()
        return set()

    def get_failed_requests(self):
        """
        Retourne l'ensemble des demandes échouées depuis le dernier appel.

        Returns:
            set: Ensemble des identifiants des demandes échouées
        """
        if hasattr(self.system_launcher, 'get_failed_requests'):
            return self.system_launcher.get_failed_requests()
        return set()

    def get_failure_reason(self, request_id):
        """
        Retourne la raison de l'échec d'une demande.

        Args:
            request_id (str): Identifiant de la demande échouée

        Returns:
            str: Raison de l'échec, ou None si la demande n'a pas échoué
        """
        if hasattr(self.system_launcher, 'get_failure_reason'):
            return self.system_launcher.get_failure_reason(request_id)
        return "unknown_failure (failure tracking not implemented)"

    def __del__(self):
        """
        Nettoyage des ressources lors de la destruction de l'objet.
        """
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)