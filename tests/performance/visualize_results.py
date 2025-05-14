# tests/performance/visualize_results.py

import os
import re
import matplotlib.pyplot as plt
import numpy as np
import argparse
import glob
from datetime import datetime


def parse_log_file(log_file, test_type):
    """
    Extrait les données pertinentes d'un fichier de rapport de test.

    Args:
        log_file (str): Chemin du fichier de rapport
        test_type (str): Type de test (constant, increasing, burst, dependency)

    Returns:
        dict: Données extraites du rapport
    """
    data = {}

    with open(log_file, 'r') as f:
        content = f.read()

        if test_type == "constant":
            # Extraire les temps de réponse
            success_match = re.search(r"Demandes complétées: (\d+) \(([\d\.]+)%\)", content)
            response_match = re.search(r"Temps de réponse moyen: ([\d\.]+)s", content)
            vip_time_match = re.search(r"Temps moyen VIP: ([\d\.]+)s", content)
            std_time_match = re.search(r"Temps moyen standard: ([\d\.]+)s", content)
            equity_match = re.search(r"Ratio d'équité \(std/vip\): ([\d\.]+)", content)

            if success_match:
                data["success_rate"] = float(success_match.group(2))
            if response_match:
                data["avg_response_time"] = float(response_match.group(1))
            if vip_time_match:
                data["vip_time"] = float(vip_time_match.group(1))
            if std_time_match:
                data["std_time"] = float(std_time_match.group(1))
            if equity_match:
                data["equity_ratio"] = float(equity_match.group(1))

        elif test_type == "increasing":
            # Extraire les RPS et temps par palier
            rps_levels = []
            response_times = []
            success_rates = []

            palier_pattern = re.compile(
                r"--- Palier: (\d+) req/s.*?Temps de réponse moyen: ([\d\.]+)s.*?Demandes complétées: (\d+) \(([\d\.]+)%\)",
                re.DOTALL)

            for match in palier_pattern.finditer(content):
                rps = int(match.group(1))
                resp_time = float(match.group(2))
                success_rate = float(match.group(4))

                rps_levels.append(rps)
                response_times.append(resp_time)
                success_rates.append(success_rate)

            data["rps_levels"] = rps_levels
            data["response_times"] = response_times
            data["success_rates"] = success_rates

            # Extraire le point de rupture
            rupture_match = re.search(r"Charge maximale stable: (\d+) req/s", content)
            if rupture_match:
                data["max_stable_rps"] = int(rupture_match.group(1))

        elif test_type == "burst":
            # Extraire les temps de réponse par phase
            pre_match = re.search(r"Temps de réponse moyen avant le pic: ([\d\.]+)s", content)
            during_match = re.search(r"Temps de réponse moyen pendant le pic: ([\d\.]+)s", content)
            post_match = re.search(r"Temps de réponse moyen après le pic: ([\d\.]+)s", content)

            pre_success_match = re.search(r"Taux de succès avant le pic: ([\d\.]+)%", content)
            during_success_match = re.search(r"Taux de succès pendant le pic: ([\d\.]+)%", content)
            post_success_match = re.search(r"Taux de succès après le pic: ([\d\.]+)%", content)

            if pre_match:
                data["pre_response_time"] = float(pre_match.group(1))
            if during_match:
                data["during_response_time"] = float(during_match.group(1))
            if post_match:
                data["post_response_time"] = float(post_match.group(1))

            if pre_success_match:
                data["pre_success_rate"] = float(pre_success_match.group(1))
            if during_success_match:
                data["during_success_rate"] = float(during_success_match.group(1))
            if post_success_match:
                data["post_success_rate"] = float(post_success_match.group(1))

        elif test_type == "dependency":
            # Extraire les temps d'exécution par profondeur
            depth_pattern = re.compile(r"  - Profondeur (\d+): ([\d\.]+)s", re.MULTILINE)
            depths = []
            depth_times = []

            for match in depth_pattern.finditer(content):
                depth = int(match.group(1))
                time_value = float(match.group(2))

                depths.append(depth)
                depth_times.append(time_value)

            data["depths"] = depths
            data["depth_times"] = depth_times

            # Extraire le ratio graphe/indépendant
            ratio_match = re.search(r"Ratio \(graphe/indép\.\): ([\d\.]+)x", content)
            if ratio_match:
                data["graph_indep_ratio"] = float(ratio_match.group(1))

    return data


