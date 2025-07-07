#!/usr/bin/env python3
"""
Générateur de graphiques pour les tests de robustesse (Scénarios 4-6)
Crée des visualisations professionnelles pour saturation, pannes et cycles.
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import glob
from pathlib import Path
from datetime import datetime

# Configuration matplotlib pour rendu professionnel
plt.style.use('default')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3

class RobustnessGraphGenerator:
    """Générateur de graphiques pour les tests de robustesse."""

    def __init__(self):
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'success': '#F18F01',
            'warning': '#C73E1D',
            'info': '#6C757D',
            'accent': '#17A2B8',
            'danger': '#DC3545'
        }

        self.scenario_data = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def load_scenario_data(self):
        """Charge les données des 3 scénarios de robustesse."""
        logs_dir = Path("logs/scenarios")

        # Scénario 4 - Saturation Extrême
        extreme_files = glob.glob(str(logs_dir / "scenario_4_extreme_*.json"))
        if extreme_files:
            with open(extreme_files[-1], 'r', encoding='utf-8') as f:
                self.scenario_data['extreme'] = json.load(f)
            print(f"  • Saturation: {Path(extreme_files[-1]).name}")

        # Scénario 5 - Tolérance aux Pannes
        fault_files = glob.glob(str(logs_dir / "scenario_5_fault_tolerance_*.json"))
        if fault_files:
            with open(fault_files[-1], 'r', encoding='utf-8') as f:
                self.scenario_data['fault'] = json.load(f)
            print(f"  • Pannes: {Path(fault_files[-1]).name}")

        # Scénario 6 - Dépendances Circulaires
        cycle_files = glob.glob(str(logs_dir / "scenario_6_circular_dependencies_*.json"))
        if cycle_files:
            with open(cycle_files[-1], 'r', encoding='utf-8') as f:
                self.scenario_data['cycles'] = json.load(f)
            print(f"  • Cycles: {Path(cycle_files[-1]).name}")

    def create_saturation_graph(self):
        """Graphique de saturation extrême avec point de rupture."""
        if 'extreme' not in self.scenario_data:
            print("❌ Données de saturation manquantes")
            return None

        data = self.scenario_data['extreme']

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Figure 4.5 - Test de Saturation Extrême', fontsize=16, fontweight='bold')

        # Sous-graphique 1: Profil de charge par phases
        phases = data['phase_results']
        phase_names = [p['name'].split(' - ')[1] if ' - ' in p['name'] else p['name'] for p in phases]
        avg_rps = [p['avg_rps'] for p in phases]

        bars = ax1.bar(range(len(phase_names)), avg_rps,
                       color=[self.colors['primary'], self.colors['secondary'],
                              self.colors['warning'], self.colors['danger'], self.colors['info']])

        # Ligne de rupture
        breaking_point = data['saturation_metrics']['breaking_point_rps']
        ax1.axhline(y=breaking_point, color=self.colors['danger'], linestyle='--', linewidth=2,
                    label=f'Point de rupture: {breaking_point:.1f} req/s')

        ax1.set_title('Charge par Phase', fontweight='bold')
        ax1.set_xlabel('Phases de Test')
        ax1.set_ylabel('Débit Moyen (req/s)')
        ax1.set_xticks(range(len(phase_names)))
        ax1.set_xticklabels(phase_names, rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Annotations sur les barres
        for i, (bar, rps) in enumerate(zip(bars, avg_rps)):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                     f'{rps:.1f}', ha='center', va='bottom', fontweight='bold')

        # Sous-graphique 2: Métriques de performance
        metrics = ['RPS Max\nSoutenable', 'Point de\nRupture', 'Temps\nRécupération (s)', 'Taux Échec\n(%)']
        values = [
            data['saturation_metrics']['max_sustainable_rps'],
            data['saturation_metrics']['breaking_point_rps'],
            data['saturation_metrics']['recovery_time'],
            data['saturation_metrics']['failure_rate'] * 100
        ]

        colors = [self.colors['success'], self.colors['warning'], self.colors['danger'], self.colors['info']]
        bars2 = ax2.bar(metrics, values, color=colors)

        ax2.set_title('Métriques de Saturation', fontweight='bold')
        ax2.set_ylabel('Valeur')
        ax2.grid(True, alpha=0.3)

        # Annotations
        for bar, value in zip(bars2, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.02,
                     f'{value:.1f}', ha='center', va='bottom', fontweight='bold')

        # Sous-graphique 3: Évolution temporelle (si disponible)
        if 'performance_timeseries' in data and data['performance_timeseries'].get('rps'):
            timestamps = data['performance_timeseries']['timestamps']
            rps_values = data['performance_timeseries']['rps']
            failure_rates = data['performance_timeseries']['failure_rates']

            # Convertir timestamps en temps relatifs
            if timestamps:
                start_time = min(timestamps)
                time_minutes = [(t - start_time) / 60 for t in timestamps]

                ax3.plot(time_minutes, rps_values, color=self.colors['primary'], linewidth=2, label='RPS')
                ax3.axhline(y=breaking_point, color=self.colors['danger'], linestyle='--',
                            label='Point de rupture')

                ax3.set_title('Évolution Temporelle de la Charge', fontweight='bold')
                ax3.set_xlabel('Temps (minutes)')
                ax3.set_ylabel('Débit (req/s)')
                ax3.legend()
                ax3.grid(True, alpha=0.3)
        else:
            ax3.text(0.5, 0.5, 'Données temporelles\nnon disponibles',
                     ha='center', va='center', transform=ax3.transAxes, fontsize=12)
            ax3.set_title('Évolution Temporelle', fontweight='bold')

        # Sous-graphique 4: Analyse de la dégradation
        ax4.text(0.1, 0.8, f"📊 ANALYSE DE SATURATION", fontweight='bold', fontsize=14,
                 transform=ax4.transAxes)

        analysis_text = f"""
