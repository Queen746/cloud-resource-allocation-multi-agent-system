import asyncio
import time
import logging
import json
import random
from collections import deque
from datetime import datetime

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template

from models.enums import ClientType, RequestStatus
from algorithms.hrrn_scheduler import HRRNScheduler


class ClientManagerAgent(Agent):
    """
    Agent responsable de la gestion des files d'attente des demandes et de
    l'ordonnancement. Implémente un algorithme HRRN avec vieillissement.
    """

    def __init__(self, jid, password, resource_manager_jid, monitor_jid):
        """
        Initialise l'agent gestionnaire de clients.
        """
        super().__init__(jid, password)
        self.display_name = "ClientManagerAgent"
        self.resource_manager_jid = resource_manager_jid
        self.monitor_jid = monitor_jid
        self.logger = logging.getLogger(f"{self.display_name}-{jid.split('@')[0]}")

        # Initialiser les files d'attente et l'ordonnanceur
        self.vip_queue = []
        self.standard_queue = []
        self.scheduler = None  # Sera initialisé dans setup()

        # Ajouter ces attributs
        self.processing_requests = []  # Demandes en cours de traitement
        self.waiting_dependencies = []  # Demandes en attente de dépendances
        self.completed_requests = 0  # Compteur de demandes complétées

        # Dernier rapport sur les files d'attente
        self.last_queue_report = 0

        # Pour suivre les temps d'arrivée des demandes
        self.request_arrivals = {}

        # Référence au SystemLauncher (sera injectée)
        self.system_launcher = None

        # Variables pour la régulation
        self.throttling_active = False
        self.aging_factor = 0.5  # Facteur de vieillissement

    class RequestQueueBehaviour(CyclicBehaviour):
        """
        Comportement pour gérer les files d'attente et l'ordonnancement des demandes.
        """

        async def run(self):
            try:
                # Vérifier s'il y a des demandes en attente
                next_request = self.agent.scheduler.get_next_request()

                if next_request:
                    request_id = next_request.id
                    self.agent.logger.info(
                        f"Traitement de la demande {request_id} (Priorité: {next_request.effective_priority:.2f})")

                    # Retirer de la file d'attente
                    self.agent.remove_request_from_queue(next_request)

                    # Demander l'allocation des ressources au ResourceManagerAgent
                    message = Message(to=str(self.agent.resource_manager_jid))
                    message.set_metadata("type", "allocation_request")
                    # Après avoir envoyé la demande au ResourceManagerAgent
                    self.agent.logger.info(f"Demande d'allocation envoyée au ResourceManagerAgent pour {request_id}")

                    message_body = {
                        "request_id": next_request.id,
                        "cpu_required": next_request.cpu_required,
                        "memory_required": next_request.memory_required,
                        "estimated_duration": next_request.estimated_duration,
                        "dependencies": list(next_request.dependencies),
                        "arrival_time": next_request.arrival_time,
                        "client_type": next_request.client.client_type.name
                    }

                    message.body = json.dumps(message_body)
                    await self.send(message)

                    # Notifier le MonitorAgent
                    monitor_msg = Message(to=str(self.agent.monitor_jid))
                    monitor_msg.set_metadata("type", "request_processing")
                    monitor_msg.body = json.dumps({
                        "request_id": next_request.id,
                        "client_type": next_request.client.client_type.name,
                        "timestamp": time.time(),
                        "arrival_time": next_request.arrival_time
                    })
                    await self.send(monitor_msg)

                # Mettre à jour les priorités en fonction du temps écoulé
                self.agent.scheduler.update_priorities()

                # Envoyer périodiquement un rapport sur l'état des files d'attente
                current_time = time.time()
                if current_time - self.agent.last_queue_report > 5:  # Rapport toutes les 5 secondes
                    self.agent.logger.info(
                        f"Queue status - VIP: {len(self.agent.vip_queue)}, Standard: {len(self.agent.standard_queue)}")
                    self.agent.last_queue_report = current_time

                    # Notifier le MonitorAgent
                    await self.agent.notify_monitor_queue_update()

            except Exception as e:
                self.agent.logger.error(f"Erreur dans le comportement de file d'attente: {e}")

            # Petit délai pour éviter de surcharger le CPU
            await asyncio.sleep(0.1)

    class NewRequestProcessingBehaviour(CyclicBehaviour):
        """
        Comportement pour traiter les nouvelles demandes entrantes.
        """

        async def run(self):
            # Attendre les messages de nouvelle demande
            msg = await self.receive(timeout=10)
            if msg:
                try:
                    content = json.loads(msg.body)

                    if msg.metadata.get("type") == "new_request":
                        await self.agent._handle_new_request(content)
                    elif msg.metadata.get("type") == "allocation_response":
                        await self.agent._handle_allocation_response(content)
                    elif msg.metadata.get("type") == "dependencies_satisfied":
                        await self.agent._handle_dependencies_satisfied(content)
                    elif msg.metadata.get("type") == "request_completed":
                        await self.agent._handle_request_completed(content)

                except Exception as e:
                    self.agent.logger.error(f"Erreur lors du traitement du message: {e}")

            # Petit délai pour éviter de surcharger le CPU
            await asyncio.sleep(0.1)

    class ThrottlingBehaviour(CyclicBehaviour):
        """
        Comportement pour réguler l'entrée des demandes en fonction de la charge actuelle.
        """

        async def run(self):
            # Vérifier le nombre de demandes actives et en file d'attente
            total_requests = (len(self.agent.vip_queue) +
                              len(self.agent.standard_queue) +
                              len(self.agent.processing_requests))

            # Définir un seuil adaptatif basé sur la performance récente
            threshold = self.agent.calculate_adaptive_threshold()

            if total_requests > threshold:
                # Mode de régulation : ralentir le traitement des nouvelles demandes
                self.agent.throttling_active = True
                self.agent.logger.warning(f"Régulation activée - {total_requests} demandes dans le système")

                # Réduire la fréquence de traitement des nouvelles demandes
                await asyncio.sleep(1.0)  # Attendre plus longtemps avant de traiter la prochaine demande
            else:
                # Mode normal
                self.agent.throttling_active = False
                await asyncio.sleep(0.1)

    async def setup(self):
        """
        Initialise l'agent et ses comportements.
        """
        self.logger.info(f"Agent {self.display_name} starting...")

        # Initialiser l'ordonnanceur
        self.scheduler = HRRNScheduler(self.vip_queue, self.standard_queue)

        # Comportements
        queue_behaviour = self.RequestQueueBehaviour()
        self.add_behaviour(queue_behaviour)

        new_request_template = Template()
        new_request_template.set_metadata("type", "new_request")
        self.add_behaviour(self.NewRequestProcessingBehaviour(), new_request_template)

        allocation_response_template = Template()
        allocation_response_template.set_metadata("type", "allocation_response")
        self.add_behaviour(self.NewRequestProcessingBehaviour(), allocation_response_template)

        dependencies_template = Template()
        dependencies_template.set_metadata("type", "dependencies_satisfied")
        self.add_behaviour(self.NewRequestProcessingBehaviour(), dependencies_template)

        completion_template = Template()
        completion_template.set_metadata("type", "request_completed")
        self.add_behaviour(self.NewRequestProcessingBehaviour(), completion_template)

        # Ajouter le comportement de régulation
        self.add_behaviour(self.ThrottlingBehaviour())

    # Méthodes de traitement des messages
    async def _handle_new_request(self, content):
        """Traite une nouvelle demande."""
        request_id = content.get("id")
        client = content.get("client")
        cpu_required = content.get("cpu_required")
        memory_required = content.get("memory_required")
        estimated_duration = content.get("estimated_duration")
        dependencies = set(content.get("dependencies", []))

        self.logger.info(
            f"Nouvelle demande reçue: {request_id} du client {client['id']} (type: {client['client_type']})")

        # Créer l'objet de demande
        from models.client import Client
        from models.resource_request import ResourceRequest

        client_obj = Client(
            client_id=client["id"],
            client_type=ClientType[client["client_type"]]
        )

        request = ResourceRequest(
            request_id=request_id,
            client=client_obj,
            cpu_required=cpu_required,
            memory_required=memory_required,
            estimated_duration=estimated_duration,
            dependencies=dependencies
        )

        # Ajouter à la file d'attente appropriée
        self.add_request_to_queue(request)

        # Notifier le MonitorAgent
        monitor_msg = Message(to=str(self.monitor_jid))
        monitor_msg.set_metadata("type", "new_request")
        monitor_msg.body = json.dumps({
            "request_id": request_id,
            "client_type": client["client_type"],
            "timestamp": time.time(),
            "arrival_time": request.arrival_time
        })
        await self.send(monitor_msg)

    async def _handle_allocation_response(self, content):
        """Traite une réponse d'allocation."""
        request_id = content.get("request_id")
        status = content.get("status")

        if status == "allocated":
            server_id = content.get("server_id")
            estimated_completion = content.get("estimated_completion")

            self.logger.info(
                f"Demande {request_id} allouée sur {server_id}, complétion estimée: {datetime.fromtimestamp(estimated_completion).strftime('%H:%M:%S')}")

        elif status == "rejected":
            reason = content.get("reason")
            self.logger.warning(f"Demande {request_id} rejetée: {reason}")

        elif status == "pending":
            reason = content.get("reason")
            self.logger.info(f"Demande {request_id} en attente: {reason}")

    async def _handle_dependencies_satisfied(self, content):
        """Traite la satisfaction des dépendances."""
        request_id = content.get("request_id")
        self.logger.info(f"Dépendances satisfaites pour {request_id}, prêt à être traité")

    async def _handle_request_completed(self, content):
        """Traite la complétion d'une demande."""
        request_id = content.get("request_id")
        server_id = content.get("server_id")
        await self.on_request_completed(request_id, server_id)

    def add_request_to_queue(self, request):
        """
        Ajoute une demande à la file d'attente appropriée.
        """
        request.status = RequestStatus.PENDING
        request.arrival_time = time.time()

        # Enregistrer le temps d'arrivée
        self.request_arrivals[request.id] = request.arrival_time

        if request.client.client_type == ClientType.VIP:
            self.vip_queue.append(request)
            self.logger.info(f"Demande {request.id} ajoutée à la file VIP (taille: {len(self.vip_queue)})")
        else:
            self.standard_queue.append(request)
            self.logger.info(f"Demande {request.id} ajoutée à la file standard (taille: {len(self.standard_queue)})")

    def remove_request_from_queue(self, request):
        """
        Retire une demande de la file d'attente.
        """
        if request.client.client_type == ClientType.VIP:
            if request in self.vip_queue:
                self.vip_queue.remove(request)
                self.logger.info(f"Demande {request.id} retirée de la file VIP (taille: {len(self.vip_queue)})")
        else:
            if request in self.standard_queue:
                self.standard_queue.remove(request)
                self.logger.info(
                    f"Demande {request.id} retirée de la file standard (taille: {len(self.standard_queue)})")

    def calculate_adaptive_threshold(self):
        """Calcule un seuil adaptatif basé sur les performances récentes."""
        base_threshold = 100  # Valeur de base

        # Ajuster en fonction du taux de réussite récent
        if hasattr(self, 'recent_success_rate'):
            if self.recent_success_rate < 0.8:  # Si taux de réussite < 80%
                return max(20, base_threshold * self.recent_success_rate)  # Réduire le seuil, mais pas en dessous de 20

        return base_threshold

    def update_priorities(self):
        """
        Met à jour les priorités des demandes pour maintenir l'équité.
        """
        vip_queue_size = len(self.vip_queue)
        standard_queue_size = len(self.standard_queue)
        total_size = vip_queue_size + standard_queue_size

        if total_size > 0:
            vip_ratio = vip_queue_size / total_size

            # Si le ratio de VIP est trop élevé (> 30%), augmenter l'âge effectif des demandes standard
            if vip_ratio > 0.3 and standard_queue_size > 0:
                self.logger.info("Augmentation de la priorité des demandes standard pour maintenir l'équité")
                aging_factor = 1.2  # Augmenter de 20%

                for request in self.standard_queue:
                    if hasattr(request, 'priority'):
                        # Augmenter la priorité effective par l'âge
                        age = time.time() - request.arrival_time
                        request.effective_priority = request.priority + (self.aging_factor * aging_factor * age)

            # Si le ratio de standard est trop élevé, augmenter la priorité des VIP
            elif vip_ratio < 0.1 and vip_queue_size > 0:
                self.logger.info("Augmentation de la priorité des demandes VIP pour maintenir le SLA")
                for request in self.vip_queue:
                    if hasattr(request, 'priority'):
                        request.priority *= 1.5  # Augmenter de 50%

    async def notify_monitor_queue_update(self):
        """
        Envoie une mise à jour des files d'attente au MonitorAgent.
        """
        monitor_msg = Message(to=str(self.monitor_jid))
        monitor_msg.set_metadata("type", "queue_status")
        monitor_msg.body = json.dumps({
            "vip_size": len(self.vip_queue),
            "standard_size": len(self.standard_queue),
            "timestamp": time.time()
        })

        # Créer un comportement OneShot pour envoyer le message
        class SendQueueUpdateBehaviour(OneShotBehaviour):
            async def run(self):
                await self.send(monitor_msg)

        self.add_behaviour(SendQueueUpdateBehaviour())

    async def process_simulation_request(self, request_data):
        """
        Traite une demande de simulation.
        """
        try:
            # Créer l'objet Client à partir du dictionnaire
            from models.client import Client
            client = Client.from_dict(request_data["client"])

            # Créer l'objet ResourceRequest
            from models.resource_request import ResourceRequest
            request = ResourceRequest(
                request_id=request_data["id"],
                client=client,
                cpu_required=request_data["cpu_required"],
                memory_required=request_data["memory_required"],
                estimated_duration=request_data["estimated_duration"],
                dependencies=set(request_data["dependencies"])
            )

            # Ajouter à la file d'attente appropriée
            self.add_request_to_queue(request)

            # Notifier le MonitorAgent
            class NotifyMonitorBehaviour(OneShotBehaviour):
                async def run(self):
                    message = Message(to=str(self.agent.monitor_jid))
                    message.set_metadata("type", "new_request")
                    message.body = json.dumps({
                        "request_id": request.id,
                        "client_type": client.client_type.name,
                        "timestamp": time.time(),
                        "arrival_time": request.arrival_time
                    })
                    await self.send(message)

            self.add_behaviour(NotifyMonitorBehaviour())

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la demande de simulation: {e}", exc_info=True)

    async def on_request_completed(self, request_id, server_id):
        """
        Appelé lorsqu'une demande est complétée.
        """
        self.logger.info(f"Demande {request_id} complétée sur {server_id}")

        # Trouver et retirer la demande
        request_found = False
        found_request = None

        # Chercher dans toutes les listes
        for request_list in [self.processing_requests, self.vip_queue, self.standard_queue, self.waiting_dependencies]:
            for request in list(request_list):
                if request.id == request_id:
                    found_request = request
                    request_list.remove(request)
                    request_found = True
                    break
            if request_found:
                break

        if request_found and found_request:
            # Mettre à jour les statistiques
            self.completed_requests += 1

            # Notifier le client (simulation)
            self.logger.info(f"Client {found_request.client.id} notifié de la complétion de la demande {request_id}")

            # Vérifier les dépendances satisfaites
            await self._check_dependencies_satisfied(request_id)

            # Mettre à jour les tailles des files d'attente
            await self.notify_monitor_queue_update()

            # Notifier le MonitorAgent
            await self._notify_monitor_completion(request_id, server_id)

            # CORRECTION: Notifier le SystemLauncher
            if hasattr(self, 'system_launcher') and self.system_launcher:
                self.logger.info(
                    f"[IMPORTANT] Marquer la demande {request_id} comme complétée dans SystemLauncher (CMA)")
                self.system_launcher.mark_request_completed(request_id)
        else:
            self.logger.warning(f"Demande {request_id} marquée comme complétée mais non trouvée dans les listes")

    async def _check_dependencies_satisfied(self, completed_request_id):
        """
        Vérifie si la complétion d'une demande satisfait les dépendances d'autres demandes.
        """
        requests_to_move = []

        for request in self.waiting_dependencies:
            if completed_request_id in request.dependencies:
                request.dependencies.remove(completed_request_id)

                if not request.dependencies:
                    requests_to_move.append(request)
                    await self._notify_monitor_dependencies_satisfied(request.id)

        # Déplacer les demandes dont les dépendances sont satisfaites
        for request in requests_to_move:
            self.waiting_dependencies.remove(request)

            if request.client.client_type == ClientType.VIP:
                self.vip_queue.append(request)
                self.logger.info(f"Demande {request.id} déplacée vers la file VIP (dépendances satisfaites)")
            else:
                self.standard_queue.append(request)
                self.logger.info(f"Demande {request.id} déplacée vers la file standard (dépendances satisfaites)")

    async def _notify_monitor_completion(self, request_id, server_id):
        """
        Notifie le MonitorAgent de la complétion d'une demande.
        """
        if self.monitor_jid:
            try:
                msg = Message(to=str(self.monitor_jid))
                msg.set_metadata("type", "request_completed")
                msg.body = json.dumps({
                    "request_id": request_id,
                    "server_id": server_id,
                    "timestamp": time.time()
                })
                await self.send(msg)
            except Exception as e:
                self.logger.error(f"Erreur lors de la notification du MonitorAgent: {e}")

    async def _notify_monitor_dependencies_satisfied(self, request_id):
        """
        Notifie le MonitorAgent que toutes les dépendances d'une demande sont satisfaites.
        """
        if self.monitor_jid:
            try:
                msg = Message(to=str(self.monitor_jid))
                msg.set_metadata("type", "dependencies_satisfied")
                msg.body = json.dumps({
                    "request_id": request_id,
                    "timestamp": time.time()
                })
                await self.send(msg)
            except Exception as e:
                self.logger.error(f"Erreur lors de la notification du MonitorAgent: {e}")