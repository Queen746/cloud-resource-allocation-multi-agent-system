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

import system_launcher
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

        Args:
            jid (str): JID de l'agent
            password (str): Mot de passe pour l'authentification
            resource_manager_jid (str): JID de l'agent gestionnaire de ressources
            monitor_jid (str): JID de l'agent de monitoring
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
        self.system_launcher = system_launcher  # Ajouter cette ligne

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
                        request_id = content.get("id")
                        client = content.get("client")
                        cpu_required = content.get("cpu_required")
                        memory_required = content.get("memory_required")
                        estimated_duration = content.get("estimated_duration")
                        dependencies = set(content.get("dependencies", []))

                        self.agent.logger.info(
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
                        self.agent.add_request_to_queue(request)

                        # Notifier le MonitorAgent
                        monitor_msg = Message(to=str(self.agent.monitor_jid))
                        monitor_msg.set_metadata("type", "new_request")
                        monitor_msg.body = json.dumps({
                            "request_id": request_id,
                            "client_type": client["client_type"],
                            "timestamp": time.time(),
                            "arrival_time": request.arrival_time
                        })
                        await self.send(monitor_msg)

                    elif msg.metadata.get("type") == "allocation_response":
                        request_id = content.get("request_id")
                        status = content.get("status")

                        if status == "allocated":
                            server_id = content.get("server_id")
                            estimated_completion = content.get("estimated_completion")

                            self.agent.logger.info(
                                f"Demande {request_id} allouée sur {server_id}, complétion estimée: {datetime.fromtimestamp(estimated_completion).strftime('%H:%M:%S')}")

                            # Notifier le client (simulé)
                            self.agent.logger.info(
                                f"Notification au client: Demande {request_id} en cours de traitement sur {server_id}")

                        elif status == "rejected":
                            reason = content.get("reason")

                            self.agent.logger.warning(f"Demande {request_id} rejetée: {reason}")

                            # Notifier le client (simulé)
                            self.agent.logger.info(f"Notification au client: Demande {request_id} rejetée ({reason})")

                        elif status == "pending":
                            reason = content.get("reason")

                            self.agent.logger.info(f"Demande {request_id} en attente: {reason}")

                            # Si la demande est en attente, la remettre dans la file mais avec un délai
                            # Pour éviter de retenter immédiatement
                            if reason == "dependencies_not_satisfied":
                                self.agent.logger.info(
                                    f"Remise en file d'attente de {request_id} (dépendances non satisfaites)")

                    elif msg.metadata.get("type") == "dependencies_satisfied":
                        request_id = content.get("request_id")

                        self.agent.logger.info(f"Dépendances satisfaites pour {request_id}, prêt à être traité")

                        # Notifier le client (simulé)
                        self.agent.logger.info(f"Notification au client: Dépendances satisfaites pour {request_id}")

                    elif msg.metadata.get("type") == "request_completed":
                        request_id = content.get("request_id")
                        server_id = content.get("server_id")

                        self.agent.logger.info(f"Demande {request_id} complétée sur {server_id}")

                        # Notifier le client (simulé)
                        self.agent.logger.info(f"Notification au client: Demande {request_id} complétée")

                except Exception as e:
                    self.agent.logger.error(f"Erreur lors du traitement du message: {e}")

            # Petit délai pour éviter de surcharger le CPU
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

    def add_request_to_queue(self, request):
        """
        Ajoute une demande à la file d'attente appropriée.

        Args:
            request (ResourceRequest): Demande à ajouter
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

        Args:
            request (ResourceRequest): Demande à retirer
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
    async def _update_queue_sizes(self):
        """
        Met à jour les tailles des files d'attente et notifie le MonitorAgent.
        """
        await self.notify_monitor_queue_update()

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

        Args:
            request_data (dict): Données de la demande de simulation
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

            # Notifier le MonitorAgent via comportement OneShot
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

    def process_request(self, request):
        """
        Traite une demande et met à jour les files d'attente.

        Args:
            request (ResourceRequest): La demande à traiter
        """
        # Retirer la demande de la file d'attente appropriée
        self.remove_request_from_queue(request)

        # Ajouter comportement pour notifier le MonitorAgent
        class NotifyQueueUpdateBehaviour(OneShotBehaviour):
            async def run(self):
                await self.agent.notify_monitor_queue_update()

    async def on_request_completed(self, request_id, server_id):
        """
        Appelé lorsqu'une demande est complétée par le ResourceManagerAgent.

        Args:
            request_id (str): Identifiant de la demande
            server_id (str): Identifiant du serveur où la demande a été traitée
        """
        self.logger.info(f"Demande {request_id} complétée sur {server_id}")

        # Trouver la demande dans les listes de demandes actives/en attente
        request_found = False
        found_request = None

        # Chercher d'abord dans les demandes en cours de traitement
        for request in list(self.processing_requests):
            if request.id == request_id:
                found_request = request
                self.processing_requests.remove(request)
                request_found = True
                break

        # Si non trouvée, chercher dans les files d'attente VIP et standard
        if not request_found:
            for queue in [self.vip_queue, self.standard_queue]:
                for request in list(queue):
                    if request.id == request_id:
                        found_request = request
                        queue.remove(request)
                        request_found = True
                        break
                if request_found:
                    break

        # Si non trouvée, chercher dans les demandes en attente de dépendances
        if not request_found:
            for request in list(self.waiting_dependencies):
                if request.id == request_id:
                    found_request = request
                    self.waiting_dependencies.remove(request)
                    request_found = True
                    break

        if request_found and found_request:
            # Mettre à jour les statistiques
            self.completed_requests += 1

            # Notifier le client (simulation)
            self.logger.info(f"Client {found_request.client.id} notifié de la complétion de la demande {request_id}")

            # Vérifier si cette demande est une dépendance pour d'autres demandes
            # et les déplacer vers la file d'attente appropriée si toutes leurs dépendances sont satisfaites
            await self._check_dependencies_satisfied(request_id)

            # Mettre à jour les tailles des files d'attente
            await self._update_queue_sizes()

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

        Args:
            completed_request_id (str): Identifiant de la demande complétée
        """
        # Parcourir les demandes en attente de dépendances
        requests_to_move = []

        for request in self.waiting_dependencies:
            if completed_request_id in request.dependencies:
                # Retirer la dépendance
                request.dependencies.remove(completed_request_id)

                # Si toutes les dépendances sont satisfaites, déplacer vers la file d'attente
                if not request.dependencies:
                    requests_to_move.append(request)

                    # Notifier le MonitorAgent que les dépendances sont satisfaites
                    await self._notify_monitor_dependencies_satisfied(request.id)

        # Déplacer les demandes dont les dépendances sont satisfaites vers la file appropriée
        for request in requests_to_move:
            self.waiting_dependencies.remove(request)

            # Déterminer la file d'attente appropriée
            if request.client.is_vip():
                self.vip_queue.append(request)
                self.logger.info(f"Demande {request.id} déplacée vers la file VIP (dépendances satisfaites)")
            else:
                self.standard_queue.append(request)
                self.logger.info(f"Demande {request.id} déplacée vers la file standard (dépendances satisfaites)")

    async def _notify_monitor_completion(self, request_id, server_id):
        """
        Notifie le MonitorAgent de la complétion d'une demande.

        Args:
            request_id (str): Identifiant de la demande complétée
            server_id (str): Identifiant du serveur où la demande a été traitée
        """
        if self.monitor_jid:
            try:
                # Créer le message
                msg = Message(to=str(self.monitor_jid))
                msg.set_metadata("type", "request_completed")

                # Préparer le contenu
                content = {
                    "request_id": request_id,
                    "server_id": server_id,
                    "timestamp": time.time()
                }

                msg.body = json.dumps(content)

                # Envoyer le message
                await self.send(msg)
            except Exception as e:
                self.logger.error(f"Erreur lors de la notification du MonitorAgent: {e}")

    async def _notify_monitor_dependencies_satisfied(self, request_id):
        """
        Notifie le MonitorAgent que toutes les dépendances d'une demande sont satisfaites.

        Args:
            request_id (str): Identifiant de la demande dont les dépendances sont satisfaites
        """
        if self.monitor_jid:
            try:
                # Créer le message
                msg = Message(to=str(self.monitor_jid))
                msg.set_metadata("type", "dependencies_satisfied")

                # Préparer le contenu
                content = {
                    "request_id": request_id,
                    "timestamp": time.time()
                }

                msg.body = json.dumps(content)

                # Envoyer le message
                await self.send(msg)
            except Exception as e:
                self.logger.error(f"Erreur lors de la notification du MonitorAgent: {e}")

