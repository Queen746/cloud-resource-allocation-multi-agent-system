import asyncio
import time
import logging
import json
import random
from collections import deque

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template


class ResourceManagerAgent(Agent):
    """
    Agent responsable de l'allocation des ressources et de la gestion des dépendances
    entre les demandes.
    """

    def __init__(self, jid, password, load_balancer_jid, monitor_jid):
        """
        Initialise l'agent gestionnaire de ressources.

        Args:
            jid (str): JID de l'agent
            password (str): Mot de passe pour l'authentification
            load_balancer_jid (str): JID de l'agent d'équilibrage de charge
            monitor_jid (str): JID de l'agent de monitoring
        """
        super().__init__(jid, password)
        self.display_name = "ResourceManagerAgent"
        self.load_balancer_jid = load_balancer_jid
        self.monitor_jid = monitor_jid
        self.logger = logging.getLogger(f"{self.display_name}-{jid.split('@')[0]}")

        # Ressources disponibles par serveur
        self.servers = {
            "server-1": {"cpu": 100, "memory": 100},
            "server-2": {"cpu": 100, "memory": 100},
            "server-3": {"cpu": 100, "memory": 100},
            "server-4": {"cpu": 100, "memory": 100},
            "server-5": {"cpu": 100, "memory": 100}
        }

        # Pour suivre les demandes en cours de traitement
        self.active_requests = {}  # {request_id: {"server_id": server_id, "completion_time": timestamp}}

        # Pour suivre les demandes en attente de dépendances
        self.dependency_waiters = {}  # {dependent_id: [dependency_ids]}

        # Pour suivre les demandes qui sont des dépendances d'autres demandes
        self.dependencies_of = {}  # {dependency_id: [dependent_ids]}

        # Pour suivre les temps d'arrivée des demandes
        self.request_arrivals = {}

        # Référence au SystemLauncher, sera injectée par ce dernier
        self.system_launcher = None

    class RequestProcessingBehaviour(CyclicBehaviour):
        """
        Comportement pour traiter les demandes d'allocation de ressources.
        """

        async def run(self):
            # Attendre les messages de demande d'allocation
            msg = await self.receive(timeout=10)
            if msg:
                try:
                    content = json.loads(msg.body)

                    if msg.metadata.get("type") == "allocation_request":
                        request_id = content.get("request_id")
                        cpu_required = content.get("cpu_required")
                        memory_required = content.get("memory_required")
                        estimated_duration = content.get("estimated_duration")
                        dependencies = set(content.get("dependencies", []))
                        arrival_time = content.get("arrival_time", time.time())
                        client_type = content.get("client_type", "STANDARD")

                        # Enregistrer le temps d'arrivée
                        self.agent.request_arrivals[request_id] = arrival_time

                        # Au début du traitement d'une demande d'allocation
                        self.agent.logger.info(f"Réception d'une demande d'allocation pour {request_id}")

                        # Vérifier les dépendances
                        dependencies_satisfied = True
                        unsatisfied_deps = []

                        for dep_id in dependencies:
                            if dep_id not in self.agent.active_requests:
                                dependencies_satisfied = False
                                unsatisfied_deps.append(dep_id)

                        if not dependencies_satisfied:
                            # Enregistrer cette demande comme en attente de dépendances
                            self.agent.dependency_waiters[request_id] = unsatisfied_deps

                            # Enregistrer cette demande comme dépendante pour chaque dépendance
                            for dep_id in unsatisfied_deps:
                                if dep_id not in self.agent.dependencies_of:
                                    self.agent.dependencies_of[dep_id] = []
                                if request_id not in self.agent.dependencies_of[dep_id]:
                                    self.agent.dependencies_of[dep_id].append(request_id)

                            # Répondre au ClientManagerAgent
                            response = Message(to=str(msg.sender))
                            response.set_metadata("type", "allocation_response")
                            response.body = json.dumps({
                                "request_id": request_id,
                                "status": "pending",
                                "reason": "dependencies_not_satisfied",
                                "unsatisfied_deps": unsatisfied_deps
                            })
                            await self.send(response)

                            # Notifier le MonitorAgent
                            monitor_msg = Message(to=str(self.agent.monitor_jid))
                            monitor_msg.set_metadata("type", "dependency_wait")
                            monitor_msg.body = json.dumps({
                                "request_id": request_id,
                                "dependencies": unsatisfied_deps,
                                "timestamp": time.time()
                            })
                            await self.send(monitor_msg)

                            return  # Ne pas continuer le traitement

                        # Allouer les ressources
                        allocation_result = await self.agent.allocate_resources(
                            request_id, cpu_required, memory_required, estimated_duration,
                            dependencies, arrival_time, client_type
                        )

                        if allocation_result["success"]:
                            server_id = allocation_result["server_id"]
                            completion_time = allocation_result["completion_time"]

                            # Enregistrer cette demande comme active
                            self.agent.active_requests[request_id] = {
                                "server_id": server_id,
                                "completion_time": completion_time,
                                "cpu": cpu_required,
                                "memory": memory_required
                            }

                            # Vérifier si cette demande est une dépendance d'autres demandes
                            if request_id in self.agent.dependencies_of:
                                for dependent_id in self.agent.dependencies_of[request_id]:
                                    # Mettre à jour les dépendances non satisfaites
                                    if dependent_id in self.agent.dependency_waiters:
                                        if request_id in self.agent.dependency_waiters[dependent_id]:
                                            self.agent.dependency_waiters[dependent_id].remove(request_id)

                                        # Si toutes les dépendances sont satisfaites
                                        if not self.agent.dependency_waiters[dependent_id]:
                                            del self.agent.dependency_waiters[dependent_id]

                                            # Notifier le ClientManagerAgent
                                            notify_msg = Message(to=str(msg.sender))
                                            notify_msg.set_metadata("type", "dependencies_satisfied")
                                            notify_msg.body = json.dumps({
                                                "request_id": dependent_id,
                                                "timestamp": time.time()
                                            })
                                            await self.send(notify_msg)

                                            # Notifier le MonitorAgent
                                            monitor_msg = Message(to=str(self.agent.monitor_jid))
                                            monitor_msg.set_metadata("type", "dependencies_satisfied")
                                            monitor_msg.body = json.dumps({
                                                "request_id": dependent_id,
                                                "timestamp": time.time()
                                            })
                                            await self.send(monitor_msg)

                            # Répondre au ClientManagerAgent
                            response = Message(to=str(msg.sender))
                            response.set_metadata("type", "allocation_response")
                            response.body = json.dumps({
                                "request_id": request_id,
                                "status": "allocated",
                                "server_id": server_id,
                                "estimated_completion": completion_time
                            })
                            await self.send(response)

                            # Planifier la libération automatique des ressources après la durée estimée
                            self.agent.schedule_resource_release(
                                request_id, server_id, cpu_required, memory_required, estimated_duration)

                        else:
                            reason = allocation_result["reason"]

                            # Répondre au ClientManagerAgent
                            response = Message(to=str(msg.sender))
                            response.set_metadata("type", "allocation_response")
                            response.body = json.dumps({
                                "request_id": request_id,
                                "status": "rejected",
                                "reason": reason
                            })
                            await self.send(response)

                            # Notifier le MonitorAgent de la pénurie de ressources
                            monitor_msg = Message(to=str(self.agent.monitor_jid))
                            monitor_msg.set_metadata("type", "resource_shortage")
                            monitor_msg.body = json.dumps({
                                "request_id": request_id,
                                "server_id": allocation_result.get("server_id", "unknown"),
                                "cpu_required": cpu_required,
                                "memory_required": memory_required,
                                "timestamp": time.time()
                            })
                            await self.send(monitor_msg)

                except Exception as e:
                    self.agent.logger.error(f"Erreur lors du traitement de la demande: {e}")

            # Petit délai pour éviter de surcharger le CPU
            await asyncio.sleep(0.1)

    class RequestCompletionBehaviour(PeriodicBehaviour):
        """
        Comportement périodique pour vérifier les demandes terminées.
        """

        async def run(self):
            try:
                current_time = time.time()
                completed_requests = []

                # Chercher les demandes qui sont terminées
                for request_id, info in list(self.agent.active_requests.items()):
                    if current_time >= info["completion_time"]:
                        # Log très détaillé pour le débogage
                        self.agent.logger.info(f"[IMPORTANT] Demande {request_id} terminée (temps écoulé)")
                        completed_requests.append((request_id, info))

                # Traiter les demandes terminées
                for request_id, info in completed_requests:
                    server_id = info["server_id"]
                    cpu = info["cpu"]
                    memory = info["memory"]

                    # Libérer les ressources
                    self.agent.release_resources(server_id, cpu, memory)

                    # Retirer de la liste des demandes actives
                    if request_id in self.agent.active_requests:
                        del self.agent.active_requests[request_id]

                    # Notifier le ClientManagerAgent
                    self.agent.logger.info(f"[IMPORTANT] Notifier la complétion de {request_id} sur {server_id}")
                    client_msg = Message(to="client_manager@localhost")
                    client_msg.set_metadata("type", "request_completed")
                    client_msg.body = json.dumps({
                        "request_id": request_id,
                        "server_id": server_id,
                        "timestamp": current_time
                    })
                    await self.send(client_msg)

                    # Notifier le MonitorAgent
                    monitor_msg = Message(to=str(self.agent.monitor_jid))
                    monitor_msg.set_metadata("type", "request_completed")
                    monitor_msg.body = json.dumps({
                        "request_id": request_id,
                        "server_id": server_id,
                        "timestamp": current_time
                    })
                    await self.send(monitor_msg)

                    # SUPER IMPORTANT: Notifier directement le SystemLauncher
                    if hasattr(self.agent, 'system_launcher') and self.agent.system_launcher:
                        try:
                            self.agent.logger.info(
                                f"[CRITIQUE] Marquage de {request_id} comme complétée dans SystemLauncher (RMA)")
                            self.agent.system_launcher.mark_request_completed(request_id)
                        except Exception as e:
                            self.agent.logger.error(
                                f"[ERREUR CRITIQUE] Erreur lors du marquage de la demande {request_id} comme complétée: {e}")
            except Exception as e:
                self.agent.logger.error(f"[ERREUR CRITIQUE] Erreur dans RequestCompletionBehaviour: {e}")

    class DebugBehaviour(CyclicBehaviour):
        """
        Comportement pour déboguer les messages reçus.
        """

        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                self.agent.logger.info(f"Message reçu: {msg}")
                self.agent.logger.info(f"Type: {msg.metadata.get('type', 'inconnu')}")
                self.agent.logger.info(f"Contenu: {msg.body}")

            await asyncio.sleep(0.1)

    async def setup(self):
        """
        Initialise l'agent et ses comportements.
        """
        self.logger.info(f"Agent {self.display_name} starting...")

        # Comportement pour traiter les demandes d'allocation
        allocation_template = Template()
        allocation_template.set_metadata("type", "allocation_request")
        self.add_behaviour(self.RequestProcessingBehaviour(), allocation_template)

        # Comportement pour vérifier les demandes terminées (5 fois par seconde)
        self.add_behaviour(self.RequestCompletionBehaviour(period=0.2))

        # Comportement de debug (temporaire)
        debug_template = Template()
        self.add_behaviour(self.DebugBehaviour(), debug_template)

    async def allocate_resources(self, request_id, cpu_required, memory_required, estimated_duration, dependencies,
                                 arrival_time=None, client_type=None):
        """
        Tente d'allouer les ressources nécessaires pour une demande.

        Args:
            request_id (str): Identifiant de la demande
            cpu_required (float): Quantité de CPU requise
            memory_required (float): Quantité de mémoire requise
            estimated_duration (float): Durée estimée du traitement
            dependencies (set): Ensemble des identifiants des dépendances
            arrival_time (float, optional): Moment d'arrivée de la demande
            client_type (str, optional): Type de client (VIP ou STANDARD)

        Returns:
            dict: Résultat de l'allocation
        """
        # Vérifier d'abord avec le LoadBalancerAgent pour le choix du serveur
        lb_msg = Message(to=str(self.load_balancer_jid))
        lb_msg.set_metadata("type", "server_selection")
        lb_msg.body = json.dumps({
            "request_id": request_id,
            "cpu_required": cpu_required,
            "memory_required": memory_required
        })

        # Envoyer et attendre la réponse
        response = None
        try:
            # Créer un comportement OneShot pour envoyer le message et attendre la réponse
            class AskLoadBalancerBehaviour(OneShotBehaviour):
                async def run(self):
                    nonlocal response
                    try:
                        await self.send(lb_msg)
                        response_msg = await self.receive(timeout=5)
                        if response_msg:
                            response = json.loads(response_msg.body)
                    except Exception as e:
                        self.agent.logger.error(f"Erreur lors de la communication avec LoadBalancer: {e}")

            # Ajouter le comportement et attendre son exécution
            behaviour = AskLoadBalancerBehaviour()
            self.add_behaviour(behaviour)
            await asyncio.sleep(1)  # Attendre un peu que le comportement s'exécute
        except Exception as e:
            self.logger.error(f"Erreur lors de la communication avec LoadBalancer: {e}")

        # Si le LoadBalancerAgent a répondu
        server_id = None
        if response and "selected_server" in response:
            server_id = response["selected_server"]
            self.logger.info(f"LoadBalancer a sélectionné {server_id} pour {request_id}")
        else:
            # Choisir le serveur avec le plus de ressources disponibles
            best_server = None
            best_fit = -1

            for srv_id, resources in self.servers.items():
                if resources["cpu"] >= cpu_required and resources["memory"] >= memory_required:
                    # Utiliser un fit basé sur l'utilisation la plus équilibrée
                    fit = min(resources["cpu"] / cpu_required, resources["memory"] / memory_required)
                    if fit > best_fit:
                        best_fit = fit
                        best_server = srv_id

            server_id = best_server
            if not server_id:
                self.logger.warning(f"Aucun serveur approprié pour {request_id}")
                return {
                    "success": False,
                    "reason": "insufficient_resources",
                    "server_id": "unknown"
                }

        # Allouer les ressources sur le serveur choisi
        if server_id in self.servers:
            if (self.servers[server_id]["cpu"] >= cpu_required and
                    self.servers[server_id]["memory"] >= memory_required):

                # Réserver les ressources
                self.servers[server_id]["cpu"] -= cpu_required
                self.servers[server_id]["memory"] -= memory_required

                # Calculer la durée estimée de complétion
                completion_time = time.time() + estimated_duration

                self.logger.info(
                    f"Ressources restantes - CPU: {self.servers[server_id]['cpu']}, Mémoire: {self.servers[server_id]['memory']}")
                self.logger.info(f"Allocation réussie pour {request_id} sur {server_id}")

                # Si on a le temps d'arrivée, envoyer une notification au MonitorAgent pour le temps d'attente
                monitor_msg = Message(to=str(self.monitor_jid))
                monitor_msg.set_metadata("type", "allocation_event")

                allocation_data = {
                    "request_id": request_id,
                    "server_id": server_id,
                    "cpu": cpu_required,
                    "memory": memory_required,
                    "timestamp": time.time(),
                    "start_time": time.time()  # Le temps de début de traitement est maintenant
                }

                # Ajouter le temps d'arrivée s'il est disponible
                if arrival_time:
                    allocation_data["arrival_time"] = arrival_time

                # Ajouter le type client s'il est disponible
                if client_type:
                    allocation_data["client_type"] = client_type

                monitor_msg.body = json.dumps(allocation_data)

                # Créer un comportement OneShot pour envoyer le message
                class NotifyMonitorBehaviour(OneShotBehaviour):
                    async def run(self):
                        await self.send(monitor_msg)

                self.add_behaviour(NotifyMonitorBehaviour())

                return {
                    "success": True,
                    "server_id": server_id,
                    "completion_time": completion_time
                }
            else:
                self.logger.warning(
                    f"Ressources insuffisantes sur {server_id} pour {request_id} - Disponible: CPU={self.servers[server_id]['cpu']}, Mem={self.servers[server_id]['memory']} - Requis: CPU={cpu_required}, Mem={memory_required}")
                return {
                    "success": False,
                    "reason": f"insufficient_resources_on_{server_id}",
                    "server_id": server_id
                }
        else:
            self.logger.error(f"Serveur inconnu: {server_id}")
            return {
                "success": False,
                "reason": "unknown_server",
                "server_id": server_id
            }

    def release_resources(self, server_id, cpu, memory):
        """
        Libère les ressources sur un serveur.

        Args:
            server_id (str): Identifiant du serveur
            cpu (float): Quantité de CPU à libérer
            memory (float): Quantité de mémoire à libérer
        """
        if server_id in self.servers:
            self.servers[server_id]["cpu"] += cpu
            self.servers[server_id]["memory"] += memory
            self.logger.info(
                f"Ressources libérées sur {server_id} - CPU: {cpu}, Mémoire: {memory} - Disponible: CPU={self.servers[server_id]['cpu']}, Mem={self.servers[server_id]['memory']}")
        else:
            self.logger.error(f"Tentative de libération sur serveur inconnu: {server_id}")

    def schedule_resource_release(self, request_id, server_id, cpu, memory, duration):
        """
        Planifie la libération automatique des ressources après un certain délai.

        Args:
            request_id (str): Identifiant de la demande
            server_id (str): Identifiant du serveur
            cpu (float): Quantité de CPU à libérer
            memory (float): Quantité de mémoire à libérer
            duration (float): Délai en secondes avant la libération
        """
        # Pour les tests, réduire le temps d'exécution
        # Si c'est dans un contexte de test, réduire drastiquement la durée
        if hasattr(self, 'system_launcher') and self.system_launcher:
            test_duration = min(duration, 5.0)  # Max 5 secondes pour les tests
            self.logger.info(f"[TEST] Durée modifiée pour {request_id}: {duration}s -> {test_duration}s")
            duration = test_duration

        # La complétion sera détectée par RequestCompletionBehaviour
        # Ajouter la demande avec sa date de complétion
        completion_time = time.time() + duration

        # Vérifier si la demande est déjà active
        if request_id in self.active_requests:
            self.logger.warning(f"La demande {request_id} est déjà active. Mise à jour des informations.")

        # Enregistrer les informations de la demande pour la libération future
        self.active_requests[request_id] = {
            "server_id": server_id,
            "completion_time": completion_time,
            "cpu": cpu,
            "memory": memory
        }

        self.logger.info(
            f"[IMPORTANT] Libération planifiée pour {request_id} sur {server_id} à {completion_time} (dans {duration}s)")

    def on_allocation_failed(self, request_id, reason):
        """
        Appelé lorsqu'une allocation échoue.

        Args:
            request_id (str): Identifiant de la demande
            reason (str): Raison de l'échec
        """
        self.logger.warning(f"Allocation échouée pour {request_id}: {reason}")

        # Notifier le SystemLauncher
        if hasattr(self, 'system_launcher') and self.system_launcher:
            self.system_launcher.mark_request_failed(request_id, reason)