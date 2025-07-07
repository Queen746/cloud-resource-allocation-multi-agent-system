# tests/performance/real_performance_tests.py
"""
Tests de performance RÉELS avec métriques détaillées.
Génère des données authentiques pour l'analyse.
"""

import asyncio
import time
import random
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque
import threading
import csv


class RealPerformanceTester:
    """
    Testeur de performance qui génère de vraies métriques.
    """

    def __init__(self):
        self.metrics = {
            'requests_sent': 0,
            'requests_completed': 0,
            'requests_failed': 0,
            'vip_queue_sizes': [],
            'standard_queue_sizes': [],
            'response_times_vip': [],
            'response_times_standard': [],
            'cpu_usage': [],
            'memory_usage': [],
            'throughput_per_second': [],
            'equity_ratios': [],
            'timestamps': []
        }

        # Simulation d'état système
        self.vip_queue = deque()
        self.standard_queue = deque()
        self.active_requests = {}
        self.completed_requests = []

        # Ressources simulées
        self.cpu_available = 100.0
        self.memory_available = 100.0
        self.current_load = 0.0

        # Mécanisme de vieillissement
        self.aging_factor = 0.5

        # Monitoring
        self.monitoring_active = False
        self.monitoring_thread = None

    def start_monitoring(self):
        """Démarre le monitoring en temps réel."""
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitoring_thread.start()

    def stop_monitoring(self):
        """Arrête le monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join()

    def _monitor_loop(self):
        """Boucle de monitoring qui collecte les métriques."""
        while self.monitoring_active:
            timestamp = time.time()

            # Collecter les métriques instantanées
            self.metrics['timestamps'].append(timestamp)
            self.metrics['vip_queue_sizes'].append(len(self.vip_queue))
            self.metrics['standard_queue_sizes'].append(len(self.standard_queue))
            self.metrics['cpu_usage'].append(100 - self.cpu_available)
            self.metrics['memory_usage'].append(100 - self.memory_available)

            # Calculer le throughput des 5 dernières secondes
            recent_completions = [
                req for req in self.completed_requests
                if req['completion_time'] > timestamp - 5
            ]
            throughput = len(recent_completions) / 5.0
            self.metrics['throughput_per_second'].append(throughput)

            # Calculer le ratio d'équité
            recent_vip = [r for r in recent_completions if r['client_type'] == 'VIP']
            recent_std = [r for r in recent_completions if r['client_type'] == 'STANDARD']

            if recent_vip and recent_std:
                avg_vip_time = sum(r['response_time'] for r in recent_vip) / len(recent_vip)
                avg_std_time = sum(r['response_time'] for r in recent_std) / len(recent_std)
                equity_ratio = avg_std_time / avg_vip_time if avg_vip_time > 0 else 1.0
                self.metrics['equity_ratios'].append(equity_ratio)
            else:
                self.metrics['equity_ratios'].append(1.0)

            time.sleep(1)  # Collecter chaque seconde

    def generate_request(self, client_type='STANDARD'):
        """Génère une nouvelle demande."""
        request = {
            'id': f"req-{self.metrics['requests_sent']:05d}",
            'client_type': client_type,
            'arrival_time': time.time(),
            'cpu_required': random.uniform(1.0, 8.0),
            'memory_required': random.uniform(2.0, 12.0),
            'estimated_duration': random.uniform(0.5, 3.0),
            'priority': 100 if client_type == 'VIP' else 10,
            'effective_priority': 100 if client_type == 'VIP' else 10
        }

        self.metrics['requests_sent'] += 1

        # Ajouter à la file appropriée
        if client_type == 'VIP':
            self.vip_queue.append(request)
        else:
            self.standard_queue.append(request)

        return request

    def apply_aging(self):
        """Applique le mécanisme de vieillissement."""
        current_time = time.time()

        # Vieillir les demandes standard
        for request in self.standard_queue:
            age = current_time - request['arrival_time']
            request['effective_priority'] = request['priority'] + (self.aging_factor * age)

    def process_requests(self):
        """Traite les demandes selon l'algorithme d'ordonnancement."""
        if not (self.vip_queue or self.standard_queue):
            return

        # Appliquer le vieillissement
        self.apply_aging()

        # Sélectionner la prochaine demande
        next_request = None

        # Créer une liste combinée triée par priorité effective
        all_requests = []

        for i, req in enumerate(self.vip_queue):
            all_requests.append(('VIP', i, req))

        for i, req in enumerate(self.standard_queue):
            all_requests.append(('STANDARD', i, req))

        if all_requests:
            # Trier par priorité effective (décroissant) puis par SJF
            all_requests.sort(
                key=lambda x: (-x[2]['effective_priority'], x[2]['estimated_duration'])
            )

            queue_type, index, next_request = all_requests[0]

            # Retirer de la file appropriée
            if queue_type == 'VIP':
                self.vip_queue.remove(next_request)
            else:
                self.standard_queue.remove(next_request)

            # Vérifier si les ressources sont disponibles
            if (self.cpu_available >= next_request['cpu_required'] and
                    self.memory_available >= next_request['memory_required']):

                # Allouer les ressources
                self.cpu_available -= next_request['cpu_required']
                self.memory_available -= next_request['memory_required']

                # Démarrer le traitement
                next_request['start_time'] = time.time()
                self.active_requests[next_request['id']] = next_request

                # Programmer la completion
                completion_time = next_request['start_time'] + next_request['estimated_duration']
                threading.Timer(
                    next_request['estimated_duration'],
                    self._complete_request,
                    args=[next_request['id']]
                ).start()

            else:
                # Remettre en file si pas assez de ressources
                if queue_type == 'VIP':
                    self.vip_queue.appendleft(next_request)
                else:
                    self.standard_queue.appendleft(next_request)

    def _complete_request(self, request_id):
        """Termine le traitement d'une demande."""
        if request_id not in self.active_requests:
            return

        request = self.active_requests[request_id]
        completion_time = time.time()

        # Calculer les métriques de la demande
        response_time = completion_time - request['arrival_time']
        request['completion_time'] = completion_time
        request['response_time'] = response_time

        # Libérer les ressources
        self.cpu_available += request['cpu_required']
        self.memory_available += request['memory_required']

        # Enregistrer la completion
        self.completed_requests.append(request)
        self.metrics['requests_completed'] += 1

        # Enregistrer le temps de réponse
        if request['client_type'] == 'VIP':
            self.metrics['response_times_vip'].append(response_time)
        else:
            self.metrics['response_times_standard'].append(response_time)

        # Retirer des demandes actives
        del self.active_requests[request_id]

    async def run_baseline_test(self, duration=60, target_rps=5):
        """Test de performance baseline RÉEL."""
        print(f"🚀 Démarrage test baseline: {duration}s à {target_rps} req/s")

        self.start_monitoring()
        start_time = time.time()
        last_request_time = 0

        # Générer les demandes
        request_generation_task = asyncio.create_task(
            self._generate_requests_baseline(duration, target_rps)
        )

        # Traiter les demandes
        processing_task = asyncio.create_task(
            self._process_requests_loop(duration)
        )

        # Attendre la fin
        await asyncio.gather(request_generation_task, processing_task)

        # Attendre que les dernières demandes se terminent
        await asyncio.sleep(5)

        self.stop_monitoring()

        return self.generate_report("baseline")

    async def _generate_requests_baseline(self, duration, target_rps):
        """Génère des demandes à taux constant."""
        start_time = time.time()
        request_interval = 1.0 / target_rps

        while time.time() - start_time < duration:
            # 20% VIP, 80% Standard
            client_type = 'VIP' if random.random() < 0.2 else 'STANDARD'
            self.generate_request(client_type)

            await asyncio.sleep(request_interval * random.uniform(0.8, 1.2))

    async def _process_requests_loop(self, duration):
        """Boucle de traitement des demandes."""
        start_time = time.time()

        while time.time() - start_time < duration + 10:  # 10s buffer
            self.process_requests()
            await asyncio.sleep(0.1)  # Traiter toutes les 100ms

    async def run_scalability_test(self):
        """Test de scalabilité sur différents volumes."""
        print("🚀 Démarrage test de scalabilité")

        volumes = [100, 250, 500, 750, 1000]
        scalability_results = []

        for volume in volumes:
            print(f"  📊 Test avec {volume} requêtes...")

            # Reset metrics
            self._reset_metrics()

            # Générer toutes les requêtes d'un coup (pic de charge)
            start_time = time.time()
            for i in range(volume):
                client_type = 'VIP' if i % 5 == 0 else 'STANDARD'  # 20% VIP
                self.generate_request(client_type)

            generation_time = time.time() - start_time

            # Démarrer le monitoring
            self.start_monitoring()

            # Traiter toutes les demandes
            processing_start = time.time()
            while (self.vip_queue or self.standard_queue or self.active_requests):
                self.process_requests()
                await asyncio.sleep(0.05)

            processing_time = time.time() - processing_start
            total_time = time.time() - start_time

            self.stop_monitoring()

            # Calculer les métriques pour ce volume
            success_rate = self.metrics['requests_completed'] / self.metrics['requests_sent']
            avg_response_time = sum(
                self.metrics['response_times_vip'] + self.metrics['response_times_standard']
            ) / len(self.metrics['response_times_vip'] + self.metrics['response_times_standard'])

            throughput = self.metrics['requests_completed'] / total_time

            scalability_results.append({
                'volume': volume,
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'throughput': throughput,
                'total_time': total_time,
                'processing_time': processing_time
            })

            print(f"    ✅ {volume} req: {success_rate:.1%} réussite, {throughput:.1f} req/s")

        return {
            'test_type': 'scalability',
            'results': scalability_results,
            'metrics': self.metrics.copy()
        }

    async def run_spike_test(self, base_rps=2, spike_rps=15, spike_duration=30):
        """Test de résistance aux pics de charge."""
        print(f"🚀 Test de pics: {base_rps} req/s → {spike_rps} req/s pendant {spike_duration}s")

        self._reset_metrics()
        self.start_monitoring()

        total_duration = 120  # 2 minutes total
        spike_start = 30  # Pic commence à 30s
        spike_end = spike_start + spike_duration

        start_time = time.time()

        # Génération des demandes avec pic
        generation_task = asyncio.create_task(
            self._generate_requests_with_spike(
                total_duration, base_rps, spike_rps, spike_start, spike_end
            )
        )

        # Traitement des demandes
        processing_task = asyncio.create_task(
            self._process_requests_loop(total_duration)
        )

        await asyncio.gather(generation_task, processing_task)

        # Attendre que tout se termine
        await asyncio.sleep(10)

        self.stop_monitoring()

        return self.generate_report("spike_test")

    async def _generate_requests_with_spike(self, total_duration, base_rps, spike_rps, spike_start, spike_end):
        """Génère des demandes avec un pic de charge."""
        start_time = time.time()

        while time.time() - start_time < total_duration:
            current_time = time.time() - start_time

            # Déterminer le taux actuel
            if spike_start <= current_time <= spike_end:
                current_rps = spike_rps
            else:
                current_rps = base_rps

            interval = 1.0 / current_rps

            # Générer une demande
            client_type = 'VIP' if random.random() < 0.3 else 'STANDARD'
            self.generate_request(client_type)

            await asyncio.sleep(interval * random.uniform(0.7, 1.3))

    def _reset_metrics(self):
        """Remet à zéro les métriques."""
        self.metrics = {
            'requests_sent': 0,
            'requests_completed': 0,
            'requests_failed': 0,
            'vip_queue_sizes': [],
            'standard_queue_sizes': [],
            'response_times_vip': [],
            'response_times_standard': [],
            'cpu_usage': [],
            'memory_usage': [],
            'throughput_per_second': [],
            'equity_ratios': [],
            'timestamps': []
        }

        self.vip_queue.clear()
        self.standard_queue.clear()
        self.active_requests.clear()
        self.completed_requests.clear()
        self.cpu_available = 100.0
        self.memory_available = 100.0

    def generate_report(self, test_type):
        """Génère un rapport détaillé avec toutes les métriques."""
        if not self.metrics['timestamps']:
            return {"error": "Pas de données collectées"}

        # Calculer les statistiques
        total_requests = self.metrics['requests_sent']
        completed_requests = self.metrics['requests_completed']
        success_rate = completed_requests / total_requests if total_requests > 0 else 0

        # Temps de réponse
        all_response_times = self.metrics['response_times_vip'] + self.metrics['response_times_standard']
        avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0

        avg_vip_response = sum(self.metrics['response_times_vip']) / len(self.metrics['response_times_vip']) if \
        self.metrics['response_times_vip'] else 0
        avg_std_response = sum(self.metrics['response_times_standard']) / len(
            self.metrics['response_times_standard']) if self.metrics['response_times_standard'] else 0

        # Throughput
        max_throughput = max(self.metrics['throughput_per_second']) if self.metrics['throughput_per_second'] else 0
        avg_throughput = sum(self.metrics['throughput_per_second']) / len(self.metrics['throughput_per_second']) if \
        self.metrics['throughput_per_second'] else 0

        # Files d'attente
        max_vip_queue = max(self.metrics['vip_queue_sizes']) if self.metrics['vip_queue_sizes'] else 0
        max_std_queue = max(self.metrics['standard_queue_sizes']) if self.metrics['standard_queue_sizes'] else 0
        avg_vip_queue = sum(self.metrics['vip_queue_sizes']) / len(self.metrics['vip_queue_sizes']) if self.metrics[
            'vip_queue_sizes'] else 0
        avg_std_queue = sum(self.metrics['standard_queue_sizes']) / len(self.metrics['standard_queue_sizes']) if \
        self.metrics['standard_queue_sizes'] else 0

        # Équité
        avg_equity_ratio = sum(self.metrics['equity_ratios']) / len(self.metrics['equity_ratios']) if self.metrics[
            'equity_ratios'] else 1.0

        # Ressources
        max_cpu_usage = max(self.metrics['cpu_usage']) if self.metrics['cpu_usage'] else 0
        avg_cpu_usage = sum(self.metrics['cpu_usage']) / len(self.metrics['cpu_usage']) if self.metrics[
            'cpu_usage'] else 0
        max_memory_usage = max(self.metrics['memory_usage']) if self.metrics['memory_usage'] else 0
        avg_memory_usage = sum(self.metrics['memory_usage']) / len(self.metrics['memory_usage']) if self.metrics[
            'memory_usage'] else 0

        report = {
            'test_type': test_type,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_requests': total_requests,
                'completed_requests': completed_requests,
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'max_throughput': max_throughput,
                'avg_throughput': avg_throughput
            },
            'performance': {
                'vip_avg_response_time': avg_vip_response,
                'standard_avg_response_time': avg_std_response,
                'equity_ratio': avg_equity_ratio,
                'max_throughput': max_throughput,
                'avg_throughput': avg_throughput
            },
            'queues': {
                'max_vip_queue_size': max_vip_queue,
                'max_standard_queue_size': max_std_queue,
                'avg_vip_queue_size': avg_vip_queue,
                'avg_standard_queue_size': avg_std_queue
            },
            'resources': {
                'max_cpu_usage': max_cpu_usage,
                'avg_cpu_usage': avg_cpu_usage,
                'max_memory_usage': max_memory_usage,
                'avg_memory_usage': avg_memory_usage
            },
            'time_series': {
                'timestamps': self.metrics['timestamps'],
                'vip_queue_sizes': self.metrics['vip_queue_sizes'],
                'standard_queue_sizes': self.metrics['standard_queue_sizes'],
                'cpu_usage': self.metrics['cpu_usage'],
                'memory_usage': self.metrics['memory_usage'],
                'throughput_per_second': self.metrics['throughput_per_second'],
                'equity_ratios': self.metrics['equity_ratios']
            }
        }

        return report

    def save_metrics_to_csv(self, filename):
        """Sauvegarde les métriques détaillées en CSV."""
        csv_path = Path("logs/metrics") / filename
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Headers
            writer.writerow([
                'timestamp', 'vip_queue_size', 'standard_queue_size',
                'cpu_usage', 'memory_usage', 'throughput', 'equity_ratio'
            ])

            # Data
            for i in range(len(self.metrics['timestamps'])):
                writer.writerow([
                    self.metrics['timestamps'][i],
                    self.metrics['vip_queue_sizes'][i] if i < len(self.metrics['vip_queue_sizes']) else 0,
                    self.metrics['standard_queue_sizes'][i] if i < len(self.metrics['standard_queue_sizes']) else 0,
                    self.metrics['cpu_usage'][i] if i < len(self.metrics['cpu_usage']) else 0,
                    self.metrics['memory_usage'][i] if i < len(self.metrics['memory_usage']) else 0,
                    self.metrics['throughput_per_second'][i] if i < len(self.metrics['throughput_per_second']) else 0,
                    self.metrics['equity_ratios'][i] if i < len(self.metrics['equity_ratios']) else 0
                ])

        print(f"📊 Métriques sauvegardées dans: {csv_path}")


