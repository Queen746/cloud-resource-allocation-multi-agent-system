"""
Scénario 5: Test de Résistance aux Pannes d'Agents
Teste la résilience de l'architecture multi-agents en simulant des pannes.
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


class AgentStatus(Enum):
    """États possibles d'un agent."""
    RUNNING = "running"
    FAILED = "failed"
    RECOVERING = "recovering"
    DEGRADED = "degraded"


class FaultToleranceTestScenario:
    """Test de résistance aux pannes d'agents."""

    def __init__(self):
        self.test_name = "Test de Résistance aux Pannes"
        self.description = "Valide la résilience de l'architecture multi-agents"

        # Configuration du test
        self.test_duration = 180  # 3 minutes total
        self.baseline_rps = 8  # Charge normale pendant les pannes
        self.total_requests = 0

        # Scénarios de panne à tester
        self.fault_scenarios = [
            {
                "name": "Panne ClientManager",
                "target_agent": "client_manager",
                "start_time": 30,
                "duration": 20,
                "recovery_time": 10,
                "impact_expected": "Arrêt nouvelles requêtes, traitement continue"
            },
            {
                "name": "Panne ResourceManager",
                "target_agent": "resource_manager",
                "start_time": 70,
                "duration": 25,
                "recovery_time": 15,
                "impact_expected": "Blocage allocations, files s'accumulent"
            },
            {
                "name": "Panne LoadBalancer",
                "target_agent": "load_balancer",
                "start_time": 110,
                "duration": 15,
                "recovery_time": 8,
                "impact_expected": "Placement sous-optimal, performance dégradée"
            },
            {
                "name": "Panne Monitor",
                "target_agent": "monitor",
                "start_time": 140,
                "duration": 10,
                "recovery_time": 5,
                "impact_expected": "Perte métriques, fonctionnel sinon"
            }
        ]

        # État des agents simulés
        self.agents_status = {
            "client_manager": AgentStatus.RUNNING,
            "resource_manager": AgentStatus.RUNNING,
            "load_balancer": AgentStatus.RUNNING,
            "monitor": AgentStatus.RUNNING
        }

        # Métriques de résilience
        self.resilience_metrics = {
            'total_downtime': 0,
            'requests_lost': 0,
            'degraded_performance_time': 0,
            'recovery_times': {},
            'availability_percentage': 0,
            'fault_detection_time': {},
            'cascade_failures': 0
        }

        # Files d'attente et système
        self.vip_queue = deque()
        self.standard_queue = deque()
        self.completed_requests = set()
        self.failed_requests = set()
        self.lost_requests = set()  # Requêtes perdues lors des pannes
        self.processing_requests = {}

        # Buffers de sauvegarde (résilience)
        self.backup_queues = {
            'vip_backup': deque(),
            'standard_backup': deque()
        }

        # Métriques temporelles
        self.performance_data = defaultdict(list)
        self.fault_events = []

        # Configuration de vieillissement adaptatif aux pannes
        self.aging_factor = 1.5
        self.degraded_aging_factor = 3.0  # Plus agressif lors des pannes

        # Logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f"Scenario5-{datetime.now().strftime('%H%M%S')}")

    def simulate_agent_failure(self, agent_name, duration):
        """Simule la panne d'un agent spécifique."""
        if agent_name not in self.agents_status:
            return False

        self.logger.warning(f"🔥 SIMULATION PANNE: {agent_name} pour {duration}s")

        # Marquer l'agent comme défaillant
        self.agents_status[agent_name] = AgentStatus.FAILED

        # Enregistrer l'événement
        fault_event = {
            'timestamp': time.time(),
            'agent': agent_name,
            'event_type': 'failure_start',
            'duration_planned': duration,
            'system_state': self._capture_system_state()
        }
        self.fault_events.append(fault_event)

        return True

    def simulate_agent_recovery(self, agent_name):
        """Simule la récupération d'un agent."""
        if (agent_name not in self.agents_status or
                self.agents_status[agent_name] != AgentStatus.FAILED):
            return False

        recovery_start = time.time()
        self.logger.info(f"🔄 RÉCUPÉRATION: {agent_name}")

        # Phase de récupération (performance dégradée)
        self.agents_status[agent_name] = AgentStatus.RECOVERING

        # Simuler temps de récupération (2-8 secondes)
        recovery_time = random.uniform(2, 8)

        # Restaurer les données depuis les backups si nécessaire
        if agent_name == "client_manager":
            self._restore_queue_from_backup()

        # Marquer comme complètement récupéré
        self.agents_status[agent_name] = AgentStatus.RUNNING

        actual_recovery_time = time.time() - recovery_start
        self.resilience_metrics['recovery_times'][agent_name] = actual_recovery_time

        # Enregistrer l'événement de récupération
        recovery_event = {
            'timestamp': time.time(),
            'agent': agent_name,
            'event_type': 'recovery_complete',
            'recovery_time': actual_recovery_time,
            'system_state': self._capture_system_state()
        }
        self.fault_events.append(recovery_event)

        self.logger.info(f"✅ {agent_name} récupéré en {actual_recovery_time:.2f}s")
        return True

    def _capture_system_state(self):
        """Capture l'état actuel du système."""
        return {
            'vip_queue_size': len(self.vip_queue),
            'standard_queue_size': len(self.standard_queue),
            'processing_count': len(self.processing_requests),
            'completed_count': len(self.completed_requests),
            'failed_count': len(self.failed_requests),
            'agents_status': {k: v.value for k, v in self.agents_status.items()}
        }

    def _backup_queues(self):
        """Sauvegarde les files d'attente pour récupération."""
        if random.random() < 0.8:  # 80% de chance de backup réussi
            self.backup_queues['vip_backup'] = self.vip_queue.copy()
            self.backup_queues['standard_backup'] = self.standard_queue.copy()

    def _restore_queue_from_backup(self):
        """Restaure les files depuis la sauvegarde."""
        if self.backup_queues['vip_backup']:
            self.vip_queue.extend(self.backup_queues['vip_backup'])
            self.backup_queues['vip_backup'].clear()

        if self.backup_queues['standard_backup']:
            self.standard_queue.extend(self.backup_queues['standard_backup'])
            self.backup_queues['standard_backup'].clear()

        self.logger.info("📦 Files d'attente restaurées depuis la sauvegarde")

    def generate_request_during_fault(self):
        """Génère une requête adaptée au contexte de panne."""
        request_id = f"fault-{self.total_requests + 1}"
        self.total_requests += 1

        # Type client (légèrement plus de VIP en cas de problème)
        client_type = 'VIP' if random.random() < 0.3 else 'STANDARD'

        request = {
            'id': request_id,
            'client_id': f"client-fault-{random.randint(1, 50)}",
            'client_type': client_type,
            'cpu_requested': random.uniform(1.0, 4.0),
            'memory_requested': random.uniform(2.0, 8.0),
            'estimated_duration': random.uniform(0.3, 1.5),
            'arrival_time': time.time(),
            'priority': 1000 if client_type == 'VIP' else 10,
            'dependencies': [],  # Pas de dépendances pendant les tests de panne
            'fault_context': {
                'failed_agents': [name for name, status in self.agents_status.items()
                                  if status == AgentStatus.FAILED],
                'system_degraded': any(status != AgentStatus.RUNNING
                                       for status in self.agents_status.values())
            }
        }

        return request

    def process_requests_with_faults(self):
        """Traite les requêtes en tenant compte des pannes d'agents."""
        if not self.vip_queue and not self.standard_queue:
            return

        # Vérifier l'état des agents critiques
        client_manager_ok = self.agents_status["client_manager"] == AgentStatus.RUNNING
        resource_manager_ok = self.agents_status["resource_manager"] == AgentStatus.RUNNING
        load_balancer_ok = self.agents_status["load_balancer"] == AgentStatus.RUNNING

        # Déterminer la capacité de traitement selon les pannes
        base_capacity = 10

        if not resource_manager_ok:
            # Panne critique - pas d'allocation possible
            self.logger.warning("🚫 ResourceManager en panne - Traitement suspendu")
            return

        if not client_manager_ok:
            # Pas de nouvelles requêtes, mais traitement continue
            current_capacity = max(1, base_capacity // 2)
            self.logger.warning("⚠️ ClientManager en panne - Capacité réduite")
        else:
            current_capacity = base_capacity

        if not load_balancer_ok:
            # Placement sous-optimal
            current_capacity = max(1, int(base_capacity * 0.7))
            self.logger.warning("⚠️ LoadBalancer en panne - Performance dégradée")

        # Facteur de vieillissement adaptatif
        current_aging = (self.degraded_aging_factor if any(status != AgentStatus.RUNNING
                                                           for status in self.agents_status.values())
                         else self.aging_factor)

        # Traiter les requêtes en cours
        completed_ids = []
        for req_id, (request, start_time) in list(self.processing_requests.items()):
            processing_time = time.time() - start_time

            # Temps de traitement affecté par les pannes
            slowdown_factor = 1.0
            if not load_balancer_ok:
                slowdown_factor *= 1.4  # 40% plus lent
            if self.agents_status["monitor"] == AgentStatus.FAILED:
                slowdown_factor *= 1.1  # 10% plus lent (perte métriques)

            adjusted_duration = request['estimated_duration'] * slowdown_factor

            if processing_time >= adjusted_duration:
                completed_ids.append(req_id)

                # Risque d'échec accru lors des pannes
                failure_risk = 0.01  # 1% de base
                if not load_balancer_ok:
                    failure_risk += 0.03  # +3% si LoadBalancer en panne
                if len([s for s in self.agents_status.values() if s != AgentStatus.RUNNING]) > 1:
                    failure_risk += 0.02  # +2% si pannes multiples

                if random.random() < failure_risk:
                    self.failed_requests.add(req_id)
                    self.logger.warning(f"❌ Requête {req_id} échouée (contexte de panne)")
                else:
                    self.completed_requests.add(req_id)

                del self.processing_requests[req_id]

        # Démarrer nouvelles requêtes selon la capacité disponible
        started_count = 0
        max_new = max(0, current_capacity - len(self.processing_requests))

        while (started_count < max_new and (self.vip_queue or self.standard_queue)):

            # Priorité VIP stricte, puis Standard avec vieillissement
            if self.vip_queue:
                _, request = self.vip_queue.popleft()
                source = "VIP"
            elif self.standard_queue:
                # Vieillissement plus agressif lors des pannes
                best_idx = 0
                best_priority = 0

                for i, (arrival_time, req) in enumerate(self.standard_queue):
                    age = time.time() - arrival_time
                    eff_priority = req['priority'] + (current_aging * age)
                    if eff_priority > best_priority:
                        best_priority = eff_priority
                        best_idx = i

                # Extraire la meilleure requête
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
            started_count += 1

            self.logger.debug(f"🔄 Traitement {request['id']} ({source}) - "
                              f"Agents: {[k for k, v in self.agents_status.items() if v == AgentStatus.RUNNING]}")

    def handle_request_arrival_with_faults(self, request):
        """Gère l'arrivée d'une nouvelle requête selon l'état des agents."""
        client_manager_ok = self.agents_status["client_manager"] == AgentStatus.RUNNING

        if not client_manager_ok:
            # ClientManager en panne - requête potentiellement perdue
            if random.random() < 0.2:  # 20% de chance de perte
                self.lost_requests.add(request['id'])
                self.resilience_metrics['requests_lost'] += 1
                self.logger.warning(f"📤 Requête {request['id']} perdue (ClientManager en panne)")
                return False
            else:
                # Sauvegarde dans buffer de secours
                if request['client_type'] == 'VIP':
                    self.backup_queues['vip_backup'].append((time.time(), request))
                else:
                    self.backup_queues['standard_backup'].append((time.time(), request))
                self.logger.info(f"📦 Requête {request['id']} sauvegardée")
                return True
        else:
            # Fonctionnement normal
            arrival_time = time.time()
            if request['client_type'] == 'VIP':
                self.vip_queue.append((arrival_time, request))
            else:
                self.standard_queue.append((arrival_time, request))
            return True

    def calculate_availability_metrics(self):
        """Calcule les métriques de disponibilité."""
        total_test_time = self.test_duration

        # Calculer le temps de panne total
        total_downtime = 0
        degraded_time = 0

        for event in self.fault_events:
            if event['event_type'] == 'failure_start':
                # Trouver l'événement de récupération correspondant
                recovery_event = next(
                    (e for e in self.fault_events
                     if e['agent'] == event['agent'] and
                     e['event_type'] == 'recovery_complete' and
                     e['timestamp'] > event['timestamp']),
                    None
                )

                if recovery_event:
                    downtime = recovery_event['timestamp'] - event['timestamp']
                    total_downtime += downtime

                    # Distinguer panne totale vs dégradée
                    if event['agent'] in ['resource_manager']:
                        # Panne critique
                        pass  # Déjà compté dans downtime
                    else:
                        # Panne dégradée
                        degraded_time += downtime

        self.resilience_metrics.update({
            'total_downtime': total_downtime,
            'degraded_performance_time': degraded_time,
            'availability_percentage': ((total_test_time - total_downtime) / total_test_time) * 100
        })

    async def run_fault_tolerance_test(self):
        """Exécute le test complet de tolérance aux pannes."""
        self.logger.info(f"🚀 DÉMARRAGE - {self.test_name}")
        self.logger.info(f"📄 {self.description}")
        self.logger.info(f"⏱️ Durée: {self.test_duration}s avec {len(self.fault_scenarios)} pannes simulées")
        self.logger.info(f"🔄 Charge de base: {self.baseline_rps} req/s")
        print("-" * 90)

        start_time = time.time()
        request_count = 0

        # Index du prochain scénario de panne
        next_fault_idx = 0
        active_faults = {}  # {agent_name: end_time}

        # Boucle principale du test
        while (time.time() - start_time) < self.test_duration:
            current_time = time.time()
            elapsed = current_time - start_time

            # === GESTION DES PANNES ===

            # Vérifier si on doit déclencher une nouvelle panne
            if (next_fault_idx < len(self.fault_scenarios)):
                scenario = self.fault_scenarios[next_fault_idx]
                if elapsed >= scenario['start_time']:
                    self.simulate_agent_failure(scenario['target_agent'], scenario['duration'])
                    active_faults[scenario['target_agent']] = current_time + scenario['duration']
                    self._backup_queues()  # Sauvegarder avant la panne
                    next_fault_idx += 1

            # Vérifier les récupérations automatiques
            for agent_name, end_time in list(active_faults.items()):
                if current_time >= end_time:
                    self.simulate_agent_recovery(agent_name)
                    del active_faults[agent_name]

            # === GÉNÉRATION DE REQUÊTES ===

            # Générer requêtes selon le rythme de base
            if random.random() < (self.baseline_rps / 100):  # Probabilité basée sur RPS
                request = self.generate_request_during_fault()
                success = self.handle_request_arrival_with_faults(request)
                if success:
                    request_count += 1

            # === TRAITEMENT DES REQUÊTES ===

            self.process_requests_with_faults()

            # === COLLECTE DE MÉTRIQUES ===

            current_metrics = {
                'timestamp': current_time,
                'elapsed': elapsed,
                'vip_queue_size': len(self.vip_queue),
                'standard_queue_size': len(self.standard_queue),
                'processing_count': len(self.processing_requests),
                'completed_count': len(self.completed_requests),
                'failed_count': len(self.failed_requests),
                'lost_count': len(self.lost_requests),
                'agents_running': sum(1 for status in self.agents_status.values()
                                      if status == AgentStatus.RUNNING),
                'system_degraded': any(status != AgentStatus.RUNNING
                                       for status in self.agents_status.values())
            }

            # Stocker métriques
            for key, value in current_metrics.items():
                self.performance_data[key].append(value)

            # Attendre avant prochaine itération
            await asyncio.sleep(0.1)

        # === PHASE DE RÉCUPÉRATION FINALE ===

        self.logger.info("🔄 Phase de récupération finale...")
        recovery_start = time.time()

        # S'assurer que tous les agents sont récupérés
        for agent_name, status in list(self.agents_status.items()):
            if status != AgentStatus.RUNNING:
                self.simulate_agent_recovery(agent_name)

        # Finir le traitement des requêtes restantes
        while (self.vip_queue or self.standard_queue or self.processing_requests):
            self.process_requests_with_faults()
            await asyncio.sleep(0.1)

            # Timeout de sécurité
            if time.time() - recovery_start > 60:  # 1 minute max
                break

        # === CALCUL DES MÉTRIQUES FINALES ===

        total_duration = time.time() - start_time
        self.calculate_availability_metrics()

        # Sauvegarder et afficher résultats
        results = await self.save_fault_tolerance_results(
            request_count, total_duration
        )

        self.display_fault_tolerance_results(results)

        return results

    async def save_fault_tolerance_results(self, total_requests, duration):
        """Sauvegarde les résultats du test de tolérance aux pannes."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        total_completed = len(self.completed_requests)
        total_failed = len(self.failed_requests)
        total_lost = len(self.lost_requests)
        total_processed = total_completed + total_failed

        results = {
            "test_type": "fault_tolerance",
            "scenario_name": self.test_name,
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "test_duration": self.test_duration,
                "baseline_rps": self.baseline_rps,
                "fault_scenarios_count": len(self.fault_scenarios),
                "aging_factor": self.aging_factor,
                "degraded_aging_factor": self.degraded_aging_factor
            },
            "summary": {
                "total_requests_generated": total_requests,
                "completed_requests": total_completed,
                "failed_requests": total_failed,
                "lost_requests": total_lost,
                "success_rate": total_completed / max(total_requests, 1),
                "effective_success_rate": total_completed / max(total_processed, 1),
                "test_duration": duration
            },
            "resilience_metrics": self.resilience_metrics,
            "fault_scenarios": self.fault_scenarios,
            "fault_events": self.fault_events,
            "recovery_times": self.resilience_metrics['recovery_times'],
            "availability": {
                "uptime_percentage": self.resilience_metrics['availability_percentage'],
                "total_downtime": self.resilience_metrics['total_downtime'],
                "degraded_time": self.resilience_metrics['degraded_performance_time']
            },
            "performance_timeseries": {
                k: v[-50:] for k, v in self.performance_data.items()  # Derniers 50 points
            }
        }

        # Sauvegarder
        logs_dir = Path("logs/scenarios")
        logs_dir.mkdir(parents=True, exist_ok=True)

        filename = f"scenario_5_fault_tolerance_{timestamp}.json"
        filepath = logs_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"📄 Rapport tolérance aux pannes: {filepath}")

        return results

    def display_fault_tolerance_results(self, results):
        """Affiche les résultats du test de tolérance aux pannes."""
        print("📊 RÉSULTATS DU TEST DE TOLÉRANCE AUX PANNES:")
        print(f"✅ Taux de réussite: {results['summary']['success_rate'] * 100:.1f}%")
        print(f"🎯 Taux de réussite effectif: {results['summary']['effective_success_rate'] * 100:.1f}%")
        print(f"📈 Disponibilité: {self.resilience_metrics['availability_percentage']:.1f}%")
        print(f"⏱️  Temps d'arrêt total: {self.resilience_metrics['total_downtime']:.1f}s")
        print(f"📤 Requêtes perdues: {self.resilience_metrics['requests_lost']}")
        print(f"🔄 Récupérations réussies: {len(self.resilience_metrics['recovery_times'])}")

        if self.resilience_metrics['recovery_times']:
            avg_recovery = sum(self.resilience_metrics['recovery_times'].values()) / len(
                self.resilience_metrics['recovery_times'])
            print(f"⚡ Temps de récupération moyen: {avg_recovery:.2f}s")

        print("\n🛡️ DÉTAILS DES PANNES SIMULÉES:")
        for i, scenario in enumerate(self.fault_scenarios):
            print(f"  {i + 1}. {scenario['name']}: {scenario['duration']}s")
            agent_recovery = self.resilience_metrics['recovery_times'].get(scenario['target_agent'], 'N/A')
            print(
                f"     Récupération: {agent_recovery}s" if agent_recovery != 'N/A' else "     Récupération: Non mesurée")

        print("\n" + "=" * 90)
        print("RÉSUMÉ SCÉNARIO 5 - TEST DE TOLÉRANCE AUX PANNES")
        print("=" * 90)
        print(f"🔢 Requêtes générées: {results['summary']['total_requests_generated']}")
        print(f"✅ Requêtes complétées: {results['summary']['completed_requests']}")
        print(f"❌ Requêtes échouées: {results['summary']['failed_requests']}")
        print(f"📤 Requêtes perdues: {results['summary']['lost_requests']}")
        print(f"📈 Taux de réussite: {results['summary']['success_rate'] * 100:.1f}%")
        print(f"🛡️  Disponibilité: {self.resilience_metrics['availability_percentage']:.1f}%")
        print(f"🔄 Pannes simulées: {len(self.fault_scenarios)}")
        print(f"⚡ Récupérations: {len(self.resilience_metrics['recovery_times'])}")
        print(f"⏰ Durée totale: {results['summary']['test_duration']:.1f}s")

        # Évaluation de la résilience
        if self.resilience_metrics['availability_percentage'] >= 95:
            print("🏆 RÉSILIENCE: Excellente (≥95%)")
        elif self.resilience_metrics['availability_percentage'] >= 90:
            print("🥈 RÉSILIENCE: Bonne (≥90%)")
        elif self.resilience_metrics['availability_percentage'] >= 80:
            print("🥉 RÉSILIENCE: Acceptable (≥80%)")
        else:
            print("⚠️  RÉSILIENCE: Insuffisante (<80%)")


async def main():
    """Fonction principale pour exécuter le test de tolérance aux pannes."""
    scenario = FaultToleranceTestScenario()

    print("🛡️" * 20)
    print("🚀 SCÉNARIO 5: Test de Tolérance aux Pannes")
    print(f"📄 Description: {scenario.description}")
    print(f"⏱️ Durée: {scenario.test_duration}s")
    print(f"🔥 Pannes simulées: {len(scenario.fault_scenarios)}")
    print(f"🔄 Charge de base: {scenario.baseline_rps} req/s")
    print("-" * 90)

    try:
        results = await scenario.run_fault_tolerance_test()
        return results
    except Exception as e:
        scenario.logger.error(f"Erreur fatale: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    results = asyncio.run(main())
    if results:
        print("🎯 Test de tolérance aux pannes terminé avec succès!")
    else:
        print("❌ Échec du test de tolérance aux pannes")