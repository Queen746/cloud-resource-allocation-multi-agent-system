# tests/performance/increasing_load_test.py

import time
import random
import logging
from datetime import datetime
from models.client import Client
from models.enums import ClientType
from models.resource_request import ResourceRequest


class IncreasingLoadTest:
    """
    Test avec un taux croissant de demandes par seconde.
    Identifie le point de rupture du système.
    """

    def __init__(self, system_launcher, initial_rps=1, increment=1,
                 increment_interval=30, max_rps=20, max_duration=600,
                 vip_ratio=0.2, dependency_ratio=0.3):
        self.system_launcher = system_launcher
        self.initial_rps = initial_rps  # Demandes par seconde initiales
        self.increment = increment  # Augmentation à chaque palier
        self.increment_interval = increment_interval  # Durée de chaque palier en secondes
        self.max_rps = max_rps  # RPS maximum à atteindre
        self.max_duration = max_duration  # Durée max du test en secondes
        self.vip_ratio = vip_ratio
        self.dependency_ratio = dependency_ratio
        self.logger = logging.getLogger("IncreasingLoadTest")

        # Préparer les clients
        self.vip_clients = [Client(f"vip-{i}", ClientType.VIP) for i in range(10)]
        self.standard_clients = [Client(f"std-{i}", ClientType.STANDARD) for i in range(40)]

        # Métriques
        self.sent_requests = []
        self.completed_requests = []
        self.failed_requests = []
        self.metrics_by_rps = {}  # {rps: {sent: X, completed: Y, avg_time: Z, ...}}

    def run(self):
        """Exécute le test de charge croissante"""
        self.logger.info(f"Démarrage du test - Charge croissante de {self.initial_rps} à {self.max_rps} req/s")

        start_time = time.time()
        request_id_counter = 0
        current_rps = self.initial_rps
        active_request_ids = set()
        all_dependencies = set()

        # Initialiser les métriques pour chaque palier de RPS
        for rps in range(self.initial_rps, self.max_rps + self.increment, self.increment):
            self.metrics_by_rps[rps] = {
                "sent": 0,
                "completed": 0,
                "failed": 0,
                "response_times": [],
                "vip_times": [],
                "std_times": [],
                "start_time": None,
                "end_time": None
            }

        # Boucle principale du test
        while (time.time() - start_time < self.max_duration and
               current_rps <= self.max_rps):

            # Marquer le début du palier actuel
            if self.metrics_by_rps[current_rps]["start_time"] is None:
                self.metrics_by_rps[current_rps]["start_time"] = time.time()
                self.logger.info(f"Palier {current_rps} req/s démarré")

            # Générer les demandes pour cette seconde
            for _ in range(current_rps):
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
                    "submit_time": time.time(),
                    "rps": current_rps  # Enregistrer le RPS actuel
                }

                # Envoyer la demande au système
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
                self.metrics_by_rps[current_rps]["sent"] += 1
                active_request_ids.add(request_id)
                all_dependencies.add(request_id)

            # Attendre 1 seconde avant la prochaine vague
            time.sleep(1)

            # Vérifier les demandes complétées
            completed = self.system_launcher.get_completed_requests()
            for request_id in completed:
                if request_id in active_request_ids:
                    active_request_ids.remove(request_id)
                    completion_time = time.time()

                    # Trouver les données originales de la demande
                    original_request = None
                    for req in self.sent_requests:
                        if req["id"] == request_id:
                            original_request = req
                            break

                    if original_request:
                        response_time = completion_time - original_request["submit_time"]
                        rps_level = original_request["rps"]

                        completion_data = {
                            "id": request_id,
                            "completion_time": completion_time,
                            "response_time": response_time,
                            "rps": rps_level
                        }

                        self.completed_requests.append(completion_data)
                        self.metrics_by_rps[rps_level]["completed"] += 1
                        self.metrics_by_rps[rps_level]["response_times"].append(response_time)

                        # Enregistrer le temps selon le type de client
                        if original_request["client"].client_type == ClientType.VIP:
                            self.metrics_by_rps[rps_level]["vip_times"].append(response_time)
                        else:
                            self.metrics_by_rps[rps_level]["std_times"].append(response_time)

            # Vérifier les demandes échouées
            failed = self.system_launcher.get_failed_requests()
            for request_id in failed:
                if request_id in active_request_ids:
                    active_request_ids.remove(request_id)
                    failure_time = time.time()

                    # Trouver les données originales de la demande
                    original_request = None
                    for req in self.sent_requests:
                        if req["id"] == request_id:
                            original_request = req
                            break

                    if original_request:
                        rps_level = original_request["rps"]

                        failure_data = {
                            "id": request_id,
                            "failure_time": failure_time,
                            "reason": self.system_launcher.get_failure_reason(request_id),
                            "rps": rps_level
                        }

                        self.failed_requests.append(failure_data)
                        self.metrics_by_rps[rps_level]["failed"] += 1

            # Vérifier s'il est temps de passer au palier suivant
            current_time = time.time()
            palier_start_time = self.metrics_by_rps[current_rps]["start_time"]
            if current_time - palier_start_time >= self.increment_interval:
                self.metrics_by_rps[current_rps]["end_time"] = current_time

                # Analyser rapidement les résultats du palier
                metrics = self.metrics_by_rps[current_rps]
                success_rate = metrics["completed"] / metrics["sent"] if metrics["sent"] > 0 else 0
                avg_time = sum(metrics["response_times"]) / len(metrics["response_times"]) if metrics[
                    "response_times"] else 0

                self.logger.info(f"Palier {current_rps} req/s terminé - "
                                 f"Succès: {success_rate * 100:.1f}%, "
                                 f"Temps moyen: {avg_time:.2f}s")

                # Passer au palier suivant
                current_rps += self.increment
                if current_rps > self.max_rps:
                    break

        end_time = time.time()
        test_duration = end_time - start_time

        # Rapport de test
        self.generate_report(test_duration)

    def generate_report(self, test_duration):
        """Génère un rapport détaillé des résultats du test"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"logs/test_increasing_load_{timestamp}.log"

        with open(report_filename, "w") as report_file:
            # En-tête du rapport
            report_file.write(f"=== Rapport de test de charge croissante ===\n")
            report_file.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            report_file.write(f"Durée totale: {test_duration:.2f} secondes\n")
            report_file.write(f"Charge: {self.initial_rps} à {self.max_rps} req/s\n")
            report_file.write(f"Intervalle d'incrémentation: {self.increment_interval}s\n\n")

            # Statistiques générales
            total_sent = len(self.sent_requests)
            total_completed = len(self.completed_requests)
            total_failed = len(self.failed_requests)

            report_file.write(f"Demandes envoyées: {total_sent}\n")
            report_file.write(f"Demandes complétées: {total_completed} ({total_completed / total_sent * 100:.2f}%)\n")
            report_file.write(f"Demandes échouées: {total_failed} ({total_failed / total_sent * 100:.2f}%)\n")
            report_file.write(f"Demandes en attente: {total_sent - total_completed - total_failed}\n\n")

            # Analyse par palier de RPS
            report_file.write("=== Analyse par palier ===\n")

            for rps in sorted(self.metrics_by_rps.keys()):
                metrics = self.metrics_by_rps[rps]

                # Ignorer les paliers non atteints
                if metrics["start_time"] is None:
                    continue

                report_file.write(f"\n--- Palier: {rps} req/s ---\n")

                # Durée du palier
                if metrics["end_time"] is None:
                    metrics["end_time"] = time.time()

                palier_duration = metrics["end_time"] - metrics["start_time"]
                report_file.write(f"Durée: {palier_duration:.2f}s\n")

                # Statistiques de base
                sent = metrics["sent"]
                completed = metrics["completed"]
                failed = metrics["failed"]

                report_file.write(f"Demandes envoyées: {sent}\n")
                report_file.write(f"Demandes complétées: {completed}")
                if sent > 0:
                    report_file.write(f" ({completed / sent * 100:.2f}%)")
                report_file.write("\n")

                report_file.write(f"Demandes échouées: {failed}")
                if sent > 0:
                    report_file.write(f" ({failed / sent * 100:.2f}%)")
                report_file.write("\n")

                # Temps de réponse
                response_times = metrics["response_times"]
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    max_response_time = max(response_times)
                    min_response_time = min(response_times)

                    # Calcul des percentiles
                    response_times.sort()
                    p50 = response_times[int(len(response_times) * 0.5)] if len(response_times) > 0 else 0
                    p90 = response_times[int(len(response_times) * 0.9)] if len(response_times) > 1 else 0
                    p95 = response_times[int(len(response_times) * 0.95)] if len(response_times) > 1 else 0
                    p99 = response_times[int(len(response_times) * 0.99)] if len(response_times) > 2 else 0

                    report_file.write(f"Temps de réponse moyen: {avg_response_time:.2f}s\n")
                    report_file.write(f"Temps de réponse min: {min_response_time:.2f}s\n")
                    report_file.write(f"Temps de réponse max: {max_response_time:.2f}s\n")
                    report_file.write(f"Percentile 50: {p50:.2f}s\n")
                    report_file.write(f"Percentile 90: {p90:.2f}s\n")
                    report_file.write(f"Percentile 95: {p95:.2f}s\n")
                    report_file.write(f"Percentile 99: {p99:.2f}s\n")

                # Analyse par type de client
                vip_times = metrics["vip_times"]
                std_times = metrics["std_times"]

                if vip_times:
                    avg_vip_time = sum(vip_times) / len(vip_times)
                    report_file.write(f"Temps moyen VIP: {avg_vip_time:.2f}s\n")

                if std_times:
                    avg_std_time = sum(std_times) / len(std_times)
                    report_file.write(f"Temps moyen standard: {avg_std_time:.2f}s\n")

                if vip_times and std_times:
                    equity_ratio = avg_std_time / avg_vip_time
                    report_file.write(f"Ratio d'équité (std/vip): {equity_ratio:.2f}\n")

            # Détermination du point de rupture
            best_rps = self.initial_rps
            for rps, metrics in sorted(self.metrics_by_rps.items()):
                if metrics["start_time"] is None:
                    continue

                sent = metrics["sent"]
                completed = metrics["completed"]
                success_rate = completed / sent if sent > 0 else 0

                # Si le taux de succès est supérieur à 95%, on considère que ce palier est stable
                if success_rate >= 0.95:
                    best_rps = rps
                else:
                    break

            report_file.write(f"\n=== Point de rupture ===\n")
            report_file.write(f"Charge maximale stable: {best_rps} req/s\n")

            next_rps = best_rps + self.increment
            if next_rps in self.metrics_by_rps and self.metrics_by_rps[next_rps]["start_time"] is not None:
                metrics = self.metrics_by_rps[next_rps]
                sent = metrics["sent"]
                completed = metrics["completed"]
                success_rate = completed / sent if sent > 0 else 0

                report_file.write(f"Premier palier instable: {next_rps} req/s "
                                  f"(taux de succès: {success_rate * 100:.2f}%)\n")

            # Recommandations
            report_file.write("\n=== Recommandations ===\n")
            report_file.write(
                f"Basé sur les résultats, nous recommandons de ne pas dépasser {int(best_rps * 0.8)} req/s "
                f"en production pour garantir une marge de sécurité adéquate.\n")