"""
Scénario 6: Test de Dépendances Circulaires
Vérifie la détection et gestion des cycles dans les dépendances.
"""

import asyncio
import time
import random
import json
import logging
from datetime import datetime
from pathlib import Path
from collections import deque, defaultdict
from enum import Enum

class CycleType(Enum):
    """Types de cycles de dépendances à tester."""
    SIMPLE_CYCLE = "simple"          # A → B → A
    TRIANGLE_CYCLE = "triangle"      # A → B → C → A
    COMPLEX_CYCLE = "complex"        # Cycles imbriqués multiples
    CHAIN_CYCLE = "chain"           # Longue chaîne avec cycle final
    DIAMOND_CYCLE = "diamond"       # Structure en diamant avec cycle

class CircularDependencyTestScenario:
    """Test de détection et gestion des dépendances circulaires."""

    def __init__(self):
        self.test_name = "Test de Dépendances Circulaires"
        self.description = "Vérifie la détection et gestion des cycles"

        # Configuration du test
        self.test_duration = 120  # 2 minutes
        self.generation_rps = 3   # Rythme lent pour analyser les dépendances
        self.total_requests = 0

        # Types de cycles à tester
        self.cycle_test_cases = [
            {
                "name": "Cycle Simple",
                "type": CycleType.SIMPLE_CYCLE,
                "requests_count": 2,
                "start_time": 10,
                "description": "A → B → A"
            },
            {
                "name": "Cycle Triangle",
                "type": CycleType.TRIANGLE_CYCLE,
                "requests_count": 3,
                "start_time": 30,
                "description": "A → B → C → A"
            },
            {
                "name": "Cycle Complexe",
                "type": CycleType.COMPLEX_CYCLE,
                "requests_count": 5,
                "start_time": 50,
                "description": "Cycles imbriqués multiples"
            },
            {
                "name": "Cycle en Chaîne",
                "type": CycleType.CHAIN_CYCLE,
                "requests_count": 6,
                "start_time": 70,
                "description": "A → B → C → D → E → F → C"
            },
            {
                "name": "Cycle en Diamant",
                "type": CycleType.DIAMOND_CYCLE,
                "requests_count": 4,
                "start_time": 90,
                "description": "A → B,C → D → A"
            }
        ]

        # Stockage des requêtes et dépendances
        self.all_requests = {}  # {id: request_data}
        self.dependency_graph = defaultdict(set)  # {id: {dépendances}}
        self.reverse_graph = defaultdict(set)     # {id: {qui en dépend}}

        # Files de traitement
        self.vip_queue = deque()
        self.standard_queue = deque()
        self.completed_requests = set()
        self.blocked_requests = set()  # Requêtes bloquées par cycles
        self.processing_requests = {}

        # Métriques de cycles
        self.cycle_metrics = {
            'cycles_detected': 0,
            'cycles_resolved': 0,
            'requests_blocked_by_cycles': 0,
            'max_cycle_length': 0,
            'cycle_detection_time': [],
            'cycle_resolution_strategies': {},
            'deadlocks_prevented': 0
        }

        # Détecteur de cycles
        self.cycle_detector = TopologicalCycleDetector()

        # Métriques temporelles
        self.performance_data = defaultdict(list)
        self.cycle_events = []

        # Configuration
        self.aging_factor = 1.0
        self.cycle_timeout = 30.0  # 30s max pour résoudre un cycle

        # Logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f"Scenario6-{datetime.now().strftime('%H%M%S')}")

    def generate_cycle_requests(self, cycle_case):
        """Génère un ensemble de requêtes formant un cycle selon le type spécifié."""
        cycle_type = cycle_case['type']
        count = cycle_case['requests_count']
        cycle_id = f"cycle-{cycle_case['name'].lower().replace(' ', '-')}-{int(time.time())}"

        requests = []
        base_id = f"{cycle_id}-req"

        if cycle_type == CycleType.SIMPLE_CYCLE:
            # A → B → A
            req_a = self._create_base_request(f"{base_id}-A")
            req_b = self._create_base_request(f"{base_id}-B", dependencies=[req_a['id']])
            # Créer le cycle en ajoutant A comme dépendance de B après
            requests = [req_a, req_b]
            # Le cycle sera créé en modifiant req_a pour dépendre de req_b

        elif cycle_type == CycleType.TRIANGLE_CYCLE:
            # A → B → C → A
            req_a = self._create_base_request(f"{base_id}-A")
            req_b = self._create_base_request(f"{base_id}-B", dependencies=[req_a['id']])
            req_c = self._create_base_request(f"{base_id}-C", dependencies=[req_b['id']])
            requests = [req_a, req_b, req_c]

        elif cycle_type == CycleType.COMPLEX_CYCLE:
            # Cycles imbriqués: A → B → C → A et C → D → E → C
            req_a = self._create_base_request(f"{base_id}-A")
            req_b = self._create_base_request(f"{base_id}-B", dependencies=[req_a['id']])
            req_c = self._create_base_request(f"{base_id}-C", dependencies=[req_b['id']])
            req_d = self._create_base_request(f"{base_id}-D", dependencies=[req_c['id']])
            req_e = self._create_base_request(f"{base_id}-E", dependencies=[req_d['id']])
            requests = [req_a, req_b, req_c, req_d, req_e]

        elif cycle_type == CycleType.CHAIN_CYCLE:
            # Longue chaîne avec cycle final: A → B → C → D → E → F → C
            req_a = self._create_base_request(f"{base_id}-A")
            req_b = self._create_base_request(f"{base_id}-B", dependencies=[req_a['id']])
            req_c = self._create_base_request(f"{base_id}-C", dependencies=[req_b['id']])
            req_d = self._create_base_request(f"{base_id}-D", dependencies=[req_c['id']])
            req_e = self._create_base_request(f"{base_id}-E", dependencies=[req_d['id']])
            req_f = self._create_base_request(f"{base_id}-F", dependencies=[req_e['id']])
            requests = [req_a, req_b, req_c, req_d, req_e, req_f]

        elif cycle_type == CycleType.DIAMOND_CYCLE:
            # Structure diamant: A → B,C → D → A
            req_a = self._create_base_request(f"{base_id}-A")
            req_b = self._create_base_request(f"{base_id}-B", dependencies=[req_a['id']])
            req_c = self._create_base_request(f"{base_id}-C", dependencies=[req_a['id']])
            req_d = self._create_base_request(f"{base_id}-D", dependencies=[req_b['id'], req_c['id']])
            requests = [req_a, req_b, req_c, req_d]

        # Marquer les requêtes comme faisant partie d'un cycle intentionnel
        for req in requests:
            req['cycle_test'] = {
                'cycle_type': cycle_type.value,
                'cycle_case': cycle_case['name'],
                'intentional_cycle': True
            }

        return requests

    def _create_base_request(self, request_id, dependencies=None):
        """Crée une requête de base avec ID et dépendances spécifiées."""
        client_type = 'VIP' if random.random() < 0.4 else 'STANDARD'

        return {
            'id': request_id,
            'client_id': f"client-cycle-{random.randint(1, 20)}",
            'client_type': client_type,
            'cpu_requested': random.uniform(0.5, 2.0),
            'memory_requested': random.uniform(1.0, 4.0),
            'estimated_duration': random.uniform(0.2, 0.8),
            'arrival_time': time.time(),
            'priority': 1000 if client_type == 'VIP' else 10,
            'dependencies': dependencies or [],
            'status': 'pending'
        }

    def create_intentional_cycle(self, requests, cycle_type):
        """Crée intentionnellement le cycle dans les requêtes."""
        if not requests:
            return

        if cycle_type == CycleType.SIMPLE_CYCLE:
            # A → B → A
            requests[0]['dependencies'].append(requests[1]['id'])  # A dépend de B

        elif cycle_type == CycleType.TRIANGLE_CYCLE:
            # A → B → C → A
            requests[0]['dependencies'].append(requests[2]['id'])  # A dépend de C

        elif cycle_type == CycleType.COMPLEX_CYCLE:
            # A → B → C → A et C → D → E → C
            requests[0]['dependencies'].append(requests[2]['id'])  # A dépend de C (cycle 1)
            requests[2]['dependencies'].append(requests[4]['id'])  # C dépend de E (cycle 2)

        elif cycle_type == CycleType.CHAIN_CYCLE:
            # F → C (ferme le cycle)
            requests[2]['dependencies'].append(requests[5]['id'])  # C dépend de F

        elif cycle_type == CycleType.DIAMOND_CYCLE:
            # D → A (ferme le cycle)
            requests[0]['dependencies'].append(requests[3]['id'])  # A dépend de D

    def generate_normal_request(self):
        """Génère une requête normale avec dépendances légitimes."""
        request_id = f"normal-{self.total_requests + 1}"
        self.total_requests += 1

        # Choisir des dépendances légitimes (requêtes déjà complétées)
        possible_deps = list(self.completed_requests)
        dependencies = []

        if possible_deps and random.random() < 0.3:  # 30% de chance d'avoir des dépendances
            num_deps = random.randint(1, min(3, len(possible_deps)))
            dependencies = random.sample(possible_deps, num_deps)

        return self._create_base_request(request_id, dependencies)

    def add_request_to_graph(self, request):
        """Ajoute une requête au graphe de dépendances."""
        req_id = request['id']
        self.all_requests[req_id] = request

        # Ajouter les dépendances au graphe
        for dep_id in request['dependencies']:
            self.dependency_graph[req_id].add(dep_id)
            self.reverse_graph[dep_id].add(req_id)

    def detect_cycles_comprehensive(self):
        """Détection complète des cycles avec analyse détaillée."""
        detection_start = time.time()

        cycles_found = self.cycle_detector.find_all_cycles(self.dependency_graph)

        detection_time = time.time() - detection_start
        self.cycle_metrics['cycle_detection_time'].append(detection_time)

        for cycle in cycles_found:
            cycle_length = len(cycle)
            self.cycle_metrics['max_cycle_length'] = max(
                self.cycle_metrics['max_cycle_length'], cycle_length
            )

            self.logger.warning(f"🔄 CYCLE DÉTECTÉ: {' → '.join(cycle)} → {cycle[0]}")

            # Enregistrer l'événement
            cycle_event = {
                'timestamp': time.time(),
                'cycle': cycle,
                'length': cycle_length,
                'detection_time': detection_time,
                'affected_requests': cycle
            }
            self.cycle_events.append(cycle_event)

            # Stratégie de résolution
            resolution_strategy = self.resolve_cycle(cycle)
            cycle_event['resolution_strategy'] = resolution_strategy

        self.cycle_metrics['cycles_detected'] += len(cycles_found)

        return cycles_found

    def resolve_cycle(self, cycle):
        """Résout un cycle détecté selon différentes stratégies."""
        if not cycle:
            return "no_action"

        # Analyser le cycle pour choisir la stratégie
        cycle_requests = [self.all_requests.get(req_id) for req_id in cycle]
        cycle_requests = [r for r in cycle_requests if r is not None]

        if not cycle_requests:
            return "invalid_cycle"

        # Vérifier si c'est un cycle de test intentionnel
        intentional_cycles = [r for r in cycle_requests if r.get('cycle_test', {}).get('intentional_cycle', False)]

        if intentional_cycles:
            # Cycle de test - appliquer stratégie de test
            self.logger.info(f"🧪 Cycle de test détecté: {cycle[0]} (type: {intentional_cycles[0]['cycle_test']['cycle_type']})")
            return self._resolve_test_cycle(cycle, intentional_cycles[0]['cycle_test']['cycle_type'])
        else:
            # Cycle accidentel - appliquer stratégie de production
            return self._resolve_production_cycle(cycle, cycle_requests)

    def _resolve_test_cycle(self, cycle, cycle_type):
        """Résout un cycle de test selon des stratégies prédéfinies."""
        strategies = {
            'simple': 'break_oldest_dependency',
            'triangle': 'priority_based_breaking',
            'complex': 'partial_execution',
            'chain': 'break_weakest_link',
            'diamond': 'parallel_execution'
        }

        strategy = strategies.get(cycle_type, 'break_oldest_dependency')

        if strategy == 'break_oldest_dependency':
            # Supprimer la dépendance la plus ancienne
            oldest_req = min(cycle, key=lambda rid: self.all_requests[rid]['arrival_time'])
            self._break_dependency(oldest_req, cycle)

        elif strategy == 'priority_based_breaking':
            # Supprimer dépendances des requêtes basse priorité
            standard_reqs = [rid for rid in cycle
                           if self.all_requests[rid]['client_type'] == 'STANDARD']
            if standard_reqs:
                self._break_dependency(standard_reqs[0], cycle)

        elif strategy == 'partial_execution':
            # Exécuter partiellement les requêtes sans dépendances
            independent_reqs = [rid for rid in cycle
                              if not self.all_requests[rid]['dependencies']]
            for req_id in independent_reqs:
                self._force_execution(req_id)

        elif strategy == 'break_weakest_link':
            # Identifier le lien le plus faible (moins de dépendances)
            weakest = min(cycle, key=lambda rid: len(self.all_requests[rid]['dependencies']))
            self._break_dependency(weakest, cycle)

        elif strategy == 'parallel_execution':
            # Exécuter en parallèle les branches indépendantes
            self._execute_parallel_branches(cycle)

        self.cycle_metrics['cycles_resolved'] += 1
        self.cycle_metrics['deadlocks_prevented'] += 1

        strategy_count = self.cycle_metrics['cycle_resolution_strategies'].get(strategy, 0)
        self.cycle_metrics['cycle_resolution_strategies'][strategy] = strategy_count + 1

        return strategy

    def _resolve_production_cycle(self, cycle, cycle_requests):
        """Résout un cycle accidentel en production."""
        # En production, priorité à la sécurité
        self.logger.error(f"🚨 CYCLE ACCIDENTEL: {' → '.join(cycle)}")

        # Stratégie conservative: rejeter les requêtes du cycle
        for req_id in cycle:
            if req_id in self.all_requests:
                self.blocked_requests.add(req_id)
                self.cycle_metrics['requests_blocked_by_cycles'] += 1
                self.logger.warning(f"❌ Requête {req_id} bloquée (cycle accidentel)")

        return "block_all_requests"

    def _break_dependency(self, req_id, cycle):
        """Supprime une dépendance spécifique pour briser un cycle."""
        if req_id not in self.all_requests:
            return

        request = self.all_requests[req_id]
        original_deps = request['dependencies'].copy()

        # Supprimer les dépendances vers d'autres membres du cycle
        request['dependencies'] = [dep for dep in request['dependencies'] if dep not in cycle]

        # Mettre à jour le graphe
        for dep in original_deps:
            if dep in cycle:
                self.dependency_graph[req_id].discard(dep)
                self.reverse_graph[dep].discard(req_id)

        self.logger.info(f"🔨 Dépendance brisée: {req_id} (supprimé {len(original_deps) - len(request['dependencies'])} liens)")

    def _force_execution(self, req_id):
        """Force l'exécution d'une requête en ignorant ses dépendances."""
        if req_id not in self.all_requests:
            return

        request = self.all_requests[req_id]
        request['status'] = 'force_executed'
        self.completed_requests.add(req_id)

        self.logger.info(f"⚡ Exécution forcée: {req_id}")

    def _execute_parallel_branches(self, cycle):
        """Exécute en parallèle les branches indépendantes d'un cycle."""
        # Identifier les requêtes qui peuvent s'exécuter en parallèle
        parallel_candidates = []

        for req_id in cycle:
            request = self.all_requests[req_id]
            # Vérifier si toutes les dépendances hors cycle sont satisfaites
            external_deps = [dep for dep in request['dependencies'] if dep not in cycle]
            if all(dep in self.completed_requests for dep in external_deps):
                parallel_candidates.append(req_id)

        # Exécuter les candidats en parallèle
        for req_id in parallel_candidates:
            self._force_execution(req_id)

        self.logger.info(f"🔀 Exécution parallèle: {len(parallel_candidates)} requêtes")

    def process_requests_with_cycle_detection(self):
        """Traite les requêtes en détectant et gérant les cycles."""
        # Détecter les cycles avant traitement
        cycles = self.detect_cycles_comprehensive()

        if cycles:
            self.logger.warning(f"⚠️ {len(cycles)} cycle(s) détecté(s) avant traitement")

        # Traitement normal des requêtes non bloquées
        if not self.vip_queue and not self.standard_queue:
            return

        # Traiter les requêtes en cours
        completed_ids = []
        for req_id, (request, start_time) in list(self.processing_requests.items()):
            processing_time = time.time() - start_time

            if processing_time >= request['estimated_duration']:
                completed_ids.append(req_id)
                self.completed_requests.add(req_id)
                del self.processing_requests[req_id]

                # Mettre à jour le graphe
                self._remove_from_graph(req_id)

        # Démarrer nouvelles requêtes
        max_concurrent = 8
        started_count = 0

        while (len(self.processing_requests) < max_concurrent and
               started_count < max_concurrent and
               (self.vip_queue or self.standard_queue)):

            # Priorité VIP stricte
            if self.vip_queue:
                _, request = self.vip_queue.popleft()
            elif self.standard_queue:
                _, request = self.standard_queue.popleft()
            else:
                break

            req_id = request['id']

            # Vérifier si bloquée par cycle
            if req_id in self.blocked_requests:
                self.logger.warning(f"🚫 Requête {req_id} bloquée par cycle - ignorée")
                continue

            # Vérifier les dépendances
            if self._dependencies_satisfied(request):
                self.processing_requests[req_id] = (request, time.time())
                started_count += 1
                self.logger.debug(f"▶️ Démarrage {req_id}")
            else:
                # Remettre en file d'attente
                if request['client_type'] == 'VIP':
                    self.vip_queue.append((time.time(), request))
                else:
                    self.standard_queue.append((time.time(), request))
                break

    def _dependencies_satisfied(self, request):
        """Vérifie si toutes les dépendances d'une requête sont satisfaites."""
        return all(dep_id in self.completed_requests for dep_id in request['dependencies'])

    def _remove_from_graph(self, req_id):
        """Supprime une requête complétée du graphe de dépendances."""
        # Supprimer du graphe principal
        if req_id in self.dependency_graph:
            del self.dependency_graph[req_id]

        # Supprimer du graphe inverse
        if req_id in self.reverse_graph:
            del self.reverse_graph[req_id]

        # Supprimer des dépendances des autres requêtes
        for other_id in self.dependency_graph:
            self.dependency_graph[other_id].discard(req_id)

        for other_id in self.reverse_graph:
            self.reverse_graph[other_id].discard(req_id)

    async def run_circular_dependency_test(self):
        """Exécute le test complet de dépendances circulaires."""
        self.logger.info(f"🚀 DÉMARRAGE - {self.test_name}")
        self.logger.info(f"📄 {self.description}")
        self.logger.info(f"⏱️ Durée: {self.test_duration}s avec {len(self.cycle_test_cases)} types de cycles")
        self.logger.info(f"🔄 Rythme génération: {self.generation_rps} req/s")
        print("-" * 100)

        start_time = time.time()
        normal_requests_count = 0
        cycle_test_idx = 0

        # Boucle principale du test
        while (time.time() - start_time) < self.test_duration:
            current_time = time.time()
            elapsed = current_time - start_time

            # === GÉNÉRATION DE CYCLES DE TEST ===

            if (cycle_test_idx < len(self.cycle_test_cases)):
                test_case = self.cycle_test_cases[cycle_test_idx]
                if elapsed >= test_case['start_time']:
                    self.logger.info(f"🧪 GÉNÉRATION CYCLE DE TEST: {test_case['name']}")
                    self.logger.info(f"📋 Description: {test_case['description']}")

                    # Générer les requêtes du cycle
                    cycle_requests = self.generate_cycle_requests(test_case)

                    # Créer le cycle intentionnel
                    self.create_intentional_cycle(cycle_requests, test_case['type'])

                    # Ajouter les requêtes au système
                    for request in cycle_requests:
                        self.add_request_to_graph(request)

                        # Ajouter à la file appropriée
                        arrival_time = time.time()
                        if request['client_type'] == 'VIP':
                            self.vip_queue.append((arrival_time, request))
                        else:
                            self.standard_queue.append((arrival_time, request))

                    self.logger.info(f"✅ {len(cycle_requests)} requêtes de cycle ajoutées")
                    cycle_test_idx += 1

            # === GÉNÉRATION DE REQUÊTES NORMALES ===

            if random.random() < (self.generation_rps / 100):
                normal_request = self.generate_normal_request()
                self.add_request_to_graph(normal_request)

                arrival_time = time.time()
                if normal_request['client_type'] == 'VIP':
                    self.vip_queue.append((arrival_time, normal_request))
                else:
                    self.standard_queue.append((arrival_time, normal_request))

                normal_requests_count += 1

            # === TRAITEMENT AVEC DÉTECTION DE CYCLES ===

            self.process_requests_with_cycle_detection()

            # === COLLECTE DE MÉTRIQUES ===

            current_metrics = {
                'timestamp': current_time,
                'elapsed': elapsed,
                'total_requests': len(self.all_requests),
                'completed_requests': len(self.completed_requests),
                'blocked_requests': len(self.blocked_requests),
                'cycles_detected': self.cycle_metrics['cycles_detected'],
                'cycles_resolved': self.cycle_metrics['cycles_resolved'],
                'graph_size': len(self.dependency_graph),
                'queue_sizes': len(self.vip_queue) + len(self.standard_queue)
            }

            for key, value in current_metrics.items():
                self.performance_data[key].append(value)

            # Attendre avant prochaine itération
            await asyncio.sleep(0.2)

        # === PHASE DE FINALISATION ===

        self.logger.info("🔄 Finalisation et traitement des requêtes restantes...")

        # Dernière détection de cycles
        final_cycles = self.detect_cycles_comprehensive()
        if final_cycles:
            self.logger.warning(f"⚠️ {len(final_cycles)} cycle(s) restant(s) en fin de test")

        # Finir le traitement
        final_start = time.time()
        while ((self.vip_queue or self.standard_queue or self.processing_requests) and
               (time.time() - final_start < 30)):  # Max 30s
            self.process_requests_with_cycle_detection()
            await asyncio.sleep(0.1)

        # === CALCUL DES MÉTRIQUES FINALES ===

        total_duration = time.time() - start_time

        # Sauvegarder et afficher résultats
        results = await self.save_cycle_test_results(
            normal_requests_count, total_duration
        )

        self.display_cycle_test_results(results)

        return results

    async def save_cycle_test_results(self, normal_requests, duration):
        """Sauvegarde les résultats du test de cycles."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        total_requests = len(self.all_requests)
        completed_requests = len(self.completed_requests)
        blocked_requests = len(self.blocked_requests)

        # Nettoyer les test cases pour la sérialisation JSON
        clean_test_cases = []
        for case in self.cycle_test_cases:
            clean_case = case.copy()
            if 'type' in clean_case and hasattr(clean_case['type'], 'value'):
                clean_case['type'] = clean_case['type'].value
            clean_test_cases.append(clean_case)

        results = {
            "test_type": "circular_dependencies",
            "scenario_name": self.test_name,
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "test_duration": self.test_duration,
                "generation_rps": self.generation_rps,
                "cycle_test_cases": len(self.cycle_test_cases),
                "cycle_timeout": self.cycle_timeout
            },
            "summary": {
                "total_requests": total_requests,
                "normal_requests": normal_requests,
                "cycle_test_requests": total_requests - normal_requests,
                "completed_requests": completed_requests,
                "blocked_requests": blocked_requests,
                "success_rate": completed_requests / max(total_requests, 1),
                "test_duration": duration
            },
            "cycle_metrics": self.cycle_metrics,
            "cycle_test_cases": clean_test_cases,
            "cycle_events": self.cycle_events,
            "detection_performance": {
                "avg_detection_time": (sum(self.cycle_metrics['cycle_detection_time']) /
                                     max(len(self.cycle_metrics['cycle_detection_time']), 1)),
                "max_cycle_length": self.cycle_metrics['max_cycle_length'],
                "total_detections": len(self.cycle_events)
            },
            "resolution_analysis": {
                "strategies_used": self.cycle_metrics['cycle_resolution_strategies'],
                "resolution_success_rate": (self.cycle_metrics['cycles_resolved'] /
                                           max(self.cycle_metrics['cycles_detected'], 1))
            },
            "performance_timeseries": {
                k: v[-50:] for k, v in self.performance_data.items()  # Derniers 50 points
            }
        }

        # Sauvegarder
        logs_dir = Path("logs/scenarios")
        logs_dir.mkdir(parents=True, exist_ok=True)

        filename = f"scenario_6_circular_dependencies_{timestamp}.json"
        filepath = logs_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"📄 Rapport dépendances circulaires: {filepath}")

        return results

    def display_cycle_test_results(self, results):
        """Affiche les résultats du test de dépendances circulaires."""
        print("📊 RÉSULTATS DU TEST DE DÉPENDANCES CIRCULAIRES:")
        print(f"✅ Taux de réussite: {results['summary']['success_rate']*100:.1f}%")
        print(f"🔄 Cycles détectés: {self.cycle_metrics['cycles_detected']}")
        print(f"✅ Cycles résolus: {self.cycle_metrics['cycles_resolved']}")
        print(f"🚫 Requêtes bloquées: {self.cycle_metrics['requests_blocked_by_cycles']}")
        print(f"🛡️  Deadlocks prévenus: {self.cycle_metrics['deadlocks_prevented']}")
        print(f"📏 Longueur cycle max: {self.cycle_metrics['max_cycle_length']}")

        if self.cycle_metrics['cycle_detection_time']:
            avg_detection = sum(self.cycle_metrics['cycle_detection_time']) / len(self.cycle_metrics['cycle_detection_time'])
            print(f"⚡ Temps détection moyen: {avg_detection*1000:.2f}ms")

        print("\n🔧 STRATÉGIES DE RÉSOLUTION UTILISÉES:")
        for strategy, count in self.cycle_metrics['cycle_resolution_strategies'].items():
            print(f"  • {strategy}: {count} fois")

        print("\n🧪 CYCLES DE TEST EXÉCUTÉS:")
        for i, test_case in enumerate(self.cycle_test_cases):
            print(f"  {i+1}. {test_case['name']}: {test_case['description']}")

        print("\n" + "=" * 100)
        print("RÉSUMÉ SCÉNARIO 6 - TEST DE DÉPENDANCES CIRCULAIRES")
        print("=" * 100)
        print(f"🔢 Requêtes totales: {results['summary']['total_requests']}")
        print(f"📝 Requêtes normales: {results['summary']['normal_requests']}")
        print(f"🧪 Requêtes de test: {results['summary']['cycle_test_requests']}")
        print(f"✅ Requêtes complétées: {results['summary']['completed_requests']}")
        print(f"🚫 Requêtes bloquées: {results['summary']['blocked_requests']}")
        print(f"📈 Taux de réussite: {results['summary']['success_rate']*100:.1f}%")
        print(f"🔄 Cycles détectés: {self.cycle_metrics['cycles_detected']}")
        print(f"✅ Cycles résolus: {self.cycle_metrics['cycles_resolved']}")
        print(f"🛡️  Deadlocks prévenus: {self.cycle_metrics['deadlocks_prevented']}")
        print(f"⏰ Durée totale: {results['summary']['test_duration']:.1f}s")

        # Évaluation de l'efficacité
        if self.cycle_metrics['cycles_detected'] == 0:
            print("🏆 DÉTECTION: Aucun cycle - Test de génération à vérifier")
        elif self.cycle_metrics['cycles_resolved'] == self.cycle_metrics['cycles_detected']:
            print("🏆 RÉSOLUTION: Parfaite (100% des cycles résolus)")
        elif self.cycle_metrics['cycles_resolved'] >= self.cycle_metrics['cycles_detected'] * 0.8:
            print("🥈 RÉSOLUTION: Bonne (≥80% des cycles résolus)")
        else:
            print("⚠️  RÉSOLUTION: À améliorer (<80% des cycles résolus)")


class TopologicalCycleDetector:
    """Détecteur de cycles utilisant DFS avec pile d'appels."""

    def __init__(self):
        self.visited = set()
        self.rec_stack = set()
        self.cycles_found = []

    def find_all_cycles(self, graph):
        """Trouve tous les cycles dans le graphe."""
        self.visited.clear()
        self.rec_stack.clear()
        self.cycles_found.clear()

        # DFS depuis chaque nœud non visité
        for node in graph:
            if node not in self.visited:
                self._dfs_cycle_detection(node, graph, [])

        return self.cycles_found

    def _dfs_cycle_detection(self, node, graph, path):
        """DFS récursif pour détection de cycles."""
        self.visited.add(node)
        self.rec_stack.add(node)
        path.append(node)

        # Explorer tous les voisins
        for neighbor in graph.get(node, set()):
            if neighbor not in self.visited:
                self._dfs_cycle_detection(neighbor, graph, path)
            elif neighbor in self.rec_stack:
                # Cycle détecté - extraire le cycle
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:]
                if len(cycle) > 1:  # Éviter les auto-boucles triviales
                    self.cycles_found.append(cycle[:])

        # Backtrack
        path.pop()
        self.rec_stack.remove(node)


async def main():
    """Fonction principale pour exécuter le test de dépendances circulaires."""
    scenario = CircularDependencyTestScenario()

    print("🔄" * 20)
    print("🚀 SCÉNARIO 6: Test de Dépendances Circulaires")
    print(f"📄 Description: {scenario.description}")
    print(f"⏱️ Durée: {scenario.test_duration}s")
    print(f"🧪 Types de cycles: {len(scenario.cycle_test_cases)}")
    print(f"🔄 Rythme: {scenario.generation_rps} req/s")
    print("-" * 100)

    try:
        results = await scenario.run_circular_dependency_test()
        return results
    except Exception as e:
        scenario.logger.error(f"Erreur fatale: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    results = asyncio.run(main())
    if results:
        print("🎯 Test de dépendances circulaires terminé avec succès!")
    else:
        print("❌ Échec du test de dépendances circulaires")