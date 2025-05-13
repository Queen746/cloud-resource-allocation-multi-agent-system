import asyncio
import time
import logging
import json
import datetime
from collections import deque
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.message import Message
from spade.template import Template
import aiohttp
import random
import csv
import os
from datetime import datetime


class MonitorAgent(Agent):
    """
    Agent responsable de la surveillance du système, de la collecte des métriques
    et de la génération d'alertes.
    """

    def __init__(self, jid, password, dashboard_url=None):
        """
        Initialise l'agent de monitoring.

        Args:
            jid (str): JID de l'agent
            password (str): Mot de passe pour l'authentification
            dashboard_url (str, optional): URL de base pour mettre à jour le tableau de bord
        """
        super().__init__(jid, password)
        self.display_name = "MonitorAgent"
        self.dashboard_url = dashboard_url

        # Si l'URL contient "/update", l'enlever pour avoir l'URL de base
        if self.dashboard_url and "/update" in self.dashboard_url:
            self.dashboard_url = self.dashboard_url.split("/update")[0]

        self.logger = logging.getLogger(f"{self.display_name}-{jid.split('@')[0]}")

        # Événements et alertes
        self.events = deque(maxlen=1000)  # Limiter à 1000 événements
        self.active_alerts = {}  # {alert_id: alert_details}

        # Métriques du système
        self.server_metrics = {}  # {server_id: {"cpu_used": X, "memory_used": Y}}
        self.resource_history = {}  # {server_id: [{"timestamp": X, "cpu_used": Y, "memory_used": Z}, ...]}

        # Tailles des files d'attente
        self.queue_sizes = {"vip": 0, "standard": 0}
        self.queue_history = {"vip": deque(maxlen=30), "standard": deque(maxlen=30)}

        # Temps d'attente
        self.wait_times = {
            "vip": deque(maxlen=50),
            "standard": deque(maxlen=50)
        }

        # Données métriques pour le tableau de bord
        self.metrics_data = {
            "normalized": {
                "cpu_percentage": 0,
                "memory_percentage": 0
            },
            "wait_times": {
                "vip": 0,
                "standard": 0
            }
        }

        # Initialiser des données de test pour les graphiques
        self.initialize_test_data()

    class EventCollectionBehaviour(CyclicBehaviour):
        """
        Comportement pour collecter les événements du système.
        """

        async def run(self):
            # Attendre les messages d'événements
            msg = await self.receive(timeout=10)
            if msg:
                try:
                    content = json.loads(msg.body)
                    event_type = msg.metadata.get("type", "unknown")

                    # Traiter différents types d'événements
                    if event_type == "allocation_event":
                        request_id = content.get("request_id")
                        server_id = content.get("server_id")
                        cpu = content.get("cpu")
                        memory = content.get("memory")
                        client_type = content.get("client_type", "STANDARD").lower()

                        # Récupérer les timestamps
                        arrival_time = content.get("arrival_time", 0)
                        start_time = content.get("start_time", time.time())

                        self.agent.logger.info(
                            f"Allocation pour {request_id} sur {server_id}: CPU={cpu}, Mémoire={memory}")

                        # Enregistrer l'événement
                        event = {
                            "type": "allocation",
                            "timestamp": content.get("timestamp", time.time()),
                            "request_id": request_id,
                            "server_id": server_id,
                            "cpu": cpu,
                            "memory": memory
                        }
                        self.agent.add_event(event)

                        # Calculer et enregistrer le temps d'attente si les deux timestamps sont disponibles
                        if arrival_time > 0:
                            wait_time = start_time - arrival_time

                            # Ajouter à la liste des temps d'attente
                            if client_type == "vip":
                                self.agent.wait_times["vip"].append(wait_time)
                            else:
                                self.agent.wait_times["standard"].append(wait_time)

                            # Calculer et mettre à jour les moyennes
                            vip_avg = sum(self.agent.wait_times["vip"]) / len(self.agent.wait_times["vip"]) if \
                            self.agent.wait_times["vip"] else 0
                            std_avg = sum(self.agent.wait_times["standard"]) / len(self.agent.wait_times["standard"]) if \
                            self.agent.wait_times["standard"] else 0

                            self.agent.metrics_data["wait_times"] = {
                                "vip": vip_avg,
                                "standard": std_avg
                            }

                            self.agent.logger.info(
                                f"Temps d'attente pour {request_id} ({client_type}): {wait_time:.2f}s")

                        # Mettre à jour les métriques
                        self.agent.update_metrics(
                            server_id=server_id,
                            cpu_delta=cpu,
                            memory_delta=memory,
                            is_allocation=True
                        )

                    elif event_type == "resource_release":
                        request_id = content.get("request_id")
                        server_id = content.get("server_id", "unknown")

                        self.agent.logger.info(f"Libération pour {request_id} sur {server_id}")

                        # Enregistrer l'événement
                        event = {
                            "type": "release",
                            "timestamp": content.get("timestamp", time.time()),
                            "request_id": request_id,
                            "server_id": server_id
                        }
                        self.agent.add_event(event)

                        # Si les informations de ressources sont disponibles, mettre à jour les métriques
                        if "cpu" in content and "memory" in content:
                            self.agent.update_metrics(
                                server_id=server_id,
                                cpu_delta=content.get("cpu"),
                                memory_delta=content.get("memory"),
                                is_allocation=False
                            )

                    elif event_type == "new_request":
                        request_id = content.get("request_id")
                        client_type = content.get("client_type")

                        self.agent.logger.info(f"Nouvelle demande {request_id} de type {client_type}")

                        # Enregistrer l'événement
                        event = {
                            "type": "new_request",
                            "timestamp": content.get("timestamp", time.time()),
                            "request_id": request_id,
                            "client_type": client_type
                        }
                        self.agent.add_event(event)

                        # Mettre à jour les métriques de file d'attente
                        queue_type = "vip" if client_type == "VIP" else "standard"
                        self.agent.queue_sizes[queue_type] += 1
                        self.agent.queue_history[queue_type].append((time.time(), self.agent.queue_sizes[queue_type]))

                    elif event_type == "request_completed":
                        request_id = content.get("request_id")

                        self.agent.logger.info(f"Demande {request_id} complétée")

                        # Enregistrer l'événement
                        event = {
                            "type": "completion",
                            "timestamp": content.get("timestamp", time.time()),
                            "request_id": request_id
                        }
                        self.agent.add_event(event)

                        # Gérer la fin de traitement de la demande
                        await self.agent.handle_request_completed(content)

                    elif event_type == "dependency_wait":
                        request_id = content.get("request_id")
                        dependencies = content.get("dependencies", [])

                        self.agent.logger.info(f"Demande {request_id} en attente de dépendances: {dependencies}")

                        # Enregistrer l'événement
                        event = {
                            "type": "dependency_wait",
                            "timestamp": content.get("timestamp", time.time()),
                            "request_id": request_id,
                            "dependencies": dependencies
                        }
                        self.agent.add_event(event)

                    elif event_type == "dependencies_satisfied":
                        request_id = content.get("request_id")

                        self.agent.logger.info(f"Dépendances satisfaites pour {request_id}")

                        # Enregistrer l'événement
                        event = {
                            "type": "dependencies_satisfied",
                            "timestamp": content.get("timestamp", time.time()),
                            "request_id": request_id
                        }
                        self.agent.add_event(event)

                    elif event_type == "resource_shortage":
                        request_id = content.get("request_id")
                        server_id = content.get("server_id", "unknown")
                        cpu_required = content.get("cpu_required")
                        memory_required = content.get("memory_required")

                        self.agent.logger.warning(
                            f"Pénurie de ressources pour {request_id} sur {server_id}: CPU={cpu_required}, Mémoire={memory_required}")

                        # Enregistrer l'événement
                        event = {
                            "type": "resource_shortage",
                            "timestamp": content.get("timestamp", time.time()),
                            "request_id": request_id,
                            "server_id": server_id,
                            "cpu_required": cpu_required,
                            "memory_required": memory_required
                        }
                        self.agent.add_event(event)

                        # Créer une alerte
                        alert = {
                            "id": f"alert-{int(time.time())}-{request_id}",
                            "type": "resource_shortage",
                            "severity": "warning",
                            "message": f"Ressources insuffisantes pour {request_id} sur {server_id}",
                            "timestamp": time.time(),
                            "details": {
                                "request_id": request_id,
                                "server_id": server_id,
                                "cpu_required": cpu_required,
                                "memory_required": memory_required
                            }
                        }
                        self.agent.add_alert(alert)

                    elif event_type == "overload_alert":
                        cpu_required = content.get("cpu_required")
                        memory_required = content.get("memory_required")

                        self.agent.logger.warning(f"Alerte de surcharge: CPU={cpu_required}, Mémoire={memory_required}")

                        # Enregistrer l'événement
                        event = {
                            "type": "overload",
                            "timestamp": content.get("timestamp", time.time()),
                            "cpu_required": cpu_required,
                            "memory_required": memory_required
                        }
                        self.agent.add_event(event)

                        # Créer une alerte
                        alert = {
                            "id": f"alert-{int(time.time())}-overload",
                            "type": "overload",
                            "severity": "critical",
                            "message": f"Surcharge système détectée: demande CPU={cpu_required}, Mémoire={memory_required}",
                            "timestamp": time.time(),
                            "details": {
                                "cpu_required": cpu_required,
                                "memory_required": memory_required
                            }
                        }
                        self.agent.add_alert(alert)

                    elif event_type == "load_rebalanced":
                        server_loads = content.get("server_loads", {})

                        self.agent.logger.info(f"Rééquilibrage de charge effectué")

                        # Enregistrer l'événement
                        event = {
                            "type": "load_rebalance",
                            "timestamp": content.get("timestamp", time.time()),
                            "server_loads": server_loads
                        }
                        self.agent.add_event(event)

                    elif event_type == "queue_status":
                        vip_size = content.get("vip_size", 0)
                        standard_size = content.get("standard_size", 0)

                        # Mettre à jour les tailles des files d'attente
                        self.agent.queue_sizes["vip"] = vip_size
                        self.agent.queue_sizes["standard"] = standard_size

                        # Mettre à jour l'historique des files
                        current_time = content.get("timestamp", time.time())
                        self.agent.queue_history["vip"].append((current_time, vip_size))
                        self.agent.queue_history["standard"].append((current_time, standard_size))

                        self.agent.logger.info(
                            f"Files d'attente mises à jour: VIP={vip_size}, Standard={standard_size}")

                    # Mettre à jour le tableau de bord
                    await self.agent.update_dashboard()

                except Exception as e:
                    self.agent.logger.error(f"Erreur lors du traitement de l'événement: {e}")

            # Petit délai pour éviter de surcharger le CPU
            await asyncio.sleep(0.1)

    class DashboardUpdateBehaviour(PeriodicBehaviour):
        """
        Comportement pour mettre à jour périodiquement le tableau de bord.
        """

        async def run(self):
            try:
                # Mettre à jour le tableau de bord
                await self.agent.update_dashboard()

                # Vérifier l'état du système et générer des alertes si nécessaire
                await self.agent.check_system_health()
            except Exception as e:
                self.agent.logger.error(f"Erreur lors de la mise à jour du tableau de bord: {e}")

    class AlertCleanupBehaviour(PeriodicBehaviour):
        """
        Comportement pour nettoyer les alertes résolues ou expirées.
        """

        async def run(self):
            try:
                current_time = time.time()

                # Nettoyer les alertes de plus de 1 heure
                expired_alerts = []

                for alert_id, alert in list(self.agent.active_alerts.items()):
                    if current_time - alert["timestamp"] > 3600:  # 1 heure
                        expired_alerts.append(alert_id)

                for alert_id in expired_alerts:
                    self.agent.logger.info(f"Suppression de l'alerte expirée {alert_id}")
                    del self.agent.active_alerts[alert_id]

                # Mettre à jour le tableau de bord si des alertes ont été supprimées
                if expired_alerts:
                    await self.agent.update_dashboard()

            except Exception as e:
                self.agent.logger.error(f"Erreur lors du nettoyage des alertes: {e}")

    async def setup(self):
        """
        Initialise l'agent et ses comportements.
        """
        self.logger.info(f"Agent {self.display_name} starting...")

        # Comportements
        event_template = Template()
        self.add_behaviour(self.EventCollectionBehaviour(), event_template)

        # Mise à jour périodique du tableau de bord (toutes les 5 secondes)
        self.add_behaviour(self.DashboardUpdateBehaviour(period=5))

        # Nettoyage périodique des alertes (toutes les 30 secondes)
        self.add_behaviour(self.AlertCleanupBehaviour(period=30))

    def add_event(self, event):
        """
        Ajoute un événement à l'historique.

        Args:
            event (dict): Détails de l'événement
        """
        self.events.append(event)

    def add_alert(self, alert):
        """
        Ajoute une alerte active.

        Args:
            alert (dict): Détails de l'alerte
        """
        self.active_alerts[alert["id"]] = alert

    def normalize_metrics(self):
        """Normalise les métriques pour l'affichage"""
        # Définir les capacités maximales par serveur
        server_capacities = {
            "server-1": {"cpu": 100.0, "memory": 100.0},
            "server-2": {"cpu": 100.0, "memory": 100.0},
            "server-3": {"cpu": 100.0, "memory": 100.0},
            "server-4": {"cpu": 100.0, "memory": 100.0},
            "server-5": {"cpu": 100.0, "memory": 100.0}
        }

        total_cpu_capacity = 0.0
        total_memory_capacity = 0.0
        total_cpu_used = 0.0
        total_memory_used = 0.0

        # Accumuler les totaux
        for server_id, metrics in self.server_metrics.items():
            capacity = server_capacities.get(server_id, {"cpu": 100.0, "memory": 100.0})
            total_cpu_capacity += float(capacity["cpu"])
            total_memory_capacity += float(capacity["memory"])
            total_cpu_used += float(metrics.get("cpu_used", 0.0))
            total_memory_used += float(metrics.get("memory_used", 0.0))

        # Calculer les pourcentages
        if total_cpu_capacity > 0.0:
            cpu_percentage = (total_cpu_used / total_cpu_capacity) * 100.0
        else:
            cpu_percentage = 0.0

        if total_memory_capacity > 0.0:
            memory_percentage = (total_memory_used / total_memory_capacity) * 100.0
        else:
            memory_percentage = 0.0

        # Limiter à 100% pour l'affichage
        cpu_percentage = min(100.0, cpu_percentage)
        memory_percentage = min(100.0, memory_percentage)

        # Mettre à jour les métriques normalisées
        self.metrics_data["normalized"] = {
            "cpu_percentage": round(cpu_percentage, 1),
            "memory_percentage": round(memory_percentage, 1)
        }

    def initialize_test_data(self):
        """Initialise des données de test pour les graphiques"""
        # Générer un historique de files d'attente
        current_time = time.time()
        for i in range(30):
            timestamp = current_time - (30 - i) * 60  # Un point par minute

            vip_size = random.randint(0, 5)
            std_size = random.randint(1, 15)

            self.queue_history["vip"].append((timestamp, vip_size))
            self.queue_history["standard"].append((timestamp, std_size))

            # Mettre à jour les valeurs actuelles pour le dernier point
            if i == 29:
                self.queue_sizes["vip"] = vip_size
                self.queue_sizes["standard"] = std_size

        # Générer un historique de ressources pour chaque serveur
        for server_id in ["server-1", "server-2", "server-3", "server-4", "server-5"]:
            if server_id not in self.resource_history:
                self.resource_history[server_id] = []
            if server_id not in self.server_metrics:
                self.server_metrics[server_id] = {"cpu_used": 0.0, "memory_used": 0.0}

            for i in range(30):
                timestamp = current_time - (30 - i) * 60

                # Générer des valeurs aléatoires
                cpu_value = random.uniform(5.0, 25.0)
                memory_value = random.uniform(10.0, 40.0)

                self.resource_history[server_id].append({
                    "timestamp": timestamp,
                    "cpu_used": cpu_value,
                    "memory_used": memory_value
                })

                # Mettre à jour les métriques actuelles avec les dernières valeurs
                if i == 29:
                    self.server_metrics[server_id]["cpu_used"] = cpu_value
                    self.server_metrics[server_id]["memory_used"] = memory_value

    def update_metrics(self, server_id, cpu_delta, memory_delta, is_allocation=True):
        """
        Met à jour les métriques pour un serveur.

        Args:
            server_id (str): Identifiant du serveur
            cpu_delta (float): Changement de CPU
            memory_delta (float): Changement de mémoire
            is_allocation (bool): True si c'est une allocation, False si c'est une libération
        """
        # Initialiser les métriques pour ce serveur si nécessaire
        if server_id not in self.server_metrics:
            self.server_metrics[server_id] = {"cpu_used": 0, "memory_used": 0}

        if server_id not in self.resource_history:
            self.resource_history[server_id] = []

        # Mettre à jour les métriques
        if is_allocation:
            self.server_metrics[server_id]["cpu_used"] += cpu_delta
            self.server_metrics[server_id]["memory_used"] += memory_delta
        else:
            self.server_metrics[server_id]["cpu_used"] = max(0, self.server_metrics[server_id]["cpu_used"] - cpu_delta)
            self.server_metrics[server_id]["memory_used"] = max(0, self.server_metrics[server_id][
                "memory_used"] - memory_delta)

        # Ajouter à l'historique
        self.resource_history[server_id].append({
            "timestamp": time.time(),
            "cpu_used": self.server_metrics[server_id]["cpu_used"],
            "memory_used": self.server_metrics[server_id]["memory_used"]
        })

        # Limiter l'historique à 50 points maximum
        if len(self.resource_history[server_id]) > 50:
            self.resource_history[server_id] = self.resource_history[server_id][-50:]

        # Normaliser les métriques
        self.normalize_metrics()

    async def handle_request_completed(self, data):
        """Traite les notifications de demandes complétées"""
        request_id = data.get("request_id")
        client_type = data.get("client_type", "standard")
        arrival_time = data.get("arrival_time", 0)
        start_time = data.get("start_time", 0)

        # Calculer le temps d'attente (de l'arrivée jusqu'au début du traitement)
        if arrival_time > 0 and start_time > 0:
            wait_time = start_time - arrival_time
            self.wait_times[client_type].append(wait_time)

            # Mettre à jour les statistiques
            self.logger.info(f"Temps d'attente pour {request_id} ({client_type}): {wait_time:.2f}s")

            # Mettre à jour le tableau de bord avec les temps d'attente moyens réels
            vip_avg = sum(self.wait_times["vip"]) / len(self.wait_times["vip"]) if self.wait_times["vip"] else 0
            std_avg = sum(self.wait_times["standard"]) / len(self.wait_times["standard"]) if self.wait_times[
                "standard"] else 0

            # Ajouter ces valeurs aux métriques envoyées au tableau de bord
            self.metrics_data["wait_times"] = {
                "vip": vip_avg,
                "standard": std_avg
            }

    async def update_dashboard(self):
        """
        Met à jour le tableau de bord avec les dernières métriques et événements.
        """
        try:
            # Normaliser les métriques
            self.normalize_metrics()

            # Calculer le nombre de demandes actives
            # C'est une estimation basée sur ce que l'agent connaît
            active_requests_count = sum(1 for event in self.events
                                        if event["type"] == "allocation" and
                                        all(completion["request_id"] != event["request_id"]
                                            for completion in self.events if completion["type"] == "completion"))

            # Calculer le déséquilibre de charge
            load_imbalance = self.calculate_load_imbalance()

            # Récupérer les événements et alertes
            recent_events = list(self.events)[-50:] if self.events else []
            active_alerts = list(self.active_alerts.values())

            self.logger.info(f"Updating dashboard with {len(recent_events)} events, {len(active_alerts)} active alerts")

            if not self.dashboard_url:
                return

            # Envoyer les données au tableau de bord
            async with aiohttp.ClientSession() as session:
                # Métriques système - Assurez-vous d'envoyer des valeurs numériques, pas des chaînes vides
                metrics_data = {
                    "server_metrics": {k: v for k, v in self.server_metrics.items()},
                    "queue_sizes": {
                        "vip": self.queue_sizes.get("vip", 0),
                        "standard": self.queue_sizes.get("standard", 0)
                    },
                    "normalized": self.metrics_data.get("normalized", {
                        "cpu_percentage": 0,
                        "memory_percentage": 0
                    }),
                    "wait_times": self.metrics_data.get("wait_times", {
                        "vip": 0,
                        "standard": 0
                    }),
                    "active_requests_count": active_requests_count,
                    "load_imbalance": load_imbalance
                }

                try:
                    async with session.post(
                            f"{self.dashboard_url}/api/metrics",
                            json=metrics_data
                    ) as response:
                        if response.status != 200:
                            self.logger.warning(f"Échec de la mise à jour des métriques: {response.status}")
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'envoi des métriques: {e}")

                # Historique des files d'attente
                # Historique des files d'attente
                queue_history_data = {
                    "vip": list(self.queue_history["vip"])[-20:],  # Limiter à 20 points
                    "standard": list(self.queue_history["standard"])[-20:]  # Limiter à 20 points
                }
                try:
                    async with session.post(
                            f"{self.dashboard_url}/api/queue_history",
                            json=queue_history_data
                    ) as response:
                        if response.status != 200:
                            self.logger.warning(f"Échec de la mise à jour de l'historique des files: {response.status}")
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'envoi de l'historique des files: {e}")

                # Historique des ressources
                resource_history_data = {}
                for server_id, history in self.resource_history.items():
                    resource_history_data[server_id] = list(history)[-30:]  # Limiter à 30 points

                try:
                    async with session.post(
                            f"{self.dashboard_url}/api/resource_history",
                            json=resource_history_data
                    ) as response:
                        if response.status != 200:
                            self.logger.warning(
                                f"Échec de la mise à jour de l'historique des ressources: {response.status}")
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'envoi de l'historique des ressources: {e}")

                # Événements
                try:
                    async with session.post(
                            f"{self.dashboard_url}/api/events",
                            json={"events": recent_events}
                    ) as response:
                        if response.status != 200:
                            self.logger.warning(f"Échec de la mise à jour des événements: {response.status}")
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'envoi des événements: {e}")

                # Alertes
                try:
                    async with session.post(
                            f"{self.dashboard_url}/api/alerts",
                            json={"alerts": active_alerts}
                    ) as response:
                        if response.status != 200:
                            self.logger.warning(f"Échec de la mise à jour des alertes: {response.status}")
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'envoi des alertes: {e}")

        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour du tableau de bord: {e}")

    async def check_system_health(self):
        """Vérifie l'état du système et génère des alertes si nécessaire"""
        try:
            alerts = []

            # Vérifier l'utilisation CPU globale
            total_cpu_used = sum(float(server.get("cpu_used", 0.0)) for server in self.server_metrics.values())
            total_cpu_capacity = 500.0  # Somme des capacités CPU (à ajuster selon votre système)
            cpu_usage_percentage = total_cpu_used / total_cpu_capacity * 100.0 if total_cpu_capacity > 0.0 else 0.0

            if cpu_usage_percentage > 85.0:
                alerts.append({
                    "id": f"alert-cpu-warning-{int(time.time())}",
                    "type": "cpu_warning",
                    "level": "warning",
                    "message": f"Utilisation CPU élevée: {cpu_usage_percentage:.1f}%",
                    "timestamp": float(time.time())
                })

            if cpu_usage_percentage > 95.0:
                alerts.append({
                    "id": f"alert-cpu-critical-{int(time.time())}",
                    "type": "cpu_critical",
                    "level": "critical",
                    "message": f"Utilisation CPU critique: {cpu_usage_percentage:.1f}%",
                    "timestamp": float(time.time())
                })

            # Vérifier l'utilisation mémoire globale
            total_memory_used = sum(float(server.get("memory_used", 0.0)) for server in self.server_metrics.values())
            total_memory_capacity = 500.0  # Somme des capacités mémoire (à ajuster)
            memory_usage_percentage = total_memory_used / total_memory_capacity * 100.0 if total_memory_capacity > 0.0 else 0.0

            if memory_usage_percentage > 90.0:
                alerts.append({
                    "id": f"alert-memory-warning-{int(time.time())}",
                    "type": "memory_warning",
                    "level": "warning",
                    "message": f"Utilisation mémoire élevée: {memory_usage_percentage:.1f}%",
                    "timestamp": float(time.time())
                })

                # Vérifier les files d'attente
                vip_queue_size = float(self.queue_sizes.get("vip", 0.0))
                std_queue_size = float(self.queue_sizes.get("standard", 0.0))

                if vip_queue_size > 10.0:
                    alerts.append({
                        "id": f"alert-vip-queue-{int(time.time())}",
                        "type": "queue_warning",
                        "level": "warning",
                        "message": f"File d'attente VIP élevée: {int(vip_queue_size)} demandes",
                        "timestamp": float(time.time())
                    })

                if std_queue_size > 20.0:
                    alerts.append({
                        "id": f"alert-std-queue-{int(time.time())}",
                        "type": "queue_warning",
                        "level": "warning",
                        "message": f"File d'attente standard élevée: {int(std_queue_size)} demandes",
                        "timestamp": float(time.time())
                    })

                # Vérifier le déséquilibre de charge
                cpu_loads = [float(server.get("cpu_used", 0.0)) for server in self.server_metrics.values() if server]
                if len(cpu_loads) > 1:
                    avg_load = sum(cpu_loads) / float(len(cpu_loads)) if cpu_loads else 0.0
                    max_load = max(cpu_loads) if cpu_loads else 0.0
                    min_load = min(cpu_loads) if cpu_loads else 0.0

                    imbalance = (max_load - min_load) / avg_load if avg_load > 0.0 else 0.0

                    if imbalance > 0.5:  # Déséquilibre de plus de 50%
                        alerts.append({
                            "id": f"alert-imbalance-{int(time.time())}",
                            "type": "imbalance_warning",
                            "level": "warning",
                            "message": f"Déséquilibre de charge important: {imbalance:.2f}",
                            "timestamp": float(time.time())
                        })

                # Mettre à jour les alertes actives
                self.active_alerts = {alert["id"]: alert for alert in alerts}
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de l'état du système: {e}")

    async def save_metrics_to_csv(self):
        """Sauvegarde les métriques dans un fichier CSV"""
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)

        # Fichier pour les métriques des serveurs
        server_metrics_file = os.path.join(logs_dir, f"servermetrics{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(server_metrics_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'server_id', 'cpu_used', 'memory_used'])

            timestamp = time.time()
            for server_id, metrics in self.server_metrics.items():
                writer.writerow([
                    timestamp,
                    server_id,
                    metrics.get('cpu_used', 0),
                    metrics.get('memory_used', 0)
                ])

        # Fichier pour les tailles de files d'attente
        queue_metrics_file = os.path.join(logs_dir, f"queuemetrics{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(queue_metrics_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'queue_type', 'size'])

            timestamp = time.time()
            for queue_type, size in self.queue_sizes.items():
                writer.writerow([
                    timestamp,
                    queue_type,
                    size
                ])

        # Fichier pour les temps d'attente
        wait_times_file = os.path.join(logs_dir, f"waittimes{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(wait_times_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['queue_type', 'avg_wait_time'])

            for queue_type, times in self.wait_times.items():
                avg_time = sum(times) / len(times) if times else 0
                writer.writerow([
                    queue_type,
                    avg_time
                ])

        self.logger.info(f"Métriques sauvegardées dans {logs_dir}")

    def calculate_load_imbalance(self):
        """
        Calcule le déséquilibre de charge entre les serveurs.

        Returns:
            float: Valeur du déséquilibre (0 = équilibré)
        """
        if not self.server_metrics or len(self.server_metrics) <= 1:
            return 0.0

        # Calculer la charge CPU moyenne
        cpu_loads = [metrics.get("cpu_used", 0.0) for metrics in self.server_metrics.values()]
        if not cpu_loads:
            return 0.0

        avg_cpu = sum(cpu_loads) / len(cpu_loads)
        if avg_cpu == 0:
            return 0.0

        # Calculer l'écart maximal par rapport à la moyenne
        max_deviation = max(abs(load - avg_cpu) for load in cpu_loads)

        # Normaliser l'écart
        imbalance = max_deviation / avg_cpu

        return imbalance