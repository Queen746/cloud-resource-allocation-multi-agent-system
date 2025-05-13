import networkx as nx
from collections import defaultdict, deque
import logging


class TopologicalSorter:
    """
    Implémentation de l'algorithme de tri topologique pour gérer les dépendances
    entre les demandes de ressources. Utilise l'algorithme de Kahn pour le tri.
    """

    def __init__(self):
        """
        Initialise le trieur topologique.
        """
        self.logger = logging.getLogger("TopologicalSorter")
        self.cache = {}  # Cache pour stocker les résultats de tri précédents

    def topological_sort(self, requests):
        """
        Effectue un tri topologique des demandes en respectant leurs dépendances.

        Args:
            requests (dict): Dictionnaire de demandes indexé par ID

        Returns:
            list: Liste ordonnée des IDs de demandes respectant les dépendances
            None: Si un cycle est détecté (dépendances circulaires)
        """
        # Construire le graphe de dépendances
        graph = nx.DiGraph()

        # Ajouter tous les nœuds (demandes)
        for req_id in requests:
            graph.add_node(req_id)

        # Ajouter les arêtes (dépendances)
        for req_id, request in requests.items():
            for dep_id in request.get_dependencies():
                if dep_id in requests:  # Ne considérer que les dépendances valides
                    graph.add_edge(dep_id, req_id)  # La demande req_id dépend de dep_id

        # Vérifier s'il y a des cycles
        try:
            # Utiliser l'algorithme de détection de cycle de networkx
            cycles = list(nx.simple_cycles(graph))
            if cycles:
                self.logger.error(f"Cycle detected in dependencies: {cycles}")
                return None
        except nx.NetworkXNoCycle:
            pass  # Pas de cycle, c'est bon

        # Effectuer le tri topologique avec Kahn
        try:
            sorted_ids = list(nx.topological_sort(graph))
            self.logger.info(f"Topological sort result: {sorted_ids}")
            return sorted_ids
        except nx.NetworkXUnfeasible:
            self.logger.error("Unfeasible topological sort (possible cycle)")
            return None

    def kahn_algorithm(self, graph):
        """
        Implémentation manuelle de l'algorithme de Kahn pour le tri topologique.
        Utilisé comme alternative à l'implémentation NetworkX.

        Args:
            graph (dict): Graphe représenté comme un dictionnaire d'adjacence

        Returns:
            list: Liste ordonnée des nœuds respectant les dépendances
            None: Si un cycle est détecté
        """
        # Copier le graphe pour ne pas le modifier
        in_degree = defaultdict(int)
        graph_copy = defaultdict(list)

        # Calculer les degrés entrants et copier le graphe
        for u in graph:
            graph_copy[u] = list(graph[u])
            for v in graph[u]:
                in_degree[v] += 1

        # Initialiser avec les nœuds sans prédécesseurs
        queue = deque([u for u in graph if in_degree[u] == 0])
        sorted_result = []

        # Traiter tous les nœuds
        while queue:
            u = queue.popleft()
            sorted_result.append(u)

            for v in graph_copy[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        # Vérifier si tous les nœuds ont été visités
        if len(sorted_result) != len(graph):
            return None  # Cycle détecté

        return sorted_result

    def prioritize_independent_batches(self, requests, sorted_ids, priority_func):
        """
        Réorganise les demandes indépendantes au sein de chaque groupe
        par ordre de priorité décroissante.

        Args:
            requests (dict): Dictionnaire de demandes
            sorted_ids (list): Liste d'IDs ordonnés par topologie
            priority_func (callable): Fonction qui calcule la priorité d'une demande

        Returns:
            list: Liste ordonnée optimisée des IDs de demandes
        """
        if not sorted_ids:
            return []

        # Construire le graphe pour trouver les composants indépendants
        graph = nx.DiGraph()

        for req_id in requests:
            graph.add_node(req_id)

        for req_id, request in requests.items():
            for dep_id in request.get_dependencies():
                if dep_id in requests:
                    graph.add_edge(dep_id, req_id)

        # Trouver les niveaux (demandes pouvant être exécutées en parallèle)
        levels = []
        remaining = set(sorted_ids)

        while remaining:
            # Trouver les nœuds sans prédécesseurs dans le sous-graphe restant
            level = {n for n in remaining if not any(pred in remaining for pred in graph.predecessors(n))}
            if not level:
                break  # Devrait être impossible si le tri topologique est valide

            # Trier ce niveau par priorité
            sorted_level = sorted(level, key=lambda n: priority_func(requests[n]), reverse=True)

            levels.append(sorted_level)
            remaining -= level

        # Aplatir les niveaux
        result = []
        for level in levels:
            result.extend(level)

        return result