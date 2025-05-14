# tests/performance/constant_load_test.py

import time
import random
import logging
from datetime import datetime
from models.client import Client
from models.enums import ClientType
from models.resource_request import ResourceRequest


class ConstantLoadTest:
    """
    Test avec un taux fixe de demandes par seconde pendant une période donnée.
    Mesure la capacité du système à maintenir des performances stables.
    """

    def __init__(self, system_launcher, requests_per_second=5, duration_seconds=300,
                 vip_ratio=0.2, dependency_ratio=0.3):
        self.system_launcher = system_launcher
        self.requests_per_second = requests_per_second
        self.duration_seconds = duration_seconds
        self.vip_ratio = vip_ratio  # 20% de clients VIP par défaut
        self.dependency_ratio = dependency_ratio  # 30% des demandes ont des dépendances
        self.logger = logging.getLogger("ConstantLoadTest")

        # Préparer les clients
        self.vip_clients = [Client(f"vip-{i}", ClientType.VIP) for i in range(10)]
        self.standard_clients = [Client(f"std-{i}", ClientType.STANDARD) for i in range(40)]

        # Métriques
        self.sent_requests = []
        self.completed_requests = []
        self.failed_requests = []

    def run(self):
        """Exécute le test de charge constante"""
        self.logger.info(f"Démarrage du test - {self.requests_per_second} req/s pendant {self.duration_seconds}s")

        start_time = time.time()
        request_id_counter = 0
        active_request_ids = set()  # Pour suivre les demandes en cours
        all_dependencies = set()  # Pour suivre les dépendances disponibles

        while time.time() - start_time < self.duration_seconds:
            # Générer les demandes pour cette seconde
            for _ in range(self.requests_per_second):
                request_id_counter += 1
                request_id = f"req-{request_id_counter}"

                # Sélectionner le type de client
                if random.random() < self.vip_ratio:
                    client = random.choice(self.vip_clients)
                else:
                    client = random.choice(self.standard_clients)

                # Générer des caractéristiques aléatoires
                cpu = random.uniform(1.0, 5.0)
                memory = random.uniform(2.0, 8.0)
                duration = random.uniform(10.0, 90.0)

                # Gestion des dépendances
                dependencies = set()
                if random.random() < self.dependency_ratio and all_dependencies:
                    # Sélectionner 1 à 3 dépendances aléatoires parmi les demandes existantes
                    num_deps = random.randint(1, min(3, len(all_dependencies)))
                    dependencies = set(random.sample(all_dependencies, num_deps))

                # Créer et envoyer la demande
                self.logger.info(f"Envoi de la demande {request_id} du client {client.id} "
                                 f"(CPU: {cpu:.1f}, Mémoire: {memory:.1f}, Durée: {duration:.1f}s, "
                                 f"Dépendances: {dependencies})")

                request_data = {
                    "id": request_id,
                    "client": client,
                    "cpu": cpu,
                    "memory": memory,
                    "duration": duration,
                    "dependencies": dependencies,
                    "submit_time": time.time()
                }

                # Envoyer la demande au système (simulation)
                self.system_launcher.submit_request(
                    client=client,
                    request_id=request_id,
                    cpu_required=cpu,
                    memory_required=memory,
                    estimated_duration=duration,
                    dependencies=dependencies
                )

                # Enregistrer les métriques
                self.sent_requests.append(request_data)
                active_request_ids.add(request_id)
                all_dependencies.add(request_id)

            # Attendre 1 seconde avant la prochaine vague
            time.sleep(1)

            # Vérifier les demandes complétées (à implémenter selon votre système)
            completed = self.system_launcher.get_completed_requests()
            for request_id in completed:
                if request_id in active_request_ids:
                    active_request_ids.remove(request_id)
                    completion_data = {
                        "id": request_id,
                        "completion_time": time.time()
                    }
                    self.completed_requests.append(completion_data)

            # Vérifier les demandes échouées (à implémenter selon votre système)
            failed = self.system_launcher.get_failed_requests()
            for request_id in failed:
                if request_id in active_request_ids:
                    active_request_ids.remove(request_id)
                    failure_data = {
                        "id": request_id,
                        "failure_time": time.time(),
                        "reason": self.system_launcher.get_failure_reason(request_id)
                    }
                    self.failed_requests.append(failure_data)

        end_time = time.time()
        test_duration = end_time - start_time

        # Rapport de test
        self.generate_report(test_duration)

    def generate_report(self, test_duration):
        """Génère un rapport détaillé des résultats du test"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"logs/test_constant_load_{timestamp}.log"

        with open(report_filename, "w") as report_file:
            # En-tête du rapport
            report_file.write(f"=== Rapport de test de charge constante ===\n")
            report_file.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            report_file.write(f"Durée: {test_duration:.2f} secondes\n")
            report_file.write(f"Demandes par seconde: {self.requests_per_second}\n")
            report_file.write(f"Ratio VIP: {self.vip_ratio:.2f}\n")
            report_file.write(f"Ratio de dépendances: {self.dependency_ratio:.2f}\n\n")

            # Statistiques générales
            total_sent = len(self.sent_requests)
            total_completed = len(self.completed_requests)
            total_failed = len(self.failed_requests)

            report_file.write(f"Demandes envoyées: {total_sent}\n")
            report_file.write(f"Demandes complétées: {total_completed} ({total_completed / total_sent * 100:.2f}%)\n")
            report_file.write(f"Demandes échouées: {total_failed} ({total_failed / total_sent * 100:.2f}%)\n")
            report_file.write(f"Demandes en attente: {total_sent - total_completed - total_failed}\n\n")

            # Temps de réponse
            if self.completed_requests:
                response_times = []
                for completed in self.completed_requests:
                    request_id = completed["id"]
                    for sent in self.sent_requests:
                        if sent["id"] == request_id:
                            submit_time = sent["submit_time"]
                            completion_time = completed["completion_time"]
                            response_time = completion_time - submit_time
                            response_times.append(response_time)
                            break

                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)

                # Calcul des percentiles
                response_times.sort()
                p50 = response_times[int(len(response_times) * 0.5)]
                p90 = response_times[int(len(response_times) * 0.9)]
                p95 = response_times[int(len(response_times) * 0.95)]
                p99 = response_times[int(len(response_times) * 0.99)]

                report_file.write(f"Temps de réponse moyen: {avg_response_time:.2f}s\n")
                report_file.write(f"Temps de réponse min: {min_response_time:.2f}s\n")
                report_file.write(f"Temps de réponse max: {max_response_time:.2f}s\n")
                report_file.write(f"Percentile 50: {p50:.2f}s\n")
                report_file.write(f"Percentile 90: {p90:.2f}s\n")
                report_file.write(f"Percentile 95: {p95:.2f}s\n")
                report_file.write(f"Percentile 99: {p99:.2f}s\n\n")

            # Analyse par type de client
            vip_times = []
            std_times = []

            for completed in self.completed_requests:
                request_id = completed["id"]
                for sent in self.sent_requests:
                    if sent["id"] == request_id:
                        client = sent["client"]
                        submit_time = sent["submit_time"]
                        completion_time = completed["completion_time"]
                        response_time = completion_time - submit_time

                        if client.client_type == ClientType.VIP:
                            vip_times.append(response_time)
                        else:
                            std_times.append(response_time)
                        break

            if vip_times:
                avg_vip_time = sum(vip_times) / len(vip_times)
                report_file.write(f"Temps moyen VIP: {avg_vip_time:.2f}s\n")

            if std_times:
                avg_std_time = sum(std_times) / len(std_times)
                report_file.write(f"Temps moyen standard: {avg_std_time:.2f}s\n")

            if vip_times and std_times:
                equity_ratio = avg_std_time / avg_vip_time
                report_file.write(f"Ratio d'équité (std/vip): {equity_ratio:.2f}\n\n")

            # Analyse des dépendances
            dependency_success = 0
            dependency_total = 0

            for sent in self.sent_requests:
                if sent["dependencies"]:
                    dependency_total += 1
                    request_id = sent["id"]
                    if any(comp["id"] == request_id for comp in self.completed_requests):
                        dependency_success += 1

            if dependency_total > 0:
                dep_success_rate = dependency_success / dependency_total * 100
                report_file.write(f"Taux de succès des dépendances: {dep_success_rate:.2f}%\n")
                report_file.write(f"({dependency_success}/{dependency_total} demandes avec dépendances complétées)\n\n")

            # Échecs
            if total_failed > 0:
                failure_reasons = {}
                for failed in self.failed_requests:
                    reason = failed.get("reason", "unknown")
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

                report_file.write("Analyse des échecs:\n")
                for reason, count in failure_reasons.items():
                    report_file.write(f"  - {reason}: {count} ({count / total_failed * 100:.2f}%)\n")

        self.logger.info(f"Rapport généré: {report_filename}")
        return report_filename