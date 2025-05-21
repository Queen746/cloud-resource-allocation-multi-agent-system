# tests/performance/run_performance_tests.py

import os
import logging
import argparse
import time
from datetime import datetime

from system_launcher import SystemLauncher
from tests.performance.constant_load_test import ConstantLoadTest
from tests.performance.increasing_load_test import IncreasingLoadTest
from tests.performance.burst_load_test import BurstLoadTest
from tests.performance.dependency_test import DependencyTest
from tests.performance.test_adapter import TestAdapter
# Important: Utilisez le bon import pour SystemLauncher
from system_launcher_test import SystemLauncher as TestSystemLauncher

# Logger global pour ce module
logger = logging.getLogger("PerformanceTests")


def setup_logging():
    """Configure les logs pour les tests de performance"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = "logs/performance"

    # Créer le répertoire de logs s'il n'existe pas
    os.makedirs(log_dir, exist_ok=True)

    # Configuration du logger principal
    log_file = f"{log_dir}/performance_tests_{timestamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger("PerformanceTests"), log_file


def run_tests(args):
    """Exécute les tests de performance sélectionnés"""
    global logger
    logger_instance, log_file = setup_logging()
    logger = logger_instance  # Mettre à jour le logger global
    results = {}

    # Afficher la configuration
    logger.info("=== Configuration des tests de performance ===")
    logger.info(
        f"Tests activés: {', '.join(test for test in ['constant', 'increasing', 'burst', 'dependency'] if getattr(args, test))}")
    logger.info(f"Modes de test:")
    logger.info(f"  - Constant load: {args.constant_rps} req/s pendant {args.constant_duration}s")
    logger.info(
        f"  - Increasing load: {args.inc_initial_rps} à {args.inc_max_rps} req/s par paliers de {args.inc_step}s")
    logger.info(
        f"  - Burst load: base {args.burst_base_rps} req/s, pic à {args.burst_peak_rps} req/s pendant {args.burst_duration}s")
    logger.info(f"  - Dependency: {args.dep_num_graphs} graphes de dépendances")
    logger.info(f"Ratio de clients VIP: {args.vip_ratio * 100:.0f}%")
    logger.info(f"Ratio de dépendances: {args.dependency_ratio * 100:.0f}%")

    # Initialiser le système
    system_launcher = None
    try:
        logger.info("Initialisation du système...")
        # Utiliser TestSystemLauncher pour les tests
        system_launcher = TestSystemLauncher()
        system_launcher.start()  # Maintenant une méthode synchrone

        # Attendre que le système soit prêt
        time.sleep(10)
        logger.info("Système prêt pour les tests")

        # Exécuter les tests sélectionnés
        if args.constant:
            logger.info("=== Début du test de charge constante ===")
            test = ConstantLoadTest(
                system_launcher=system_launcher,  # Utilisez le SystemLauncher directement
                requests_per_second=args.constant_rps,
                duration_seconds=args.constant_duration,
                vip_ratio=args.vip_ratio,
                dependency_ratio=args.dependency_ratio
            )
            report_file = test.run()
            results["constant_load"] = report_file
            logger.info(f"Test de charge constante terminé. Rapport: {report_file}")
            # Pause entre les tests
            time.sleep(30)

        if args.increasing:
            logger.info("=== Début du test de charge croissante ===")
            test = IncreasingLoadTest(
                system_launcher=system_launcher,
                initial_rps=args.inc_initial_rps,
                max_rps=args.inc_max_rps,
                increment=args.inc_step_rps,
                increment_interval=args.inc_step,
                vip_ratio=args.vip_ratio,
                dependency_ratio=args.dependency_ratio
            )
            report_file = test.run()
            results["increasing_load"] = report_file
            logger.info(f"Test de charge croissante terminé. Rapport: {report_file}")
            # Pause plus longue après un test intensif
            time.sleep(60)

        if args.burst:
            logger.info("=== Début du test de pic de charge ===")
            test = BurstLoadTest(
                system_launcher=system_launcher,
                base_rps=args.burst_base_rps,
                burst_rps=args.burst_peak_rps,
                burst_duration=args.burst_duration,
                recovery_duration=args.burst_recovery,
                vip_ratio=args.vip_ratio,
                dependency_ratio=args.dependency_ratio
            )
            report_file = test.run()
            results["burst_load"] = report_file
            logger.info(f"Test de pic de charge terminé. Rapport: {report_file}")
            # Pause plus longue après un test intensif
            time.sleep(60)

        if args.dependency:
            logger.info("=== Début du test de dépendances complexes ===")
            test = DependencyTest(
                system_launcher=system_launcher,
                num_graphs=args.dep_num_graphs,
                base_rps=args.dep_base_rps,
                vip_ratio=args.vip_ratio
            )
            report_file = test.run()
            results["dependency"] = report_file
            logger.info(f"Test de dépendances complexes terminé. Rapport: {report_file}")

        # Générer un rapport de synthèse
        summary_file = generate_summary_report(results, args)
        logger.info(f"Tous les tests terminés. Rapport de synthèse: {summary_file}")

    except Exception as e:
        logger.error(f"Erreur lors de l'exécution des tests: {e}", exc_info=True)
    finally:
        # Arrêt propre du système
        logger.info("Arrêt du système...")
        try:
            if system_launcher:
                system_launcher.shutdown()
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du système: {e}")

    # Attente supplémentaire et vérification finale
    logger.info("Attente supplémentaire pour permettre aux demandes de se terminer...")
    time.sleep(60)  # Attendre une minute supplémentaire

    if system_launcher and hasattr(system_launcher, 'manually_mark_all_active_as_completed'):
        if hasattr(system_launcher, 'active_requests'):
            active_count = len(system_launcher.active_requests)
            if active_count > 0:
                logger.warning(f"Il reste {active_count} demandes actives, marquage manuel...")
                system_launcher.manually_mark_all_active_as_completed()

    logger.info("Vérification finale des demandes...")
    if system_launcher and hasattr(system_launcher, 'active_requests') and system_launcher.active_requests:
        active_count = len(system_launcher.active_requests)
        completed_count = len(system_launcher.completed_requests) if hasattr(system_launcher,
                                                                             'completed_requests') else 0

        logger.warning(f"État final: {active_count} actives, {completed_count} complétées")

        # Marquer toutes les demandes actives restantes comme complétées
        for request_id in list(system_launcher.active_requests):
            logger.info(f"Marquage final de {request_id} comme complétée")
            system_launcher.mark_request_completed(request_id)

    return results, log_file


def generate_summary_report(results, args):
    """Génère un rapport de synthèse des résultats de tous les tests"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = f"logs/performance/summary_{timestamp}.log"

    with open(summary_file, "w") as report:
        report.write("=== Rapport de synthèse des tests de performance ===\n")
        report.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Configuration des tests
        report.write("--- Configuration ---\n")
        report.write(f"Tests exécutés: {', '.join(results.keys())}\n")
        report.write(f"Ratio VIP: {args.vip_ratio * 100:.0f}%\n")
        report.write(f"Ratio dépendances: {args.dependency_ratio * 100:.0f}%\n\n")

        # Résumé des résultats
        report.write("--- Résumé des résultats ---\n")
        for test_name, report_file in results.items():
            if not report_file:
                report.write(f"{test_name}: Aucun rapport généré\n")
                continue

            report.write(f"{test_name}: {report_file}\n")

            # Extraire et ajouter les principales conclusions de chaque rapport
            try:
                if not os.path.exists(report_file):
                    report.write(f"  Fichier de rapport introuvable: {report_file}\n")
                    continue

                with open(report_file, "r") as f:
                    content = f.read()

                    # Extraire des sections clés selon le type de test
                    if test_name == "constant_load":
                        # Extraire le taux de réussite et les temps de réponse
                        import re
                        success_match = re.search(r"Demandes complétées: (\d+) \(([\d\.]+)%\)", content)
                        response_match = re.search(r"Temps de réponse moyen: ([\d\.]+)s", content)
                        equity_match = re.search(r"Ratio d'équité \(std/vip\): ([\d\.]+)", content)

                        if success_match:
                            report.write(f"  - Taux de réussite: {success_match.group(2)}%\n")
                        if response_match:
                            report.write(f"  - Temps de réponse moyen: {response_match.group(1)}s\n")
                        if equity_match:
                            report.write(f"  - Ratio d'équité (std/vip): {equity_match.group(1)}\n")

                    elif test_name == "increasing_load":
                        # Extraire le point de rupture
                        import re
                        rupture_match = re.search(r"Charge maximale stable: (\d+) req/s", content)

                        if rupture_match:
                            report.write(f"  - Charge maximale stable: {rupture_match.group(1)} req/s\n")

                    elif test_name == "burst_load":
                        # Extraire l'impact du pic
                        import re
                        impact_match = re.search(r"Impact global du pic de charge: (\w+)", content)
                        factor_match = re.search(r"Facteur d'augmentation pendant le pic: ([\d\.]+)x", content)

                        if impact_match:
                            report.write(f"  - Impact du pic: {impact_match.group(1)}\n")
                        if factor_match:
                            report.write(f"  - Facteur d'augmentation: {factor_match.group(1)}x\n")

                    elif test_name == "dependency":
                        # Extraire l'efficacité de gestion des dépendances
                        import re
                        ratio_match = re.search(r"Ratio \(graphe/indép\.\): ([\d\.]+)x", content)

                        if ratio_match:
                            report.write(f"  - Ratio temps graphe/indépendant: {ratio_match.group(1)}x\n")
            except Exception as e:
                report.write(f"  Erreur lors de l'extraction des résultats: {str(e)}\n")

            report.write("\n")

        # Recommandations générales
        report.write("--- Recommandations générales ---\n")
        report.write("Basé sur l'ensemble des tests, voici les recommandations principales:\n")

        # À compléter avec les recommandations spécifiques après analyse des résultats
        report.write("1. Optimiser l'algorithme d'ordonnancement pour maintenir le ratio d'équité\n")
        report.write("2. Surveiller attentivement les performances lors des pics d'activité\n")
        report.write("3. Envisager d'augmenter les ressources système si la charge prévue dépasse 15 req/s\n")
        report.write("4. Améliorer la gestion des dépendances profondes pour réduire les temps de réponse\n")

    return summary_file


