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
    Agent responsable de l'allocation des ressources et de la gestion des dépendances.
    """

    def __init__(self, jid, password, load_balancer_jid, monitor_jid):
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
        self.active_requests = {}

        # Pour suivre les demandes en attente de dépendances
        self.dependency_waiters = {}
        self.dependencies_of = {}

        # Pour suivre les temps d'arrivée des demandes
        self.request_arrivals = {}

        # Référence au SystemLauncher, sera injectée par ce dernier
        self.system_launcher = None

        # Variables pour les optimisations
        self.in_recovery_mode = False
        self.virtual_capacity_multiplier = 1.0

    class RequestProcessingBehaviour(CyclicBehaviour):
        """
        Comportement pour traiter les demandes d'allocation de ressources.
        """

        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                try:
                    content = json.loads(msg.body)

                    if msg.metadata.get("type") == "allocation_request":
                        await self.agent._handle_allocation_request(content, msg.sender)

                except Exception as e:
                    self.agent.logger.error(f"Erreur lors du traitement de la demande: {e}")

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
                        self.agent.logger.info(f"[IMPORTANT] Demande {request_id} terminée (temps écoulé)")
                        completed_requests.append((request_id, info))

                # Traiter les demandes terminées
                for request_id, info in completed_requests:
                    await self.agent.complete_request(request_id, info, current_time)

            except Exception as e:
                self.agent.logger.error(f"[ERREUR CRITIQUE] Erreur dans RequestCompletionBehaviour: {e}")

    class PreemptiveReleaseBehaviour(PeriodicBehaviour):
        """
        Comportement pour libérer préventivement des ressources en cas de surcharge.
        """

        async def run(self):
            # Vérifier s'il y a une surcharge
            server_overload = False
            for server_id, resources in self.agent.servers.items():
                if resources["cpu"] < 10 or resources["memory"] < 10:
                    server_overload = True
                    break

            if server_overload:
                self.agent.logger.warning("Surcharge détectée, activation de la libération préventive")

                current_time = time.time()
                almost_done_requests = []

                for request_id, info in list(self.agent.active_requests.items()):
                    completion_time = info["completion_time"]
                    start_time = info.get("start_time", current_time - 10)
                    total_duration = completion_time - start_time
                    elapsed_time = current_time - start_time

                    if total_duration > 0 and (elapsed_time / total_duration) > 0.9:
                        almost_done_requests.append((request_id, info))

                # Libérer ces ressources en priorité
                for request_id, info in almost_done_requests:
                    self.agent.logger.info(f"Libération préventive pour {request_id}")
                    await self.agent.complete_request(request_id, info, current_time)

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

        # Comportement de libération préventive (toutes les 5 secondes)
        self.add_behaviour(self.PreemptiveReleaseBehaviour(period=5))

    async def _handle_allocation_request(self, content, sender):
        """
        Traite une demande d'allocation de ressources.
        """
        request_id = content.get("request_id")
        cpu_required = content.get("cpu_required")
        memory_required = content.get("memory_required")
        estimated_duration = content.get("estimated_duration")
        dependencies = set(content.get("dependencies", []))
        arrival_time = content.get("arrival_time", time.time())
        client_type = content.get("client_type", "STANDARD")

        # Enregistrer le temps d'arrivée
        self.request_arrivals[request_id] = arrival_time

        self.logger.info(f"Réception d'une demande d'allocation pour {request_id}")

        # Vérifier les dépendances
        dependencies_satisfied = True
        unsatisfied_deps = []

        for dep_id in dependencies:
            if dep_id not in self.active_requests:
                dependencies_satisfied = False
                unsatisfied_deps.append(dep_id)

        if not dependencies_satisfied:
            # Enregistrer cette demande comme en attente de dépendances
            self.dependency_waiters[request_id] = unsatisfied_deps

            # Enregistrer cette demande comme dépendante pour chaque dépendance
            for dep_id in unsatisfied_deps:
                if dep_id not in self.dependencies_of:
                    self.dependencies_of[dep_id] = []
                if request_id not in self.dependencies_of[dep_id]:
                    self.dependencies_of[dep_id].append(request_id)

            # Répondre au ClientManagerAgent
            response = Message(to=str(sender))
            response.set_metadata("type", "allocation_response")
            response.body = json.dumps({
                "request_id": request_id,
                "status": "pending",
                "reason": "dependencies_not_satisfied",
                "unsatisfied_deps": unsatisfied_deps
            })
            await self.send(response)

            return

        # Allouer les ressources
        allocation_result = await self.allocate_resources(
            request_id, cpu_required, memory_required, estimated_duration,
            dependencies, arrival_time, client_type
        )

        if allocation_result["success"]:
            server_id = allocation_result["server_id"]
            completion_time = allocation_result["completion_time"]

            # Enregistrer cette demande comme active
            self.active_requests[request_id] = {
                "server_id": server_id,
                "completion_time": completion_time,
                "start_time": time.time(),
                "cpu": cpu_required,
                "memory": memory_required
            }

            # Vérifier si cette demande est une dépendance d'autres demandes
            if request_id in self.dependencies_of:
                for dependent_id in self.dependencies_of[request_id]:
                    if dependent_id in self.dependency_waiters:
                        if request_id in self.dependency_waiters[dependent_id]:
                            self.dependency_waiters[dependent_id].remove(request_id)

                        if not self.dependency_waiters[dependent_id]:
                            del self.dependency_waiters[dependent_id]

                            # Notifier le ClientManagerAgent
                            notify_msg = Message(to=str(sender))
                            notify_msg.set_metadata("type", "dependencies_satisfied")
                            notify_msg.body = json.dumps({
                                "request_id": dependent_id,
                                "timestamp": time.time()
                            })
                            await self.send(notify_msg)

            # Répondre au ClientManagerAgent
            response = Message(to=str(sender))
            response.set_metadata("type", "allocation_response")
            response.body = json.dumps({
                "request_id": request_id,
                "status": "allocated",
                "server_id": server_id,
                "estimated_completion": completion_time
            })
            await self.send(response)

            # Planifier la libération automatique des ressources
            self.schedule_resource_release(
                request_id, server_id, cpu_required, memory_required, estimated_duration)

        else:
            reason = allocation_result["reason"]

            # Répondre au ClientManagerAgent
            response = Message(to=str(sender))
            response.set_metadata("type", "allocation_response")
            response.body = json.dumps({
                "request_id": request_id,
                "status": "rejected",
                "reason": reason
            })
            await self.send(response)

    async def complete_request(self, request_id, info, current_time):
        """
        Complète une demande (soit normalement, soit préventivement).
        """
        server_id = info["server_id"]
        cpu = info["cpu"]
        memory = info["memory"]

        # Libérer les ressources
        self.release_resources(server_id, cpu, memory)

        # Retirer de la liste des demandes actives
        if request_id in self.active_requests:
            del self.active_requests[request_id]

        # Notifier le ClientManagerAgent
        self.logger.info(f"[IMPORTANT] Notifier la complétion de {request_id} sur {server_id}")
        client_msg = Message(to="client_manager@localhost")
        client_msg.set_metadata("type", "request_completed")
        client_msg.body = json.dumps({
            "request_id": request_id,
            "server_id": server_id,
            "timestamp": current_time
        })
        await self.send(client_msg)

        # Notifier le MonitorAgent
        monitor_msg = Message(to=str(self.monitor_jid))
        monitor_msg.set_metadata("type", "request_completed")
        monitor_msg.body = json.dumps({
            "request_id": request_id,
            "server_id": server_id,
            "timestamp": current_time
        })
        await self.send(monitor_msg)

        # SUPER IMPORTANT: Notifier directement le SystemLauncher
        if hasattr(self, 'system_launcher') and self.system_launcher:
            try:
                self.logger.info(f"[CRITIQUE] Marquage de {request_id} comme complétée dans SystemLauncher (RMA)")
                self.system_launcher.mark_request_completed(request_id)
            except Exception as e:
                self.logger.error(
                    f"[ERREUR CRITIQUE] Erreur lors du marquage de la demande {request_id} comme complétée: {e}")

    async def allocate_resources(self, request_id, cpu_required, memory_required, estimated_duration, dependencies,
                                 arrival_time=None, client_type=None):
        """
        Tente d'allouer les ressources nécessaires pour une demande.
        """
        # Choisir le serveur avec le plus de ressources disponibles
        best_server = None
        best_fit = -1

        for srv_id, resources in self.servers.items():
            # Appliquer le multiplicateur de capacité virtuelle si en mode récupération
            effective_cpu = resources["cpu"] * self.virtual_capacity_multiplier
            effective_memory = resources["memory"] * self.virtual_capacity_multiplier

            if effective_cpu >= cpu_required and effective_memory >= memory_required:
                fit = min(effective_cpu / cpu_required, effective_memory / memory_required)
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

                # Adapter la durée en fonction de la charge système
                system_load = self.calculate_system_load()
                adjusted_duration = estimated_duration

                if system_load > 0.8:  # Si la charge système est > 80%
                    adjusted_duration = max(1.0, estimated_duration * 0.7)  # Réduire de 30%
                    self.logger.info(
                        f"Charge élevée, durée ajustée pour {request_id}: {estimated_duration}s -> {adjusted_duration}s")

                completion_time = time.time() + adjusted_duration

                self.logger.info(f"Allocation réussie pour {request_id} sur {server_id}")

                return {
                    "success": True,
                    "server_id": server_id,
                    "completion_time": completion_time
                }
            else:
                self.logger.warning(f"Ressources insuffisantes sur {server_id} pour {request_id}")
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
        """
        if server_id in self.servers:
            self.servers[server_id]["cpu"] += cpu
            self.servers[server_id]["memory"] += memory
            self.logger.info(f"Ressources libérées sur {server_id} - CPU: {cpu}, Mémoire: {memory}")
        else:
            self.logger.error(f"Tentative de libération sur serveur inconnu: {server_id}")

    def schedule_resource_release(self, request_id, server_id, cpu, memory, duration):
        """
        Planifie la libération automatique des ressources après un certain délai.
        """
        # Pour les tests, réduire le temps d'exécution
        if hasattr(self, 'system_launcher') and self.system_launcher:
            test_duration = min(duration, 5.0)  # Max 5 secondes pour les tests
            self.logger.info(f"[TEST] Durée modifiée pour {request_id}: {duration}s -> {test_duration}s")
            duration = test_duration

        # Adapter la durée en fonction de la charge système
        system_load = self.calculate_system_load()

        if system_load > 0.8:  # Si la charge système est > 80%
            adjusted_duration = max(1.0, duration * 0.7)  # Réduire de 30%
            self.logger.info(f"Charge élevée, durée ajustée pour {request_id}: {duration}s -> {adjusted_duration}s")
            duration = adjusted_duration

        start_time = time.time()
        completion_time = start_time + duration

        # Enregistrer les informations de la demande pour la libération future
        self.active_requests[request_id] = {
            "server_id": server_id,
            "completion_time": completion_time,
            "start_time": start_time,
            "cpu": cpu,
            "memory": memory
        }

        self.logger.info(f"[IMPORTANT] Libération planifiée pour {request_id} sur {server_id} dans {duration}s")

    def calculate_system_load(self):
        """
        Calcule la charge système actuelle (0.0 à 1.0).
        """
        total_capacity = 0
        total_used = 0

        base_capacity = {"cpu": 100, "memory": 100}

        for server_id in self.servers.keys():
            total_capacity += base_capacity["cpu"] + base_capacity["memory"]
            used_cpu = base_capacity["cpu"] - self.servers[server_id]["cpu"]
            used_memory = base_capacity["memory"] - self.servers[server_id]["memory"]
            total_used += used_cpu + used_memory

        if total_capacity == 0:
            return 0.0

        return total_used / total_capacity

    async def increase_virtual_capacity(self, multiplier):
        """
        Augmente temporairement la capacité virtuelle du système.
        """
        self.virtual_capacity_multiplier = multiplier
        self.logger.info(f"Capacité virtuelle augmentée à {multiplier}x")

    async def reset_virtual_capacity(self):
        """
        Remet la capacité à sa valeur normale.
        """
        self.virtual_capacity_multiplier = 1.0
        self.logger.info("Capacité virtuelle remise à la normale")

    def optimize_dependency_scheduling(self):
        """
        Optimise la planification des demandes avec dépendances.
        """
        # Construire un graphe de dépendances complet
        dependency_graph = {}

        for dependent_id, dependencies in self.dependency_waiters.items():
            dependency_graph[dependent_id] = set(dependencies)

        # Ajouter les dépendances inversées
        reverse_dependencies = {}
        for dependent_id, dependencies in dependency_graph.items():
            for dep_id in dependencies:
                if dep_id not in reverse_dependencies:
                    reverse_dependencies[dep_id] = set()
                reverse_dependencies[dep_id].add(dependent_id)

        # Identifier les demandes critiques
        critical_requests = []
        for req_id, dependents in reverse_dependencies.items():
            if len(dependents) > 2:
                critical_requests.append((req_id, len(dependents)))

        # Trier par nombre de dépendants
        critical_requests.sort(key=lambda x: x[1], reverse=True)

        # Prioriser ces demandes critiques
        for req_id, _ in critical_requests:
            if req_id in self.active_requests:
                info = self.active_requests[req_id]
                remaining_time = info["completion_time"] - time.time()

                if remaining_time > 1.0:
                    # Accélérer de 30%
                    new_completion_time = time.time() + (0.7 * remaining_time)
                    self.active_requests[req_id]["completion_time"] = new_completion_time
                    self.logger.info(f"Accélération de la demande critique {req_id}")

    def on_allocation_failed(self, request_id, reason):
        """
        Appelé lorsqu'une allocation échoue.
        """
        self.logger.warning(f"Allocation échouée pour {request_id}: {reason}")

        # Notifier le SystemLauncher
        if hasattr(self, 'system_launcher') and self.system_launcher:
            self.system_launcher.mark_request_failed(request_id, reason)