import time
import logging


class HRRNScheduler:
    """
    Implémentation de l'algorithme d'ordonnancement Highest Response Ratio Next (HRRN)
    avec mécanisme de vieillissement pour éviter la famine des demandes standard.
    """

    def __init__(self, vip_queue, standard_queue, aging_factor=0.5):
        """
        Initialise l'ordonnanceur HRRN.

        Args:
            vip_queue (list): Liste des demandes VIP
            standard_queue (list): Liste des demandes standard
            aging_factor (float): Facteur de vieillissement (poids du temps d'attente)
        """
        self.vip_queue = vip_queue
        self.standard_queue = standard_queue
        self.aging_factor = aging_factor
        self.logger = logging.getLogger("HRRNScheduler")

        # Priorité de base pour les demandes
        self.vip_priority = 100.0  # Priorité de base élevée pour les demandes VIP
        self.standard_priority = 10.0  # Priorité de base plus faible pour les demandes standard

    def calculate_priority(self, request):
        """
        Calcule la priorité effective d'une demande en fonction de sa priorité de base,
        du temps d'attente et du facteur de vieillissement.

        Args:
            request: Demande à évaluer

        Returns:
            float: Priorité effective
        """
        # Déterminer la priorité de base en fonction du type de client
        base_priority = self.vip_priority if request.client.is_vip() else self.standard_priority

        # Calculer le temps d'attente en secondes
        wait_time = time.time() - request.arrival_time

        # Calculer le ratio de réponse normalisé
        # HRRN = (wait_time + service_time) / service_time
        # Nous utilisons estimated_duration comme temps de service estimé
        service_time = request.estimated_duration

        if service_time <= 0:
            service_time = 1.0  # Éviter la division par zéro

        response_ratio = (wait_time + service_time) / service_time

        # Calculer la priorité effective avec vieillissement
        effective_priority = base_priority + (self.aging_factor * wait_time)

        # Ajuster la priorité en fonction du ratio de réponse
        effective_priority *= response_ratio

        return effective_priority

    def update_priorities(self):
        """
        Met à jour les priorités des demandes dans les files d'attente.
        """
        # Mettre à jour la priorité effective pour chaque demande
        for request in self.vip_queue + self.standard_queue:
            request.effective_priority = self.calculate_priority(request)

    def get_next_request(self):
        """
        Récupère la demande avec la priorité effective la plus élevée.

        Returns:
            Demande à traiter, ou None si aucune demande en attente
        """
        # Mettre à jour les priorités avant la sélection
        self.update_priorities()

        # Vérifier s'il y a des demandes en attente
        if not self.vip_queue and not self.standard_queue:
            return None

        # Trouver la demande avec la priorité la plus élevée
        best_request = None
        best_priority = -1

        # Parcourir toutes les demandes (VIP et standard)
        for request in self.vip_queue + self.standard_queue:
            if request.effective_priority > best_priority:
                best_priority = request.effective_priority
                best_request = request

        if best_request:
            self.logger.info(f"Sélection de la demande {best_request.id} avec priorité {best_priority:.2f}")

        return best_request