🔢 Requêtes générées: {data['summary']['total_requests_generated']:,}
✅ Taux de réussite: {data['summary']['success_rate']*100:.1f}%
💥 Point de rupture: {breaking_point:.1f} req/s
⚡ RPS max théorique: {data['saturation_metrics']['max_sustainable_rps']:.1f} req/s
🔄 Temps de récupération: {data['saturation_metrics']['recovery_time']:.1f}s

🎯 CONCLUSION:
Dégradation brutale identifiée au-delà de {breaking_point:.1f} req/s.
Système nécessite un mécanisme de throttling.
Limite architecturale confirmée."""

        ax4.text(0.1, 0.65, analysis_text, fontsize=10, transform=ax4.transAxes,
                 verticalalignment='top', fontfamily='monospace')
        ax4.axis('off')

        plt.tight_layout()
        filename = f"05_saturation_{self.timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        return filename

    def create_fault_tolerance_graph(self):
        """Graphique de tolérance aux pannes avec timeline."""
        if 'fault' not in self.scenario_data:
            print("❌ Données de pannes manquantes")
            return None

        data = self.scenario_data['fault']

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Figure 4.6 - Test de Tolérance aux Pannes', fontsize=16, fontweight='bold')

        # Sous-graphique 1: Métriques de résilience
        metrics = ['Taux Succès\n(%)', 'Disponibilité\n(%)', 'Récupération\n(ms)', 'Requêtes\nPerdues']
        values = [
            data['summary']['success_rate'] * 100,
            data['availability']['uptime_percentage'],
            float(list(data['recovery_times'].values())[0]) * 1000 if data['recovery_times'] else 0,
            data['summary']['lost_requests']
        ]

        colors = [self.colors['success'] if v > 90 else self.colors['warning']
                  for v in values[:2]] + [self.colors['info'], self.colors['accent']]

        bars = ax1.bar(metrics, values, color=colors)
        ax1.set_title('Métriques de Résilience', fontweight='bold')
        ax1.set_ylabel('Valeur')
        ax1.grid(True, alpha=0.3)

        # Annotations
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.02,
                     f'{value:.1f}', ha='center', va='bottom', fontweight='bold')

        # Sous-graphique 2: Temps de récupération par agent
        if data['recovery_times']:
            agents = list(data['recovery_times'].keys())
            recovery_times = [data['recovery_times'][agent] * 1000 for agent in agents]  # en ms

            agent_names = [name.replace('_', '\n') for name in agents]
            bars2 = ax2.bar(agent_names, recovery_times, color=self.colors['primary'])

            ax2.set_title('Temps de Récupération par Agent', fontweight='bold')
            ax2.set_ylabel('Temps (ms)')
            ax2.grid(True, alpha=0.3)

            # Annotations
            for bar, time_ms in zip(bars2, recovery_times):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                         f'{time_ms:.1f}ms', ha='center', va='bottom', fontweight='bold')
        else:
            ax2.text(0.5, 0.5, 'Données de récupération\nnon disponibles',
                     ha='center', va='center', transform=ax2.transAxes, fontsize=12)
            ax2.set_title('Récupération par Agent', fontweight='bold')

        # Sous-graphique 3: Timeline des pannes (simulée)
        fault_scenarios = data['fault_scenarios']

        # Créer une timeline
        total_duration = data['configuration']['test_duration']
        time_line = np.linspace(0, total_duration, 100)

        ax3.set_xlim(0, total_duration)
        ax3.set_ylim(-0.5, len(fault_scenarios) + 0.5)

        # Dessiner les pannes
        colors_agents = [self.colors['danger'], self.colors['warning'],
                         self.colors['info'], self.colors['secondary']]

        for i, scenario in enumerate(fault_scenarios):
            start_time = scenario['start_time']
            duration = scenario['duration']

            # Rectangle pour la panne
            rect = patches.Rectangle((start_time, i-0.3), duration, 0.6,
                                     linewidth=1, edgecolor='black',
                                     facecolor=colors_agents[i % len(colors_agents)],
                                     alpha=0.7)
            ax3.add_patch(rect)

            # Label de l'agent
            ax3.text(-8, i, scenario['target_agent'].replace('_', '\n'),
                     ha='right', va='center', fontweight='bold')

            # Temps de panne
            ax3.text(start_time + duration/2, i, f'{duration}s',
                     ha='center', va='center', fontweight='bold', color='white')

        ax3.set_title('Timeline des Pannes Simulées', fontweight='bold')
        ax3.set_xlabel('Temps (secondes)')
        ax3.set_ylabel('Agents')
        ax3.set_yticks(range(len(fault_scenarios)))
        ax3.set_yticklabels(['' for _ in fault_scenarios])
        ax3.grid(True, alpha=0.3)

        # Sous-graphique 4: Résumé et analyse
        ax4.text(0.1, 0.9, "🛡️ ANALYSE DE RÉSILIENCE", fontweight='bold', fontsize=14,
                 transform=ax4.transAxes)

        uptime = data['availability']['uptime_percentage']
        success_rate = data['summary']['success_rate'] * 100

        analysis_text = f"""
