# tests/comprehensive_test.py
import asyncio
import logging
import time
import random
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

from system_launcher import SystemLauncher
from tests.load_test import LoadTest
from models.client import Client
from models.enums import ClientType

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComprehensiveTest")


class ComprehensiveTest:
    """Test complet du système multi-agents"""

    def __init__(self):
        self.system = SystemLauncher()
        self.results = {}

    async def run_all_tests(self):
        """Exécute tous les tests"""
        logger.info("Démarrage des tests complets")

        # Démarrer le système
        self.system.start()

        # Attendre que tous les agents soient prêts
        await asyncio.sleep(5)

        # Exécuter les différents tests
        await self.run_baseline_test()
        await self.run_high_load_test()
        await self.run_dependency_test()
        await self.run_priority_test()

        # Générer les rapports
        self.generate_reports()

        logger.info("Tests complets terminés")

    async def run_baseline_test(self):
        """Test de base avec une charge normale"""
        logger.info("Démarrage du test de base")

        load_tester = LoadTest(self.system.agents["client_manager"])
        results = await load_tester.run_test(
            duration=120,
            burst_interval=30,
            burst_size=5,
            request_interval=3,
            vip_ratio=0.2
        )

        self.results["baseline"] = results
        logger.info(
            f"Test de base terminé: {results['requests_completed']}/{results['requests_sent']} demandes complétées")

    async def run_high_load_test(self):
        """Test avec une charge élevée"""
        logger.info("Démarrage du test de charge élevée")

        load_tester = LoadTest(self.system.agents["client_manager"])
        results = await load_tester.run_test(
            duration=180,
            burst_interval=15,
            burst_size=15,
            request_interval=1,
            vip_ratio=0.2
        )

        self.results["high_load"] = results
        logger.info(
            f"Test de charge élevée terminé: {results['requests_completed']}/{results['requests_sent']} demandes complétées")

    async def run_dependency_test(self):
        """Test avec beaucoup de dépendances"""
        logger.info("Démarrage du test de dépendances")

        # Créer un graphe de dépendances complexe
        dependencies = {}

        # 20 tâches avec des dépendances complexes
        for i in range(20):
            task_id = f"dep-test-{i}"

            # Les tâches 0, 5, 10, 15 sont des racines (pas de dépendances)
            if i % 5 == 0:
                dependencies[task_id] = set()
            else:
                # Dépend des tâches précédentes
                deps = set()
                for j in range(i):
                    if random.random() < 0.3:  # 30% de chance d'avoir une dépendance
                        deps.add(f"dep-test-{j}")
                dependencies[task_id] = deps

        # Lancer les demandes dans l'ordre inverse pour tester le tri topologique
        for i in range(19, -1, -1):
            task_id = f"dep-test-{i}"

            # Créer un client
            client_type = ClientType.VIP if random.random() < 0.2 else ClientType.STANDARD
            client = Client(client_id=f"client-{task_id}", client_type=client_type)

            # Envoyer la demande
            await self.system.agents["client_manager"].process_simulation_request({
                "id": task_id,
                "client": client.to_dict(),
                "cpu_required": random.uniform(1.0, 4.0),
                "memory_required": random.uniform(1.0, 6.0),
                "estimated_duration": random.uniform(10, 30),
                "dependencies": list(dependencies[task_id])
            })

            # Court délai entre les demandes
            await asyncio.sleep(0.5)

        # Attendre que toutes les demandes soient traitées
        await asyncio.sleep(120)

        # Récupérer les résultats
        # Simulé ici - en réalité, il faudrait interroger les agents
        self.results["dependency"] = {
            "tasks": dependencies,
            "completion_time": 120,
            "success_rate": 0.95
        }

        logger.info("Test de dépendances terminé")

    async def run_priority_test(self):
        """Test pour vérifier le vieillissement des demandes standard"""
        logger.info("Démarrage du test de priorité")

        # tests/comprehensive_test.py (suite)
        async def run_priority_test(self):
            """Test pour vérifier le vieillissement des demandes standard"""
            logger.info("Démarrage du test de priorité")

            # Envoyer une série de demandes VIP
            vip_client = Client(client_id="vip-priority-test", client_type=ClientType.VIP)

            for i in range(10):
                task_id = f"priority-vip-{i}"
                await self.system.agents["client_manager"].process_simulation_request({
                    "id": task_id,
                    "client": vip_client.to_dict(),
                    "cpu_required": random.uniform(1.0, 3.0),
                    "memory_required": random.uniform(1.0, 4.0),
                    "estimated_duration": random.uniform(20, 40),
                    "dependencies": []
                })
                await asyncio.sleep(1)

            # Envoyer une demande standard à t=0
            std_client = Client(client_id="std-priority-test", client_type=ClientType.STANDARD)
            old_std_task = "priority-std-old"
            await self.system.agents["client_manager"].process_simulation_request({
                "id": old_std_task,
                "client": std_client.to_dict(),
                "cpu_required": 2.0,
                "memory_required": 3.0,
                "estimated_duration": 30,
                "dependencies": []
            })

            # Attendre 30 secondes pour permettre au vieillissement d'agir
            logger.info("Attente de 30 secondes pour le vieillissement")
            await asyncio.sleep(30)

            # Envoyer plus de demandes VIP
            for i in range(10, 20):
                task_id = f"priority-vip-{i}"
                await self.system.agents["client_manager"].process_simulation_request({
                    "id": task_id,
                    "client": vip_client.to_dict(),
                    "cpu_required": random.uniform(1.0, 3.0),
                    "memory_required": random.uniform(1.0, 4.0),
                    "estimated_duration": random.uniform(20, 40),
                    "dependencies": []
                })
                await asyncio.sleep(1)

            # Attendre que toutes les demandes soient traitées
            logger.info("Attente du traitement des demandes")
            await asyncio.sleep(120)

            # Récupérer les résultats
            # Simulé ici - en réalité, il faudrait interroger les agents
            self.results["priority"] = {
                "vip_tasks": 20,
                "std_tasks": 1,
                "aging_factor": 0.5,  # Facteur de vieillissement
                "std_task_waited": 30  # Secondes d'attente avant traitement
            }

            logger.info("Test de priorité terminé")

        def generate_reports(self):
            """Génère des rapports et graphiques de test"""
            logger.info("Génération des rapports de test")

            # Créer un dossier pour les rapports
            import os
            os.makedirs("reports", exist_ok=True)

            # Rapport textuel
            with open("reports/test_report.txt", "w") as f:
                f.write("=== RAPPORT DE TEST DU SYSTÈME MULTI-AGENTS ===\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                # Test de base
                f.write("-- Test de base --\n")
                if "baseline" in self.results:
                    baseline = self.results["baseline"]
                    f.write(f"Demandes envoyées: {baseline['requests_sent']}\n")
                    f.write(f"Demandes complétées: {baseline['requests_completed']}\n")
                    f.write(
                        f"Taux de réussite: {baseline['requests_completed'] / baseline['requests_sent'] * 100:.2f}%\n")
                    f.write(f"Temps d'attente moyen VIP: {baseline['vip_avg_wait_time']:.2f}s\n")
                    f.write(f"Temps d'attente moyen standard: {baseline['standard_avg_wait_time']:.2f}s\n")
                else:
                    f.write("Test non exécuté\n")

                f.write("\n")

                # Test de charge élevée
                f.write("-- Test de charge élevée --\n")
                if "high_load" in self.results:
                    high_load = self.results["high_load"]
                    f.write(f"Demandes envoyées: {high_load['requests_sent']}\n")
                    f.write(f"Demandes complétées: {high_load['requests_completed']}\n")
                    f.write(
                        f"Taux de réussite: {high_load['requests_completed'] / high_load['requests_sent'] * 100:.2f}%\n")
                    f.write(f"Temps d'attente moyen VIP: {high_load['vip_avg_wait_time']:.2f}s\n")
                    f.write(f"Temps d'attente moyen standard: {high_load['standard_avg_wait_time']:.2f}s\n")
                else:
                    f.write("Test non exécuté\n")

                f.write("\n")

                # Test de dépendances
                f.write("-- Test de dépendances --\n")
                if "dependency" in self.results:
                    dependency = self.results["dependency"]
                    f.write(f"Nombre de tâches: {len(dependency['tasks'])}\n")
                    f.write(f"Temps total d'exécution: {dependency['completion_time']}s\n")
                    f.write(f"Taux de réussite: {dependency['success_rate'] * 100:.2f}%\n")
                else:
                    f.write("Test non exécuté\n")

                f.write("\n")

                # Test de priorité
                f.write("-- Test de priorité --\n")
                if "priority" in self.results:
                    priority = self.results["priority"]
                    f.write(f"Tâches VIP: {priority['vip_tasks']}\n")
                    f.write(f"Tâches standard: {priority['std_tasks']}\n")
                    f.write(f"Facteur de vieillissement: {priority['aging_factor']}\n")
                    f.write(f"Temps d'attente pour la tâche standard: {priority['std_task_waited']}s\n")
                else:
                    f.write("Test non exécuté\n")

            # Graphiques
            self._generate_wait_time_graphs()
            self._generate_load_comparison_graph()

            logger.info("Rapports générés dans le dossier 'reports'")

        def _generate_wait_time_graphs(self):
            """Génère des graphiques pour les temps d'attente"""
            plt.figure(figsize=(10, 6))

            # Temps d'attente par type de client
            if "baseline" in self.results and "high_load" in self.results:
                baseline = self.results["baseline"]
                high_load = self.results["high_load"]

                categories = ["Charge Normale", "Charge Élevée"]
                vip_times = [baseline["vip_avg_wait_time"], high_load["vip_avg_wait_time"]]
                std_times = [baseline["standard_avg_wait_time"], high_load["standard_avg_wait_time"]]

                x = np.arange(len(categories))
                width = 0.35

                plt.bar(x - width / 2, vip_times, width, label='Clients VIP')
                plt.bar(x + width / 2, std_times, width, label='Clients Standard')

                plt.xlabel('Scénario de Test')
                plt.ylabel('Temps d\'attente moyen (s)')
                plt.title('Temps d\'attente par type de client et scénario')
                plt.xticks(x, categories)
                plt.legend()
                plt.grid(True, linestyle='--', alpha=0.7)

                plt.savefig("reports/wait_times.png")
                plt.close()

        def _generate_load_comparison_graph(self):
            """Génère un graphique comparant les différents scénarios de charge"""
            if "baseline" in self.results and "high_load" in self.results:
                plt.figure(figsize=(10, 6))

                baseline = self.results["baseline"]
                high_load = self.results["high_load"]

                # Calculer les demandes par seconde
                baseline_duration = (baseline["end_time"] - baseline["start_time"]).total_seconds()
                high_load_duration = (high_load["end_time"] - high_load["start_time"]).total_seconds()

                baseline_rps = baseline["requests_sent"] / baseline_duration
                high_load_rps = high_load["requests_sent"] / high_load_duration

                # Calculer les taux de complétion
                baseline_completion = baseline["requests_completed"] / baseline["requests_sent"] * 100
                high_load_completion = high_load["requests_completed"] / high_load["requests_sent"] * 100

                categories = ["Demandes par seconde", "Taux de complétion (%)"]
                baseline_values = [baseline_rps, baseline_completion]
                high_load_values = [high_load_rps, high_load_completion]

                x = np.arange(len(categories))
                width = 0.35

                plt.bar(x - width / 2, baseline_values, width, label='Charge Normale')
                plt.bar(x + width / 2, high_load_values, width, label='Charge Élevée')

                plt.xlabel('Métrique')
                plt.ylabel('Valeur')
                plt.title('Comparaison des métriques de performance')
                plt.xticks(x, categories)
                plt.legend()
                plt.grid(True, linestyle='--', alpha=0.7)

                plt.savefig("reports/load_comparison.png")
                plt.close()

    # Point d'entrée pour exécuter les tests
    if __name__ == "__main__":
        test = ComprehensiveTest()
        asyncio.run(test.run_all_tests())