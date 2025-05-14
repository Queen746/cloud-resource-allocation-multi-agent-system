# tests/performance/burst_load_test.py

import time
import random
import logging
import threading
from datetime import datetime
from models.client import Client
from models.enums import ClientType
from models.resource_request import ResourceRequest


class BurstLoadTest:
    """
    Test de pic de charge soudain, simulant un afflux massif de demandes
    pendant une courte période, suivi d'une période de récupération.
    Évalue la résilience du système face aux pics d'activité imprévus.
    """

    def __init__(self, system_launcher, base_rps=2, burst_rps=20,
                 burst_duration=30, recovery_duration=120,
                 vip_ratio=0.2, dependency_ratio=0.3):
        self.system_launcher = system_launcher
        self.base_rps = base_rps  # Demandes par seconde en régime normal
        self.burst_rps = burst_rps  # Demandes par seconde pendant le pic
        self.burst_duration = burst_duration  # Durée du pic en secondes
        self.recovery_duration = recovery_duration  # Durée de récupération après le pic
        self.vip_ratio = vip_ratio
        self.dependency_ratio = dependency_ratio
        self.logger = logging.getLogger("BurstLoadTest")

        # Préparer les clients
        self.vip_clients = [Client(f"vip-{i}", ClientType.VIP) for i in range(10)]
        self.standard_clients = [Client(f"std-{i}", ClientType.STANDARD) for i in range(40)]

        # Métriques
        self.sent_requests = []
        self.completed_requests = []
        self.failed_requests = []
        self.phase_metrics = {
            "pre_burst": {"sent": 0, "completed": 0, "failed": 0, "response_times": []},
            "during_burst": {"sent": 0, "completed": 0, "failed": 0, "response_times": []},
            "post_burst": {"sent": 0, "completed": 0, "failed": 0, "response_times": []}
        }

        # Contrôle de l'exécution
        self.stop_flag = False
        self.collection_thread = None

    def run(self):
        """Exécute le test de pic de charge"""
        self.logger.info(f"Démarrage du test - Pic de charge de {self.burst_rps} req/s pendant {self.burst_duration}s")

        # Démarrer le thread de collecte des demandes complétées/échouées
        self.stop_flag = False
        self.collection_thread = threading.Thread(target=self._collect_results)
        self.collection_thread.start()

        # Phase pré-pic (charge normale)
        phase_duration = 60  # 1 minute de charge normale avant le pic
        self.logger.info(f"Phase pré-pic - {self.base_rps} req/s pendant {phase_duration}s")
        self._generate_load(self.base_rps, phase_duration, "pre_burst")

        # Phase de pic
        self.logger.info(f"Phase de pic - {self.burst_rps} req/s pendant {self.burst_duration}s")
        self._generate_load(self.burst_rps, self.burst_duration, "during_burst")

        # Phase post-pic (récupération)
        self.logger.info(f"Phase de récupération - {self.base_rps} req/s pendant {self.recovery_duration}s")
        self._generate_load(self.base_rps, self.recovery_duration, "post_burst")

        # Attendre que tous les résultats soient collectés
        time.sleep(10)  # Laisser le temps aux dernières demandes d'être traitées
        self.stop_flag = True
        self.collection_thread.join()

        # Générer le rapport
        self.generate_report()

    def _generate_load(self, rps, duration, phase):
        """Génère une charge avec un nombre spécifique de requêtes par seconde"""
        start_time = time.time()
        request_id_counter = 0
        all_dependencies = set()

        while time.time() - start_time < duration:
            phase_start_time = time.time()

            # Générer les demandes pour cette seconde
            for _ in range(rps):
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
                duration = random.uniform(10.0, 60.0)

                # Gestion des dépendances
                dependencies = set()
                if random.random() < self.dependency_ratio and all_dependencies:
                    num_deps = random.randint(1, min(3, len(all_dependencies)))
                    dependencies = set(random.sample(all_dependencies, num_deps))

                # Créer et envoyer la demande
                self.logger.info(f"[{phase}] Envoi de la demande {request_id} du client {client.id} "
                                 f"(CPU: {cpu:.1f}, Mémoire: {memory:.1f}, Durée: {duration:.1f}s)")

                request_data = {
                    "id": request_id,
                    "client": client,
                    "cpu": cpu,
                    "memory": memory,
                    "duration": duration,
                    "dependencies": dependencies,
                    "submit_time": time.time(),
                    "phase": phase
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
                self.phase_metrics[phase]["sent"] += 1
                all_dependencies.add(request_id)

            # Attendre jusqu'à la prochaine seconde
            processing_time = time.time() - phase_start_time
            if processing_time < 1.0:
                time.sleep(1.0 - processing_time)

    def _collect_results(self):
        """Thread séparé pour collecter les résultats des demandes"""
        while not self.stop_flag:
            # Vérifier les demandes complétées
            completed = self.system_launcher.get_completed_requests()
            for request_id in completed:
                # Vérifier si la demande n'a pas déjà été traitée
                if not any(comp["id"] == request_id for comp in self.completed_requests):
                    completion_time = time.time()

                    # Trouver les données originales de la demande
                    original_request = None
                    for req in self.sent_requests:
                        if req["id"] == request_id:
                            original_request = req
                            break

                    if original_request:
                        response_time = completion_time - original_request["submit_time"]
                        phase = original_request["phase"]

                        completion_data = {
                            "id": request_id,
                            "completion_time": completion_time,
                            "response_time": response_time,
                            "phase": phase
                        }

                        self.completed_requests.append(completion_data)
                        self.phase_metrics[phase]["completed"] += 1
                        self.phase_metrics[phase]["response_times"].append(response_time)

            # Vérifier les demandes échouées
            failed = self.system_launcher.get_failed_requests()
            for request_id in failed:
                # Vérifier si la demande n'a pas déjà été traitée
                if not any(fail["id"] == request_id for fail in self.failed_requests):
                    failure_time = time.time()

                    # Trouver les données originales de la demande
                    original_request = None
                    for req in self.sent_requests:
                        if req["id"] == request_id:
                            original_request = req
                            break

                    if original_request:
                        phase = original_request["phase"]

                        failure_data = {
                            "id": request_id,
                            "failure_time": failure_time,
                            "reason": self.system_launcher.get_failure_reason(request_id),
                            "phase": phase
                        }

                        self.failed_requests.append(failure_data)
                        self.phase_metrics[phase]["failed"] += 1

            # Attendre avant la prochaine vérification
            time.sleep(1)

    def generate_report(self):
        """Génère un rapport détaillé des résultats du test"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"logs/test_burst_load_{timestamp}.log"

        with open(report_filename, "w") as report_file:
            # En-tête du rapport
            report_file.write(f"=== Rapport de test de pic de charge ===\n")
            report_file.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            report_file.write(f"Configuration: Base {self.base_rps} req/s, "
                              f"Pic {self.burst_rps} req/s pendant {self.burst_duration}s\n")
            report_file.write(f"Durée de récupération: {self.recovery_duration}s\n\n")

            # Statistiques générales
            total_sent = len(self.sent_requests)
            total_completed = len(self.completed_requests)
            total_failed = len(self.failed_requests)

            report_file.write(f"Demandes envoyées: {total_sent}\n")
            report_file.write(f"Demandes complétées: {total_completed} ({total_completed / total_sent * 100:.2f}%)\n")
            report_file.write(f"Demandes échouées: {total_failed} ({total_failed / total_sent * 100:.2f}%)\n")
            report_file.write(f"Demandes en attente: {total_sent - total_completed - total_failed}\n\n")

            # Analyse par phase
            report_file.write("=== Analyse par phase ===\n")

            for phase in ["pre_burst", "during_burst", "post_burst"]:
                metrics = self.phase_metrics[phase]

                if phase == "pre_burst":
                    phase_name = "Pré-pic (charge normale)"
                elif phase == "during_burst":
                    phase_name = "Pendant le pic"
                else:
                    phase_name = "Post-pic (récupération)"

                report_file.write(f"\n--- {phase_name} ---\n")

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

            # Analyse de l'impact du pic
            report_file.write("\n=== Impact du pic de charge ===\n")

            pre_burst_metrics = self.phase_metrics["pre_burst"]
            during_burst_metrics = self.phase_metrics["during_burst"]
            post_burst_metrics = self.phase_metrics["post_burst"]

            # Temps de réponse avant, pendant et après le pic
            if pre_burst_metrics["response_times"] and during_burst_metrics["response_times"] and post_burst_metrics[
                "response_times"]:
                pre_avg = sum(pre_burst_metrics["response_times"]) / len(pre_burst_metrics["response_times"])
                during_avg = sum(during_burst_metrics["response_times"]) / len(during_burst_metrics["response_times"])
                post_avg = sum(post_burst_metrics["response_times"]) / len(post_burst_metrics["response_times"])

                report_file.write(f"Temps de réponse moyen avant le pic: {pre_avg:.2f}s\n")
                report_file.write(f"Temps de réponse moyen pendant le pic: {during_avg:.2f}s\n")
                report_file.write(f"Temps de réponse moyen après le pic: {post_avg:.2f}s\n\n")

                # Facteur d'augmentation pendant le pic
                increase_factor = during_avg / pre_avg if pre_avg > 0 else float('inf')
                report_file.write(f"Facteur d'augmentation pendant le pic: {increase_factor:.2f}x\n")

                # Facteur de récupération après le pic
                recovery_factor = post_avg / pre_avg if pre_avg > 0 else float('inf')
                report_file.write(f"Facteur de récupération post-pic: {recovery_factor:.2f}x\n")

                # Interprétation
                if recovery_factor <= 1.2:  # Moins de 20% de différence
                    report_file.write(
                        "Récupération complète: Le système a retrouvé ses performances normales après le pic.\n")
                elif recovery_factor <= 1.5:
                    report_file.write(
                        "Récupération partielle: Le système présente toujours un impact résiduel après le pic.\n")
                else:
                    report_file.write(
                        "Récupération difficile: Le système montre des signes de saturation persistante après le pic.\n")

            # Taux de succès avant, pendant et après le pic
            pre_success_rate = pre_burst_metrics["completed"] / pre_burst_metrics["sent"] if pre_burst_metrics[
                                                                                                 "sent"] > 0 else 0
            during_success_rate = during_burst_metrics["completed"] / during_burst_metrics["sent"] if \
            during_burst_metrics["sent"] > 0 else 0
            post_success_rate = post_burst_metrics["completed"] / post_burst_metrics["sent"] if post_burst_metrics[
                                                                                                    "sent"] > 0 else 0

            report_file.write(f"\nTaux de succès avant le pic: {pre_success_rate * 100:.2f}%\n")
            report_file.write(f"Taux de succès pendant le pic: {during_success_rate * 100:.2f}%\n")
            report_file.write(f"Taux de succès après le pic: {post_success_rate * 100:.2f}%\n")

            # Conclusion et recommandations
            report_file.write("\n=== Conclusion et recommandations ===\n")

            impact_level = "faible"
            if increase_factor > 5 or during_success_rate < 0.7:
                impact_level = "sévère"
            elif increase_factor > 2 or during_success_rate < 0.9:
                impact_level = "modéré"

            report_file.write(f"Impact global du pic de charge: {impact_level}\n")

            if impact_level == "faible":
                report_file.write("Le système démontre une bonne résilience face aux pics de charge soudains.\n")
                report_file.write("Recommandation: Maintenir la configuration actuelle.\n")
            elif impact_level == "modéré":
                report_file.write("Le système subit un impact notable mais gérable lors des pics de charge.\n")
                report_file.write("Recommandations:\n")
                report_file.write(
                    "1. Optimiser l'algorithme d'ordonnancement pour mieux prioriser en période de forte charge\n")
                report_file.write("2. Augmenter les ressources disponibles de 20% pour absorber les pics\n")
                report_file.write("3. Mettre en place un mécanisme de limitation de débit adaptatif\n")
            else:
                report_file.write(
                    "Le système est fortement impacté par les pics de charge, avec une dégradation significative.\n")
                report_file.write("Recommandations urgentes:\n")
                report_file.write("1. Revoir l'architecture pour améliorer l'élasticité du système\n")
                report_file.write("2. Implémenter un mécanisme de limitation des demandes en entrée\n")
                report_file.write("3. Augmenter substantiellement les ressources disponibles (min. 50%)\n")
                report_file.write("4. Mettre en place un système de mise en file d'attente externe\n")

        self.logger.info(f"Rapport généré: {report_filename}")
        return report_filename