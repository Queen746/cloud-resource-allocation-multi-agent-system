# monitoring/stats_collector.py
import time
import logging
import json
from collections import deque


class StatsCollector:
    """Collecte et analyse les statistiques du système"""

    def __init__(self, max_history=1000):
        self.logger = logging.getLogger("StatsCollector")
        self.max_history = max_history

        # Files d'attente et temps d'attente
        self.queue_stats = {
            "vip": {"current": 0, "history": deque(maxlen=max_history)},
            "standard": {"current": 0, "history": deque(maxlen=max_history)}
        }

        # Temps de traitement
        self.processing_times = {
            "vip": [],
            "standard": []
        }

        # Utilisation des ressources
        self.resource_usage = {
            "cpu": {"current": 0, "max": 0, "history": deque(maxlen=max_history)},
            "memory": {"current": 0, "max": 0, "history": deque(maxlen=max_history)}
        }

        # Équilibrage de charge
        self.load_balance = {
            "imbalance_index": 0,  # Indice de déséquilibre
            "server_loads": {}  # Charge par serveur
        }

        # Demandes
        self.requests = {
            "total": 0,  # Total des demandes
            "completed": 0,  # Demandes complétées
            "rejected": 0,  # Demandes rejetées
            "active": 0,  # Demandes actives
            "vip_ratio": 0,  # Ratio de demandes VIP
            "with_dependencies": 0  # Demandes avec dépendances
        }

        # Temps système
        self.start_time = time.time()
        self.last_update = self.start_time

    def update_queues(self, vip_size, std_size):
        """Met à jour les statistiques des files d'attente"""
        now = time.time()

        self.queue_stats["vip"]["current"] = vip_size
        self.queue_stats["standard"]["current"] = std_size

        self.queue_stats["vip"]["history"].append((now, vip_size))
        self.queue_stats["standard"]["history"].append((now, std_size))

    def update_processing_time(self, request_id, client_type, duration):
        """Enregistre un temps de traitement"""
        if client_type.upper() == "VIP":
            self.processing_times["vip"].append(duration)
        else:
            self.processing_times["standard"].append(duration)

        # Limiter la taille de la liste
        if len(self.processing_times["vip"]) > self.max_history:
            self.processing_times["vip"] = self.processing_times["vip"][-self.max_history:]
        if len(self.processing_times["standard"]) > self.max_history:
            self.processing_times["standard"] = self.processing_times["standard"][-self.max_history:]

    def update_resources(self, servers_data):
        """Met à jour les statistiques d'utilisation des ressources"""
        now = time.time()

        # Calculer l'utilisation totale
        total_cpu = 0
        total_memory = 0
        cpu_capacities = {}
        memory_capacities = {}

        for server_id, data in servers_data.items():
            # Supposer que chaque serveur a cpu_used, memory_used, cpu_total, memory_total
            cpu_used = data.get("cpu_used", 0)
            memory_used = data.get("memory_used", 0)
            cpu_total = data.get("cpu_total", 100)  # Valeurs par défaut
            memory_total = data.get("memory_total", 100)

            total_cpu += cpu_used
            total_memory += memory_used

            cpu_capacities[server_id] = cpu_total
            memory_capacities[server_id] = memory_total

            # Mettre à jour les charges par serveur
            self.load_balance["server_loads"][server_id] = {
                "cpu_percent": (cpu_used / cpu_total * 100) if cpu_total > 0 else 0,
                "memory_percent": (memory_used / memory_total * 100) if memory_total > 0 else 0
            }

        # Mettre à jour les ressources
        self.resource_usage["cpu"]["current"] = total_cpu
        self.resource_usage["memory"]["current"] = total_memory

        # Mettre à jour les maximums
        self.resource_usage["cpu"]["max"] = max(self.resource_usage["cpu"]["max"], total_cpu)
        self.resource_usage["memory"]["max"] = max(self.resource_usage["memory"]["max"], total_memory)

        # Mettre à jour l'historique
        self.resource_usage["cpu"]["history"].append((now, total_cpu))
        self.resource_usage["memory"]["history"].append((now, total_memory))

        # Calculer l'indice de déséquilibre
        if cpu_capacities:
            self._calculate_imbalance(cpu_capacities, memory_capacities)

    def _calculate_imbalance(self, cpu_capacities, memory_capacities):
        """Calcule l'indice de déséquilibre de charge"""
        if not self.load_balance["server_loads"]:
            self.load_balance["imbalance_index"] = 0
            return

        # Calculer l'écart type des pourcentages d'utilisation
        cpu_percentages = [data["cpu_percent"] for data in self.load_balance["server_loads"].values()]
        memory_percentages = [data["memory_percent"] for data in self.load_balance["server_loads"].values()]

        if not cpu_percentages or not memory_percentages:
            self.load_balance["imbalance_index"] = 0
            return

        # Moyenne et écart type pour CPU
        cpu_avg = sum(cpu_percentages) / len(cpu_percentages)
        cpu_variance = sum((p - cpu_avg) ** 2 for p in cpu_percentages) / len(cpu_percentages)
        cpu_std_dev = cpu_variance ** 0.5

        # Moyenne et écart type pour mémoire
        memory_avg = sum(memory_percentages) / len(memory_percentages)
        memory_variance = sum((p - memory_avg) ** 2 for p in memory_percentages) / len(memory_percentages)
        memory_std_dev = memory_variance ** 0.5

        # Indice de déséquilibre (moyenne des deux écarts types)
        self.load_balance["imbalance_index"] = (cpu_std_dev + memory_std_dev) / 2

    def update_request_stats(self, total, completed, rejected, active, vip_count, with_deps_count):
        """Met à jour les statistiques des demandes"""
        self.requests["total"] = total
        self.requests["completed"] = completed
        self.requests["rejected"] = rejected
        self.requests["active"] = active

        self.requests["vip_ratio"] = vip_count / total if total > 0 else 0
        self.requests["with_dependencies"] = with_deps_count

    def get_average_wait_times(self):
        """Calcule les temps d'attente moyens"""
        vip_avg = sum(self.processing_times["vip"]) / len(self.processing_times["vip"]) if self.processing_times[
            "vip"] else 0
        std_avg = sum(self.processing_times["standard"]) / len(self.processing_times["standard"]) if \
        self.processing_times["standard"] else 0

        return {
            "vip": vip_avg,
            "standard": std_avg
        }

    def get_system_uptime(self):
        """Retourne la durée de fonctionnement du système"""
        return time.time() - self.start_time

    def get_summary(self):
        """Retourne un résumé des statistiques"""
        avg_wait_times = self.get_average_wait_times()

        return {
            "uptime": self.get_system_uptime(),
            "requests": {
                "total": self.requests["total"],
                "completed": self.requests["completed"],
                "rejected": self.requests["rejected"],
                "active": self.requests["active"],
                "vip_ratio": self.requests["vip_ratio"]
            },
            "queues": {
                "vip": self.queue_stats["vip"]["current"],
                "standard": self.queue_stats["standard"]["current"]
            },
            "wait_times": {
                "vip": avg_wait_times["vip"],
                "standard": avg_wait_times["standard"]
            },
            "resources": {
                "cpu": self.resource_usage["cpu"]["current"],
                "memory": self.resource_usage["memory"]["current"],
                "cpu_max": self.resource_usage["cpu"]["max"],
                "memory_max": self.resource_usage["memory"]["max"]
            },
            "imbalance_index": self.load_balance["imbalance_index"]
        }