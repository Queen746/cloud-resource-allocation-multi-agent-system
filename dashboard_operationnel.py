#!/usr/bin/env python3
"""
Dashboard Modulaire - Version corrigée avec espacements optimaux
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime
import matplotlib.gridspec as gridspec


class ModularDashboard:
    """Dashboard avec graphiques séparés et espacements optimisés."""

    def __init__(self):
        self.reports_dir = Path("logs")
        self.scenarios_dir = self.reports_dir / "scenarios"

        # Style professionnel avec espacements optimisés
        plt.rcParams['figure.figsize'] = (18, 12)  # Plus large
        plt.rcParams['font.size'] = 11
        plt.rcParams['axes.titlesize'] = 13
        plt.rcParams['axes.labelsize'] = 11
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10
        plt.rcParams['legend.fontsize'] = 10

        # Espacements améliorés
        plt.rcParams['figure.subplot.top'] = 0.92
        plt.rcParams['figure.subplot.bottom'] = 0.12
        plt.rcParams['figure.subplot.left'] = 0.08
        plt.rcParams['figure.subplot.right'] = 0.95
        plt.rcParams['figure.subplot.hspace'] = 0.35
        plt.rcParams['figure.subplot.wspace'] = 0.25

    def load_reports(self):
        """Charge tous les rapports."""
        reports = {}

        if self.scenarios_dir.exists():
            # Baseline
            baseline_files = list(self.scenarios_dir.glob("*baseline*.json"))
            if baseline_files:
                latest_baseline = max(baseline_files, key=lambda f: f.stat().st_mtime)
                with open(latest_baseline, 'r', encoding='utf-8') as f:
                    reports['baseline'] = json.load(f)

            # Scalability
            scalability_files = list(self.scenarios_dir.glob("*scalability*.json"))
            if scalability_files:
                latest_scalability = max(scalability_files, key=lambda f: f.stat().st_mtime)
                with open(latest_scalability, 'r', encoding='utf-8') as f:
                    reports['scalability'] = json.load(f)

            # Spike
            spike_files = list(self.scenarios_dir.glob("*spike*.json"))
            if spike_files:
                latest_spike = max(spike_files, key=lambda f: f.stat().st_mtime)
                with open(latest_spike, 'r', encoding='utf-8') as f:
                    reports['spike_load'] = json.load(f)

        return reports

    def create_summary_dashboard(self, reports):
        """Dashboard de synthèse avec métriques clés."""
        fig = plt.figure(figsize=(18, 12))

        # Titre principal avec marge
        fig.suptitle('SYNTHESE PERFORMANCE - SYSTEME MULTI-AGENTS',
                     fontsize=16, fontweight='bold', y=0.95)

        # Grille avec espacements contrôlés
        gs = gridspec.GridSpec(2, 2, figure=fig,
                               left=0.08, right=0.95,
                               top=0.88, bottom=0.15,
                               hspace=0.4, wspace=0.25)

        # Créer les sous-graphiques
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, 0])
        ax4 = fig.add_subplot(gs[1, 1])

        # Données pour graphiques
        scenarios = []
        success_rates = []
        throughputs = []
        response_times = []
        equity_ratios = []

        for test_name, report in reports.items():
            if test_name == 'scalability':
                results = report.get('results', [])
                if results:
                    total = sum(r.get('volume', 0) for r in results)
                    completed = sum(int(r.get('volume', 0) * r.get('success_rate', 0)) for r in results)
                    success_rate = (completed / total * 100) if total > 0 else 0
                    throughput = max((r.get('throughput', 0) for r in results), default=0)
                    response_time = sum(r.get('avg_response_time', 0) for r in results) / len(results)
                    equity = 1.0
                else:
                    continue
            else:
                summary = report.get('summary', {})
                performance = report.get('performance', {})
                success_rate = summary.get('success_rate', 0) * 100
                throughput = performance.get('max_throughput', 0)
                response_time = summary.get('avg_response_time', 0)
                equity = performance.get('equity_ratio', 0)

            scenarios.append(test_name.replace('_', ' ').title())
            success_rates.append(success_rate)
            throughputs.append(throughput)
            response_times.append(response_time)
            equity_ratios.append(equity)

        colors = ['#2ecc71', '#e74c3c', '#3498db']

        # 1. Taux de réussite
        bars1 = ax1.bar(scenarios, success_rates, color=colors, alpha=0.8, width=0.6)
        ax1.set_title('Taux de Reussite (%)', fontweight='bold', pad=15)
        ax1.set_ylabel('Pourcentage (%)', fontweight='bold')
        ax1.set_ylim(95, 102)
        ax1.grid(True, alpha=0.3, axis='y')

        # Rotation labels et annotations
        ax1.tick_params(axis='x', rotation=25, labelsize=9)
        for bar, val in zip(bars1, success_rates):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                     f'{val:.1f}%', ha='center', fontweight='bold', fontsize=10)

        # 2. Débit maximum
        bars2 = ax2.bar(scenarios, throughputs, color=colors, alpha=0.8, width=0.6)
        ax2.set_title('Debit Maximum (req/s)', fontweight='bold', pad=15)
        ax2.set_ylabel('Requetes/seconde', fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

        ax2.tick_params(axis='x', rotation=25, labelsize=9)
        for bar, val in zip(bars2, throughputs):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                     f'{val:.1f}', ha='center', fontweight='bold', fontsize=10)

        # 3. Temps de réponse
        bars3 = ax3.bar(scenarios, response_times, color=colors, alpha=0.8, width=0.6)
        ax3.set_title('Temps de Reponse Moyen (s)', fontweight='bold', pad=15)
        ax3.set_ylabel('Secondes', fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')

        ax3.tick_params(axis='x', rotation=25, labelsize=9)
        for bar, val in zip(bars3, response_times):
            ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.03,
                     f'{val:.2f}s', ha='center', fontweight='bold', fontsize=10)

        # 4. Équité
        bars4 = ax4.bar(scenarios, equity_ratios, color=colors, alpha=0.8, width=0.6)
        ax4.set_title('Equite VIP/Standard', fontweight='bold', pad=15)
        ax4.set_ylabel('Ratio d\'equite', fontweight='bold')
        ax4.axhline(y=1.0, color='red', linestyle='--', alpha=0.7,
                    linewidth=2, label='Equite parfaite')
        ax4.grid(True, alpha=0.3, axis='y')
        ax4.legend(fontsize=9)

        ax4.tick_params(axis='x', rotation=25, labelsize=9)
        for bar, val in zip(bars4, equity_ratios):
            ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.03,
                     f'{val:.2f}', ha='center', fontweight='bold', fontsize=10)

        return fig

    def create_scalability_dashboard(self, scalability_report):
        """Dashboard dédié à l'analyse de scalabilité."""
        if 'results' not in scalability_report:
            return None

        results = scalability_report['results']
        volumes = [r['volume'] for r in results]
        success_rates = [r['success_rate'] * 100 for r in results]
        throughputs = [r['throughput'] for r in results]
        response_times = [r['avg_response_time'] for r in results]

        fig = plt.figure(figsize=(18, 12))
        fig.suptitle('ANALYSE DETAILLEE DE SCALABILITE',
                     fontsize=16, fontweight='bold', y=0.95)

        # Grille avec espacements optimaux
        gs = gridspec.GridSpec(2, 2, figure=fig,
                               left=0.08, right=0.95,
                               top=0.88, bottom=0.15,
                               hspace=0.4, wspace=0.25)

        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, 0])
        ax4 = fig.add_subplot(gs[1, 1])

        # 1. Taux de réussite vs Volume
        ax1.plot(volumes, success_rates, 'o-', color='green',
                 linewidth=3, markersize=8, markerfacecolor='lightgreen')
        ax1.set_title('Consistance - Taux de Reussite', fontweight='bold', pad=15)
        ax1.set_xlabel('Volume de requetes')
        ax1.set_ylabel('Taux de reussite (%)')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(99, 101)

        # Annotations espacées
        for i, (x, y) in enumerate(zip(volumes, success_rates)):
            if i % 2 == 0:  # Une annotation sur deux pour éviter le chevauchement
                ax1.annotate(f'{y:.1f}%', (x, y), xytext=(5, 15),
                             textcoords='offset points', fontweight='bold', fontsize=9)

        # 2. Débit vs Volume
        ax2.plot(volumes, throughputs, 's-', color='blue',
                 linewidth=3, markersize=8, markerfacecolor='lightblue')
        ax2.set_title('Performance - Debit Maximum', fontweight='bold', pad=15)
        ax2.set_xlabel('Volume de requetes')
        ax2.set_ylabel('Debit (req/s)')
        ax2.grid(True, alpha=0.3)

        # Ligne de tendance
        z = np.polyfit(volumes, throughputs, 1)
        p = np.poly1d(z)
        ax2.plot(volumes, p(volumes), "--", color='red', alpha=0.7,
                 label=f'Tendance: {z[0]:.3f}x + {z[1]:.1f}')
        ax2.legend(fontsize=9)

        # 3. Temps de réponse vs Volume
        ax3.plot(volumes, response_times, '^-', color='red',
                 linewidth=3, markersize=8, markerfacecolor='lightcoral')
        ax3.set_title('Latence - Temps de Reponse', fontweight='bold', pad=15)
        ax3.set_xlabel('Volume de requetes')
        ax3.set_ylabel('Temps de reponse (s)')
        ax3.grid(True, alpha=0.3)

        # 4. Efficacité système
        efficiency = [t / v * 100 for t, v in zip(throughputs, volumes)]
        ax4.plot(volumes, efficiency, 'D-', color='purple',
                 linewidth=3, markersize=8, markerfacecolor='plum')
        ax4.set_title('Efficacite Systeme', fontweight='bold', pad=15)
        ax4.set_xlabel('Volume de requetes')
        ax4.set_ylabel('Efficacite (%)')
        ax4.grid(True, alpha=0.3)

        return fig

    def create_temporal_dashboard(self, baseline_report, spike_report):
        """Dashboard des évolutions temporelles."""
        fig = plt.figure(figsize=(18, 12))
        fig.suptitle('ANALYSE TEMPORELLE - EVOLUTION EN TEMPS REEL',
                     fontsize=16, fontweight='bold', y=0.95)

        gs = gridspec.GridSpec(2, 2, figure=fig,
                               left=0.08, right=0.95,
                               top=0.88, bottom=0.15,
                               hspace=0.4, wspace=0.25)

        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, 0])
        ax4 = fig.add_subplot(gs[1, 1])

        # === BASELINE TEMPORAL DATA ===
        baseline_ts = baseline_report.get('time_series', {})
        baseline_timestamps = baseline_ts.get('timestamps', [])

        if baseline_timestamps:
            start_time = baseline_timestamps[0]
            baseline_times = [(t - start_time) for t in baseline_timestamps]

            # 1. Files d'attente Baseline
            vip_sizes = baseline_ts.get('vip_queue_sizes', [])
            std_sizes = baseline_ts.get('standard_queue_sizes', [])

            if vip_sizes and std_sizes:
                min_len = min(len(baseline_times), len(vip_sizes), len(std_sizes))
                times_sync = baseline_times[:min_len]
                vip_sync = vip_sizes[:min_len]
                std_sync = std_sizes[:min_len]

                ax1.fill_between(times_sync, 0, vip_sync,
                                 color='red', alpha=0.7, label='File VIP')
                ax1.fill_between(times_sync, vip_sync,
                                 [v + s for v, s in zip(vip_sync, std_sync)],
                                 color='blue', alpha=0.7, label='File Standard')

            ax1.set_title('Files d\'Attente - Test Baseline', fontweight='bold', pad=15)
            ax1.set_xlabel('Temps (secondes)')
            ax1.set_ylabel('Requetes en attente')
            ax1.legend(fontsize=9)
            ax1.grid(True, alpha=0.3)

            # 2. Ressources Baseline
            cpu_usage = baseline_ts.get('cpu_usage', [])
            memory_usage = baseline_ts.get('memory_usage', [])

            if cpu_usage:
                min_len_cpu = min(len(baseline_times), len(cpu_usage))
                ax2.plot(baseline_times[:min_len_cpu], cpu_usage[:min_len_cpu],
                         color='purple', linewidth=3, label='CPU')

            if memory_usage:
                min_len_mem = min(len(baseline_times), len(memory_usage))
                ax2.plot(baseline_times[:min_len_mem], memory_usage[:min_len_mem],
                         color='orange', linewidth=3, label='Memoire')

            # Seuils critiques
            ax2.axhline(y=80, color='red', linestyle='--', alpha=0.7,
                        linewidth=2, label='Seuil critique (80%)')
            ax2.axhline(y=60, color='orange', linestyle='--', alpha=0.7,
                        linewidth=2, label='Seuil attention (60%)')

            ax2.set_title('Utilisation Ressources - Baseline', fontweight='bold', pad=15)
            ax2.set_xlabel('Temps (secondes)')
            ax2.set_ylabel('Utilisation (%)')
            ax2.set_ylim(0, 100)
            ax2.legend(fontsize=8, loc='upper left')
            ax2.grid(True, alpha=0.3)

        # === SPIKE LOAD TEMPORAL DATA ===
        spike_ts = spike_report.get('time_series', {})
        spike_timestamps = spike_ts.get('timestamps', [])

        if spike_timestamps:
            start_time = spike_timestamps[0]
            spike_times = [(t - start_time) for t in spike_timestamps]

            # 3. Profil de charge
            current_rps = spike_ts.get('current_rps', [])
            throughput = spike_ts.get('throughput_per_second', [])

            if current_rps and throughput:
                min_len = min(len(spike_times), len(current_rps), len(throughput))
                times_sync = spike_times[:min_len]
                rps_sync = current_rps[:min_len]
                throughput_sync = throughput[:min_len]

                ax3.plot(times_sync, rps_sync, linewidth=4, color='red',
                         label='Charge cible (RPS)', alpha=0.8)
                ax3.plot(times_sync, throughput_sync, linewidth=3, color='blue',
                         label='Debit realise', alpha=0.7)

            ax3.set_title('Profil de Charge - Test de Pics', fontweight='bold', pad=15)
            ax3.set_xlabel('Temps (secondes)')
            ax3.set_ylabel('Requetes/seconde')
            ax3.legend(fontsize=9)
            ax3.grid(True, alpha=0.3)

            # 4. Équité sous stress
            equity_ratios = spike_ts.get('equity_ratios', [])

            if equity_ratios:
                min_len = min(len(spike_times), len(equity_ratios))
                times_sync = spike_times[:min_len]
                equity_sync = equity_ratios[:min_len]

                ax4.plot(times_sync, equity_sync, color='teal', linewidth=3)

                # Zone d'équité acceptable
                ax4.axhspan(0.8, 1.2, alpha=0.2, color='green', label='Zone equitable')
                ax4.axhline(y=1.0, color='red', linestyle='--', alpha=0.7,
                            linewidth=2, label='Equite parfaite')

                # Moyenne mobile
                if len(equity_sync) > 10:
                    window = min(10, len(equity_sync) // 4)
                    moving_avg = np.convolve(equity_sync, np.ones(window) / window, mode='valid')
                    if len(moving_avg) > 0:
                        avg_times = times_sync[window - 1:len(moving_avg) + window - 1]
                        ax4.plot(avg_times, moving_avg,
                                 color='orange', linewidth=4, alpha=0.8, label='Tendance')

            ax4.set_title('Equite sous Stress', fontweight='bold', pad=15)
            ax4.set_xlabel('Temps (secondes)')
            ax4.set_ylabel('Ratio d\'equite')
            ax4.legend(fontsize=8, loc='upper right')
            ax4.grid(True, alpha=0.3)

        return fig

    def create_critical_analysis_dashboard(self, reports):
        """Dashboard d'analyse des situations critiques."""
        fig = plt.figure(figsize=(18, 12))
        fig.suptitle('ANALYSE DES SITUATIONS CRITIQUES',
                     fontsize=16, fontweight='bold', y=0.95)

        gs = gridspec.GridSpec(2, 2, figure=fig,
                               left=0.08, right=0.95,
                               top=0.88, bottom=0.15,
                               hspace=0.4, wspace=0.25)

        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, 0])
        ax4 = fig.add_subplot(gs[1, 1])

        # Analyse des seuils critiques
        scenarios = []
        max_queue_sizes = []
        max_cpu_usage = []
        max_memory_usage = []
        dependencies_count = []
        deadlocks_count = []

        for test_name, report in reports.items():
            scenarios.append(test_name.replace('_', ' ').title())

            if test_name == 'scalability':
                max_queue_sizes.append(0)  # Non disponible
                max_cpu_usage.append(0)
                max_memory_usage.append(0)
                deps = report.get('dependencies', {})
                dependencies_count.append(deps.get('total_requests_with_deps', 0))
                deadlocks_count.append(deps.get('total_deadlocks_detected', 0))
            else:
                queues = report.get('queues', {})
                resources = report.get('resources', {})
                deps = report.get('dependencies', {})

                max_vip = queues.get('max_vip_queue_size', 0)
                max_std = queues.get('max_standard_queue_size', 0)
                max_queue_sizes.append(max_vip + max_std)
                max_cpu_usage.append(resources.get('max_cpu_usage', 0))
                max_memory_usage.append(resources.get('max_memory_usage', 0))
                dependencies_count.append(deps.get('requests_with_dependencies', 0))
                deadlocks_count.append(deps.get('deadlocks_detected', 0))

        # 1. Saturation des files d'attente
        colors = ['green' if q < 10 else 'orange' if q < 20 else 'red' for q in max_queue_sizes]
        bars1 = ax1.bar(scenarios, max_queue_sizes, color=colors, alpha=0.8, width=0.6)
        ax1.set_title('Saturation Files d\'Attente', fontweight='bold', pad=15)
        ax1.set_ylabel('Taille max des files')
        ax1.axhline(y=10, color='orange', linestyle='--', alpha=0.7,
                    label='Seuil attention (10)')
        ax1.axhline(y=20, color='red', linestyle='--', alpha=0.7,
                    label='Seuil critique (20)')
        ax1.legend(fontsize=9)
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.tick_params(axis='x', rotation=25, labelsize=9)

        for bar, val in zip(bars1, max_queue_sizes):
            if val > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                         f'{val}', ha='center', fontweight='bold', fontsize=10)

        # 2. Utilisation maximale des ressources
        x = np.arange(len(scenarios))
        width = 0.35

        bars2a = ax2.bar(x - width / 2, max_cpu_usage, width, label='CPU Max',
                         color='purple', alpha=0.8)
        bars2b = ax2.bar(x + width / 2, max_memory_usage, width, label='Memoire Max',
                         color='orange', alpha=0.8)

        ax2.axhline(y=80, color='red', linestyle='--', alpha=0.7,
                    label='Seuil critique (80%)')
        ax2.axhline(y=60, color='orange', linestyle='--', alpha=0.7,
                    label='Seuil attention (60%)')

        ax2.set_title('Pics d\'Utilisation Ressources', fontweight='bold', pad=15)
        ax2.set_ylabel('Utilisation maximale (%)')
        ax2.set_xticks(x)
        ax2.set_xticklabels([s[:8] for s in scenarios], rotation=25, fontsize=9)  # Limiter taille
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3, axis='y')

        # 3. Gestion des dépendances
        bars3a = ax3.bar(x - width / 2, dependencies_count, width, label='Dependances',
                         color='skyblue', alpha=0.8)
        bars3b = ax3.bar(x + width / 2, deadlocks_count, width, label='Deadlocks',
                         color='red', alpha=0.8)

        ax3.set_title('Gestion des Dependances', fontweight='bold', pad=15)
        ax3.set_ylabel('Nombre de requetes')
        ax3.set_xticks(x)
        ax3.set_xticklabels([s[:8] for s in scenarios], rotation=25, fontsize=9)
        ax3.legend(fontsize=9)
        ax3.grid(True, alpha=0.3, axis='y')

        # Annotations pour efficacité
        for i, (deps, deadlocks) in enumerate(zip(dependencies_count, deadlocks_count)):
            if deps > 0:
                success_rate = (deps - deadlocks) / deps * 100
                ax3.text(i, max(deps, deadlocks) + deps * 0.05, f'{success_rate:.1f}%',
                         ha='center', fontweight='bold', color='green', fontsize=9)

        # 4. Score de santé système
        health_scores = []
        for i, scenario in enumerate(scenarios):
            score = 100

            # Pénalités
            if max_queue_sizes[i] > 10:
                score -= 20
            if max_queue_sizes[i] > 20:
                score -= 30
            if max_cpu_usage[i] > 80:
                score -= 25
            if max_memory_usage[i] > 80:
                score -= 25
            if deadlocks_count[i] > 0:
                score -= 50

            health_scores.append(max(0, score))

        health_colors = ['green' if s >= 80 else 'orange' if s >= 60 else 'red' for s in health_scores]
        bars4 = ax4.bar(scenarios, health_scores, color=health_colors, alpha=0.8, width=0.6)

        ax4.set_title('Score de Sante Systeme', fontweight='bold', pad=15)
        ax4.set_ylabel('Score de sante (/100)')
        ax4.set_ylim(0, 105)
        ax4.axhline(y=80, color='green', linestyle='--', alpha=0.7,
                    label='Seuil sante (80)')
        ax4.axhline(y=60, color='orange', linestyle='--', alpha=0.7,
                    label='Seuil attention (60)')
        ax4.legend(fontsize=9)
        ax4.grid(True, alpha=0.3, axis='y')
        ax4.tick_params(axis='x', rotation=25, labelsize=9)

        for bar, val in zip(bars4, health_scores):
            ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                     f'{val}', ha='center', fontweight='bold', fontsize=10)

        return fig

    def generate_modular_dashboard(self):
        """Génère tous les dashboards modulaires."""
        print("🔍 GÉNÉRATION DU DASHBOARD MODULAIRE...")

        reports = self.load_reports()
        if not reports:
            print("❌ Aucun rapport trouvé")
            return

        print(f"✅ {len(reports)} rapports chargés: {list(reports.keys())}")

        # Créer dossier de sortie
        output_dir = Path("dashboard_output")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        figures = []

        # 1. Dashboard de synthèse
        print("📊 Génération du dashboard de synthèse...")
        summary_fig = self.create_summary_dashboard(reports)
        summary_path = output_dir / f"01_synthese_{timestamp}.png"
        summary_fig.savefig(summary_path, dpi=300, bbox_inches='tight',
                            facecolor='white', edgecolor='none')
        figures.append(('Synthèse Performance', summary_path))
        plt.close(summary_fig)  # Libérer mémoire

        # 2. Dashboard de scalabilité
        if 'scalability' in reports:
            print("📈 Génération du dashboard de scalabilité...")
            scalability_fig = self.create_scalability_dashboard(reports['scalability'])
            if scalability_fig:
                scalability_path = output_dir / f"02_scalabilite_{timestamp}.png"
                scalability_fig.savefig(scalability_path, dpi=300, bbox_inches='tight',
                                        facecolor='white', edgecolor='none')
                figures.append(('Analyse Scalabilité', scalability_path))
                plt.close(scalability_fig)

        # 3. Dashboard temporel
        if 'baseline' in reports and 'spike_load' in reports:
            print("⏱️ Génération du dashboard temporel...")
            temporal_fig = self.create_temporal_dashboard(reports['baseline'], reports['spike_load'])
            temporal_path = output_dir / f"03_temporel_{timestamp}.png"
            temporal_fig.savefig(temporal_path, dpi=300, bbox_inches='tight',
                                 facecolor='white', edgecolor='none')
            figures.append(('Analyse Temporelle', temporal_path))
            plt.close(temporal_fig)

        # 4. Dashboard des situations critiques
        print("🚨 Génération du dashboard des situations critiques...")
        critical_fig = self.create_critical_analysis_dashboard(reports)
        critical_path = output_dir / f"04_critique_{timestamp}.png"
        critical_fig.savefig(critical_path, dpi=300, bbox_inches='tight',
                             facecolor='white', edgecolor='none')
        figures.append(('Situations Critiques', critical_path))
        plt.close(critical_fig)

        print(f"\n✅ {len(figures)} dashboards générés dans: {output_dir}")
        for name, path in figures:
            print(f"  📊 {name}: {path.name}")

        print("\n🔍 ANALYSE DES SITUATIONS CRITIQUES:")
        self.analyze_critical_situations(reports)

        return figures

    def analyze_critical_situations(self, reports):
        """Analyse détaillée des situations critiques."""
        print("\n🚨 SITUATIONS CRITIQUES DETECTEES:")

        critical_found = False

        for test_name, report in reports.items():
            print(f"\n📋 {test_name.upper()}:")

            if test_name == 'scalability':
                continue  # Pas de données critiques pour scalabilité

            # Files d'attente
            queues = report.get('queues', {})
            max_vip = queues.get('max_vip_queue_size', 0)
            max_std = queues.get('max_standard_queue_size', 0)
            total_queue = max_vip + max_std

            if total_queue > 20:
                print(f"  🔴 CRITIQUE: Files saturées (max: {total_queue})")
                critical_found = True
            elif total_queue > 10:
                print(f"  🟡 ATTENTION: Files élevées (max: {total_queue})")
            else:
                print(f"  ✅ Files d'attente: {total_queue} (normal)")

            # Ressources
            resources = report.get('resources', {})
            max_cpu = resources.get('max_cpu_usage', 0)
            max_memory = resources.get('max_memory_usage', 0)

            if max_cpu > 80 or max_memory > 80:
                print(f"  🔴 CRITIQUE: Ressources saturées (CPU: {max_cpu:.1f}%, RAM: {max_memory:.1f}%)")
                critical_found = True
            elif max_cpu > 60 or max_memory > 60:
                print(f"  🟡 ATTENTION: Ressources élevées (CPU: {max_cpu:.1f}%, RAM: {max_memory:.1f}%)")
            else:
                print(f"  ✅ Ressources: CPU {max_cpu:.1f}%, RAM {max_memory:.1f}% (normal)")

            # Deadlocks
            deps = report.get('dependencies', {})
            deadlocks = deps.get('deadlocks_detected', 0)

            if deadlocks > 0:
                print(f"  🔴 CRITIQUE: {deadlocks} deadlocks détectés !")
                critical_found = True
            else:
                print(f"  ✅ Dépendances: 0 deadlock (parfait)")

        if not critical_found:
            print("\n🏆 AUCUNE SITUATION CRITIQUE DETECTEE !")
            print("   Le système est parfaitement dimensionné et resilient.")

        print("\n💡 STRATEGIES DE GESTION DES CAS CRITIQUES:")
        print("   🔄 Anti-famine: Vieillissement automatique des requêtes")
        print("   ⚖️ Équité: Répartition équitable VIP/Standard")
        print("   🔗 Dépendances: Tri topologique + détection deadlocks")
        print("   📊 Monitoring: Métriques temps réel + alertes")


def main():
    """Fonction principale."""
    dashboard = ModularDashboard()
    dashboard.generate_modular_dashboard()


if __name__ == "__main__":
    main()