def parse_args():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(description="Tests de performance du système multi-agents")

    # Sélection des tests
    parser.add_argument("--constant", action="store_true", help="Exécuter le test de charge constante")
    parser.add_argument("--increasing", action="store_true", help="Exécuter le test de charge croissante")
    parser.add_argument("--burst", action="store_true", help="Exécuter le test de pic de charge")
    parser.add_argument("--dependency", action="store_true", help="Exécuter le test de dépendances complexes")
    parser.add_argument("--all", action="store_true", help="Exécuter tous les tests")

    # Paramètres généraux
    parser.add_argument("--vip-ratio", type=float, default=0.2, help="Proportion de clients VIP (0.0-1.0)")
    parser.add_argument("--dependency-ratio", type=float, default=0.3,
                        help="Proportion de demandes avec dépendances (0.0-1.0)")

    # Paramètres du test de charge constante
    parser.add_argument("--constant-rps", type=int, default=5, help="Demandes par seconde pour le test constant")
    parser.add_argument("--constant-duration", type=int, default=300, help="Durée du test constant (secondes)")

    # Paramètres du test de charge croissante
    parser.add_argument("--inc-initial-rps", type=int, default=1, help="RPS initial pour le test croissant")
    parser.add_argument("--inc-max-rps", type=int, default=20, help="RPS maximum pour le test croissant")
    parser.add_argument("--inc-step-rps", type=int, default=1, help="Incrément de RPS entre les paliers")
    parser.add_argument("--inc-step", type=int, default=30, help="Durée de chaque palier (secondes)")

    # Paramètres du test de pic de charge
    parser.add_argument("--burst-base-rps", type=int, default=2, help="RPS de base pour le test de pic")
    parser.add_argument("--burst-peak-rps", type=int, default=20, help="RPS durant le pic")
    parser.add_argument("--burst-duration", type=int, default=30, help="Durée du pic (secondes)")
    parser.add_argument("--burst-recovery", type=int, default=120, help="Durée de récupération (secondes)")

    # Paramètres du test de dépendances
    parser.add_argument("--dep-num-graphs", type=int, default=10, help="Nombre de graphes à tester")
    parser.add_argument("--dep-base-rps", type=int, default=3, help="RPS de fond pour le test de dépendances")

    args = parser.parse_args()

    # Si --all est spécifié, activer tous les tests
    if args.all:
        args.constant = args.increasing = args.burst = args.dependency = True

    # Si aucun test n'est spécifié, activer le test de charge constante par défaut
    if not (args.constant or args.increasing or args.burst or args.dependency):
        args.constant = True

    return args


if __name__ == "__main__":
    args = parse_args()
    results, log_file = run_tests(args)
    print(f"Tests terminés. Consultez le fichier de log principal: {log_file}")