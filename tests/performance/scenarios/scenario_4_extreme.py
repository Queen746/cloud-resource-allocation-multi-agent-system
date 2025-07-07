"""
Scénario 4: Test de Saturation Extrême
Pousse le système à ses limites absolues pour identifier le point de rupture.
"""

import asyncio
import time
import random
import json
import logging
from datetime import datetime
from pathlib import Path
from collections import deque, defaultdict
import threading


class ExtremeLoadTestScenario:
    """Test de saturation extrême pour identifier les limites du système."""

    def __init__(self):
        self.test_name = "Test de Saturation Extrême"
        self.description = "Pousse le système à ses limites absolues"

        # Configuration extrême
        self.max_requests = 5000  # 5000 requêtes au total
        self.burst_phases = [
            {"name": "Phase 1 - Montée progressive", "duration": 30, "start_rps": 5, "end_rps": 25},
            {"name": "Phase 2 - Stress intense", "duration": 60, "start_rps": 25, "end_rps": 50},
            {"name": "Phase 3 - Saturation maximale", "duration": 45, "start_rps": 50, "end_rps": 100},
            {"name": "Phase 4 - Stress extrême", "duration": 30, "start_rps": 100, "end_rps": 200},
            {"name": "Phase 5 - Recovery", "duration": 60, "start_rps": 200, "end_rps": 5}
        ]

        # Métriques de saturation
        self.vip_ratio = 0.25  # 25% VIP sous stress
        self.aging_factor = 3.0  # Plus agressif sous charge extrême
        self.dependency_ratio = 0.15  # Moins de dépendances sous stress

        # Stockage des résultats
        self.results = []
        self.performance_data = defaultdict(list)
        self.failure_points = []
        self.saturation_metrics = {
            'max_sustainable_rps': 0,
            'breaking_point_rps': 0,
            'max_queue_size': 0,
            'max_response_time': 0,
            'failure_rate': 0.0,
            'recovery_time': 0
        }

        # Simulation système
        self.vip_queue = deque()
        self.standard_queue = deque()
        self.completed_requests = set()
        self.failed_requests = set()
        self.processing_requests = {}
        self.system_resources = {
            'cpu_usage': 0.0,
            'memory_usage': 0.0,
            'network_latency': 0.0
        }

        # État système pour saturation
        self.system_overloaded = False
        self.queue_overflow_threshold = 1000
        self.response_time_threshold = 30.0  # 30s = seuil critique

        # Logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f"Scenario4-{datetime.now().strftime('%H%M%S')}")

    def generate_extreme_request(self, phase_name, current_rps):
        """Génère une requête adaptée aux conditions extrêmes."""
        request_id = f"extreme-{len(self.results) + 1}"

        # Type client selon phase (plus de VIP sous stress)
        stress_factor = min(current_rps / 50.0, 2.0)  # Factor 0-2 selon RPS
        vip_probability = self.vip_ratio * (1 + stress_factor * 0.3)
        client_type = 'VIP' if random.random() < vip_probability else 'STANDARD'

        # Durées adaptées au stress (plus courtes sous charge)
        if client_type == 'VIP':
            duration = random.uniform(0.05, 0.4)  # VIP très rapides sous stress
        else:
            duration = random.uniform(0.2, 1.0)  # Standard raccourcis

        # Ressources adaptées
        cpu_factor = 1.0 + (stress_factor * 0.5)
        memory_factor = 1.0 + (stress_factor * 0.3)

        request = {
            'id': request_id,
            'client_id': f"client-extreme-{random.randint(1, 100)}",
            'client_type': client_type,
            'cpu_requested': random.uniform(0.5, 3.0) * cpu_factor,
            'memory_requested': random.uniform(1.0, 6.0) * memory_factor,
            'estimated_duration': duration,
            'arrival_time': time.time(),
            'priority': 1000 if client_type == 'VIP' else 10,
            'dependencies': self._generate_dependencies() if random.random() < self.dependency_ratio else [],
            'phase': phase_name,
            'stress_factor': stress_factor
        }

        return request

    def _generate_dependencies(self):
        """Génère des dépendances simples pour éviter la complexité sous stress."""
        if len(self.completed_requests) < 2:
            return []

        # Maximum 1-2 dépendances sous stress
        num_deps = random.randint(1, 2)
        available_deps = list(self.completed_requests)[-20:]  # Seulement les 20 dernières

        if len(available_deps) < num_deps:
            return []

        return random.sample(available_deps, min(num_deps, len(available_deps)))

    def calculate_effective_priority(self, request):
        """Calcule la priorité effective avec vieillissement adaptatif."""
        base_priority = request['priority']
        age = time.time() - request['arrival_time']

        # Vieillissement plus agressif sous charge extrême
        current_pressure = (len(self.vip_queue) + len(self.standard_queue)) / 100.0
        dynamic_aging = self.aging_factor * (1 + current_pressure)

        return base_priority + (dynamic_aging * age)

    def update_system_resources(self, current_rps):
        """Simule l'évolution des ressources système sous charge extrême."""
        # CPU monte exponentiellement avec la charge
        base_cpu = min(current_rps * 1.5, 95.0)
        cpu_stress = random.uniform(-5, 15)  # Variabilité
        self.system_resources['cpu_usage'] = max(0, min(100, base_cpu + cpu_stress))

        # Mémoire monte plus graduellement
        base_memory = min(current_rps * 0.8 + 20, 90.0)
        memory_stress = random.uniform(-3, 10)
        self.system_resources['memory_usage'] = max(0, min(100, base_memory + memory_stress))

        # Latence réseau augmente avec surcharge
        if current_rps > 50:
            base_latency = (current_rps - 50) * 0.5
            latency_jitter = random.uniform(0, base_latency * 0.3)
            self.system_resources['network_latency'] = base_latency + latency_jitter
        else:
            self.system_resources['network_latency'] = random.uniform(1, 5)

        # Détection de surcharge système
        cpu_overload = self.system_resources['cpu_usage'] > 85
        memory_overload = self.system_resources['memory_usage'] > 80
        queue_overload = (len(self.vip_queue) + len(self.standard_queue)) > self.queue_overflow_threshold

        self.system_overloaded = cpu_overload or memory_overload or queue_overload

    def process_requests_extreme(self):
        """Traite les requêtes avec gestion de la surcharge extrême."""
        if not self.vip_queue and not self.standard_queue:
            return

        # Capacité de traitement réduite sous surcharge
        if self.system_overloaded:
            max_concurrent = max(1, 5 - len(self.processing_requests))  # Capacité réduite
            failure_probability = 0.02  # 2% de chance d'échec
        else:
            max_concurrent = max(1, 15 - len(self.processing_requests))  # Capacité normale
            failure_probability = 0.001  # 0.1% de chance d'échec

        processed_count = 0

        # Traiter les requêtes en cours
        completed_ids = []
        for req_id, (request, start_time) in list(self.processing_requests.items()):
            processing_time = time.time() - start_time

            # Vérifier si terminé
            if processing_time >= request['estimated_duration']:
                completed_ids.append(req_id)

                # Simuler échec possible sous stress
                if random.random() < failure_probability:
                    self.failed_requests.add(req_id)
                    self.logger.warning(f"Requête {req_id} échouée sous stress système")
                else:
                    self.completed_requests.add(req_id)

                del self.processing_requests[req_id]

        # Démarrer nouvelles requêtes si capacité disponible
        while (len(self.processing_requests) < max_concurrent and
               processed_count < max_concurrent and
               (self.vip_queue or self.standard_queue)):

            # Priorité stricte VIP, puis Standard avec vieillissement
            if self.vip_queue:
                _, request = self.vip_queue.popleft()
                source = "VIP"
            elif self.standard_queue:
                # Trouver la requête Standard avec priorité effective max
                best_idx = 0
                best_priority = 0

                for i, (_, req) in enumerate(self.standard_queue):
                    eff_priority = self.calculate_effective_priority(req)
                    if eff_priority > best_priority:
                        best_priority = eff_priority
                        best_idx = i

                # Retirer la meilleure requête Standard
                temp_queue = []
                for i, item in enumerate(self.standard_queue):
                    if i == best_idx:
                        _, request = item
                    else:
                        temp_queue.append(item)

                self.standard_queue.clear()
                self.standard_queue.extend(temp_queue)
                source = "STANDARD"
            else:
                break

            # Démarrer le traitement
            self.processing_requests[request['id']] = (request, time.time())
            processed_count += 1

            self.logger.debug(f"Démarrage traitement {request['id']} ({source}) - "
                              f"Charge: {len(self.processing_requests)}/{max_concurrent}")

    def detect_breaking_point(self, current_rps, avg_response_time, failure_rate):
        """Détecte le point de rupture du système."""
        # Critères de rupture
        response_time_break = avg_response_time > self.response_time_threshold
        failure_rate_break = failure_rate > 0.05  # 5% d'échecs
        queue_overflow_break = (len(self.vip_queue) + len(self.standard_queue)) > self.queue_overflow_threshold
        resource_exhaustion = (self.system_resources['cpu_usage'] > 95 or
                               self.system_resources['memory_usage'] > 95)

        if (response_time_break or failure_rate_break or
                queue_overflow_break or resource_exhaustion):

            if self.saturation_metrics['breaking_point_rps'] == 0:
                self.saturation_metrics['breaking_point_rps'] = current_rps
                self.failure_points.append({
                    'rps': current_rps,
                    'avg_response_time': avg_response_time,
                    'failure_rate': failure_rate,
                    'queue_size': len(self.vip_queue) + len(self.standard_queue),
                    'cpu_usage': self.system_resources['cpu_usage'],
                    'memory_usage': self.system_resources['memory_usage'],
                    'reason': 'breaking_point_detected'
                })
                self.logger.warning(f"🔥 POINT DE RUPTURE DÉTECTÉ à {current_rps} req/s")

        else:
            # Mettre à jour le RPS max soutenable
            self.saturation_metrics['max_sustainable_rps'] = max(
                self.saturation_metrics['max_sustainable_rps'], current_rps
            )

    async def run_extreme_load_test(self):
        """Exécute le test de charge extrême complet."""
        self.logger.info(f"🚀 DÉMARRAGE - {self.test_name}")
        self.logger.info(f"📄 {self.description}")
        self.logger.info(f"🎯 Objectif: {self.max_requests} requêtes sur {len(self.burst_phases)} phases")
        print("-" * 80)

        start_time = time.time()
        total_requests_generated = 0
        phase_results = []

        for phase_idx, phase in enumerate(self.burst_phases):
            phase_start = time.time()
            phase_requests = 0
            phase_name = phase['name']
            duration = phase['duration']
            start_rps = phase['start_rps']
            end_rps = phase['end_rps']

            self.logger.info(f"📍 {phase_name} ({start_rps}→{end_rps} req/s, {duration}s)")

            # Génération progressive selon la courbe RPS
            while (time.time() - phase_start) < duration and total_requests_generated < self.max_requests:
                elapsed_phase = time.time() - phase_start
                progress = elapsed_phase / duration

                # RPS courant (interpolation linéaire)
                current_rps = start_rps + (end_rps - start_rps) * progress

                # Mettre à jour les ressources système
                self.update_system_resources(current_rps)

                # Générer requêtes selon RPS courant
                interval = 1.0 / max(current_rps, 0.1)

                # Générer une requête
                request = self.generate_extreme_request(phase_name, current_rps)

                # Ajouter à la file appropriée
                arrival_time = time.time()
                if request['client_type'] == 'VIP':
                    self.vip_queue.append((arrival_time, request))
                else:
                    self.standard_queue.append((arrival_time, request))

                total_requests_generated += 1
                phase_requests += 1

                # Traiter les requêtes
                self.process_requests_extreme()

                # Collecter métriques en temps réel
                current_metrics = self.collect_current_metrics(current_rps)
                self.performance_data['timestamps'].append(time.time())
                self.performance_data['rps'].append(current_rps)
                self.performance_data['response_times'].append(current_metrics['avg_response_time'])
                self.performance_data['queue_sizes'].append(current_metrics['total_queue_size'])
                self.performance_data['cpu_usage'].append(self.system_resources['cpu_usage'])
                self.performance_data['failure_rates'].append(current_metrics['failure_rate'])

                # Détecter point de rupture
                self.detect_breaking_point(
                    current_rps,
                    current_metrics['avg_response_time'],
                    current_metrics['failure_rate']
                )

                # Arrêt d'urgence si système complètement cassé
                if (current_metrics['failure_rate'] > 0.2 or  # 20% d'échecs
                        current_metrics['avg_response_time'] > 60 or  # 1 minute de réponse
                        len(self.vip_queue) + len(self.standard_queue) > 2000):  # Queue énorme

                    self.logger.error(f"🆘 ARRÊT D'URGENCE - Système en échec critique")
                    self.failure_points.append({
                        'rps': current_rps,
                        'reason': 'emergency_stop',
                        'metrics': current_metrics
                    })
                    break

                # Respecter l'intervalle de génération
                await asyncio.sleep(max(0.01, interval * random.uniform(0.8, 1.2)))

            # Résumé de phase
            phase_duration = time.time() - phase_start
            phase_results.append({
                'name': phase_name,
                'duration': phase_duration,
                'requests_generated': phase_requests,
                'avg_rps': phase_requests / phase_duration,
                'final_rps': current_rps
            })

            print(f"    ✅ {phase_requests} req en {phase_duration:.1f}s "
                  f"(avg: {phase_requests / phase_duration:.1f} req/s)")

            # Pause entre phases pour stabilisation
            if phase_idx < len(self.burst_phases) - 1:
                await asyncio.sleep(2)

        # Phase de récupération finale
        self.logger.info("🔄 Phase de récupération finale...")
        recovery_start = time.time()

        # Continuer le traitement jusqu'à vidage complet
        while (self.vip_queue or self.standard_queue or self.processing_requests):
            self.process_requests_extreme()
            await asyncio.sleep(0.1)

            # Timeout de sécurité
            if time.time() - recovery_start > 300:  # 5 minutes max
                self.logger.warning("⏰ Timeout de récupération - Arrêt forcé")
                break

        self.saturation_metrics['recovery_time'] = time.time() - recovery_start

        # Finaliser les métriques globales
        total_duration = time.time() - start_time
        total_completed = len(self.completed_requests)
        total_failed = len(self.failed_requests)
        total_processed = total_completed + total_failed

        self.saturation_metrics.update({
            'max_queue_size': max(self.performance_data['queue_sizes']) if self.performance_data['queue_sizes'] else 0,
            'max_response_time': max(self.performance_data['response_times']) if self.performance_data[
                'response_times'] else 0,
            'failure_rate': total_failed / max(total_processed, 1),
            'total_duration': total_duration,
            'avg_throughput': total_processed / total_duration if total_duration > 0 else 0
        })

        # Sauvegarder résultats
        results = await self.save_results(
            total_requests_generated, total_completed, total_failed,
            total_duration, phase_results
        )

        # Affichage final
        self.display_extreme_results(results)

        return results

    def collect_current_metrics(self, current_rps):
        """Collecte les métriques système actuelles."""
        # Temps de réponse moyen des requêtes en cours
        if self.processing_requests:
            processing_times = [
                time.time() - start_time
                for _, (_, start_time) in self.processing_requests.items()
            ]
            avg_response_time = sum(processing_times) / len(processing_times)
        else:
            avg_response_time = 0.0

        # Taille totale des files
        total_queue_size = len(self.vip_queue) + len(self.standard_queue)

        # Taux d'échec récent
        total_processed = len(self.completed_requests) + len(self.failed_requests)
        failure_rate = len(self.failed_requests) / max(total_processed, 1)

        return {
            'avg_response_time': avg_response_time,
            'total_queue_size': total_queue_size,
            'failure_rate': failure_rate,
            'processing_count': len(self.processing_requests)
        }

    async def save_results(self, total_generated, total_completed, total_failed, duration, phase_results):
        """Sauvegarde les résultats du test extrême."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        results = {
            "test_type": "extreme_load",
            "scenario_name": self.test_name,
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "max_requests": self.max_requests,
                "phases": len(self.burst_phases),
                "vip_ratio": self.vip_ratio,
                "aging_factor": self.aging_factor,
                "dependency_ratio": self.dependency_ratio
            },
            "summary": {
                "total_requests_generated": total_generated,
                "completed_requests": total_completed,
                "failed_requests": total_failed,
                "success_rate": total_completed / max(total_generated, 1),
                "test_duration": duration,
                "avg_throughput": (total_completed + total_failed) / duration if duration > 0 else 0
            },
            "saturation_metrics": self.saturation_metrics,
            "phase_results": phase_results,
            "failure_points": self.failure_points,
            "performance_timeseries": {
                "timestamps": self.performance_data['timestamps'][-100:],  # Derniers 100 points
                "rps": self.performance_data['rps'][-100:],
                "response_times": self.performance_data['response_times'][-100:],
                "queue_sizes": self.performance_data['queue_sizes'][-100:],
                "cpu_usage": self.performance_data['cpu_usage'][-100:],
                "failure_rates": self.performance_data['failure_rates'][-100:]
            },
            "resource_peaks": {
                "max_cpu": max(self.performance_data['cpu_usage']) if self.performance_data['cpu_usage'] else 0,
                "max_memory": self.system_resources['memory_usage'],
                "max_latency": self.system_resources['network_latency']
            }
        }

        # Sauvegarder
        logs_dir = Path("logs/scenarios")
        logs_dir.mkdir(parents=True, exist_ok=True)

        filename = f"scenario_4_extreme_{timestamp}.json"
        filepath = logs_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"📄 Rapport saturation: {filepath}")

        return results

    def display_extreme_results(self, results):
        """Affiche les résultats du test de saturation extrême."""
        print("📊 RÉSULTATS DU TEST DE SATURATION:")
        print(f"✅ Taux de réussite: {results['summary']['success_rate'] * 100:.1f}%")
        print(f"⚡ RPS max soutenable: {self.saturation_metrics['max_sustainable_rps']:.1f} req/s")
        print(f"💥 Point de rupture: {self.saturation_metrics['breaking_point_rps']:.1f} req/s")
        print(f"📊 File d'attente max: {self.saturation_metrics['max_queue_size']}")
        print(f"⏱️  Temps de réponse max: {self.saturation_metrics['max_response_time']:.2f}s")
        print(f"❌ Taux d'échec: {self.saturation_metrics['failure_rate'] * 100:.2f}%")
        print(f"🔄 Temps de récupération: {self.saturation_metrics['recovery_time']:.1f}s")

        if self.failure_points:
            print(f"🚨 Points de défaillance détectés: {len(self.failure_points)}")

        print("=" * 80)
        print("RÉSUMÉ SCÉNARIO 4 - TEST DE SATURATION EXTRÊME")
        print("=" * 80)
        print(f"🔢 Requêtes générées: {results['summary']['total_requests_generated']}")
        print(f"✅ Requêtes complétées: {results['summary']['completed_requests']}")
        print(f"❌ Requêtes échouées: {results['summary']['failed_requests']}")
        print(f"📈 Taux de réussite: {results['summary']['success_rate'] * 100:.1f}%")
        print(f"🚀 Débit moyen: {results['summary']['avg_throughput']:.1f} req/s")
        print(f"💪 RPS max soutenable: {self.saturation_metrics['max_sustainable_rps']:.1f} req/s")
        print(f"💥 Point de rupture: {self.saturation_metrics['breaking_point_rps']:.1f} req/s")
        print(f"⏰ Durée totale: {results['summary']['test_duration']:.1f}s")
        print(f"🔄 Récupération: {self.saturation_metrics['recovery_time']:.1f}s")


async def main():
    """Fonction principale pour exécuter le test de saturation extrême."""
    scenario = ExtremeLoadTestScenario()

    print("🔥" * 20)
    print("🚀 SCÉNARIO 4: Test de Saturation Extrême")
    print(f"📄 Description: {scenario.description}")
    print(f"🎯 Volume: Jusqu'à {scenario.max_requests} requêtes")
    print(f"⚡ Charge: 5 → 200 req/s")
    print(f"🔍 Objectif: Identifier les limites du système")
    print("-" * 80)

    try:
        results = await scenario.run_extreme_load_test()
        return results
    except Exception as e:
        scenario.logger.error(f"Erreur fatale: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    results = asyncio.run(main())
    if results:
        print("🎯 Test de saturation extrême terminé avec succès!")
    else:
        print("❌ Échec du test de saturation extrême")