def create_constant_load_chart(data, output_dir):
    """Crée un graphique pour le test de charge constante"""
    if not data or "vip_time" not in data or "std_time" not in data:
        print("Données insuffisantes pour le graphique de charge constante")
        return

    # Créer une figure avec deux sous-graphiques
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Graphique des temps de réponse
    types = ["VIP", "Standard", "Moyen"]
    times = [data.get("vip_time", 0), data.get("std_time", 0), data.get("avg_response_time", 0)]

    ax1.bar(types, times, color=['#4dabf7', '#ff8787', '#a9e34b'])
    ax1.set_title('Temps de réponse par type de client')
    ax1.set_ylabel('Temps (secondes)')
    ax1.set_ylim(bottom=0)

    # Équité
    ax2.pie([1, data.get("equity_ratio", 1)],
            labels=['VIP', 'Standard'],
            autopct='%1.1f%%',
            colors=['#4dabf7', '#ff8787'],
            wedgeprops={'alpha': 0.7})
    ax2.set_title(f'Ratio d\'équité: {data.get("equity_ratio", 1):.2f}')

    # Titre global
    fig.suptitle('Résultats du test de charge constante', fontsize=16)

    # Ajouter des annotations avec les métriques clés
    plt.figtext(0.5, 0.01, f"Taux de succès: {data.get('success_rate', 0):.1f}%",
                ha="center", fontsize=12, bbox={"facecolor": "orange", "alpha": 0.2, "pad": 5})

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "constant_load_results.png"))
    plt.close()


def create_increasing_load_chart(data, output_dir):
    """Crée un graphique pour le test de charge croissante"""
    if not data or "rps_levels" not in data or "response_times" not in data or "success_rates" not in data:
        print("Données insuffisantes pour le graphique de charge croissante")
        return

    rps_levels = data["rps_levels"]
    response_times = data["response_times"]
    success_rates = data["success_rates"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Graphique des temps de réponse
    ax1.plot(rps_levels, response_times, 'o-', linewidth=2, markersize=8, color='#4dabf7')
    ax1.set_ylabel('Temps de réponse (s)')
    ax1.set_title('Impact de la charge sur les temps de réponse')
    ax1.grid(True, linestyle='--', alpha=0.7)

    # Graphique des taux de succès
    ax2.plot(rps_levels, success_rates, 'o-', linewidth=2, markersize=8, color='#a9e34b')
    ax2.set_xlabel('Demandes par seconde')
    ax2.set_ylabel('Taux de succès (%)')
    ax2.set_title('Impact de la charge sur le taux de succès')
    ax2.grid(True, linestyle='--', alpha=0.7)

    # Marquer le point de rupture
    if "max_stable_rps" in data:
        max_stable = data["max_stable_rps"]

        # Trouver l'index correspondant au point de rupture
        if max_stable in rps_levels:
            idx = rps_levels.index(max_stable)

            # Marquer sur les deux graphiques
            ax1.axvline(x=max_stable, color='red', linestyle='--', alpha=0.7)
            ax1.text(max_stable + 0.1, max(response_times) * 0.8, f'Point de rupture: {max_stable} req/s',
                     rotation=90, color='red')

            ax2.axvline(x=max_stable, color='red', linestyle='--', alpha=0.7)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "increasing_load_results.png"))
    plt.close()


def create_burst_load_chart(data, output_dir):
    """Crée un graphique pour le test de pic de charge"""
    if not (data and "pre_response_time" in data and "during_response_time" in data and "post_response_time" in data):
        print("Données insuffisantes pour le graphique de pic de charge")
        return

    # Créer une figure avec deux sous-graphiques
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Graphique des temps de réponse
    phases = ["Avant pic", "Pendant pic", "Après pic"]
    times = [data["pre_response_time"], data["during_response_time"], data["post_response_time"]]

    bars = ax1.bar(phases, times, color=['#a9e34b', '#ff8787', '#4dabf7'])
    ax1.set_title('Temps de réponse par phase')
    ax1.set_ylabel('Temps (secondes)')
    ax1.set_ylim(bottom=0)

    # Ajouter les valeurs sur les barres
    for bar in bars:
        height = bar.get_height()
        ax1.annotate(f'{height:.2f}s',
                     xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3),  # 3 points de décalage vertical
                     textcoords="offset points",
                     ha='center', va='bottom')

    # Graphique des taux de succès
    if all(key in data for key in ["pre_success_rate", "during_success_rate", "post_success_rate"]):
        success_rates = [data["pre_success_rate"], data["during_success_rate"], data["post_success_rate"]]

        success_bars = ax2.bar(phases, success_rates, color=['#a9e34b', '#ff8787', '#4dabf7'])
        ax2.set_title('Taux de succès par phase')
        ax2.set_ylabel('Taux de succès (%)')
        ax2.set_ylim(0, 105)  # Plage de 0 à 105% pour la visibilité

        # Ajouter les valeurs sur les barres
        for bar in success_bars:
            height = bar.get_height()
            ax2.annotate(f'{height:.1f}%',
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 3),  # 3 points de décalage vertical
                         textcoords="offset points",
                         ha='center', va='bottom')

    # Titre global
    fig.suptitle('Analyse de l\'impact du pic de charge', fontsize=16)

    # Facteur d'augmentation
    if data["pre_response_time"] > 0:
        increase_factor = data["during_response_time"] / data["pre_response_time"]
        recovery_factor = data["post_response_time"] / data["pre_response_time"]

        plt.figtext(0.5, 0.01,
                    f"Facteur d'augmentation: {increase_factor:.2f}x | Facteur de récupération: {recovery_factor:.2f}x",
                    ha="center", fontsize=12, bbox={"facecolor": "orange", "alpha": 0.2, "pad": 5})

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "burst_load_results.png"))
    plt.close()