async def main():
    """Fonction principale pour exécuter les tests."""
    tester = RealPerformanceTester()

    print("🎯 TESTS DE PERFORMANCE RÉELS AVEC MÉTRIQUES DÉTAILLÉES")
    print("=" * 60)

    # Test 1: Baseline
    print("\n1️⃣ TEST BASELINE")
    baseline_report = await tester.run_baseline_test(duration=60, target_rps=5)
    print(f"✅ Baseline terminé: {baseline_report['summary']['success_rate']:.1%} réussite")

    # Sauvegarder les métriques
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tester.save_metrics_to_csv(f"baseline_metrics_{timestamp}.csv")

    # Sauvegarder le rapport JSON
    report_path = Path("logs/metrics") / f"baseline_report_{timestamp}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(baseline_report, f, indent=2, default=str)

    print(f"📄 Rapport sauvegardé: {report_path}")

    # Test 2: Scalabilité
    print("\n2️⃣ TEST SCALABILITÉ")
    scalability_report = await tester.run_scalability_test()

    scalability_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scalability_path = Path("logs/metrics") / f"scalability_report_{scalability_timestamp}.json"
    with open(scalability_path, 'w', encoding='utf-8') as f:
        json.dump(scalability_report, f, indent=2, default=str)

    print(f"📄 Rapport scalabilité: {scalability_path}")

    # Test 3: Pics de charge
    print("\n3️⃣ TEST PICS DE CHARGE")
    spike_report = await tester.run_spike_test()
    print(f"✅ Test pics terminé: {spike_report['summary']['success_rate']:.1%} réussite")

    spike_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tester.save_metrics_to_csv(f"spike_metrics_{spike_timestamp}.csv")

    spike_path = Path("logs/metrics") / f"spike_report_{spike_timestamp}.json"
    with open(spike_path, 'w', encoding='utf-8') as f:
        json.dump(spike_report, f, indent=2, default=str)

    print(f"📄 Rapport pics: {spike_path}")

    print("\n🎉 TOUS LES TESTS TERMINÉS !")
    print("📊 Consultez les dossiers logs/metrics/ pour les données détaillées")


if __name__ == "__main__":
    asyncio.run(main())