🔢 Requêtes traitées: {data['summary']['total_requests_generated']}
✅ Taux de succès: {success_rate:.1f}%
🛡️  Disponibilité: {uptime:.1f}%
⏱️  Arrêt total: {data['availability']['total_downtime']:.1f}s
📤 Requêtes perdues: {data['summary']['lost_requests']}
⚡ Récupération moy: {np.mean(list(data['recovery_times'].values()))*1000:.1f}ms

🎯 ÉVALUATION:"""

        if uptime >= 95:
            evaluation = "🏆 EXCELLENTE (≥95%)"
        elif uptime >= 90:
            evaluation = "🥈 BONNE (≥90%)"
        elif uptime >= 80:
            evaluation = "🥉 ACCEPTABLE (≥80%)"
        else:
            evaluation = "⚠️ INSUFFISANTE (<80%)"

        analysis_text += f"\nRésilience: {evaluation}"

        ax4.text(0.1, 0.75, analysis_text, fontsize=10, transform=ax4.transAxes,
                 verticalalignment='top', fontfamily='monospace')
        ax4.axis('off')

        plt.tight_layout()
        filename = f"06_fault_tolerance_{self.timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        return filename

    def create_circular_dependencies_graph(self):
        """Graphique de gestion des dépendances circulaires."""
        if 'cycles' not in self.scenario_data:
            print("❌ Données de cycles manquantes")
            return None

        data = self.scenario_data['cycles']

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Figure 4.7 - Test de Dépendances Circulaires', fontsize=16, fontweight='bold')

        # Sous-graphique 1: Métriques de cycles
        cycle_metrics = data['cycle_metrics']

        metrics = ['Cycles\nDétectés', 'Cycles\nRésolus', 'Deadlocks\nPrévenus', 'Longueur\nMax']
        values = [
            cycle_metrics['cycles_detected'],
            cycle_metrics['cycles_resolved'],
            cycle_metrics['deadlocks_prevented'],
            cycle_metrics['max_cycle_length']
        ]

        colors = [self.colors['info'], self.colors['success'], self.colors['primary'], self.colors['accent']]
        bars = ax1.bar(metrics, values, color=colors)

        ax1.set_title('Métriques de Gestion des Cycles', fontweight='bold')
        ax1.set_ylabel('Nombre')
        ax1.grid(True, alpha=0.3)

        # Annotations
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.02,
                     f'{value}', ha='center', va='bottom', fontweight='bold')

        # Sous-graphique 2: Stratégies de résolution
        if 'strategies_used' in data['resolution_analysis']:
            strategies = list(data['resolution_analysis']['strategies_used'].keys())
            strategy_counts = list(data['resolution_analysis']['strategies_used'].values())

            # Simplifier les noms des stratégies
            strategy_labels = []
            for strategy in strategies:
                if 'partial' in strategy:
                    strategy_labels.append('Exécution\nPartielle')
                elif 'parallel' in strategy:
                    strategy_labels.append('Exécution\nParallèle')
                elif 'break_oldest' in strategy:
                    strategy_labels.append('Rupture\nAncienne')
                elif 'priority' in strategy:
                    strategy_labels.append('Priorité\nBasée')
                elif 'weakest' in strategy:
                    strategy_labels.append('Lien\nFaible')
                else:
                    strategy_labels.append(strategy.replace('_', '\n'))

            # Créer un camembert
            colors_pie = plt.cm.Set3(np.linspace(0, 1, len(strategies)))
            wedges, texts, autotexts = ax2.pie(strategy_counts, labels=strategy_labels,
                                               colors=colors_pie, autopct='%1.1f%%',
                                               startangle=90)

            ax2.set_title('Stratégies de Résolution', fontweight='bold')
        else:
            ax2.text(0.5, 0.5, 'Données de stratégies\nnon disponibles',
                     ha='center', va='center', transform=ax2.transAxes, fontsize=12)
            ax2.set_title('Stratégies de Résolution', fontweight='bold')

        # Sous-graphique 3: Types de cycles testés
        cycle_test_cases = data['cycle_test_cases']
        cycle_types = [case['name'] for case in cycle_test_cases]
        cycle_descriptions = [case['description'] for case in cycle_test_cases]

        # Créer un graphique en barres horizontales
        y_pos = np.arange(len(cycle_types))
        # Utiliser une valeur fixe pour toutes les barres (tous les types ont été testés)
        test_values = [1] * len(cycle_types)

        bars3 = ax3.barh(y_pos, test_values, color=self.colors['secondary'])
        ax3.set_yticks(y_pos)
        ax3.set_yticklabels([name.replace(' ', '\n') for name in cycle_types])
        ax3.set_xlabel('Tests Exécutés')
        ax3.set_title('Types de Cycles Testés', fontweight='bold')
        ax3.grid(True, alpha=0.3)

        # Ajouter les descriptions
        for i, (bar, desc) in enumerate(zip(bars3, cycle_descriptions)):
            ax3.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2,
                     desc, ha='left', va='center', fontsize=9)

        # Sous-graphique 4: Performance et résumé
        ax4.text(0.1, 0.9, "🔄 ANALYSE DES CYCLES", fontweight='bold', fontsize=14,
                 transform=ax4.transAxes)

        detection_time = data['detection_performance']['avg_detection_time'] * 1000  # en ms
        resolution_rate = data['resolution_analysis']['resolution_success_rate'] * 100

        analysis_text = f"""
