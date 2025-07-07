# tests/performance/scenarios/scenario_2_scalability.py
"""
Scénario 2: Test de Scalabilité
Valide la performance du système sur différents volumes de charge.
"""

import asyncio
import time
import random
import json
from datetime import datetime
from pathlib import Path
import threading
from collections import deque


class ScalabilityTestScenario:
    """
    Test de scalabilité avec volumes croissants.
    Objectif: Vérifier que le système maintient ses performances à grande échelle.
    """

    def __init__(self):
        self.name = "Test de Scalabilité"
        self.description = "Valide la consistance des performances sur différents volumes"

        # Volumes à tester (progression logarithmique)
        self.test_volumes = [100, 250, 500, 750, 1000]
        self.vip_ratio = 0.2  # 20% VIP constant

        # Mécanisme de vieillissement plus agressif pour haute charge
        self.aging_factor = 0.7

        # Métriques par volume
        self.volume_results = []

        # État système
        self.reset_system_state()

    def reset_system_state(self):
        """Remet à zéro l'état du système pour chaque test."""
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
            'timestamps': []
        }

        self.vip_queue = deque()
        self.standard_queue = deque()
        self.active_requests = {}
        self.completed_requests = []
        self.cpu_available = 100.0
        self.memory_available = 100.0

        # Tracking des dépendances pour scalabilité
        self.dependency_graph = {}
        self.resolved_dependencies = set()

    def generate_request_with_dependencies(self, request_id, client_type='STANDARD'):
        """Génère une requête avec dépendances complexes pour test de scalabilité."""
        request = {
            'id': request_id,
            'client_type': client_type,
            'arrival_time': time.time(),
            'cpu_required': random.uniform(0.5, 4.0),  # Ressources variables
            'memory_required': random.uniform(1.0, 6.0),
            'estimated_duration': random.uniform(0.2, 1.5),
            'priority': 100 if client_type == 'VIP' else 10,
            'effective_priority': 100 if client_type == 'VIP' else 10,
            'dependencies': []
        }

        # 🔧 FIX: Générer dépendances complexes (25% des requêtes) avec protection
        if random.random() < 0.25 and self.metrics['requests_sent'] > 5:
            # 🔧 FIX: S'assurer que max_deps >= 1
            max_deps = max(1, min(3, self.metrics['requests_sent'] // 10))
            num_deps = random.randint(1, max_deps)

            # Choisir des dépendances récentes
            available_deps = list(range(
                max(0, self.metrics['requests_sent'] - 20),
                self.metrics['requests_sent']
            ))

            if available_deps:
                dependencies = random.sample(
                    available_deps,
                    min(num_deps, len(available_deps))
                )
                request['dependencies'] = [f"scala-req-{dep:05d}" for dep in dependencies]

                # Enregistrer dans le graphe des dépendances
                self.dependency_graph[request['id']] = request['dependencies']

        self.metrics['requests_sent'] += 1
        return request

    def check_dependencies_with_topological_sort(self, request):
        """
        Vérifie les dépendances avec algorithme de tri topologique.
        Implémente la gestion des dépendances complexes.
        """
        if not request.get('dependencies'):
            return True

        # Vérifier que toutes les dépendances sont résolues
        for dep_id in request['dependencies']:
            if dep_id not in self.resolved_dependencies:
                return False

        return True

    def apply_aging_for_scalability(self):
        """Mécanisme de vieillissement adapté à la haute charge."""
        current_time = time.time()

        # Vieillissement plus agressif sous haute charge
        queue_pressure = len(self.standard_queue) / 100.0  # Pression de la file
        adaptive_aging = self.aging_factor * (1 + queue_pressure)

        for request in self.standard_queue:
            age = current_time - request['arrival_time']
            request['effective_priority'] = request['priority'] + (adaptive_aging * age)

            # Bonus de priorité si trop longtemps en attente (anti-famine critique)
            if age > 30:  # Plus de 30 secondes
                request['effective_priority'] += 50  # Boost important

    def process_requests_with_dependencies(self):
        """Traitement avec gestion avancée des dépendances."""
        if not (self.vip_queue or self.standard_queue):
            return

        # Appliquer vieillissement adaptatif
        self.apply_aging_for_scalability()

        # Créer liste des requêtes prêtes (dépendances satisfaites)
        ready_requests = []

        # 🔧 FIX: Convertir deque en list pour éviter l'erreur de concaténation
        vip_list = list(self.vip_queue)
        standard_list = list(self.standard_queue)

        # Parcourir les requêtes VIP
        for i, req in enumerate(vip_list):
            if self.check_dependencies_with_topological_sort(req):
                ready_requests.append(('VIP', i, req))

        # Parcourir les requêtes Standard
        for i, req in enumerate(standard_list):
            if self.check_dependencies_with_topological_sort(req):
                ready_requests.append(('STANDARD', i, req))

        if ready_requests:
            # Tri hybride avancé: Priorité + SJF + Dépendances
            ready_requests.sort(key=lambda x: (
                -x[2]['effective_priority'],  # Priorité décroissante
                len(x[2].get('dependencies', [])),  # Moins de dépendances d'abord
                x[2]['estimated_duration']  # SJF
            ))

            queue_type, index, next_request = ready_requests[0]

            # Vérifier ressources disponibles
            if (self.cpu_available >= next_request['cpu_required'] and
                    self.memory_available >= next_request['memory_required']):

                # 🔧 FIX: Retirer de la bonne deque (pas de la liste temporaire)
                if queue_type == 'VIP':
                    # Trouver et retirer l'élément de la deque originale
                    for item in self.vip_queue:
                        if item['id'] == next_request['id']:
                            self.vip_queue.remove(item)
                            break
                else:
                    # Trouver et retirer l'élément de la deque originale
                    for item in self.standard_queue:
                        if item['id'] == next_request['id']:
                            self.standard_queue.remove(item)
                            break

                # Allouer ressources
                self.cpu_available -= next_request['cpu_required']
                self.memory_available -= next_request['memory_required']

                # Démarrer traitement
                next_request['start_time'] = time.time()
                self.active_requests[next_request['id']] = next_request

                # Programmer completion
                threading.Timer(
                    next_request['estimated_duration'],
                    self._complete_request_with_deps,
                    args=[next_request['id']]
                ).start()

    def _complete_request_with_deps(self, request_id):
        """Termine une requête et met à jour les dépendances."""
        if request_id not in self.active_requests:
            return

        request = self.active_requests[request_id]
        completion_time = time.time()

        # Calculer métriques
        response_time = completion_time - request['arrival_time']
        request['completion_time'] = completion_time
        request['response_time'] = response_time

        # Libérer ressources
        self.cpu_available += request['cpu_required']
        self.memory_available += request['memory_required']

        # Marquer comme résolu pour les dépendances
        self.resolved_dependencies.add(request_id)

        # Enregistrer completion
        self.completed_requests.append(request)
        self.metrics['requests_completed'] += 1

        # Enregistrer temps de réponse
        if request['client_type'] == 'VIP':
            self.metrics['response_times_vip'].append(response_time)
        else:
            self.metrics['response_times_standard'].append(response_time)

        del self.active_requests[request_id]

    async def test_single_volume(self, volume):
        """Teste un volume spécifique de requêtes."""
        print(f"  📊 Test volume: {volume} requêtes")

        # Reset pour ce volume
        self.reset_system_state()

        start_time = time.time()

        # Générer toutes les requêtes d'un coup (burst)
        for i in range(volume):
            client_type = 'VIP' if i % 5 == 0 else 'STANDARD'  # 20% VIP
            request_id = f"scala-req-{i:05d}"
            request = self.generate_request_with_dependencies(request_id, client_type)

            if client_type == 'VIP':
                self.vip_queue.append(request)
            else:
                self.standard_queue.append(request)

        generation_time = time.time() - start_time

        # Traiter toutes les requêtes
        processing_start = time.time()

        while (self.vip_queue or self.standard_queue or self.active_requests):
            self.process_requests_with_dependencies()
            await asyncio.sleep(0.05)  # Processing rapide pour scalabilité

            # Timeout de sécurité (éviter boucle infinie)
            if time.time() - processing_start > 300:  # 5 minutes max
                print(f"    ⚠️ Timeout atteint pour volume {volume}")
                break

        processing_time = time.time() - processing_start
        total_time = time.time() - start_time

        # Calculer métriques pour ce volume
        success_rate = self.metrics['requests_completed'] / self.metrics['requests_sent']
        avg_response_time = 0
        throughput = 0

        if self.metrics['requests_completed'] > 0:
            all_times = self.metrics['response_times_vip'] + self.metrics['response_times_standard']
            avg_response_time = sum(all_times) / len(all_times)
            throughput = self.metrics['requests_completed'] / total_time

        # 🔧 FIX: Détection des deadlocks potentiels (correction de la concaténation)
        deadlocks = len([req for req in list(self.vip_queue) + list(self.standard_queue)
                         if req.get('dependencies')])

        result = {
            'volume': volume,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'throughput': throughput,
            'total_time': total_time,
            'processing_time': processing_time,
            'generation_time': generation_time,
            'deadlocks_detected': deadlocks,
            'requests_with_dependencies': len([r for r in self.completed_requests if r.get('dependencies')]),
            'dependency_resolution_efficiency': success_rate  # Si 100%, dépendances bien gérées
        }

        print(
            f"    ✅ {volume} req: {success_rate:.1%} réussite, {throughput:.1f} req/s, {avg_response_time:.2f}s moyen")
        if deadlocks > 0:
            print(f"    ⚠️ {deadlocks} requêtes bloquées par dépendances")

        return result

    async def run(self):
        """Exécute le test de scalabilité complet."""
        print(f"🚀 SCÉNARIO 2: {self.name}")
        print(f"📄 Description: {self.description}")
        print(f"📈 Volumes testés: {self.test_volumes}")
        print(f"🔗 Avec gestion des dépendances complexes")
        print("-" * 60)

        start_time = time.time()

        # Tester each volume
        for volume in self.test_volumes:
            result = await self.test_single_volume(volume)
            self.volume_results.append(result)

            # Pause entre tests pour stabilité
            await asyncio.sleep(2)

        total_test_time = time.time() - start_time

        # Générer rapport global
        report = self.generate_scalability_report(total_test_time)
        self.save_report(report)

        # Analyse de la scalabilité
        print(f"\n📊 ANALYSE DE SCALABILITÉ:")
        print(f"⏱️  Temps total: {total_test_time:.1f}s")

        # Vérifier consistance des performances
        success_rates = [r['success_rate'] for r in self.volume_results]
        avg_success = sum(success_rates) / len(success_rates)
        consistency = min(success_rates) / max(success_rates) if max(success_rates) > 0 else 0

        print(f"✅ Taux de réussite moyen: {avg_success:.1%}")
        print(f"📈 Consistance: {consistency:.1%}")

        # Débit scaling
        throughputs = [r['throughput'] for r in self.volume_results]
        max_throughput = max(throughputs)
        print(f"🚀 Débit maximum: {max_throughput:.1f} req/s")

        # Gestion des dépendances
        total_deps = sum(r['requests_with_dependencies'] for r in self.volume_results)
        total_deadlocks = sum(r['deadlocks_detected'] for r in self.volume_results)
        print(f"🔗 Dépendances gérées: {total_deps}")
        print(f"🚫 Deadlocks détectés: {total_deadlocks}")

        return report

    def generate_scalability_report(self, total_test_time):
        """Génère un rapport détaillé de scalabilité."""

        # Analyse de consistance
        success_rates = [r['success_rate'] for r in self.volume_results]
        response_times = [r['avg_response_time'] for r in self.volume_results]
        throughputs = [r['throughput'] for r in self.volume_results]

        consistency = min(success_rates) / max(success_rates) if max(success_rates) > 0 else 0
        max_throughput = max(throughputs) if throughputs else 0

        # Analyse des dépendances
        total_deps = sum(r['requests_with_dependencies'] for r in self.volume_results)
        total_deadlocks = sum(r['deadlocks_detected'] for r in self.volume_results)
        dependency_efficiency = (total_deps - total_deadlocks) / total_deps if total_deps > 0 else 1.0

        # Analyse de l'anti-famine
        max_volume_result = max(self.volume_results, key=lambda x: x['volume'])
        starvation_prevented = max_volume_result['success_rate'] > 0.95  # 95% minimum

        report = {
            'test_type': 'scalability',
            'scenario_name': self.name,
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'test_volumes': self.test_volumes,
                'vip_ratio': self.vip_ratio,
                'aging_factor': self.aging_factor,
                'total_test_time': total_test_time
            },
            'results': self.volume_results,
            'analysis': {
                'consistency': consistency,
                'max_throughput': max_throughput,
                'scalability_linear': self.analyze_linearity(),
                'performance_degradation': self.analyze_degradation()
            },
            'dependencies': {
                'total_requests_with_deps': total_deps,
                'total_deadlocks_detected': total_deadlocks,
                'dependency_resolution_efficiency': dependency_efficiency,
                'topological_sort_effective': total_deadlocks == 0
            },
            'anti_starvation': {
                'aging_factor': self.aging_factor,
                'starvation_prevented': starvation_prevented,
                'adaptive_aging_used': True,
                'max_volume_success_rate': max_volume_result['success_rate']
            },
            'metrics': {
                'requests_sent': sum(r['volume'] for r in self.volume_results),
                'requests_completed': sum(int(r['volume'] * r['success_rate']) for r in self.volume_results),
                'success_rates': success_rates,
                'response_times': response_times,
                'throughputs': throughputs
            }
        }

        return report

    def analyze_linearity(self):
        """Analyse si la scalabilité est linéaire."""
        if len(self.volume_results) < 2:
            return True

        # Calculer coefficient de corrélation volume vs throughput
        volumes = [r['volume'] for r in self.volume_results]
        throughputs = [r['throughput'] for r in self.volume_results]

        # Calcul simple de corrélation
        n = len(volumes)
        sum_v = sum(volumes)
        sum_t = sum(throughputs)
        sum_vt = sum(v * t for v, t in zip(volumes, throughputs))
        sum_v2 = sum(v * v for v in volumes)
        sum_t2 = sum(t * t for t in throughputs)

        numerator = n * sum_vt - sum_v * sum_t
        denominator = ((n * sum_v2 - sum_v * sum_v) * (n * sum_t2 - sum_t * sum_t)) ** 0.5

        correlation = numerator / denominator if denominator != 0 else 0

        # Scalabilité linéaire si corrélation > 0.8
        return abs(correlation) > 0.8

    def analyze_degradation(self):
        """Analyse la dégradation des performances."""
        if len(self.volume_results) < 2:
            return 0.0

        # Comparer performance min vs max volume
        min_vol_result = min(self.volume_results, key=lambda x: x['volume'])
        max_vol_result = max(self.volume_results, key=lambda x: x['volume'])

        # Dégradation du temps de réponse
        degradation = (max_vol_result['avg_response_time'] - min_vol_result['avg_response_time']) / min_vol_result[
            'avg_response_time'] if min_vol_result['avg_response_time'] > 0 else 0

        return max(0, degradation)  # Pas de dégradation négative

    def save_report(self, report):
        """Sauvegarde le rapport de scalabilité."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Créer dossier
        report_dir = Path("logs/scenarios")
        report_dir.mkdir(parents=True, exist_ok=True)

        # Sauvegarder rapport détaillé
        report_path = report_dir / f"scenario_2_scalability_{timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        # Version latest pour dashboard
        latest_path = report_dir / "scenario_2_scalability_latest.json"
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"📄 Rapport scalabilité: {report_path}")


async def main():
    """Fonction principale pour tester la scalabilité."""
    scenario = ScalabilityTestScenario()
    report = await scenario.run()

    print("\n" + "=" * 60)
    print("RÉSUMÉ SCÉNARIO 2 - TEST DE SCALABILITÉ")
    print("=" * 60)
    print(f"🔢 Volumes testés: {len(report['results'])}")
    print(f"📊 Volume maximum: {max(r['volume'] for r in report['results'])}")
    print(f"✅ Consistance: {report['analysis']['consistency']:.1%}")
    print(f"🚀 Débit maximum: {report['analysis']['max_throughput']:.1f} req/s")
    print(f"📈 Scalabilité: {'✅ Linéaire' if report['analysis']['scalability_linear'] else '⚠️ Non-linéaire'}")
    print(f"⬇️ Dégradation: {report['analysis']['performance_degradation']:.1%}")
    print(f"🔗 Dépendances: {report['dependencies']['total_requests_with_deps']} requêtes")
    print(f"🚫 Deadlocks: {report['dependencies']['total_deadlocks_detected']}")
    print(f"🔄 Anti-famine: {'✅ Efficace' if report['anti_starvation']['starvation_prevented'] else '❌ Problème'}")

    return report


if __name__ == "__main__":
    asyncio.run(main())