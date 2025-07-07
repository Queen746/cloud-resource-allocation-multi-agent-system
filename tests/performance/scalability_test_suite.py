# tests/performance/scalability_test_suite.py

import logging
import time
import asyncio
from datetime import datetime
import json
import os
from typing import Dict, List, Tuple

from tests.performance.direct_test_adapter import DirectTestAdapter
from system_launcher import SystemLauncher
from models.client import Client
from models.enums import ClientType
from config.production_config import calculate_optimal_queue_sizes, validate_scalability_performance


class ScalabilityTestSuite:
    """
    Suite de tests pour valider que les performances restent cohérentes
    indépendamment du nombre de requêtes (100 vs 1000 vs 10000).
    """

    def __init__(self, system_launcher):
        self.system_launcher = system_launcher
        self.logger = logging.getLogger("ScalabilityTestSuite")

        # Configurations de test par niveau de charge
        self.load_configs = {
            100: {
                "max_concurrent": 100,
                "vip_queue_size": 500,
                "standard_queue_size": 2000,
                "cpu_pool": 50.0,
                "memory_pool": 50.0,
                "test_duration": 120,  # 2 minutes
                "rps": 5
            },
            500: {
                "max_concurrent": 500,
                "vip_queue_size": 1500,
                "standard_queue_size": 6000,
                "cpu_pool": 150.0,
                "memory_pool": 150.0,
                "test_duration": 180,  # 3 minutes
                "rps": 8
            },
            1000: {
                "max_concurrent": 1000,
                "vip_queue_size": 2000,
                "standard_queue_size": 8000,
                "cpu_pool": 200.0,
                "memory_pool": 200.0,
                "test_duration": 300,  # 5 minutes
                "rps": 10
            },
            2500: {
                "max_concurrent": 2500,
                "vip_queue_size": 3500,
                "standard_queue_size": 12000,
                "cpu_pool": 350.0,
                "memory_pool": 350.0,
                "test_duration": 420,  # 7 minutes
                "rps": 12
            },
            5000: {
                "max_concurrent": 5000,
                "vip_queue_size": 5000,
                "standard_queue_size": 20000,
                "cpu_pool": 500.0,
                "memory_pool": 500.0,
                "test_duration": 600,  # 10 minutes
                "rps": 15
            }
        }

    def run_complete_scalability_test(self) -> Dict:
        """
        Exécute la suite complète de tests de scalabilité.

        Returns:
            Dict: Résultats complets avec analyse comparative
        """
        self.logger.info("=== DÉBUT DE LA SUITE DE TESTS DE SCALABILITÉ ===")

        results = {}
        performance_consistency = {}

        # Exécuter les tests pour chaque niveau de charge
        for load_level in [100, 500, 1000, 2500, 5000]:
            self.logger.info(f"--- Test de scalabilité pour {load_level} requêtes ---")

            try:
                # Configurer le système pour ce niveau de charge
                self._configure_system_for_load(load_level)

                # Exécuter le test
                test_result = self._run_load_level_test(load_level)
                results[load_level] = test_result

                self.logger.info(f"Test {load_level} requêtes terminé - "
                                 f"Succès: {test_result['success_rate']:.2%}, "
                                 f"Temps moyen: {test_result['avg_response_time']:.2f}s")

                # Pause entre les tests
                time.sleep(30)

            except Exception as e:
                self.logger.error(f"Erreur lors du test {load_level}: {e}")
                results[load_level] = {"error": str(e)}

        # Analyser la cohérence des performances
        performance_consistency = self._analyze_performance_consistency(results)

        # Générer le rapport final
        report = self._generate_scalability_report(results, performance_consistency)

        self.logger.info("=== FIN DE LA SUITE DE TESTS DE SCALABILITÉ ===")

        return {
            "results": results,
            "performance_consistency": performance_consistency,
            "report": report
        }

    def _configure_system_for_load(self, load_level: int):
        """Configure le système pour le niveau de charge spécifié."""
        config = self.load_configs[load_level]

        # Mise à jour de la configuration du système
        if hasattr(self.system_launcher, 'config'):
            self.system_launcher.config.update({
                'vip_queue_size': config['vip_queue_size'],
                'standard_queue_size': config['standard_queue_size'],
                'cpu_pool_size': config['cpu_pool'],
                'memory_pool_size': config['memory_pool']
            })

        self.logger.info(f"Système configuré pour {load_level} requêtes: "
                         f"VIP={config['vip_queue_size']}, "
                         f"STD={config['standard_queue_size']}")

    def _run_load_level_test(self, load_level: int) -> Dict:
        """Exécute un test pour un niveau de charge spécifique."""
        config = self.load_configs[load_level]

        # Créer l'adaptateur de test
        test_adapter = DirectTestAdapter(self.system_launcher)

        # Statistiques du test
        start_time = time.time()
        requests_sent = 0
        requests_completed = 0
        requests_failed = 0
        response_times = []
        vip_response_times = []
        std_response_times = []

        # Générer et envoyer les requêtes
        target_requests = load_level
        rps = config['rps']
        request_interval = 1.0 / rps

        self.logger.info(f"Génération de {target_requests} requêtes à {rps} req/s")

        # Phase 1: Génération des requêtes
        for i in range(target_requests):
            # Créer un client (20% VIP, 80% Standard)
            is_vip = (i % 5 == 0)  # Chaque 5ème requête est VIP
            client_id = f"client-{load_level}-{i}"
            client_type = ClientType.VIP if is_vip else ClientType.STANDARD
            client = Client(client_id=client_id, client_type=client_type)

            # Paramètres de la requête
            request_id = f"req-{load_level}-{i}"
            cpu_required = random.uniform(1.0, 3.0)
            memory_required = random.uniform(1.0, 4.0)
            estimated_duration = random.uniform(5.0, 30.0)

            # Dépendances occasionnelles (20% des requêtes)
            dependencies = []
            if i > 0 and random.random() < 0.2:
                num_deps = random.randint(1, min(3, i))
                dependencies = [f"req-{load_level}-{j}" for j in
                                random.sample(range(i), num_deps)]

            # Envoyer la requête
            request_start = time.time()
            success = test_adapter.submit_request(
                client, request_id, cpu_required, memory_required,
                estimated_duration, dependencies
            )

            if success:
                requests_sent += 1

                # Stocker le temps de début pour calculer le temps de réponse
                if not hasattr(test_adapter, 'request_start_times'):
                    test_adapter.request_start_times = {}
                test_adapter.request_start_times[request_id] = request_start

            # Respecter l'intervalle entre requêtes
            time.sleep(request_interval)

        # Phase 2: Attendre la complétion des requêtes
        self.logger.info(f"Attente de la complétion des {requests_sent} requêtes...")

        max_wait_time = config['test_duration']
        wait_start = time.time()

        while time.time() - wait_start < max_wait_time:
            # Vérifier les requêtes complétées
            completed = test_adapter.get_completed_requests()
            for req_id in completed:
                if req_id.startswith(f"req-{load_level}-") and req_id not in [r['id'] for r in response_times]:
                    # Calculer le temps de réponse
                    if hasattr(test_adapter, 'request_start_times') and req_id in test_adapter.request_start_times:
                        response_time = time.time() - test_adapter.request_start_times[req_id]

                        # Déterminer le type de client
                        req_index = int(req_id.split('-')[-1])
                        is_vip = (req_index % 5 == 0)

                        response_times.append({
                            'id': req_id,
                            'time': response_time,
                            'is_vip': is_vip
                        })

                        if is_vip:
                            vip_response_times.append(response_time)
                        else:
                            std_response_times.append(response_time)

                        requests_completed += 1

            # Vérifier les requêtes échouées
            failed = test_adapter.get_failed_requests()
            for req_id in failed:
                if req_id.startswith(f"req-{load_level}-"):
                    requests_failed += 1

            # Pause courte avant la prochaine vérification
            time.sleep(1)

        # Phase 3: Forcer la completion des requêtes restantes
        test_adapter.wait_for_completion(timeout=60)

        # Calcul des métriques finales
        total_time = time.time() - start_time

        # Calculer les statistiques
        all_response_times = [r['time'] for r in response_times]
        avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0

        vip_avg_time = sum(vip_response_times) / len(vip_response_times) if vip_response_times else 0
        std_avg_time = sum(std_response_times) / len(std_response_times) if std_response_times else 0

        equity_ratio = std_avg_time / max(vip_avg_time, 0.1) if vip_avg_time > 0 else 1.0
        success_rate = requests_completed / max(requests_sent, 1)

        # Calculs de percentiles
        sorted_times = sorted(all_response_times)
        percentiles = {}
        if sorted_times:
            percentiles = {
                'p50': sorted_times[int(len(sorted_times) * 0.5)],
                'p90': sorted_times[int(len(sorted_times) * 0.9)],
                'p95': sorted_times[int(len(sorted_times) * 0.95)],
                'p99': sorted_times[int(len(sorted_times) * 0.99)]
            }

        # Nettoyer l'adaptateur
        test_adapter.cleanup()

        return {
            'load_level': load_level,
            'requests_sent': requests_sent,
            'requests_completed': requests_completed,
            'requests_failed': requests_failed,
            'success_rate': success_rate,
            'total_time': total_time,
            'avg_response_time': avg_response_time,
            'vip_avg_response_time': vip_avg_time,
            'std_avg_response_time': std_avg_time,
            'equity_ratio': equity_ratio,
            'percentiles': percentiles,
            'throughput_rps': requests_completed / total_time,
            'configuration': config
        }

    def _analyze_performance_consistency(self, results: Dict) -> Dict:
        """Analyse la cohérence des performances entre différents niveaux de charge."""
        consistency_analysis = {
            'response_time_consistency': {},
            'success_rate_consistency': {},
            'equity_consistency': {},
            'throughput_scalability': {},
            'overall_grade': 'A'
        }

        # Utiliser le niveau 100 comme référence
        baseline = results.get(100, {})
        if 'error' in baseline:
            return {'error': 'Baseline test failed'}

        baseline_response_time = baseline.get('avg_response_time', 0)
        baseline_success_rate = baseline.get('success_rate', 0)
        baseline_equity = baseline.get('equity_ratio', 1.0)

        for load_level, result in results.items():
            if load_level == 100 or 'error' in result:
                continue

            # Analyse du temps de réponse
            response_time_ratio = result['avg_response_time'] / max(baseline_response_time, 0.1)
            consistency_analysis['response_time_consistency'][load_level] = {
                'ratio': response_time_ratio,
                'degradation_percent': (response_time_ratio - 1) * 100,
                'acceptable': response_time_ratio <= 1.5  # Max 50% de dégradation
            }

            # Analyse du taux de succès
            success_rate_diff = abs(result['success_rate'] - baseline_success_rate)
            consistency_analysis['success_rate_consistency'][load_level] = {
                'difference': success_rate_diff,
                'difference_percent': success_rate_diff * 100,
                'acceptable': success_rate_diff <= 0.1  # Max 10% de différence
            }

            # Analyse de l'équité
            equity_diff = abs(result['equity_ratio'] - baseline_equity)
            consistency_analysis['equity_consistency'][load_level] = {
                'difference': equity_diff,
                'baseline_equity': baseline_equity,
                'current_equity': result['equity_ratio'],
                'acceptable': equity_diff <= 0.5  # Max 0.5 de différence
            }

            # Analyse de la scalabilité du throughput
            expected_throughput = baseline.get('throughput_rps', 0) * (load_level / 100)
            actual_throughput = result.get('throughput_rps', 0)
            throughput_efficiency = actual_throughput / max(expected_throughput, 0.1)

            consistency_analysis['throughput_scalability'][load_level] = {
                'expected_rps': expected_throughput,
                'actual_rps': actual_throughput,
                'efficiency': throughput_efficiency,
                'acceptable': throughput_efficiency >= 0.8  # Min 80% d'efficacité
            }

        # Calcul de la note globale
        all_acceptable = True
        for category in ['response_time_consistency', 'success_rate_consistency',
                         'equity_consistency', 'throughput_scalability']:
            for load_level, metrics in consistency_analysis[category].items():
                if not metrics.get('acceptable', True):
                    all_acceptable = False
                    break

        if all_acceptable:
            consistency_analysis['overall_grade'] = 'A'
        else:
            # Calculer une note basée sur les métriques
            acceptable_count = sum(
                1 for category in consistency_analysis.values()
                if isinstance(category, dict)
                for metrics in category.values()
                if isinstance(metrics, dict) and metrics.get('acceptable', False)
            )
            total_count = sum(
                len(category) for category in consistency_analysis.values()
                if isinstance(category, dict)
            )

            if total_count > 0:
                score = acceptable_count / total_count
                if score >= 0.9:
                    consistency_analysis['overall_grade'] = 'A'
                elif score >= 0.8:
                    consistency_analysis['overall_grade'] = 'B'
                elif score >= 0.7:
                    consistency_analysis['overall_grade'] = 'C'
                else:
                    consistency_analysis['overall_grade'] = 'D'

        return consistency_analysis

    def _generate_scalability_report(self, results: Dict, consistency: Dict) -> str:
        """Génère un rapport détaillé des tests de scalabilité."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""
=== RAPPORT DE TESTS DE SCALABILITÉ ===
Date: {timestamp}
Objectif: Valider que les performances restent cohérentes de 100 à 5000 requêtes

=== RÉSULTATS PAR NIVEAU DE CHARGE ===
"""

        for load_level in sorted(results.keys()):
            result = results[load_level]
            if 'error' in result:
                report += f"\n--- {load_level} requêtes ---\n"
                report += f"ERREUR: {result['error']}\n"
                continue

            report += f"""
--- {load_level} requêtes ---
Durée du test: {result['total_time']:.1f}s
Requêtes envoyées: {result['requests_sent']}
Requêtes complétées: {result['requests_completed']} ({result['success_rate']:.1%})
Requêtes échouées: {result['requests_failed']}

Temps de réponse moyen: {result['avg_response_time']:.2f}s
Temps moyen VIP: {result['vip_avg_response_time']:.2f}s
Temps moyen Standard: {result['std_avg_response_time']:.2f}s
Ratio d'équité: {result['equity_ratio']:.2f}

Percentiles de temps de réponse:
  - 50%: {result['percentiles'].get('p50', 0):.2f}s
  - 90%: {result['percentiles'].get('p90', 0):.2f}s
  - 95%: {result['percentiles'].get('p95', 0):.2f}s
  - 99%: {result['percentiles'].get('p99', 0):.2f}s

Throughput: {result['throughput_rps']:.2f} req/s
"""

        report += f"""
=== ANALYSE DE COHÉRENCE DES PERFORMANCES ===
Note globale: {consistency.get('overall_grade', 'N/A')}

"""

        # Analyse détaillée de la cohérence
        if 'response_time_consistency' in consistency:
            report += "--- Cohérence des temps de réponse ---\n"
            for load_level, metrics in consistency['response_time_consistency'].items():
                status = "✓ ACCEPTABLE" if metrics['acceptable'] else "✗ DÉGRADÉ"
                report += f"{load_level} req: {metrics['ratio']:.2f}x (+{metrics['degradation_percent']:.1f}%) {status}\n"

        if 'success_rate_consistency' in consistency:
            report += "\n--- Cohérence des taux de succès ---\n"
            for load_level, metrics in consistency['success_rate_consistency'].items():
                status = "✓ STABLE" if metrics['acceptable'] else "✗ INSTABLE"
                report += f"{load_level} req: ±{metrics['difference_percent']:.1f}% {status}\n"

        if 'throughput_scalability' in consistency:
            report += "\n--- Scalabilité du throughput ---\n"
            for load_level, metrics in consistency['throughput_scalability'].items():
                status = "✓ EFFICACE" if metrics['acceptable'] else "✗ INEFFICACE"
                report += f"{load_level} req: {metrics['efficiency']:.1%} efficacité {status}\n"

        # Recommandations
        report += """
=== RECOMMANDATIONS ===

Basé sur les résultats de scalabilité:
"""

        grade = consistency.get('overall_grade', 'D')
        if grade == 'A':
            report += """
✓ EXCELLENT: Le système maintient des performances cohérentes
✓ Prêt pour la production avec confiance
✓ Scalabilité linéaire validée jusqu'à 5000 requêtes simultanées
"""
        elif grade == 'B':
            report += """
✓ BON: Le système montre une bonne scalabilité avec légères dégradations
⚠ Surveiller les performances en production
⚠ Optimisations mineures recommandées
"""
        elif grade == 'C':
            report += """
⚠ ACCEPTABLE: Dégradations notables mais le système reste fonctionnel
⚠ Optimisations nécessaires avant production intensive
⚠ Tests supplémentaires recommandés
"""
        else:
            report += """
✗ CRITIQUE: Dégradations importantes détectées
✗ Optimisations urgentes requises
✗ Ne pas déployer en production sans corrections
"""

        # Limites recommandées
        successful_loads = [k for k, v in results.items()
                            if 'error' not in v and v.get('success_rate', 0) >= 0.9]
        if successful_loads:
            max_load = max(successful_loads)
            recommended_load = max_load * 0.8  # 80% de la charge max pour sécurité

            report += f"""
=== LIMITES OPÉRATIONNELLES RECOMMANDÉES ===
Charge maximale testée avec succès: {max_load} requêtes
Charge recommandée pour production: {int(recommended_load)} requêtes
Marge de sécurité: 20%
"""

        return report

    def save_results(self, results: Dict, filename: str = None):
        """Sauvegarde les résultats dans un fichier JSON."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scalability_test_results_{timestamp}.json"

        os.makedirs("logs/scalability", exist_ok=True)
        filepath = os.path.join("logs/scalability", filename)

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        self.logger.info(f"Résultats sauvegardés dans: {filepath}")
        return filepath


# Fonction utilitaire pour lancer les tests de scalabilité
def run_scalability_tests():
    """Lance une suite complète de tests de scalabilité."""

    # Configurer les logs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/scalability_tests.log")
        ]
    )

    logger = logging.getLogger("ScalabilityRunner")
    logger.info("Initialisation des tests de scalabilité...")

    try:
        # Créer le système
        system_launcher = SystemLauncher(simulation_mode=False)

        # Créer la suite de tests
        test_suite = ScalabilityTestSuite(system_launcher)

        # Exécuter les tests
        results = test_suite.run_complete_scalability_test()

        # Sauvegarder les résultats
        report_file = test_suite.save_results(results)

        # Afficher le rapport
        print("\n" + "=" * 80)
        print(results['report'])
        print("=" * 80)
        print(f"\nRapport complet sauvegardé: {report_file}")

        # Retourner les résultats pour utilisation externe
        return results

    except Exception as e:
        logger.error(f"Erreur lors des tests de scalabilité: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import random  # Import manquant

    # Lancer les tests de scalabilité
    results = run_scalability_tests()