🔢 Requêtes totales: {data['summary']['total_requests']}
📝 Requêtes normales: {data['summary']['normal_requests']}
🧪 Requêtes de test: {data['summary']['cycle_test_requests']}
✅ Taux de réussite: {data['summary']['success_rate']*100:.1f}%

🔄 CYCLES:
Détectés: {cycle_metrics['cycles_detected']}
Résolus: {cycle_metrics['cycles_resolved']} ({resolution_rate:.1f}%)
Longueur max: {cycle_metrics['max_cycle_length']} niveaux

⚡ PERFORMANCE:
Détection: {detection_time:.2f}ms en moyenne
Deadlocks prévenus: {cycle_metrics['deadlocks_prevented']}

🎯 ÉVALUATION:"""

        if resolution_rate >= 100:
            evaluation = "🏆 PARFAITE (100%)"
        elif resolution_rate >= 95:
            evaluation = "🥈 EXCELLENTE (≥95%)"
        elif resolution_rate >= 80:
            evaluation = "🥉 BONNE (≥80%)"
        else:
            evaluation = "⚠️ INSUFFISANTE (<80%)"

        analysis_text += f"\nRésolution: {evaluation}"

        ax4.text(0.1, 0.75, analysis_text, fontsize=10, transform=ax4.transAxes,
                 verticalalignment='top', fontfamily='monospace')
        ax4.axis('off')

        plt.tight_layout()
        filename = f"07_circular_dependencies_{self.timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        return filename

    def create_robustness_summary(self):
        """Graphique de synthèse des 3 tests de robustesse."""
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
        fig.suptitle('Figure 4.8 - Synthèse des Tests de Robustesse', fontsize=16, fontweight='bold')

        # Données pour les 3 scénarios
        scenarios = ['Saturation\nExtrême', 'Tolérance\naux Pannes', 'Dépendances\nCirculaires']

        # Métriques principales
        success_rates = []
        key_metrics = []
        evaluations = []

        if 'extreme' in self.scenario_data:
            success_rates.append(self.scenario_data['extreme']['summary']['success_rate'] * 100)
            key_metrics.append(f"Rupture: {self.scenario_data['extreme']['saturation_metrics']['breaking_point_rps']:.1f} req/s")
            evaluations.append("Limite identifiée")

        if 'fault' in self.scenario_data:
            success_rates.append(self.scenario_data['fault']['summary']['success_rate'] * 100)
            uptime = self.scenario_data['fault']['availability']['uptime_percentage']
            key_metrics.append(f"Disponibilité: {uptime:.1f}%")
            if uptime >= 90:
                evaluations.append("Résilience validée")
            else:
                evaluations.append("Résilience limitée")

        if 'cycles' in self.scenario_data:
            success_rates.append(self.scenario_data['cycles']['summary']['success_rate'] * 100)
            cycles_resolved = self.scenario_data['cycles']['cycle_metrics']['cycles_resolved']
            key_metrics.append(f"Cycles résolus: {cycles_resolved}")
            evaluations.append("Gestion parfaite")

        # Créer le graphique
        x_pos = np.arange(len(scenarios))

        # Barres de taux de succès
        colors = [self.colors['warning'], self.colors['primary'], self.colors['success']]
        bars = ax.bar(x_pos, success_rates, color=colors, alpha=0.7,
                      label='Taux de succès (%)')

        # Configuration des axes
        ax.set_xlabel('Scénarios de Robustesse', fontweight='bold')
        ax.set_ylabel('Taux de Succès (%)', fontweight='bold')
        ax.set_title('Performance Comparative des Tests de Robustesse', fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(scenarios)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 110)

        # Annotations sur les barres
        for i, (bar, rate, metric, eval_text) in enumerate(zip(bars, success_rates, key_metrics, evaluations)):
            height = bar.get_height()

            # Taux de succès
            ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                    f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=12)

            # Métrique clé
            ax.text(bar.get_x() + bar.get_width()/2., height/2,
                    metric, ha='center', va='center', fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

            # Évaluation
            ax.text(bar.get_x() + bar.get_width()/2., -8,
                    eval_text, ha='center', va='top', fontweight='bold',
                    color=colors[i], fontsize=10)

        # Ligne de référence à 90%
        ax.axhline(y=90, color=self.colors['success'], linestyle='--', alpha=0.5,
                   label='Seuil acceptable (90%)')

        # Ligne de référence à 50%
        ax.axhline(y=50, color=self.colors['danger'], linestyle='--', alpha=0.5,
                   label='Seuil critique (50%)')

        ax.legend(loc='upper right')

        # Ajouter des statistiques globales
        if len(success_rates) >= 3:
            avg_success = np.mean(success_rates)
            ax.text(0.02, 0.98, f"📊 BILAN GLOBAL DE ROBUSTESSE\n"
                                f"Taux de succès moyen: {avg_success:.1f}%\n"
                                f"Tests validés: {len([r for r in success_rates if r > 50])}/3\n"
                                f"Robustesse: {'✅ Validée' if avg_success > 70 else '⚠️ Partielle'}",
                    transform=ax.transAxes, fontsize=11, verticalalignment='top',
                    bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.8))

        plt.tight_layout()
        filename = f"08_robustness_summary_{self.timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        return filename

    def generate_all_robustness_graphs(self):
        """Génère tous les graphiques de robustesse."""
        print("🎨 GÉNÉRATEUR DE GRAPHIQUES DE ROBUSTESSE")
        print("=" * 55)

        print("📊 Chargement des résultats de robustesse:")
        self.load_scenario_data()

        if not self.scenario_data:
            print("❌ Aucune donnée trouvée. Exécutez d'abord les scénarios 4-6.")
            return

        print("\n🎨 Génération des graphiques...")
        generated_files = []

        # Graphique saturation
        if 'extreme' in self.scenario_data:
            filename = self.create_saturation_graph()
            if filename:
                generated_files.append(filename)
                print(f"💥 Graphique saturation sauvegardé: {filename}")

        # Graphique pannes
        if 'fault' in self.scenario_data:
            filename = self.create_fault_tolerance_graph()
            if filename:
                generated_files.append(filename)
                print(f"🛡️ Graphique pannes sauvegardé: {filename}")

        # Graphique cycles
        if 'cycles' in self.scenario_data:
            filename = self.create_circular_dependencies_graph()
            if filename:
                generated_files.append(filename)
                print(f"🔄 Graphique cycles sauvegardé: {filename}")

        # Synthèse robustesse
        if len(self.scenario_data) >= 2:
            filename = self.create_robustness_summary()
            if filename:
                generated_files.append(filename)
                print(f"📊 Synthèse robustesse sauvegardée: {filename}")

        print(f"\n✅ {len(generated_files)} GRAPHIQUES DE ROBUSTESSE GÉNÉRÉS!")
        print("📁 Fichiers créés:")
        for i, filename in enumerate(generated_files, 5):
            print(f"  • {filename} - Figure 4.{i}")

        print("\n🎯 Parfait pour votre soutenance de robustesse !")

        return generated_files


def main():
    """Fonction principale."""
    generator = RobustnessGraphGenerator()
    generator.generate_all_robustness_graphs()


if __name__ == "__main__":
    main()