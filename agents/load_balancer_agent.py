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


class LoadBalancerAgent(Agent):
    """
    Agent responsable de l'équilibrage de charge entre les serveurs.
    """

    def __init__(self, jid, password, monitor_jid):
        super().__init__(jid, password)
        self.display_name = "LoadBalancerAgent"
        self.monitor_jid = monitor_jid
        self.logger = logging.getLogger(f"{self.display_name}-{jid.split('@')[0]}")

        # Charges actuelles des serveurs
        self.server_loads = {
            "server-1": {"cpu": 0.0, "memory": 0.0},
            "server-2": {"cpu": 0.0, "memory": 0.0},
            "server-3": {"cpu": 0.0, "memory": 0.0},
            "server-4": {"cpu": 0.0, "memory": 0.0},
            "server-5": {"cpu": 0.0, "memory": 0.0}
        }

        # Capacités des serveurs
        self.server_capacities = {
            "server-1": {"cpu": 100.0, "memory": 100.0},
            "server-2": {"cpu": 100.0, "memory": 100.0},
            "server-3": {"cpu": 100.0, "memory": 100.0},
            "server-4": {"cpu": 100.0, "memory": 100.0},
            "server-5": {"cpu": 100.0, "memory": 100.0}
        }

        # Historique des allocations par serveur
        self.allocation_history = {
            "server-1": deque(maxlen=100),
            "server-2": deque(maxlen=100),
            "server-3": deque(maxlen=100),
            "server-4": deque(maxlen=100),
            "server-5": deque(maxlen=100)
        }

        # Stratégie d'équilibrage actuelle
        self.strategy = "least_loaded"
        self.round_robin_index = 0
        self.server_weights = {f"server-{i}": 1.0 for i in range(1, 6)}

    class ServerSelectionBehaviour(CyclicBehaviour):
        """
        Comportement pour sélectionner un serveur pour une nouvelle demande.
        """

        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                try:
                    content = json.loads(msg.body)

                    if msg.metadata.get("type") == "server_selection":
                        request_id = content.get("request_id")
                        cpu_required = content.get("cpu_required")
                        memory_required = content.get("memory_required")

                        self.agent.logger.info(f"Sélection de serveur pour {request_id}")

                        # Sélectionner le serveur selon la stratégie actuelle
                        selected_server = self.agent.select_server(cpu_required, memory_required, request_id)

                        if selected_server:
                            self.agent.logger.info(f"Serveur sélectionné pour {request_id}: {selected_server}")

                            # Mettre à jour les charges
                            self.agent.update_server_load(selected_server, cpu_required, memory_required,
                                                          is_addition=True)

                            # Enregistrer dans l'historique
                            self.agent.allocation_history[selected_server].append({
                                "timestamp": time.time(),
                                "request_id": request_id,
                                "cpu": cpu_required,
                                "memory": memory_required
                            })

                            # Répondre avec le serveur sélectionné
                            response = Message(to=str(msg.sender))
                            response.set_metadata("type", "server_selection_response")
                            response.body = json.dumps({
                                "request_id": request_id,
                                "selected_server": selected_server
                            })
                            await self.send(response)
                        else:
                            self.agent.logger.warning(f"Aucun serveur disponible pour {request_id}")

                            # Répondre qu'aucun serveur n'est disponible
                            response = Message(to=str(msg.sender))
                            response.set_metadata("type", "server_selection_response")
                            response.body = json.dumps({
                                "request_id": request_id,
                                "selected_server": None,
                                "error": "no_server_available"
                            })
                            await self.send(response)

                except Exception as e:
                    self.agent.logger.error(f"Erreur lors de la sélection de serveur: {e}")

            await asyncio.sleep(0.1)

    class LoadMonitoringBehaviour(PeriodicBehaviour):
        """
        Comportement périodique pour surveiller et équilibrer les charges des serveurs.
        """

        async def run(self):
            try:
                imbalance_detected = self.agent.check_load_imbalance()
                if imbalance_detected:
                    self.agent.logger.info("Déséquilibre de charge détecté, tentative de rééquilibrage...")
                    await self.agent.rebalance_load()
            except Exception as e:
                self.agent.logger.error(f"Erreur lors de la surveillance des charges: {e}")

    async def setup(self):
        """
        Initialise l'agent et ses comportements.
        """
        self.logger.info(f"Agent {self.display_name} starting...")

        # Comportement pour la sélection de serveur
        selection_template = Template()
        selection_template.set_metadata("type", "server_selection")
        self.add_behaviour(self.ServerSelectionBehaviour(), selection_template)

        # Comportement pour la surveillance des charges (toutes les 30 secondes)
        self.add_behaviour(self.LoadMonitoringBehaviour(period=30))

    def select_server(self, cpu_required, memory_required, request_id=None):
        """
        Version optimisée de la sélection de serveur.
        """
        if request_id:
            self.logger.info(f"Sélection de serveur pour demande {request_id}")

        # Filtrer les serveurs avec assez de capacité
        available_servers = []
        for server_id, capacity in self.server_capacities.items():
            current_load = self.server_loads[server_id]
            available_cpu = capacity["cpu"] - current_load["cpu"]
            available_memory = capacity["memory"] - current_load["memory"]

            if available_cpu >= cpu_required and available_memory >= memory_required:
                placement_score = self.calculate_placement_score(server_id, cpu_required, memory_required)
                available_servers.append((server_id, placement_score))

        if not available_servers:
            self.logger.warning(
                f"Aucun serveur avec assez de capacité pour CPU={cpu_required}, Mémoire={memory_required}")
            return None

        # Trier les serveurs par score (le plus élevé d'abord)
        available_servers.sort(key=lambda x: x[1], reverse=True)

        # Prendre le meilleur serveur
        selected_server = available_servers[0][0]

        if selected_server and request_id:
            self.logger.info(
                f"Serveur {selected_server} sélectionné pour la demande {request_id} (score: {available_servers[0][1]:.2f})")

        return selected_server

    def calculate_placement_score(self, server_id, cpu_required, memory_required):
        """
        Calcule un score de placement pour une demande sur un serveur donné.
        """
        capacity = self.server_capacities[server_id]
        current_load = self.server_loads[server_id]

        # Ressources disponibles
        available_cpu = capacity["cpu"] - current_load["cpu"]
        available_memory = capacity["memory"] - current_load["memory"]

        # Ratio d'utilisation actuel (0-1)
        cpu_usage_ratio = current_load["cpu"] / capacity["cpu"] if capacity["cpu"] > 0 else 1.0
        memory_usage_ratio = current_load["memory"] / capacity["memory"] if capacity["memory"] > 0 else 1.0

        # Facteur de convenance
        cpu_fit = 1 - abs((cpu_required / available_cpu) - 0.5) * 2 if available_cpu > 0 else 0
        memory_fit = 1 - abs((memory_required / available_memory) - 0.5) * 2 if available_memory > 0 else 0

        # Facteur de répartition
        avg_cpu_usage = sum(self.server_loads[srv]["cpu"] / self.server_capacities[srv]["cpu"]
                            for srv in self.server_loads if self.server_capacities[srv]["cpu"] > 0) / len(self.server_loads)

        balance_factor = 1 - abs(cpu_usage_ratio - avg_cpu_usage)

        # Score final
        score = (0.4 * cpu_fit) + (0.4 * memory_fit) + (0.2 * balance_factor)
        return score

    def update_server_load(self, server_id, cpu_delta, memory_delta, is_addition=True):
        """
        Met à jour la charge d'un serveur.
        """
        if server_id in self.server_loads:
            factor = 1 if is_addition else -1

            self.server_loads[server_id]["cpu"] += factor * cpu_delta
            self.server_loads[server_id]["memory"] += factor * memory_delta

            # S'assurer que les valeurs ne sont pas négatives
            self.server_loads[server_id]["cpu"] = max(0, self.server_loads[server_id]["cpu"])
            self.server_loads[server_id]["memory"] = max(0, self.server_loads[server_id]["memory"])

            self.logger.info(
                f"Charge du serveur {server_id} mise à jour: CPU={self.server_loads[server_id]['cpu']:.2f}, Mémoire={self.server_loads[server_id]['memory']:.2f}")
        else:
            self.logger.error(f"Tentative de mise à jour de charge pour un serveur inconnu: {server_id}")

    def check_load_imbalance(self):
        """
        Vérifie s'il y a un déséquilibre de charge entre les serveurs.
        """
        # Calculer la charge moyenne
        total_cpu_percentage = 0.0
        total_memory_percentage = 0.0
        count = 0

        for server_id, load in self.server_loads.items():
            capacity = self.server_capacities[server_id]

            if capacity["cpu"] > 0 and capacity["memory"] > 0:
                cpu_percentage = load["cpu"] / capacity["cpu"]
                memory_percentage = load["memory"] / capacity["memory"]

                total_cpu_percentage += cpu_percentage
                total_memory_percentage += memory_percentage
                count += 1

        if count == 0:
            return False

        avg_cpu_percentage = total_cpu_percentage / count
        avg_memory_percentage = total_memory_percentage / count

        # Vérifier s'il y a un écart significatif
        imbalance_detected = False
        imbalance_threshold = 0.3  # 30% d'écart

        for server_id, load in self.server_loads.items():
            capacity = self.server_capacities[server_id]

            if capacity["cpu"] > 0 and capacity["memory"] > 0:
                cpu_percentage = load["cpu"] / capacity["cpu"]
                memory_percentage = load["memory"] / capacity["memory"]

                cpu_diff = abs(cpu_percentage - avg_cpu_percentage)
                memory_diff = abs(memory_percentage - avg_memory_percentage)

                if cpu_diff > imbalance_threshold or memory_diff > imbalance_threshold:
                    self.logger.info(
                        f"Déséquilibre détecté pour {server_id}: CPU={cpu_percentage:.2f}/{avg_cpu_percentage:.2f}, Mémoire={memory_percentage:.2f}/{avg_memory_percentage:.2f}")
                    imbalance_detected = True

        return imbalance_detected

    async def rebalance_load(self):
        """
        Tente de rééquilibrer la charge entre les serveurs.
        """
        # Calculer la charge moyenne
        total_cpu_percentage = 0.0
        total_memory_percentage = 0.0
        count = 0

        for server_id, load in self.server_loads.items():
            capacity = self.server_capacities[server_id]

            if capacity["cpu"] > 0 and capacity["memory"] > 0:
                cpu_percentage = load["cpu"] / capacity["cpu"]
                memory_percentage = load["memory"] / capacity["memory"]

                total_cpu_percentage += cpu_percentage
                total_memory_percentage += memory_percentage
                count += 1

        if count == 0:
            return

        avg_cpu_percentage = total_cpu_percentage / count
        avg_memory_percentage = total_memory_percentage / count

        # Mettre à jour les pondérations pour favoriser les serveurs moins chargés
        for server_id, load in self.server_loads.items():
            capacity = self.server_capacities[server_id]

            if capacity["cpu"] > 0 and capacity["memory"] > 0:
                cpu_percentage = load["cpu"] / capacity["cpu"]
                memory_percentage = load["memory"] / capacity["memory"]

                # Calcul de la pondération inverse à la charge
                cpu_weight = max(0.1, 1.0 - (cpu_percentage / avg_cpu_percentage))
                memory_weight = max(0.1, 1.0 - (memory_percentage / avg_memory_percentage))

                # Combiner les deux pondérations
                self.server_weights[server_id] = (cpu_weight + memory_weight) / 2.0

                self.logger.info(f"Nouvelle pondération pour {server_id}: {self.server_weights[server_id]:.2f}")

        # Notifier le MonitorAgent du rééquilibrage
        monitor_msg = Message(to=str(self.monitor_jid))
        monitor_msg.set_metadata("type", "load_rebalanced")
        monitor_msg.body = json.dumps({
            "timestamp": time.time(),
            "server_loads": {s: {"cpu": l["cpu"], "memory": l["memory"]} for s, l in self.server_loads.items()},
            "server_weights": self.server_weights
        })

        # Créer un comportement OneShot pour envoyer le message
        class NotifyRebalanceBehaviour(OneShotBehaviour):
            async def run(self):
                await self.send(monitor_msg)

        self.add_behaviour(NotifyRebalanceBehaviour())