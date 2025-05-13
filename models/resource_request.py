import time
from models.enums import RequestStatus


class ResourceRequest:
    """
    Représente une demande de ressources dans le système cloud.
    """

    def __init__(self, request_id, client, cpu_required, memory_required, estimated_duration, dependencies=None):
        """
        Initialise une nouvelle demande de ressources.

        Args:
            request_id (str): Identifiant unique de la demande
            client (Client): Client associé à la demande
            cpu_required (float): Quantité de CPU requise
            memory_required (float): Quantité de mémoire requise
            estimated_duration (float): Durée estimée d'exécution (en secondes)
            dependencies (set, optional): Ensemble des IDs de demandes dont dépend cette demande
        """
        self.id = request_id
        self.client = client
        self.cpu_required = float(cpu_required)
        self.memory_required = float(memory_required)
        self.estimated_duration = float(estimated_duration)
        self.dependencies = set(dependencies or [])

        # État de la demande
        self.status = RequestStatus.CREATED

        # Timestamps
        self.arrival_time = time.time()
        self.start_time = None
        self.completion_time = None

        # Serveur assigné
        self.assigned_server = None

        # Priorité effective (calculée par l'ordonnanceur)
        self.effective_priority = 0.0

    def get_wait_time(self):
        """
        Calcule le temps d'attente de la demande.

        Returns:
            float: Temps d'attente en secondes (ou 0 si la demande n'a pas encore démarré)
        """
        if self.start_time:
            return self.start_time - self.arrival_time
        return time.time() - self.arrival_time

    def get_turnaround_time(self):
        """
        Calcule le temps de réponse total de la demande.

        Returns:
            float: Temps de réponse en secondes (ou None si la demande n'est pas terminée)
        """
        if self.completion_time:
            return self.completion_time - self.arrival_time
        return None

    def __str__(self):
        """
        Représentation sous forme de chaîne de caractères.

        Returns:
            str: Représentation de la demande
        """
        return f"ResourceRequest(id={self.id}, client={self.client.id}, status={self.status.name}, priority={self.effective_priority:.2f})"