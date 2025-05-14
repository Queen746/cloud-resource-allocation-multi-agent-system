# tests/performance/dependency_test.py

import time
import random
import logging
import networkx as nx
from datetime import datetime
from models.client import Client
from models.enums import ClientType
from models.resource_request import ResourceRequest


class DependencyTest:
    """
    Test spécialisé pour évaluer la gestion des dépendances complexes.
    Crée des graphes de dépendances de différentes profondeurs et largeurs.
    """

    def __init__(self, system_launcher, num_graphs=10, base_rps=3,
                 vip_ratio=0.2):
        self.system_launcher = system_launcher
        self.num_graphs = num_graphs  # Nombre de graphes de dépendances à tester
        self.base_rps = base_rps  # Demandes indépendantes par seconde (fond)
        self.vip_ratio = vip_ratio
        self.logger = logging.getLogger("DependencyTest")

        # Préparer les clients
        self.vip_clients = [Client(f"vip-{i}", ClientType.VIP) for i in range(10)]
        self.standard_clients = [Client(f"std-{i}", ClientType.STANDARD) for i in range(40)]

        # Métriques
        self.sent_requests = []
        self.completed_requests = []
        self.failed_requests = []
        self.graph_metrics = {}  # {graph_id: {depth: X, width: Y, sent: Z, completed: W, ...}}

    def run(self):
        """Exécute le test de dépendances complexes"""
        self.logger.info(f"Démarrage du test - {self.num_graphs} graphes de dépendances")

        # Générer et envoyer les graphes de dépendances
        for graph_id in range(1, self.num_graphs + 1):
            # Choisir une structure de graphe aléatoire
            depth = random.randint(2, 5)
            width = random.randint(2, 4)

            self.logger.info(f"Création du graphe {graph_id} (profondeur: {depth}, largeur: {width})")

            # Créer le graphe de dépendances
            graph = self._create_dependency_graph(graph_id, depth, width)

            # Envoyer les demandes selon le graphe
            self._submit_graph_requests(graph, graph_id, depth, width)

            # Envoyer quelques demandes indépendantes pour le "bruit de fond"
            for _ in range(self.base_rps * 3):  # 3 secondes de demandes de fond
                self._submit_independent_request()
                time.sleep(1 / self.base_rps)

            # Attendre un peu avant le prochain graphe
            time.sleep(5)

        # Continuer à envoyer des demandes indépendantes pendant que les graphes se traitent
        end_time = time.time() + 120  # 2 minutes supplémentaires
        while time.time() < end_time:
            self._submit_independent_request()
            time.sleep(1 / self.base_rps)

        # Attendre que toutes les demandes soient traitées
        time.sleep(30)

        # Collecter les résultats finaux
        self._collect_final_results()

        # Générer le rapport
        self.generate_report()

    def _create_dependency_graph(self, graph_id, depth, width):
        """
        Crée un graphe acyclique dirigé représentant des dépendances.
        Retourne un dictionnaire {node_id: [dependencies]}.
        """
        # Utiliser networkx pour créer un graphe acyclique dirigé
        G = nx.DiGraph()

        # Créer les nœuds pour chaque niveau
        nodes_by_level = {}
        total_nodes = 0

        for level in range(depth):
            # Le nombre de nœuds à ce niveau
            if level == 0:
                # Un seul nœud racine
                num_nodes = 1
            elif level == depth - 1:
                # Niveau terminal
                num_nodes = width ** 2
            else:
                # Niveaux intermédiaires
                num_nodes = width

            # Créer les nœuds pour ce niveau
            nodes_at_level = []
            for i in range(num_nodes):
                node_id = f"g{graph_id}_l{level}_n{i}"
                G.add_node(node_id)
                nodes_at_level.append(node_id)
                total_nodes += 1

            nodes_by_level[level] = nodes_at_level

        # Créer les arêtes pour représenter les dépendances
        for level in range(1, depth):
            for node in nodes_by_level[level]:
                # Chaque nœud dépend d'au moins un nœud du niveau supérieur
                if level == 1:
                    # Le premier niveau ne dépend que de la racine
                    G.add_edge(nodes_by_level[0][0], node)
                else:
                    # Les autres niveaux dépendent de plusieurs nœuds du niveau précédent
                    num_dependencies = random.randint(1, len(nodes_by_level[level - 1]))
                    dependencies = random.sample(nodes_by_level[level - 1], num_dependencies)
                    for dep in dependencies:
                        G.add_edge(dep, node)

        # Vérifier l'absence de cycles
        if not nx.is_directed_acyclic_graph(G):
            self.logger.warning(f"Le graphe {graph_id} contient des cycles - correction nécessaire")
            # Retirer des arêtes jusqu'à ce que le graphe soit acyclique
            while not nx.is_directed_acyclic_graph(G):
                edges = list(G.edges())
                if not edges:
                    break
                edge_to_remove = random.choice(edges)
                G.remove_edge(*edge_to_remove)

        # Convertir en dictionnaire {node: [dependencies]}
        dependency_dict = {}
        for node in G.nodes():
            dependency_dict[node] = list(G.predecessors(node))

        # Initialiser les métriques pour ce graphe
        self.graph_metrics[graph_id] = {
            "depth": depth,
            "width": width,
            "total_nodes": total_nodes,
            "structure": dependency_dict,
            "sent": 0,
            "completed": 0,
            "failed": 0,
            "response_times": [],
            "completion_time": None,
            "critical_path": None,
            "start_time": time.time()
        }

        return dependency_dict

    def _submit_graph_requests(self, graph, graph_id, depth, width):
        """Envoie les demandes selon le graphe de dépendances"""
        # Pour chaque nœud du graphe, créer et envoyer une demande
        for node_id, dependencies in graph.items():
            # Déterminer le niveau du nœud pour ajuster les paramètres
            level = int(node_id.split('_l')[1].split('_')[0])
            level_factor = (level + 1) / depth  # Plus élevé pour les niveaux plus profonds

            # Sélectionner le type de client (VIP plus fréquent aux niveaux critiques)
            if level == 0 or random.random() < self.vip_ratio + 0.1 * level_factor:
                client = random.choice(self.vip_clients)
            else:
                client = random.choice(self.standard_clients)

            # Générer des caractéristiques ajustées selon le niveau
            cpu = random.uniform(1.0, 3.0 + level_factor * 2.0)
            memory = random.uniform(2.0, 4.0 + level_factor * 4.0)
            duration = random.uniform(5.0, 15.0 + level_factor * 30.0)

            # Convertir les IDs de nœuds dépendances en IDs de requêtes
            request_dependencies = set(dependencies)

            # Créer et envoyer la demande
            self.logger.info(f"Envoi de la demande {node_id} du client {client.id} "
                             f"(CPU: {cpu:.1f}, Mémoire: {memory:.1f}, Durée: {duration:.1f}s, "
                             f"Dépendances: {request_dependencies})")

            request_data = {
                "id": node_id,
                "client": client,
                "cpu": cpu,
                "memory": memory,
                "duration": duration,
                "dependencies": request_dependencies,
                "submit_time": time.time(),
                "graph_id": graph_id,
                "level": level
            }

            # Envoyer la demande au système
            self.system_launcher.submit_request(
                client=client,
                request_id=node_id,
                cpu_required=cpu,
                memory_required=memory,
                estimated_duration=duration,
                dependencies=request_dependencies
            )

            # Enregistrer les métriques
            self.sent_requests.append(request_data)
            self.graph_metrics[graph_id]["sent"] += 1

            # Petite pause pour éviter de surcharger le système
            time.sleep(0.2)

    def _submit_independent_request(self):
        """Envoie une demande indépendante"""
        request_id = f"ind-{len(self.sent_requests) + 1}"

        # Sélectionner le type de client
        if random.random() < self.vip_ratio:
            client = random.choice(self.vip_clients)
        else:
            client = random.choice(self.standard_clients)

        # Générer des caractéristiques aléatoires
        cpu = random.uniform(1.0, 4.0)
        memory = random.uniform(2.0, 6.0)
        duration = random.uniform(5.0, 45.0)

        # Créer et envoyer la demande
        self.logger.info(f"Envoi de la demande indépendante {request_id} du client {client.id} "
                         f"(CPU: {cpu:.1f}, Mémoire: {memory:.1f}, Durée: {duration:.1f}s)")

        request_data = {
            "id": request_id,
            "client": client,
            "cpu": cpu,
            "memory": memory,
            "duration": duration,
            "dependencies": set(),
            "submit_time": time.time(),
            "graph_id": None,  # Pas associé à un graphe
            "level": None
        }

        # Envoyer la demande au système
        self.system_launcher.submit_request(
            client=client,
            request_id=request_id,
            cpu_required=cpu,
            memory_required=memory,
            estimated_duration=duration,
            dependencies=set()
        )

        # Enregistrer les métriques
        self.sent_requests.append(request_data)

    def _collect_final_results(self):
        """Collecte les résultats de toutes les demandes"""
        # Récupérer les demandes complétées
        completed = self.system_launcher.get_completed_requests()
        for request_id in completed:
            if not any(comp["id"] == request_id for comp in self.completed_requests):
                completion_time = time.time()

                # Trouver les données originales de la demande
                original_request = None
                for req in self.sent_requests:
                    if req["id"] == request_id:
                        original_request = req
                        break

                if original_request:
                    response_time = completion_time - original_request["submit_time"]
                    graph_id = original_request.get("graph_id")

                    completion_data = {
                        "id": request_id,
                        "completion_time": completion_time,
                        "response_time": response_time,
                        "graph_id": graph_id,
                        "level": original_request.get("level")
                    }

                    self.completed_requests.append(completion_data)

                    # Mettre à jour les métriques du graphe si applicable
                    if graph_id is not None:
                        self.graph_metrics[graph_id]["completed"] += 1
                        self.graph_metrics[graph_id]["response_times"].append(response_time)

        # Récupérer les demandes échouées
        failed = self.system_launcher.get_failed_requests()
        for request_id in failed:
            if not any(fail["id"] == request_id for fail in self.failed_requests):
                failure_time = time.time()

                # Trouver les données originales de la demande
                original_request = None
                for req in self.sent_requests:
                    if req["id"] == request_id:
                        original_request = req
                        break

                if original_request:
                    graph_id = original_request.get("graph_id")

                    failure_data = {
                        "id": request_id,
                        "failure_time": failure_time,
                        "reason": self.system_launcher.get_failure_reason(request_id),
                        "graph_id": graph_id,
                        "level": original_request.get("level")
                    }

                    self.failed_requests.append(failure_data)

                    # Mettre à jour les métriques du graphe si applicable
                    if graph_id is not None:
                        self.graph_metrics[graph_id]["failed"] += 1

        # Calculer le temps total d'exécution pour chaque graphe
        for graph_id, metrics in self.graph_metrics.items():
            completed_in_graph = [req for req in self.completed_requests if req.get("graph_id") == graph_id]
            if completed_in_graph:
                completion_times = [req["completion_time"] for req in completed_in_graph]
                start_time = metrics["start_time"]
                end_time = max(completion_times)
                metrics["completion_time"] = end_time - start_time

                # Calculer le chemin critique (temps le plus long entre tous les niveaux)
                level_times = {}
                for req in completed_in_graph:
                    level = req.get("level")
                    if level is not None:
                        if level not in level_times:
                            level_times[level] = []
                        level_times[level].append(req["completion_time"] - start_time)

                if level_times:
                    # Le temps maximum par niveau
                    max_level_times = {level: max(times) for level, times in level_times.items()}
                    metrics["critical_path"] = max(max_level_times.values())

    def generate_report(self):
        """Génère un rapport détaillé des résultats du test"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"logs/test_dependency_{timestamp}.log"

        with open(report_filename, "w") as report_file:
            # En-tête du rapport
            report_file.write(f"=== Rapport de test de dépendances complexes ===\n")
            report_file.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            report_file.write(f"Configuration: {self.num_graphs} graphes, {self.base_rps} req/s indépendantes\n\n")

            # Statistiques générales
            total_sent = len(self.sent_requests)
            total_completed = len(self.completed_requests)
            total_failed = len(self.failed_requests)

            graph_sent = sum(metrics["sent"] for metrics in self.graph_metrics.values())
            indep_sent = total_sent - graph_sent

            report_file.write(f"Demandes envoyées: {total_sent} "
                              f"({graph_sent} dans des graphes, {indep_sent} indépendantes)\n")
            report_file.write(f"Demandes complétées: {total_completed} ({total_completed / total_sent * 100:.2f}%)\n")
            report_file.write(f"Demandes échouées: {total_failed} ({total_failed / total_sent * 100:.2f}%)\n")
            report_file.write(f"Demandes en attente: {total_sent - total_completed - total_failed}\n\n")

            # Analyse par graphe
            report_file.write("=== Analyse des graphes de dépendances ===\n")

            for graph_id, metrics in sorted(self.graph_metrics.items()):
                depth = metrics["depth"]
                width = metrics["width"]
                total_nodes = metrics["total_nodes"]
                sent = metrics["sent"]
                completed = metrics["completed"]
                failed = metrics["failed"]

                report_file.write(
                    f"\n--- Graphe {graph_id} (profondeur: {depth}, largeur: {width}, nœuds: {total_nodes}) ---\n")

                report_file.write(f"Demandes envoyées: {sent}\n")
                report_file.write(f"Demandes complétées: {completed}")
                if sent > 0:
                    report_file.write(f" ({completed / sent * 100:.2f}%)")
                report_file.write("\n")

                report_file.write(f"Demandes échouées: {failed}")
                if sent > 0:
                    report_file.write(f" ({failed / sent * 100:.2f}%)")
                report_file.write("\n")

                # Temps d'exécution total du graphe
                completion_time = metrics.get("completion_time")
                if completion_time:
                    report_file.write(f"Temps d'exécution total: {completion_time:.2f}s\n")

                    # Temps moyen par niveau de profondeur
                    level_times = {}
                    for req in self.completed_requests:
                        if req.get("graph_id") == graph_id and req.get("level") is not None:
                            level = req.get("level")
                            if level not in level_times:
                                level_times[level] = []
                            level_times[level].append(req["response_time"])

                    if level_times:
                        report_file.write("Temps de réponse moyen par niveau:\n")
                        for level in sorted(level_times.keys()):
                            avg_time = sum(level_times[level]) / len(level_times[level])
                            report_file.write(f"  - Niveau {level}: {avg_time:.2f}s\n")

                    # Chemin critique
                    critical_path = metrics.get("critical_path")
                    if critical_path:
                        report_file.write(f"Temps du chemin critique: {critical_path:.2f}s\n")

                # Temps de réponse par demande
                response_times = metrics["response_times"]
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    max_response_time = max(response_times)
                    min_response_time = min(response_times)

                    report_file.write(f"Temps de réponse moyen: {avg_response_time:.2f}s\n")
                    report_file.write(f"Temps de réponse min: {min_response_time:.2f}s\n")
                    report_file.write(f"Temps de réponse max: {max_response_time:.2f}s\n")

            # Comparaison de performance: demandes dans graphes vs. indépendantes
            report_file.write("\n=== Comparaison de performances ===\n")

            # Temps de réponse des demandes dans des graphes
            graph_response_times = []
            for req in self.completed_requests:
                if req.get("graph_id") is not None:
                    graph_response_times.append(req["response_time"])

            # Temps de réponse des demandes indépendantes
            indep_response_times = []
            for req in self.completed_requests:
                if req.get("graph_id") is None:
                    indep_response_times.append(req["response_time"])

            if graph_response_times:
                avg_graph_time = sum(graph_response_times) / len(graph_response_times)
                report_file.write(f"Temps de réponse moyen des demandes dans des graphes: {avg_graph_time:.2f}s\n")

            if indep_response_times:
                avg_indep_time = sum(indep_response_times) / len(indep_response_times)
                report_file.write(f"Temps de réponse moyen des demandes indépendantes: {avg_indep_time:.2f}s\n")

            if graph_response_times and indep_response_times:
                ratio = avg_graph_time / avg_indep_time if avg_indep_time > 0 else float('inf')
                report_file.write(f"Ratio (graphe/indép.): {ratio:.2f}x\n")

                # Interprétation
                if ratio <= 1.2:
                    report_file.write("\nGestion efficace des dépendances: "
                                      "Les demandes dans des graphes sont traitées presque aussi "
                                      "rapidement que les demandes indépendantes.\n")
                elif ratio <= 2.0:
                    report_file.write("\nGestion acceptable des dépendances: "
                                      "Les demandes dans des graphes subissent un retard modéré "
                                      "par rapport aux demandes indépendantes.\n")
                else:
                    report_file.write("\nGestion problématique des dépendances: "
                                      "Les demandes dans des graphes sont significativement plus lentes "
                                      "que les demandes indépendantes.\n")

            # Analyse de la profondeur vs. temps d'exécution
            report_file.write("\n=== Impact de la profondeur ===\n")

            depth_times = {}
            for graph_id, metrics in self.graph_metrics.items():
                depth = metrics["depth"]
                completion_time = metrics.get("completion_time")
                if completion_time:
                    if depth not in depth_times:
                        depth_times[depth] = []
                    depth_times[depth].append(completion_time)

            if depth_times:
                report_file.write("Temps d'exécution moyen par profondeur:\n")
                for depth in sorted(depth_times.keys()):
                    avg_time = sum(depth_times[depth]) / len(depth_times[depth])
                    report_file.write(f"  - Profondeur {depth}: {avg_time:.2f}s\n")

                # Calculer un facteur d'augmentation par niveau
                depths = sorted(depth_times.keys())
                if len(depths) >= 2:
                    min_depth = min(depths)
                    max_depth = max(depths)
                    min_time = sum(depth_times[min_depth]) / len(depth_times[min_depth])
                    max_time = sum(depth_times[max_depth]) / len(depth_times[max_depth])
                    depth_diff = max_depth - min_depth
                    if depth_diff > 0 and min_time > 0:
                        increase_per_level = (max_time / min_time) ** (1 / depth_diff) - 1
                        report_file.write(
                            f"\nAugmentation moyenne du temps par niveau supplémentaire: {increase_per_level * 100:.2f}%\n")

            # Conclusion et recommandations
            report_file.write("\n=== Conclusion et recommandations ===\n")

            # Calculer le taux de réussite global des graphes
            total_graph_sent = sum(metrics["sent"] for metrics in self.graph_metrics.values())
            total_graph_completed = sum(metrics["completed"] for metrics in self.graph_metrics.values())
            graph_success_rate = total_graph_completed / total_graph_sent if total_graph_sent > 0 else 0

            if graph_success_rate >= 0.95:
                report_file.write("Le système gère efficacement les dépendances complexes, "
                                  "avec un taux de réussite élevé.\n")
                report_file.write("Recommandation: Maintenir l'algorithme actuel de gestion des dépendances.\n")
            elif graph_success_rate >= 0.8:
                report_file.write("Le système gère correctement la plupart des dépendances, "
                                  "mais montre des signes de stress sur les graphes complexes.\n")
                report_file.write("Recommandations:\n")
                report_file.write(
                    "1. Optimiser l'algorithme de tri topologique pour traiter plus efficacement les graphes profonds\n")
                report_file.write(
                    "2. Considérer une approche parallélisée pour les nœuds indépendants d'un même niveau\n")
                report_file.write("3. Améliorer la priorisation des nœuds sur le chemin critique\n")
            else:
                report_file.write(
                    "Le système rencontre des difficultés significatives avec les dépendances complexes.\n")
                report_file.write("Recommandations urgentes:\n")
                report_file.write("1. Revoir fondamentalement l'algorithme de gestion des dépendances\n")
                report_file.write("2. Mettre en place un mécanisme de détection précoce des cycles ou deadlocks\n")
                report_file.write("3. Prévoir une gestion de timeout pour éviter les attentes infinies\n")
                report_file.write("4. Fractionner les graphes profonds en sous-graphes plus gérables\n")

        self.logger.info(f"Rapport généré: {report_filename}")
        return report_filename