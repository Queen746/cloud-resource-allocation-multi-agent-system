import asyncio
import time
import logging
import json
import random
from collections import deque

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.message import Message
from spade.template import Template


class LoadBalancerAgent(Agent):
    """
    Agent responsable de l'équilibrage de charge entre les serveurs.
    Implémente différentes stratégies d'allocation.
    """

    def __init__(self, jid, password, monitor_jid):
        """
        Initialise l'agent d'équilibrage de charge.

        Args:
            jid (str): JID de l'agent
            password (str): Mot de passe pour l'authentification
            monitor_jid (str): JID de l'agent de monitoring
        """
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
        self.strategy = "least_loaded"  # Alternatives: "round_robin", "random", "weighted"

        # Compteur pour round-robin
        self.round_robin_index = 0

        # Pondérations pour weighted strategy
        self.server_weights = {
            "server-1": 1.0,
            "server-2": 1.0,
            "server-3": 1.0,
            "server-4": 1.0,
            "server-5": 1.0
        }

    class ServerSelectionBehaviour(CyclicBehaviour):
        """
        Comportement pour sélectionner un serveur pour une nouvelle demande.
        """

        async def run(self):
            # Attendre les messages de demande de sélection de serveur
            msg = await self.receive(timeout=10)
            if msg:
                try:
                    content = json.loads(msg.body)

                    if msg.metadata.get("type") == "server_selection":
                        request_id = content.get("request_id")
                        cpu_required = content.get("cpu_required")
                        memory_required = content.get("memory_required")

                        self.agent.logger.info(
                            f"Sélection de serveur pour {request_id}: CPU={cpu_required}, Mémoire={memory_required}")

                        # Sélectionner le serveur selon la stratégie actuelle
                        selected_server = self.agent.select_server(cpu_required, memory_required)

                        if selected_server:
                            self.agent.logger.info(f"Serveur sélectionné pour {request_id}: {selected_server}")

                            # Mettre à jour les charges
                            self.agent.update_server_load(selected_server, cpu_required, memory_required,
                                                          is_addition=True)

                            # Enregistrer dans l'historique des allocations
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

            # Petit délai pour éviter de surcharger le CPU
            await asyncio.sleep(0.1)

    class LoadMonitoringBehaviour(PeriodicBehaviour):
        """
        Comportement périodique pour surveiller et équilibrer les charges des serveurs.
        """

        async def run(self):
            try:
                # Vérifier les déséquilibres de charge
                imbalance_detected = self.agent.check_load_imbalance()

                if imbalance_detected:
                    # Si un déséquilibre est détecté, tenter de rééquilibrer
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

    def select_server(self, cpu_required, memory_required):
        """
        Sélectionne un serveur pour une demande selon la stratégie actuelle.

        Args:
            cpu_required (float): Quantité de CPU requise
            memory_required (float): Quantité de mémoire requise

        Returns:
            str: Identifiant du serveur sélectionné, ou None si aucun serveur disponible
        """
        # Filtrer les serveurs avec assez de capacité
        available_servers = []
        for server_id, capacity in self.server_capacities.items():
            current_load = self.server_loads[server_id]
            available_cpu = capacity["cpu"] - current_load["cpu"]
            available_memory = capacity["memory"] - current_load["memory"]

            if available_cpu >= cpu_required and available_memory >= memory_required:
                available_servers.append(server_id)

        if not available_servers:
            self.logger.warning(
                f"Aucun serveur avec assez de capacité pour CPU={cpu_required}, Mémoire={memory_required}")
            return None

        selected_server = None

        if self.strategy == "round_robin":
            # Stratégie Round-Robin
            selected_server = available_servers[self.round_robin_index % len(available_servers)]
            self.round_robin_index += 1

        elif self.strategy == "random":
            # Stratégie aléatoire
            selected_server = random.choice(available_servers)

        elif self.strategy == "weighted":
            # Stratégie pondérée
            total_weight = sum(self.server_weights[server] for server in available_servers)
            if total_weight > 0:
                rand_value = random.uniform(0, total_weight)
                cumulative_weight = 0
                for server in available_servers:
                    cumulative_weight += self.server_weights[server]
                    if cumulative_weight >= rand_value:
                        selected_server = server
                        break
            else:
                selected_server = random.choice(available_servers)

        else:  # "least_loaded" (par défaut)
            # Stratégie du serveur le moins chargé (en pourcentage de CPU+Mémoire)
            best_server = None
            best_load_percentage = float('inf')

            for server in available_servers:
                current_load = self.server_loads[server]
                capacity = self.server_capacities[server]

                # Calculer le pourcentage de charge combiné (CPU + Mémoire)
                cpu_percentage = current_load["cpu"] / capacity["cpu"] if capacity["cpu"] > 0 else 1.0
                memory_percentage = current_load["memory"] / capacity["memory"] if capacity["memory"] > 0 else 1.0
                combined_percentage = (cpu_percentage + memory_percentage) / 2.0

                if combined_percentage < best_load_percentage:
                    best_load_percentage = combined_percentage
                    best_server = server

            selected_server = best_server

        return selected_server

    def update_server_load(self, server_id, cpu_delta, memory_delta, is_addition=True):
        """
        Met à jour la charge d'un serveur.

        Args:
            server_id (str): Identifiant du serveur
            cpu_delta (float): Changement de CPU
            memory_delta (float): Changement de mémoire
            is_addition (bool): True si c'est une addition, False si c'est une soustraction
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

        Returns:
            bool: True si un déséquilibre est détecté, False sinon
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

        # Vérifier s'il y a un écart significatif entre les serveurs
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
                # Plus la charge est élevée, plus la pondération est faible
                # Calcul de la pondération inverse à la charge
                # Plus la charge est élevée, plus la pondération est faible
                cpu_weight = max(0.1, 1.0 - (cpu_percentage / avg_cpu_percentage))
                memory_weight = max(0.1, 1.0 - (memory_percentage / avg_memory_percentage))

                # Combiner les deux pondérations
                self.server_weights[server_id] = (cpu_weight + memory_weight) / 2.0

                self.logger.info(f"Nouvelle pondération pour {server_id}: {self.server_weights[server_id]:.2f}")

                # Passer à la stratégie pondérée pour utiliser ces nouvelles pondérations
            old_strategy = self.strategy
            self.strategy = "weighted"
            self.logger.info(f"Stratégie changée de {old_strategy} à {self.strategy} pour rééquilibrage")

            # Notifier le MonitorAgent du rééquilibrage
            monitor_msg = Message(to=str(self.monitor_jid))
            monitor_msg.set_metadata("type", "load_rebalanced")
            monitor_msg.body = json.dumps({
                "timestamp": time.time(),
                "server_loads": {s: {"cpu": l["cpu"], "memory": l["memory"]} for s, l in self.server_loads.items()},
                "server_weights": self.server_weights,
                "old_strategy": old_strategy,
                "new_strategy": self.strategy
            })

            # Créer un comportement OneShot pour envoyer le message
            class NotifyRebalanceBehaviour(CyclicBehaviour):
                async def run(self):
                    await self.send(monitor_msg)
                    self.kill()

            behaviour = NotifyRebalanceBehaviour()
            self.add_behaviour(behaviour)

            # Après un certain temps, revenir à la stratégie initiale
            await asyncio.sleep(300)  # 5 minutes

            self.strategy = old_strategy
            self.logger.info(f"Retour à la stratégie initiale: {self.strategy}")