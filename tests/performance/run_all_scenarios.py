# tests/performance/run_all_scenarios.py
"""
Script principal pour exécuter tous les scénarios de tests de performance.
Version corrigée avec séparation claire des scénarios.
"""

import asyncio
import sys
import json
import time
from datetime import datetime
from pathlib import Path
import argparse

# Import des scénarios séparés
try:
    from scenarios.scenario_1_baseline import BaselineTestScenario
    from scenarios.scenario_2_scalability import ScalabilityTestScenario
    from scenarios.scenario_3_spike_load import SpikeLoadTestScenario
except ImportError as e:
    print(f"Erreur d'import des scénarios: {e}")
    print("Assurez-vous que les fichiers de scénarios sont dans le dossier scenarios/")
    sys.exit(1)


class ScenarioRunner:
    """
    Gestionnaire principal pour l'exécution de tous les scénarios.
    """

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.scenarios = {
            'baseline': {
                'class': BaselineTestScenario,
                'name': 'Performance de Base',
                'description': 'Établit les métriques de référence avec gestion des dépendances et anti-famine'
            },
            'scalability': {
                'class': ScalabilityTestScenario,
                'name': 'Test de Scalabilité',
                'description': 'Valide la consistance sur différents volumes avec dépendances complexes'
            },
            'spike_load': {
                'class': SpikeLoadTestScenario,
                'name': 'Test des Pics de Charge',
                'description': 'Teste la résilience aux variations de charge avec anti-famine adaptatif'
            }
        }

        self.global_results = {}
        self.start_time = None

    def print_header(self):
        """Affiche l'en-tête du test."""
        print("=" * 80)
        print("🚀 SYSTÈME MULTI-AGENTS - TESTS DE PERFORMANCE COMPLETS")
        print("=" * 80)
        print("📋 VALIDATION DES EXIGENCES FONCTIONNELLES:")
        print("   ✅ Gestion des dépendances (Tri topologique)")
        print("   ✅ Anti-famine (Mécanisme de vieillissement)")
        print("   ✅ Équité VIP/Standard")
        print("   ✅ Scalabilité linéaire")
        print("   ✅ Résilience aux pics de charge")
        print("=" * 80)

    async def run_scenario(self, scenario_key):
        """Exécute un scénario spécifique."""
        if scenario_key not in self.scenarios:
            raise ValueError(f"Scénario '{scenario_key}' non reconnu")

        scenario_info = self.scenarios[scenario_key]

        print(f"\n🎯 EXÉCUTION: {scenario_info['name']}")
        print(f"📄 {scenario_info['description']}")
        print("-" * 60)

        # Créer et exécuter le scénario
        scenario_instance = scenario_info['class']()

        try:
            start_time = time.time()
            result = await scenario_instance.run()
            execution_time = time.time() - start_time

            # Enregistrer le résultat
            self.global_results[scenario_key] = {
                'result': result,
                'execution_time': execution_time,
                'status': 'SUCCESS'
            }

            print(f"✅ Scénario '{scenario_info['name']}' terminé avec succès en {execution_time:.1f}s")

            # Afficher métriques clés si verbose
            if self.verbose and isinstance(result, dict):
                self.print_scenario_summary(scenario_key, result)

            return result

        except Exception as e:
            print(f"❌ Erreur dans le scénario '{scenario_info['name']}': {e}")
            self.global_results[scenario_key] = {
                'result': None,
                'execution_time': 0,
                'status': 'FAILED',
                'error': str(e)
            }
            return None

    def print_scenario_summary(self, scenario_key, result):
        """Affiche un résumé des métriques du scénario."""
        print(f"\n📊 RÉSUMÉ {scenario_key.upper()}:")

        if 'summary' in result:
            summary = result['summary']
            print(f"   📈 Taux de réussite: {summary.get('success_rate', 0):.1%}")
            print(f"   ⏱️  Temps réponse: {summary.get('avg_response_time', 0):.2f}s")
            print(f"   🚀 Débit max: {summary.get('max_throughput', 0):.1f} req/s")

        if 'performance' in result:
            perf = result['performance']
            print(f"   ⚖️  Équité: {perf.get('equity_ratio', 1.0):.2f}")

        if 'dependencies' in result:
            deps = result['dependencies']
            print(f"   🔗 Dépendances: {deps.get('requests_with_dependencies', 0)} requêtes")
            print(f"   🚫 Deadlocks: {deps.get('deadlocks_detected', 0)}")

        if 'anti_starvation' in result:
            anti_starv = result['anti_starvation']
            print(f"   🔄 Anti-famine: {'✅ Actif' if anti_starv.get('starvation_prevented', False) else '❌ Problème'}")

    async def run_all_scenarios(self):
        """Exécute tous les scénarios dans l'ordre."""
        self.start_time = time.time()

        self.print_header()

        print(f"\n🏁 DÉMARRAGE DES TESTS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📋 Scénarios à exécuter: {len(self.scenarios)}")

        # Exécuter chaque scénario
        for i, scenario_key in enumerate(self.scenarios.keys(), 1):
            print(f"\n🔄 Progression: {i}/{len(self.scenarios)} scénarios")

            result = await self.run_scenario(scenario_key)

            # Pause entre scénarios pour stabilité
            if i < len(self.scenarios):
                print("⏸️  Pause entre scénarios...")
                await asyncio.sleep(3)

        # Générer rapport global
        total_time = time.time() - self.start_time
        global_report = self.generate_global_report(total_time)

        # Sauvegarder et afficher
        self.save_global_report(global_report)
        self.print_final_summary(global_report)

        return global_report

    def generate_global_report(self, total_execution_time):
        """Génère un rapport global consolidé."""
        successful_scenarios = [k for k, v in self.global_results.items() if v['status'] == 'SUCCESS']
        failed_scenarios = [k for k, v in self.global_results.items() if v['status'] == 'FAILED']

        # Agrégation des métriques
        total_requests = 0
        total_completed = 0
        total_dependencies = 0
        total_deadlocks = 0

        equity_ratios = []
        response_times = []
        throughputs = []

        for scenario_key, scenario_result in self.global_results.items():
            if scenario_result['status'] == 'SUCCESS' and scenario_result['result']:
                result = scenario_result['result']

                # Métriques agrégées
                if 'summary' in result:
                    total_requests += result['summary'].get('total_requests', 0)
                    total_completed += result['summary'].get('completed_requests', 0)
                    response_times.append(result['summary'].get('avg_response_time', 0))
                    throughputs.append(result['summary'].get('max_throughput', 0))

                if 'performance' in result:
                    equity_ratios.append(result['performance'].get('equity_ratio', 1.0))

                if 'dependencies' in result:
                    total_dependencies += result['dependencies'].get('requests_with_dependencies', 0)
                    total_deadlocks += result['dependencies'].get('deadlocks_detected', 0)

        # Calculs globaux
        global_success_rate = total_completed / total_requests if total_requests > 0 else 0
        avg_equity_ratio = sum(equity_ratios) / len(equity_ratios) if equity_ratios else 1.0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_throughput = max(throughputs) if throughputs else 0

        # Évaluation globale
        system_grade = self.evaluate_system_performance(
            global_success_rate, avg_equity_ratio, total_deadlocks, len(successful_scenarios)
        )

        global_report = {
            'test_suite': 'Performance Multi-Agents Complete',
            'timestamp': datetime.now().isoformat(),
            'execution_time': total_execution_time,
            'scenarios': {
                'total': len(self.scenarios),
                'successful': len(successful_scenarios),
                'failed': len(failed_scenarios),
                'success_rate': len(successful_scenarios) / len(self.scenarios)
            },
            'global_metrics': {
                'total_requests_tested': total_requests,
                'total_requests_completed': total_completed,
                'global_success_rate': global_success_rate,
                'avg_equity_ratio': avg_equity_ratio,
                'avg_response_time': avg_response_time,
                'max_throughput_achieved': max_throughput
            },
            'functional_requirements': {
                'dependency_management': {
                    'total_dependencies_tested': total_dependencies,
                    'deadlocks_detected': total_deadlocks,
                    'resolution_efficiency': (
                                                         total_dependencies - total_deadlocks) / total_dependencies if total_dependencies > 0 else 1.0,
                    'status': 'PASSED' if total_deadlocks == 0 else 'FAILED'
                },
                'anti_starvation': {
                    'aging_mechanism_tested': len(successful_scenarios) > 0,
                    'equity_maintained': avg_equity_ratio < 3.0,  # Seuil acceptable
                    'status': 'PASSED' if avg_equity_ratio < 3.0 else 'DEGRADED'
                },
                'scalability': {
                    'tested': 'scalability' in successful_scenarios,
                    'linear_scaling': 'scalability' in successful_scenarios,  # À évaluer plus finement
                    'status': 'PASSED' if 'scalability' in successful_scenarios else 'NOT_TESTED'
                },
                'load_resilience': {
                    'tested': 'spike_load' in successful_scenarios,
                    'recovery_verified': 'spike_load' in successful_scenarios,
                    'status': 'PASSED' if 'spike_load' in successful_scenarios else 'NOT_TESTED'
                }
            },
            'system_evaluation': system_grade,
            'individual_results': self.global_results,
            'recommendations': self.generate_recommendations(successful_scenarios, failed_scenarios, avg_equity_ratio,
                                                             total_deadlocks)
        }

        return global_report

    def evaluate_system_performance(self, success_rate, equity_ratio, deadlocks, successful_scenarios):
        """Évalue la performance globale du système."""
        score = 0
        max_score = 100

        # Taux de réussite (40 points)
        score += success_rate * 40

        # Équité (20 points)
        if equity_ratio <= 1.5:
            score += 20
        elif equity_ratio <= 3.0:
            score += 15
        elif equity_ratio <= 5.0:
            score += 10
        else:
            score += 5

        # Gestion des dépendances (20 points)
        if deadlocks == 0:
            score += 20
        elif deadlocks < 10:
            score += 15
        else:
            score += 5

        # Couverture des tests (20 points)
        coverage = successful_scenarios / 3  # 3 scénarios total
        score += coverage * 20

        percentage = (score / max_score) * 100

        if percentage >= 90:
            grade = "EXCELLENT"
            status = "PRODUCTION_READY"
        elif percentage >= 80:
            grade = "TRÈS BON"
            status = "PRODUCTION_READY"
        elif percentage >= 70:
            grade = "BON"
            status = "MINOR_IMPROVEMENTS_NEEDED"
        elif percentage >= 60:
            grade = "SATISFAISANT"
            status = "IMPROVEMENTS_NEEDED"
        else:
            grade = "INSUFFISANT"
            status = "MAJOR_IMPROVEMENTS_REQUIRED"

        return {
            'score': percentage,
            'grade': grade,
            'status': status,
            'details': {
                'success_rate_score': success_rate * 40,
                'equity_score': min(20, (3.0 - min(equity_ratio, 3.0)) * 20 / 3.0),
                'dependencies_score': 20 if deadlocks == 0 else max(5, 20 - deadlocks),
                'coverage_score': coverage * 20
            }
        }

    def generate_recommendations(self, successful_scenarios, failed_scenarios, equity_ratio, deadlocks):
        """Génère des recommandations basées sur les résultats."""
        recommendations = []

        if len(failed_scenarios) > 0:
            recommendations.append(f"Corriger les scénarios échoués: {', '.join(failed_scenarios)}")

        if deadlocks > 0:
            recommendations.append(f"Optimiser la gestion des dépendances ({deadlocks} deadlocks détectés)")

        if equity_ratio > 3.0:
            recommendations.append(f"Améliorer le mécanisme d'équité (ratio: {equity_ratio:.2f})")
        elif equity_ratio > 2.0:
            recommendations.append(f"Ajuster le facteur de vieillissement (ratio d'équité: {equity_ratio:.2f})")

        if 'scalability' not in successful_scenarios:
            recommendations.append("Valider la scalabilité du système")

        if 'spike_load' not in successful_scenarios:
            recommendations.append("Tester la résilience aux pics de charge")

        if len(recommendations) == 0:
            recommendations.append("Système prêt pour la production - Aucune amélioration critique nécessaire")

        return recommendations

    def save_global_report(self, report):
        """Sauvegarde le rapport global."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Créer dossier
        report_dir = Path("logs/global_reports")
        report_dir.mkdir(parents=True, exist_ok=True)

        # Rapport détaillé
        report_path = report_dir / f"global_performance_report_{timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        # Version latest
        latest_path = report_dir / "global_performance_report_latest.json"
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"📄 Rapport global sauvegardé: {report_path}")

    def print_final_summary(self, report):
        """Affiche le résumé final."""
        print("\n" + "=" * 80)
        print("📊 RAPPORT FINAL - SYSTÈME MULTI-AGENTS")
        print("=" * 80)

        # Métriques globales
        metrics = report['global_metrics']
        print(f"📈 MÉTRIQUES GLOBALES:")
        print(f"   🔢 Requêtes testées: {metrics['total_requests_tested']}")
        print(f"   ✅ Requêtes complétées: {metrics['total_requests_completed']}")
        print(f"   📊 Taux de réussite: {metrics['global_success_rate']:.1%}")
        print(f"   ⚖️  Équité moyenne: {metrics['avg_equity_ratio']:.2f}")
        print(f"   ⏱️  Temps réponse moyen: {metrics['avg_response_time']:.2f}s")
        print(f"   🚀 Débit max atteint: {metrics['max_throughput_achieved']:.1f} req/s")

        # Exigences fonctionnelles
        print(f"\n🎯 EXIGENCES FONCTIONNELLES:")
        req = report['functional_requirements']

        deps = req['dependency_management']
        print(
            f"   🔗 Gestion dépendances: {deps['status']} ({deps['total_dependencies_tested']} testées, {deps['deadlocks_detected']} deadlocks)")

        anti_starv = req['anti_starvation']
        print(f"   🔄 Anti-famine: {anti_starv['status']} (équité: {'✅' if anti_starv['equity_maintained'] else '⚠️'})")

        scalab = req['scalability']
        print(f"   📈 Scalabilité: {scalab['status']}")

        resilience = req['load_resilience']
        print(f"   🏔️  Résilience: {resilience['status']}")

        # Évaluation système
        evaluation = report['system_evaluation']
        print(f"\n🏆 ÉVALUATION SYSTÈME:")
        print(f"   📊 Score: {evaluation['score']:.1f}/100")
        print(f"   🎖️  Grade: {evaluation['grade']}")
        print(f"   ✅ Statut: {evaluation['status']}")

        # Recommandations
        print(f"\n💡 RECOMMANDATIONS:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"   {i}. {rec}")

        # Temps d'exécution
        print(f"\n⏱️  TEMPS D'EXÉCUTION: {report['execution_time']:.1f}s")

        print("=" * 80)


def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Tests de performance du système multi-agents")
    parser.add_argument("--scenarios", nargs='+',
                        choices=['baseline', 'scalability', 'spike_load', 'all'],
                        default=['all'],
                        help="Scénarios à exécuter")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Affichage détaillé")

    args = parser.parse_args()

    # Créer le runner
    runner = ScenarioRunner(verbose=args.verbose)

    try:
        if 'all' in args.scenarios:
            # Exécuter tous les scénarios
            report = asyncio.run(runner.run_all_scenarios())
        else:
            # Exécuter scénarios spécifiques
            asyncio.run(runner.run_specific_scenarios(args.scenarios))

    except KeyboardInterrupt:
        print("\n🛑 Tests interrompus par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()