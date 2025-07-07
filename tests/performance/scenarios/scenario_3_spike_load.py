# tests/performance/scenarios/scenario_3_spike_load.py
"""
Scénario 3: Test de Résistance aux Pics de Charge
Valide la résilience du système face aux variations brusques de charge.
"""

import asyncio
import time
import random
import json
from datetime import datetime
from pathlib import Path
import threading
from collections import deque
import math


class SpikeLoadTestScenario:
    """
    Test de résistance aux pics de charge avec récupération automatique.
    Objectif: Vérifier que le système gère les pics sans perdre d'équité.
    """

    def __init__(self):
        self.name = "Test de Pics de Charge"
        self.description = "Teste la résilience aux variations brusques de charge"

        # Configuration du test
        self.total_duration = 120  # 2 minutes total
        self.base_rps = 2  # Charge de base
        self.spike_rps = 15  # Pic de charge (7.5x plus élevé)
        self.spike_start = 30  # Début du pic à 30s
        self.spike_duration = 30  # Durée du pic: 30s
        self.recovery_duration = 60  # Temps de récupération: 60s

        # Mécanisme d'équité renforcé sous stress
        self.base_aging_factor = 0.5
        self.spike_aging_factor = 1.5  # Plus agressif sous pic
        self.current_aging_factor = self.base_aging_factor

        # Monitoring des phases
        self.phases = {
            'warmup': {'start': 0, 'end': self.spike_start, 'name': 'Charge normale'},
            'spike': {'start': self.spike_start, 'end': self.spike_start + self.spike_duration,
                      'name': 'Pic de charge'},
            'recovery': {'start': self.spike_start + self.spike_duration, 'end': self.total_duration,
                         'name': 'Récupération'}
        }

        self.current_phase = 'warmup'
        self.phase_metrics = {}

        # État système
        self.reset_system_state()

    def reset_system_state(self):
        """Initialise l'état du système."""
        self.metrics = {
            'requests_sent': 0,
            'requests_completed': 0,
            'vip_queue_sizes': [],
            'standard_queue_sizes': [],
            'response_times_vip': [],
            'response_times_standard': [],
            'cpu_usage': [],
            'memory_usage': [],
            'throughput_per_second': [],
            'equity_ratios': [],
            'timestamps': [],
            'current_rps': [],
            'phase_indicators': []
        }

        self.vip_queue = deque()
        self.standard_queue = deque()
        self.active_requests = {}
        self.completed_requests = []
        self.cpu_available = 100.0
        self.memory_available = 100.0

        # Métriques de stress
        self.queue_pressure_history = []
        self.recovery_metrics = []

        # Monitoring thread
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
        """Boucle de monitoring qui collecte les métriques par phase."""
        while self.monitoring_active:
            timestamp = time.time()

            # Métriques de base
            self.metrics['timestamps'].append(timestamp)
            self.metrics['vip_queue_sizes'].append(len(self.vip_queue))
            self.metrics['standard_queue_sizes'].append(len(self.standard_queue))
            self.metrics['cpu_usage'].append(100 - self.cpu_available)
            self.metrics['memory_usage'].append(100 - self.memory_available)
            self.metrics['phase_indicators'].append(self.current_phase)

            # Calcul du throughput récent
            recent_completions = [
                req for req in self.completed_requests
                if req['completion_time'] > timestamp - 5
            ]
            throughput = len(recent_completions) / 5.0
            self.metrics['throughput_per_second'].append(throughput)

            # Pression des files d'attente (indicateur de stress)
            queue_pressure = (len(self.vip_queue) + len(self.standard_queue)) / 100.0
            self.queue_pressure_history.append(queue_pressure)

            # Ratio d'équité par phase
            recent_vip = [r for r in recent_completions if r['client_type'] == 'VIP']
            recent_std = [r for r in recent_completions if r['client_type'] == 'STANDARD']

            if recent_vip and recent_std:
                avg_vip_time = sum(r['response_time'] for r in recent_vip) / len(recent_vip)
                avg_std_time = sum(r['response_time'] for r in recent_std) / len(recent_std)
                equity_ratio = avg_std_time / avg_vip_time if avg_vip_time > 0 else 1.0
                self.metrics['equity_ratios'].append(equity_ratio)
            else:
                self.metrics['equity_ratios'].append(1.0)

            time.sleep(1)

    def determine_current_phase(self, elapsed_time):
        """Détermine la phase actuelle et ajuste les paramètres."""
        old_phase = self.current_phase

        if elapsed_time < self.spike_start:
            self.current_phase = 'warmup'
            self.current_aging_factor = self.base_aging_factor
        elif elapsed_time < self.spike_start + self.spike_duration:
            self.current_phase = 'spike'
            self.current_aging_factor = self.spike_aging_factor
        else:
            self.current_phase = 'recovery'
            # Vieillissement adaptatif basé sur la pression des files
            queue_pressure = (len(self.vip_queue) + len(self.standard_queue)) / 50.0
            self.current_aging_factor = self.base_aging_factor + (queue_pressure * 0.5)

        # Log changement de phase
        if old_phase != self.current_phase:
            print(f"  📍 Phase: {self.phases[self.current_phase]['name']} "
                  f"(vieillissement: {self.current_aging_factor:.1f})")

    def generate_spike_request(self, client_type='STANDARD'):
        """Génère une requête adaptée au test de pics."""
        request = {
            'id': f"spike-req-{self.metrics['requests_sent']:05d}",
            'client_type': client_type,
            'arrival_time': time.time(),
            'phase': self.current_phase,
            'cpu_required': random.uniform(0.5, 3.0),
            'memory_required': random.uniform(1.0, 5.0),
            'estimated_duration': random.uniform(0.2, 1.2),
            'priority': 100 if client_type == 'VIP' else 10,
            'effective_priority': 100 if client_type == 'VIP' else 10,
            'dependencies': []
        }

        # Ajouter quelques dépendances pendant le pic (complexité accrue)
        if self.current_phase == 'spike' and random.random() < 0.15:
            if self.metrics['requests_sent'] > 5:
                dep_range = min(10, self.metrics['requests_sent'])
                dep_id = f"spike-req-{random.randint(max(0, self.metrics['requests_sent'] - dep_range), self.metrics['requests_sent'] - 1):05d}"
                request['dependencies'] = [dep_id]

        self.metrics['requests_sent'] += 1
        return request

    def apply_adaptive_aging(self):
        """Mécanisme d'anti-famine adaptatif selon la phase."""
        current_time = time.time()

        # Calculer la pression du système
        total_queue_size = len(self.vip_queue) + len(self.standard_queue)
        system_pressure = min(total_queue_size / 100.0, 2.0)  # Cap à 2.0

        # Facteur d'urgence pour les requêtes anciennes
        for request in self.standard_queue:
            age = current_time - request['arrival_time']

            # Vieillissement de base
            base_aging = self.current_aging_factor * age

            # Bonus de phase (plus agressif sous stress)
            phase_bonus = 0
            if self.current_phase == 'spike':
                phase_bonus = age * 0.3  # Bonus pendant le pic
            elif self.current_phase == 'recovery' and age > 15:
                phase_bonus = age * 0.5  # Bonus de récupération

            # Bonus de pression système
            pressure_bonus = system_pressure * age * 0.2

            # Priorité effective finale
            request['effective_priority'] = (
                    request['priority'] +
                    base_aging +
                    phase_bonus +
                    pressure_bonus
            )

            # Cas critique: priorité maximale si trop ancien
            if age > 45:  # Plus de 45 secondes
                request['effective_priority'] = max(request['effective_priority'], 200)

    def check_dependencies(self, request):
        """Vérifie les dépendances (version simplifiée pour pic de charge)."""
        if not request.get('dependencies'):
            return True

        completed_ids = {req['id'] for req in self.completed_requests}
        return all(dep_id in completed_ids for dep_id in request['dependencies'])

    def process_requests_under_load(self):
        """Traitement optimisé pour pics de charge."""
        if not (self.vip_queue or self.standard_queue):
            return

        # Appliquer vieillissement adaptatif
        self.apply_adaptive_aging()

        # Sélectionner requêtes prêtes
        ready_requests = []

        for i, req in enumerate(self.vip_queue):
            if self.check_dependencies(req):
                ready_requests.append(('VIP', i, req))

        for i, req in enumerate(self.standard_queue):
            if self.check_dependencies(req):
                ready_requests.append(('STANDARD', i, req))

        if ready_requests:
            # Tri par priorité effective + SJF adaptatif
            ready_requests.sort(key=lambda x: (
                -x[2]['effective_priority'],
                x[2]['estimated_duration'] * (1.5 if self.current_phase == 'spike' else 1.0)
            # SJF plus agressif sous pic
            ))

            # Traiter plusieurs requêtes si ressources suffisantes
            processed = 0
            max_concurrent = 3 if self.current_phase == 'spike' else 1

            for queue_type, index, request in ready_requests[:max_concurrent]:
                if (self.cpu_available >= request['cpu_required'] and
                        self.memory_available >= request['memory_required']):

                    # Retirer de la file
                    if queue_type == 'VIP':
                        self.vip_queue.remove(request)
                    else:
                        self.standard_queue.remove(request)

                    # Allouer ressources
                    self.cpu_available -= request['cpu_required']
                    self.memory_available -= request['memory_required']

                    # Démarrer traitement
                    request['start_time'] = time.time()
                    self.active_requests[request['id']] = request

                    # Programmer completion
                    threading.Timer(
                        request['estimated_duration'],
                        self._complete_spike_request,
                        args=[request['id']]
                    ).start()

                    processed += 1
                else:
                    break  # Pas assez de ressources

    def _complete_spike_request(self, request_id):
        """Termine une requête et collecte métriques de phase."""
        if request_id not in self.active_requests:
            return

        request = self.active_requests[request_id]
        completion_time = time.time()

        # Métriques
        response_time = completion_time - request['arrival_time']
        wait_time = request['start_time'] - request['arrival_time']
        processing_time = completion_time - request['start_time']

        request['completion_time'] = completion_time
        request['response_time'] = response_time
        request['wait_time'] = wait_time
        request['processing_time'] = processing_time

        # Libérer ressources
        self.cpu_available += request['cpu_required']
        self.memory_available += request['memory_required']

        # Enregistrer completion
        self.completed_requests.append(request)
        self.metrics['requests_completed'] += 1

        # Métriques par type
        if request['client_type'] == 'VIP':
            self.metrics['response_times_vip'].append(response_time)
        else:
            self.metrics['response_times_standard'].append(response_time)

        # Métriques de récupération si phase recovery
        if self.current_phase == 'recovery':
            self.recovery_metrics.append({
                'completion_time': completion_time,
                'response_time': response_time,
                'wait_time': wait_time,
                'client_type': request['client_type']
            })

        del self.active_requests[request_id]

    async def run(self):
        """Exécute le test de pics de charge complet."""
        print(f"🚀 SCÉNARIO 3: {self.name}")
        print(f"📄 Description: {self.description}")
        print(f"📊 Profil de charge: {self.base_rps} → {self.spike_rps} → récupération")
        print(f"⏱️  Durée: {self.total_duration}s (pic: {self.spike_duration}s)")
        print(f"🔄 Anti-famine adaptatif: {self.base_aging_factor} → {self.spike_aging_factor}")
        print("-" * 60)

        # Démarrer monitoring
        self.start_monitoring()
        start_time = time.time()

        # Tâches parallèles
        generation_task = asyncio.create_task(self._generate_variable_load())
        processing_task = asyncio.create_task(self._process_requests_loop())

        # Attendre completion
        await asyncio.gather(generation_task, processing_task)

        # Attendre stabilisation
        await asyncio.sleep(10)

        # Arrêter monitoring
        self.stop_monitoring()

        # Générer rapport
        report = self.generate_spike_report()
        self.save_report(report)

        # Afficher résultats
        self.print_spike_results(report)

        return report

    async def _generate_variable_load(self):
        """Génère la charge variable selon le profil de pics."""
        start_time = time.time()

        while time.time() - start_time < self.total_duration:
            elapsed = time.time() - start_time

            # Déterminer phase et RPS
            self.determine_current_phase(elapsed)

            if self.current_phase == 'warmup':
                current_rps = self.base_rps
            elif self.current_phase == 'spike':
                # Pic avec variation sinusoïdale
                spike_progress = (elapsed - self.spike_start) / self.spike_duration
                intensity = 0.5 + 0.5 * math.sin(spike_progress * math.pi)
                current_rps = self.base_rps + (self.spike_rps - self.base_rps) * intensity
            else:  # recovery
                # Décroissance exponentielle
                recovery_elapsed = elapsed - (self.spike_start + self.spike_duration)
                decay = math.exp(-recovery_elapsed / 20)  # Constante de temps: 20s
                current_rps = self.base_rps + (self.spike_rps - self.base_rps) * decay

            self.metrics['current_rps'].append(current_rps)

            # Générer requête
            client_type = 'VIP' if random.random() < (0.3 if self.current_phase == 'spike' else 0.2) else 'STANDARD'
            request = self.generate_spike_request(client_type)

            if client_type == 'VIP':
                self.vip_queue.append(request)
            else:
                self.standard_queue.append(request)

            # Attendre selon RPS
            interval = 1.0 / max(current_rps, 0.1)
            await asyncio.sleep(interval * random.uniform(0.8, 1.2))

    async def _process_requests_loop(self):
        """Boucle de traitement adaptative."""
        start_time = time.time()

        while time.time() - start_time < self.total_duration + 15:
            self.process_requests_under_load()

            # Fréquence de traitement adaptée à la phase
            if self.current_phase == 'spike':
                await asyncio.sleep(0.05)  # Plus rapide sous pic
            else:
                await asyncio.sleep(0.1)

    def generate_spike_report(self):
        """Génère le rapport détaillé du test de pics."""
        if not self.metrics['timestamps']:
            return {"error": "Pas de données collectées"}

        # Métriques globales
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

        # Équité
        equity_ratios = [r for r in self.metrics['equity_ratios'] if r > 0]
        avg_equity_ratio = sum(equity_ratios) / len(equity_ratios) if equity_ratios else 1.0
        max_equity_degradation = max(equity_ratios) if equity_ratios else 1.0

        # Analyse de récupération
        recovery_time = self.analyze_recovery_time()

        # Files d'attente
        max_vip_queue = max(self.metrics['vip_queue_sizes']) if self.metrics['vip_queue_sizes'] else 0
        max_std_queue = max(self.metrics['standard_queue_sizes']) if self.metrics['standard_queue_sizes'] else 0

        # Résistance aux pics
        spike_handled = success_rate > 0.95 and max_equity_degradation < 10.0

        report = {
            'test_type': 'spike_test',
            'scenario_name': self.name,
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'total_duration': self.total_duration,
                'base_rps': self.base_rps,
                'spike_rps': self.spike_rps,
                'spike_duration': self.spike_duration,
                'base_aging_factor': self.base_aging_factor,
                'spike_aging_factor': self.spike_aging_factor
            },
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
                'max_equity_degradation': max_equity_degradation,
                'max_throughput': max_throughput,
                'avg_throughput': avg_throughput
            },
            'spike_analysis': {
                'spike_handled': spike_handled,
                'max_queue_size': max_vip_queue + max_std_queue,
                'recovery_time': recovery_time,
                'system_pressure_max': max(self.queue_pressure_history) if self.queue_pressure_history else 0,
                'adaptive_aging_effective': max_equity_degradation < 5.0
            },
            'queues': {
                'max_vip_queue_size': max_vip_queue,
                'max_standard_queue_size': max_std_queue,
                'avg_vip_queue_size': sum(self.metrics['vip_queue_sizes']) / len(self.metrics['vip_queue_sizes']) if
                self.metrics['vip_queue_sizes'] else 0,
                'avg_standard_queue_size': sum(self.metrics['standard_queue_sizes']) / len(
                    self.metrics['standard_queue_sizes']) if self.metrics['standard_queue_sizes'] else 0
            },
            'resources': {
                'max_cpu_usage': max(self.metrics['cpu_usage']) if self.metrics['cpu_usage'] else 0,
                'avg_cpu_usage': sum(self.metrics['cpu_usage']) / len(self.metrics['cpu_usage']) if self.metrics[
                    'cpu_usage'] else 0,
                'max_memory_usage': max(self.metrics['memory_usage']) if self.metrics['memory_usage'] else 0,
                'avg_memory_usage': sum(self.metrics['memory_usage']) / len(self.metrics['memory_usage']) if
                self.metrics['memory_usage'] else 0
            },
            'anti_starvation': {
                'adaptive_aging_used': True,
                'base_aging_factor': self.base_aging_factor,
                'spike_aging_factor': self.spike_aging_factor,
                'starvation_prevented': max_equity_degradation < 10.0,
                'max_wait_time': max([req['wait_time'] for req in self.completed_requests if 'wait_time' in req],
                                     default=0)
            },
            'dependencies': {
                'requests_with_dependencies': len([r for r in self.completed_requests if r.get('dependencies')]),
                'dependency_resolution_time': avg_response_time,  # Approximation
                'deadlocks_detected': len(self.vip_queue) + len(self.standard_queue)  # Requêtes non traitées
            },
            'time_series': {
                'timestamps': self.metrics['timestamps'],
                'vip_queue_sizes': self.metrics['vip_queue_sizes'],
                'standard_queue_sizes': self.metrics['standard_queue_sizes'],
                'cpu_usage': self.metrics['cpu_usage'],
                'memory_usage': self.metrics['memory_usage'],
                'throughput_per_second': self.metrics['throughput_per_second'],
                'equity_ratios': self.metrics['equity_ratios'],
                'current_rps': self.metrics['current_rps'],
                'phase_indicators': self.metrics['phase_indicators']
            }
        }

        return report

    def analyze_recovery_time(self):
        """Calcule le temps de récupération après le pic."""
        if not self.recovery_metrics:
            return 0

        # Temps pour revenir à des métriques normales
        recovery_start = self.spike_start + self.spike_duration

        # Chercher quand le système retrouve des performances normales
        normal_response_threshold = 3.0  # Seuil de temps de réponse normal

        for i, metric in enumerate(self.recovery_metrics):
            if metric['response_time'] < normal_response_threshold:
                return metric['completion_time'] - recovery_start

        return self.total_duration - recovery_start  # Pas encore récupéré

    def print_spike_results(self, report):
        """Affiche les résultats du test de pics de charge."""
        print(f"\n📊 RÉSULTATS DU TEST DE PICS:")
        print(f"✅ Taux de réussite: {report['summary']['success_rate']:.1%}")
        print(f"⚡ Débit max: {report['performance']['max_throughput']:.1f} req/s")
        print(f"⏱️  Temps réponse moyen: {report['summary']['avg_response_time']:.2f}s")
        print(f"⚖️  Équité moyenne: {report['performance']['equity_ratio']:.2f}")
        print(f"📈 Dégradation max: {report['performance']['max_equity_degradation']:.2f}")

        print(f"\n🔄 ANALYSE DE RÉCUPÉRATION:")
        print(f"🏔️  Pic géré: {'✅ Oui' if report['spike_analysis']['spike_handled'] else '❌ Non'}")
        print(f"⏰ Temps récupération: {report['spike_analysis']['recovery_time']:.1f}s")
        print(f"📊 Pression max: {report['spike_analysis']['system_pressure_max']:.2f}")
        print(
            f"🔄 Anti-famine adaptatif: {'✅ Efficace' if report['spike_analysis']['adaptive_aging_effective'] else '⚠️ Dégradé'}")

        print(f"\n📋 FILES D'ATTENTE:")
        print(f"🔴 Max VIP: {report['queues']['max_vip_queue_size']}")
        print(f"🔵 Max Standard: {report['queues']['max_standard_queue_size']}")
        print(f"📈 Total max: {report['queues']['max_vip_queue_size'] + report['queues']['max_standard_queue_size']}")

    def save_report(self, report):
        """Sauvegarde le rapport de test de pics."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Créer dossier
        report_dir = Path("logs/scenarios")
        report_dir.mkdir(parents=True, exist_ok=True)

        # Sauvegarder rapport détaillé
        report_path = report_dir / f"scenario_3_spike_load_{timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        # Version latest pour dashboard
        latest_path = report_dir / "scenario_3_spike_load_latest.json"
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"📄 Rapport pics de charge: {report_path}")


async def main():
    """Fonction principale pour tester les pics de charge."""
    scenario = SpikeLoadTestScenario()
    report = await scenario.run()

    print("\n" + "=" * 60)
    print("RÉSUMÉ SCÉNARIO 3 - TEST PICS DE CHARGE")
    print("=" * 60)
    print(f"🔢 Requêtes traitées: {report['summary']['completed_requests']}/{report['summary']['total_requests']}")
    print(f"📈 Taux de réussite: {report['summary']['success_rate']:.1%}")
    print(f"⚡ Débit maximum: {report['performance']['max_throughput']:.1f} req/s")
    print(f"🏔️  Pic géré: {'✅ Succès' if report['spike_analysis']['spike_handled'] else '❌ Échec'}")
    print(f"⏰ Récupération: {report['spike_analysis']['recovery_time']:.1f}s")
    print(f"⚖️  Équité maintenue: {'✅ Oui' if report['spike_analysis']['adaptive_aging_effective'] else '⚠️ Dégradée'}")
    print(f"🔄 Anti-famine: {'✅ Efficace' if report['anti_starvation']['starvation_prevented'] else '❌ Problème'}")
    print(f"🔗 Dépendances: {report['dependencies']['requests_with_dependencies']} requêtes")
    print(f"🚫 Requêtes bloquées: {report['dependencies']['deadlocks_detected']}")

    return report


if __name__ == "__main__":
    asyncio.run(main())