def create_dependency_chart(data, output_dir):
    """Crée un graphique pour le test de dépendances complexes"""
    if not data or "depths" not in data or "depth_times" not in data:
        print("Données insuffisantes pour le graphique de dépendances")
        return

    depths = data["depths"]
    depth_times = data["depth_times"]

    # Trier par profondeur
    sorted_indices = np.argsort(depths)
    sorted_depths = [depths[i] for i in sorted_indices]
    sorted_times = [depth_times[i] for i in sorted_indices]

    plt.figure(figsize=(10, 6))

    plt.bar(sorted_depths, sorted_times, color='#4dabf7')
    plt.xlabel('Profondeur du graphe')
    plt.ylabel('Temps d\'exécution (s)')
    plt.title('Impact de la profondeur du graphe sur le temps d\'exécution')
    plt.grid(True, linestyle='--', alpha=0.7)

    # Ajouter une ligne de tendance
    if len(sorted_depths) > 1:
        z = np.polyfit(sorted_depths, sorted_times, 1)
        p = np.poly1d(z)
        plt.plot(sorted_depths, p(sorted_depths), "r--", alpha=0.8)

        # Équation de la ligne de tendance
        slope = z[0]
        intercept = z[1]
        plt.text(0.05, 0.95, f'y = {slope:.2f}x + {intercept:.2f}',
                 transform=plt.gca().transAxes, fontsize=12,
                 bbox=dict(facecolor='white', alpha=0.8))

    # Ajouter le ratio graphe/indépendant
    if "graph_indep_ratio" in data:
        plt.figtext(0.5, 0.01,
                    f"Ratio temps graphe/indépendant: {data['graph_indep_ratio']:.2f}x",
                    ha="center", fontsize=12, bbox={"facecolor": "orange", "alpha": 0.2, "pad": 5})

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "dependency_results.png"))
    plt.close()


def visualize_all_results(log_dir="logs/performance", output_dir="reports/performance"):
    """Visualise tous les résultats de test disponibles"""
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)

    # Trouver les fichiers de rapport les plus récents pour chaque type de test
    test_types = {
        "constant": "test_constant_load_*.log",
        "increasing": "test_increasing_load_*.log",
        "burst": "test_burst_load_*.log",
        "dependency": "test_dependency_*.log"
    }

    latest_files = {}

    for test_type, pattern in test_types.items():
        files = glob.glob(os.path.join(log_dir, pattern))
        if files:
            # Trier par date de modification (le plus récent en premier)
            latest = max(files, key=os.path.getmtime)
            latest_files[test_type] = latest

    # Générer les graphiques pour chaque type de test
    for test_type, log_file in latest_files.items():
        print(f"Traitement de {test_type} - {log_file}")

        data = parse_log_file(log_file, test_type)

        if test_type == "constant":
            create_constant_load_chart(data, output_dir)
        elif test_type == "increasing":
            create_increasing_load_chart(data, output_dir)
        elif test_type == "burst":
            create_burst_load_chart(data, output_dir)
        elif test_type == "dependency":
            create_dependency_chart(data, output_dir)

    # Créer un rapport HTML pour visualiser tous les graphiques
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_file = os.path.join(output_dir, "performance_report.html")

    with open(html_file, 'w') as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Rapport de performance - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #1864ab; }}
        h2 {{ color: #495057; margin-top: 30px; }}
        .chart-container {{ margin: 20px 0; border: 1px solid #dee2e6; padding: 10px; border-radius: 5px; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    <h1>Rapport de performance - {timestamp}</h1>

    <h2>Test de charge constante</h2>
    <div class="chart-container">
        <img src="constant_load_results.png" alt="Résultats du test de charge constante">
    </div>

    <h2>Test de charge croissante</h2>
    <div class="chart-container">
        <img src="increasing_load_results.png" alt="Résultats du test de charge croissante">
    </div>

    <h2>Test de pic de charge</h2>
    <div class="chart-container">
        <img src="burst_load_results.png" alt="Résultats du test de pic de charge">
    </div>

    <h2>Test de dépendances complexes</h2>
    <div class="chart-container">
        <img src="dependency_results.png" alt="Résultats du test de dépendances complexes">
    </div>
</body>
</html>
""")

    print(f"Rapport généré: {html_file}")
    return html_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualisation des résultats des tests de performance")
    parser.add_argument("--log-dir", default="logs/performance",
                        help="Répertoire contenant les fichiers de log")
    parser.add_argument("--output-dir", default="reports/performance",
                        help="Répertoire de sortie pour les graphiques")

    args = parser.parse_args()
    visualize_all_results(args.log_dir, args.output_dir)