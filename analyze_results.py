#!/usr/bin/env python3
"""
Analyseur de données de performance - Lecture et visualisation des résultats des tests
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
from datetime import datetime
import argparse


class PerformanceAnalyzer:
    """Analyseur des résultats de tests de performance."""

    def __init__(self):
        self.reports_dir = Path("logs")
        self.scenarios_dir = self.reports_dir / "scenarios"
        self.global_dir = self.reports_dir / "global_reports"

        # Configuration des graphiques (compatible toutes versions)
        try:
            plt.style.use('seaborn-v0_8-darkgrid')
        except OSError:
            try:
                plt.style.use('seaborn-darkgrid')
            except OSError:
                plt.style.use('ggplot')  # Style par défaut si seaborn indisponible

        try:
            sns.set_palette("husl")
        except:
            pass  # Continuer sans palette spécifique si erreur

    def load_latest_reports(self):
        """Charge les derniers rapports disponibles."""
        reports = {}

        # Charger rapports de scénarios
        if self.scenarios_dir.exists():
            scenario_files = list(self.scenarios_dir.glob("scenario_*.json"))
            for file in scenario_files:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        scenario_name = data.get('scenario_name', file.stem)

                        # Garder le plus récent par type
                        if 'baseline' in file.name.lower():
                            reports['baseline'] = data
                        elif 'scalability' in file.name.lower():
                            reports['scalability'] = data
                        elif 'spike' in file.name.lower():
                            reports['spike_load'] = data

                except Exception as e:
                    print(f"⚠️ Erreur lecture {file}: {e}")

        # Charger rapport global
        if self.global_dir.exists():
            global_files = list(self.global_dir.glob("global_performance_*.json"))
            if global_files:
                latest_global = max(global_files, key=lambda f: f.stat().st_mtime)
                try:
                    with open(latest_global, 'r', encoding='utf-8') as f:
                        reports['global'] = json.load(f)
                except Exception as e:
                    print(f"⚠️ Erreur lecture rapport global: {e}")

        return reports

    def create_summary_table(self, reports):
        """Crée un tableau de résumé des performances."""
        summary_data = []

        for test_name, report in reports.items():
            if test_name == 'global':
                continue

            if 'summary' in report:
                summary = report['summary']
                performance = report.get('performance', {})

                summary_data.append({
                    'Test': test_name.replace('_', ' ').title(),
                    'Requêtes': f"{summary.get('completed_requests', 0)}/{summary.get('total_requests', 0)}",
                    'Réussite': f"{summary.get('success_rate', 0):.1%}",
                    'Temps Réponse': f"{summary.get('avg_response_time', 0):.2f}s",
                    'Débit Max': f"{performance.get('max_throughput', 0):.1f} req/s",
                    'Équité': f"{performance.get('equity_ratio', 0):.2f}"
                })

        return pd.DataFrame(summary_data)

    def plot_performance_comparison(self, reports):
        """Graphique de comparaison des performances."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('🚀 Analyse Comparative des Performances', fontsize=16, fontweight='bold')

        # Données pour graphiques
        test_names = []
        success_rates = []
        response_times = []
        throughputs = []
        equity_ratios = []

        for test_name, report in reports.items():
            if test_name == 'global' or 'summary' not in report:
                continue

            test_names.append(test_name.replace('_', '\n').title())
            success_rates.append(report['summary'].get('success_rate', 0) * 100)
            response_times.append(report['summary'].get('avg_response_time', 0))
            throughputs.append(report.get('performance', {}).get('max_throughput', 0))
            equity_ratios.append(report.get('performance', {}).get('equity_ratio', 0))

        # 1. Taux de réussite
        axes[0, 0].bar(test_names, success_rates, color=['#2ecc71', '#e74c3c', '#3498db'])
        axes[0, 0].set_title('📈 Taux de Réussite (%)')
        axes[0, 0].set_ylabel('Pourcentage')
        axes[0, 0].set_ylim(95, 101)
        for i, v in enumerate(success_rates):
            axes[0, 0].text(i, v + 0.1, f'{v:.1f}%', ha='center', fontweight='bold')

        # 2. Temps de réponse
        axes[0, 1].bar(test_names, response_times, color=['#f39c12', '#9b59b6', '#1abc9c'])
        axes[0, 1].set_title('⏱️ Temps de Réponse Moyen (s)')
        axes[0, 1].set_ylabel('Secondes')
        for i, v in enumerate(response_times):
            axes[0, 1].text(i, v + 0.02, f'{v:.2f}s', ha='center', fontweight='bold')

        # 3. Débit maximum
        axes[1, 0].bar(test_names, throughputs, color=['#e67e22', '#8e44ad', '#16a085'])
        axes[1, 0].set_title('🚀 Débit Maximum (req/s)')
        axes[1, 0].set_ylabel('Requêtes/seconde')
        for i, v in enumerate(throughputs):
            axes[1, 0].text(i, v + 0.2, f'{v:.1f}', ha='center', fontweight='bold')

        # 4. Équité
        axes[1, 1].bar(test_names, equity_ratios, color=['#27ae60', '#c0392b', '#2980b9'])
        axes[1, 1].set_title('⚖️ Ratio d\'Équité')
        axes[1, 1].set_ylabel('Ratio')
        axes[1, 1].axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='Équité parfaite')
        for i, v in enumerate(equity_ratios):
            axes[1, 1].text(i, v + 0.02, f'{v:.2f}', ha='center', fontweight='bold')
        axes[1, 1].legend()

        plt.tight_layout()
        return fig

    def plot_time_series_baseline(self, baseline_report):
        """Graphique temporel détaillé du test baseline."""
        if 'time_series' not in baseline_report:
            return None

        ts_data = baseline_report['time_series']
        timestamps = ts_data.get('timestamps', [])

        if not timestamps:
            return None

        # Convertir timestamps en durée relative
        start_time = timestamps[0] if timestamps else 0
        relative_times = [(t - start_time) for t in timestamps]

        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('📊 Test Baseline - Évolution Temporelle', fontsize=16, fontweight='bold')

        # 1. Files d'attente
        axes[0, 0].plot(relative_times, ts_data.get('vip_queue_sizes', []),
                        label='VIP', color='red', linewidth=2)
        axes[0, 0].plot(relative_times, ts_data.get('standard_queue_sizes', []),
                        label='Standard', color='blue', linewidth=2)
        axes[0, 0].set_title('📋 Tailles des Files d\'Attente')
        axes[0, 0].set_ylabel('Nombre de requêtes')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # 2. Débit
        throughput = ts_data.get('throughput_per_second', [])
        if throughput:
            axes[0, 1].plot(relative_times[:len(throughput)], throughput,
                            color='green', linewidth=2)
            axes[0, 1].axhline(y=np.mean(throughput), color='orange',
                               linestyle='--', label=f'Moyenne: {np.mean(throughput):.1f}')
        axes[0, 1].set_title('🚀 Débit (req/s)')
        axes[0, 1].set_ylabel('Requêtes/seconde')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # 3. Utilisation ressources
        cpu_usage = ts_data.get('cpu_usage', [])
        memory_usage = ts_data.get('memory_usage', [])
        if cpu_usage:
            axes[1, 0].plot(relative_times[:len(cpu_usage)], cpu_usage,
                            label='CPU', color='purple', linewidth=2)
        if memory_usage:
            axes[1, 0].plot(relative_times[:len(memory_usage)], memory_usage,
                            label='Mémoire', color='brown', linewidth=2)
        axes[1, 0].set_title('💻 Utilisation des Ressources (%)')
        axes[1, 0].set_ylabel('Pourcentage')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        # 4. Équité
        equity_ratios = ts_data.get('equity_ratios', [])
        if equity_ratios:
            axes[1, 1].plot(relative_times[:len(equity_ratios)], equity_ratios,
                            color='teal', linewidth=2)
            axes[1, 1].axhline(y=1.0, color='red', linestyle='--', alpha=0.7,
                               label='Équité parfaite')
            axes[1, 1].axhline(y=np.mean(equity_ratios), color='orange',
                               linestyle='--', label=f'Moyenne: {np.mean(equity_ratios):.2f}')
        axes[1, 1].set_title('⚖️ Évolution de l\'Équité')
        axes[1, 1].set_ylabel('Ratio d\'équité')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)

        for ax in axes.flat:
            ax.set_xlabel('Temps (secondes)')

        plt.tight_layout()
        return fig

    def plot_scalability_analysis(self, scalability_report):
        """Analyse de scalabilité si disponible."""
        if 'results' not in scalability_report:
            print("⚠️ Données de scalabilité non trouvées")
            return None

        results = scalability_report['results']
        volumes = [r['volume'] for r in results]
        success_rates = [r['success_rate'] * 100 for r in results]
        throughputs = [r['throughput'] for r in results]
        response_times = [r['avg_response_time'] for r in results]

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        fig.suptitle('📈 Analyse de Scalabilité', fontsize=16, fontweight='bold')

        # 1. Taux de réussite vs Volume
        axes[0].plot(volumes, success_rates, 'o-', color='green', linewidth=3, markersize=8)
        axes[0].set_title('✅ Taux de Réussite vs Volume')
        axes[0].set_xlabel('Volume de requêtes')
        axes[0].set_ylabel('Taux de réussite (%)')
        axes[0].grid(True, alpha=0.3)
        axes[0].set_ylim(95, 101)

        # 2. Débit vs Volume
        axes[1].plot(volumes, throughputs, 's-', color='blue', linewidth=3, markersize=8)
        axes[1].set_title('🚀 Débit vs Volume')
        axes[1].set_xlabel('Volume de requêtes')
        axes[1].set_ylabel('Débit (req/s)')
        axes[1].grid(True, alpha=0.3)

        # 3. Temps de réponse vs Volume
        axes[2].plot(volumes, response_times, '^-', color='red', linewidth=3, markersize=8)
        axes[2].set_title('⏱️ Temps de Réponse vs Volume')
        axes[2].set_xlabel('Volume de requêtes')
        axes[2].set_ylabel('Temps de réponse (s)')
        axes[2].grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def plot_spike_analysis(self, spike_report):
        """Analyse des pics de charge."""
        if 'time_series' not in spike_report:
            print("⚠️ Données temporelles de pics non trouvées")
            return None

        ts_data = spike_report['time_series']
        timestamps = ts_data.get('timestamps', [])

        if not timestamps:
            return None

        start_time = timestamps[0]
        relative_times = [(t - start_time) for t in timestamps]

        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('⚡ Test de Pics de Charge - Analyse Temporelle', fontsize=16, fontweight='bold')

        # 1. RPS et phases
        current_rps = ts_data.get('current_rps', [])
        phases = ts_data.get('phase_indicators', [])

        if current_rps:
            axes[0, 0].plot(relative_times[:len(current_rps)], current_rps,
                            linewidth=3, color='orange')

            # Colorer les phases
            if phases:
                phase_times = relative_times[:len(phases)]
                for i, phase in enumerate(phases):
                    color = {'warmup': 'lightblue', 'spike': 'lightcoral', 'recovery': 'lightgreen'}.get(phase, 'white')
                    if i < len(phase_times) - 1:
                        axes[0, 0].axvspan(phase_times[i], phase_times[i + 1], alpha=0.3, color=color)

        axes[0, 0].set_title('📊 Charge (RPS) et Phases')
        axes[0, 0].set_ylabel('Requêtes/seconde')
        axes[0, 0].grid(True, alpha=0.3)

        # 2. Files d'attente pendant le pic
        vip_queues = ts_data.get('vip_queue_sizes', [])
        std_queues = ts_data.get('standard_queue_sizes', [])

        if vip_queues:
            axes[0, 1].plot(relative_times[:len(vip_queues)], vip_queues,
                            label='VIP', color='red', linewidth=2)
        if std_queues:
            axes[0, 1].plot(relative_times[:len(std_queues)], std_queues,
                            label='Standard', color='blue', linewidth=2)

        axes[0, 1].set_title('📋 Files d\'Attente pendant le Pic')
        axes[0, 1].set_ylabel('Taille des files')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # 3. Débit réalisé
        throughput = ts_data.get('throughput_per_second', [])
        if throughput:
            axes[1, 0].plot(relative_times[:len(throughput)], throughput,
                            color='green', linewidth=2)
            max_throughput = max(throughput)
            axes[1, 0].axhline(y=max_throughput, color='red', linestyle='--',
                               label=f'Max: {max_throughput:.1f} req/s')

        axes[1, 0].set_title('🚀 Débit Réalisé')
        axes[1, 0].set_ylabel('Requêtes/seconde')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        # 4. Équité sous stress
        equity_ratios = ts_data.get('equity_ratios', [])
        if equity_ratios:
            axes[1, 1].plot(relative_times[:len(equity_ratios)], equity_ratios,
                            color='purple', linewidth=2)
            axes[1, 1].axhline(y=1.0, color='red', linestyle='--', alpha=0.7,
                               label='Équité parfaite')
            mean_equity = np.mean(equity_ratios)
            axes[1, 1].axhline(y=mean_equity, color='orange', linestyle='--',
                               label=f'Moyenne: {mean_equity:.2f}')

        axes[1, 1].set_title('⚖️ Équité sous Stress')
        axes[1, 1].set_ylabel('Ratio d\'équité')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)

        for ax in axes.flat:
            ax.set_xlabel('Temps (secondes)')

        plt.tight_layout()
        return fig

    def generate_performance_report(self, reports):
        """Génère un rapport de performance complet."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("analysis_output")
        output_dir.mkdir(exist_ok=True)

        print("🚀 GÉNÉRATION DU RAPPORT D'ANALYSE")
        print("=" * 50)

        # 1. Tableau de résumé
        summary_table = self.create_summary_table(reports)
        print("\n📊 RÉSUMÉ DES PERFORMANCES:")
        print(summary_table.to_string(index=False))

        # 2. Graphique de comparaison
        comparison_fig = self.plot_performance_comparison(reports)
        if comparison_fig:
            comparison_path = output_dir / f"performance_comparison_{timestamp}.png"
            comparison_fig.savefig(comparison_path, dpi=300, bbox_inches='tight')
            print(f"\n📈 Graphique de comparaison: {comparison_path}")
            plt.show()

        # 3. Analyse baseline détaillée
        if 'baseline' in reports:
            baseline_fig = self.plot_time_series_baseline(reports['baseline'])
            if baseline_fig:
                baseline_path = output_dir / f"baseline_analysis_{timestamp}.png"
                baseline_fig.savefig(baseline_path, dpi=300, bbox_inches='tight')
                print(f"📊 Analyse baseline: {baseline_path}")
                plt.show()

        # 4. Analyse de scalabilité
        if 'scalability' in reports:
            scalability_fig = self.plot_scalability_analysis(reports['scalability'])
            if scalability_fig:
                scalability_path = output_dir / f"scalability_analysis_{timestamp}.png"
                scalability_fig.savefig(scalability_path, dpi=300, bbox_inches='tight')
                print(f"📈 Analyse scalabilité: {scalability_path}")
                plt.show()

        # 5. Analyse des pics
        if 'spike_load' in reports:
            spike_fig = self.plot_spike_analysis(reports['spike_load'])
            if spike_fig:
                spike_path = output_dir / f"spike_analysis_{timestamp}.png"
                spike_fig.savefig(spike_path, dpi=300, bbox_inches='tight')
                print(f"⚡ Analyse pics: {spike_path}")
                plt.show()

        # 6. Métriques globales
        if 'global' in reports:
            global_data = reports['global']
            print(f"\n🏆 ÉVALUATION GLOBALE:")
            if 'evaluation' in global_data:
                eval_data = global_data['evaluation']
                print(f"Score: {eval_data.get('score', 'N/A')}/100")
                print(f"Grade: {eval_data.get('grade', 'N/A')}")
                print(f"Statut: {eval_data.get('status', 'N/A')}")

        # Sauvegarder tableau CSV
        csv_path = output_dir / f"performance_summary_{timestamp}.csv"
        summary_table.to_csv(csv_path, index=False)
        print(f"📄 Tableau CSV: {csv_path}")

        print(f"\n✅ Analyse complète sauvegardée dans: {output_dir}")
        return output_dir


def main():
    """Fonction principale d'analyse."""
    parser = argparse.ArgumentParser(description="Analyseur de performances multi-agents")
    parser.add_argument('--show-plots', action='store_true',
                        help='Afficher les graphiques à l\'écran')
    parser.add_argument('--export-only', action='store_true',
                        help='Exporter seulement sans afficher')

    args = parser.parse_args()

    analyzer = PerformanceAnalyzer()

    print("🔍 CHARGEMENT DES DONNÉES...")
    reports = analyzer.load_latest_reports()

    if not reports:
        print("❌ Aucun rapport trouvé dans logs/")
        print("💡 Exécutez d'abord vos tests de performance")
        return

    print(f"✅ {len(reports)} rapports chargés: {list(reports.keys())}")

    # Générer analyse complète
    output_dir = analyzer.generate_performance_report(reports)

    if not args.export_only:
        input("\n📊 Appuyez sur Entrée pour fermer les graphiques...")


if __name__ == "__main__":
    main()