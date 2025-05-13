# tests/load_test.py
import asyncio
import random
import time
import logging
from datetime import datetime

from models.client import Client
from models.enums import ClientType

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LoadTest")


class LoadTest:
    def __init__(self, client_manager_agent):
        self.client_manager = client_manager_agent
        self.test_results = {
            "requests_sent": 0,
            "requests_completed": 0,
            "vip_avg_wait_time": 0,
            "standard_avg_wait_time": 0,
            "start_time": None,
            "end_time": None
        }
        self.request_tracking = {}  # Pour suivre les temps d'attente

    async def run_test(self, duration=300,
                       burst_interval=30, burst_size=10,
                       request_interval=5, vip_ratio=0.2):
        """
        Exécute un test de charge sur le système.

        Args:
            duration (int): Durée du test en secondes
            burst_interval (int): Intervalle entre les pics de charge
            burst_size (int): Nombre de demandes pendant un pic
            request_interval (int): Intervalle normal entre les demandes
            vip_ratio (float): Ratio de clients VIP (0 à 1)
        """
        logger.info(f"Démarrage du test de charge pour {duration} secondes")
        self.test_results["start_time"] = datetime.now()

        # Créer des clients simulés
        vip_clients = [
            Client(client_id=f"vip-test-{i}", client_type=ClientType.VIP)
            for i in range(1, 11)
        ]
        standard_clients = [
            Client(client_id=f"std-test-{i}", client_type=ClientType.STANDARD)
            for i in range(1, 21)
        ]

        # Simuler des dépendances
        dependencies = {}  # id -> [liste d'ids dont il dépend]
        request_counter = 0

        start_time = time.time()
        last_burst_time = start_time

        try:
            while time.time() - start_time < duration:
                # Vérifier si c'est le moment d'un pic de charge
                current_time = time.time()
                is_burst = current_time - last_burst_time > burst_interval

                if is_burst:
                    logger.info(f"Simulation d'un pic de charge avec {burst_size} demandes")
                    last_burst_time = current_time

                    # Envoyer un pic de demandes
                    for i in range(burst_size):
                        await self._send_test_request(
                            vip_clients if random.random() < vip_ratio else standard_clients,
                            request_counter,
                            dependencies
                        )
                        request_counter += 1
                        await asyncio.sleep(0.5)  # Court délai entre les demandes du pic
                else:
                    # Demande normale
                    await self._send_test_request(
                        vip_clients if random.random() < vip_ratio else standard_clients,
                        request_counter,
                        dependencies
                    )
                    request_counter += 1

                    # Attendre avant la prochaine demande
                    await asyncio.sleep(request_interval * random.uniform(0.8, 1.2))

        except Exception as e:
            logger.error(f"Erreur durant le test de charge: {e}")

        self.test_results["end_time"] = datetime.now()
        logger.info(f"Test de charge terminé: {self.test_results['requests_sent']} demandes envoyées")

        return self.test_results

    async def _send_test_request(self, clients, request_id, dependencies):
        """Envoi d'une demande de test au système"""
        # Sélectionner un client aléatoire
        client = random.choice(clients)

        # Générer une demande
        request_id = f"loadtest-{request_id}"

        # CPU et mémoire aléatoires
        cpu_required = random.uniform(1.0, 8.0)
        memory_required = random.uniform(1.0, 10.0)

        # Durée d'exécution estimée
        estimated_duration = random.uniform(20, 180)  # 20s à 3min

        # Gérer les dépendances (30% de chance d'avoir des dépendances)
        request_dependencies = set()
        if random.random() < 0.3 and dependencies:
            # Choisir entre 1 et 3 demandes dont dépendre
            num_deps = min(random.randint(1, 3), len(dependencies))
            dep_ids = random.sample(list(dependencies.keys()), num_deps)
            request_dependencies = set(dep_ids)

        # Enregistrer cette demande pour les futures dépendances
        # (70% de chance d'être utilisée comme dépendance)
        if random.random() < 0.7:
            dependencies[request_id] = request_dependencies

        # Enregistrer l'heure d'envoi pour le suivi
        self.request_tracking[request_id] = {
            "send_time": time.time(),
            "client_type": client.client_type.name,
            "completed": False
        }

        # Informations de log
        logger.info(f"Test: Envoi de la demande {request_id} du client {client.id} "
                    f"(CPU: {cpu_required:.1f}, Mémoire: {memory_required:.1f}, "
                    f"Durée: {estimated_duration:.1f}s, "
                    f"Dépendances: {request_dependencies})")

        # Envoyer la demande au ClientManagerAgent
        await self.client_manager.process_simulation_request({
            "id": request_id,
            "client": client.to_dict(),
            "cpu_required": cpu_required,
            "memory_required": memory_required,
            "estimated_duration": estimated_duration,
            "dependencies": list(request_dependencies)
        })

        self.test_results["requests_sent"] += 1

    def record_completion(self, request_id, completion_time):
        """Enregistre qu'une demande a été complétée"""
        if request_id in self.request_tracking:
            info = self.request_tracking[request_id]
            info["completed"] = True
            info["completion_time"] = completion_time
            wait_time = completion_time - info["send_time"]

            if info["client_type"] == "VIP":
                self.test_results["vip_avg_wait_time"] = (
                        (self.test_results["vip_avg_wait_time"] * self.test_results["requests_completed"] + wait_time) /
                        (self.test_results["requests_completed"] + 1)
                )
            else:
                self.test_results["standard_avg_wait_time"] = (
                        (self.test_results["standard_avg_wait_time"] * self.test_results[
                            "requests_completed"] + wait_time) /
                        (self.test_results["requests_completed"] + 1)
                )

            self.test_results["requests_completed"] += 1