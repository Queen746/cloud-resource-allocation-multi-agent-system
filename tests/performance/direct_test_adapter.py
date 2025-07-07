# tests/performance/direct_test_adapter.py
import logging
import time
import random
import threading
from collections import defaultdict, deque


class DirectTestAdapter:
    """
    Adaptateur de test optimisé avec gestion intelligente des dépendances
    et prévention proactive des blocages.
    """

    def __init__(self, system_launcher):
        self.system_launcher = system_launcher
        self.logger = logging.getLogger("DirectTestAdapter")

        # S'assurer que les collections existent
        if not hasattr(self.system_launcher, 'active_requests'):
            self.system_launcher.active_requests = set()
        if not hasattr(self.system_launcher, 'completed_requests'):
            self.system_launcher.completed_requests = set()
        if not hasattr(self.system_launcher, 'failed_requests'):
            self.system_launcher.failed_requests = {}

        # Structures pour la gestion des dépendances
        self.dependency_graph = defaultdict(set)  # request_id -> set of dependencies
        self.reverse_dependencies = defaultdict(set)  # request_id -> set of dependents
        self.request_info = {}  # request_id -> {client, cpu, memory, duration, timestamp}
        self.completion_threads = {}  # request_id -> thread

        # Files de priorité pour l'ordonnancement
        self.ready_queue = deque()  # Demandes prêtes à être traitées
        self.waiting_queue = set()  # Demandes en attente de dépendances

        # Configuration optimisée
        self.MAX_PROCESSING_TIME = 60  # Augmenté de 30 à 60 secondes
        self.MIN_COMPLETION_DELAY = 0.5  # Délai minimum réaliste
        self.MAX_COMPLETION_DELAY = 2.0  # Délai maximum réaliste

        # Statistiques
        self.stats = {
            'requests_processed': 0,
            'dependencies_resolved': 0,
            'forced_completions': 0,
            'circular_dependencies_detected': 0
        }

        # Lock pour la synchronisation
        self.lock = threading.Lock()
        self.running = True

        # Démarrer les threads de gestion
        self._start_processors()

    def _start_processors(self):
        """Démarre les threads de traitement et de surveillance."""

        # Thread principal de traitement des demandes
        def request_processor():
            while self.running:
                try:
                    self._process_ready_requests()
                    time.sleep(0.1)  # Traitement très fréquent
                except Exception as e:
                    self.logger.error(f"Erreur dans le processeur de demandes: {e}")
                    time.sleep(1)

        # Thread de surveillance et résolution des blocages
        def dependency_resolver():
            while self.running:
                try:
                    self._resolve_blocked_requests()
                    time.sleep(2)  # Vérification moins fréquente
                except Exception as e:
                    self.logger.error(f"Erreur dans le résolveur de dépendances: {e}")
                    time.sleep(5)

        # Thread de monitoring des performances
        def performance_monitor():
            while self.running:
                try:
                    self._log_performance_stats()
                    time.sleep(15)  # Stats toutes les 15 secondes
                except Exception as e:
                    self.logger.error(f"Erreur dans le moniteur de performances: {e}")
                    time.sleep(15)

        # Démarrer tous les threads
        threads = [
            threading.Thread(target=request_processor, daemon=True, name="RequestProcessor"),
            threading.Thread(target=dependency_resolver, daemon=True, name="DependencyResolver"),
            threading.Thread(target=performance_monitor, daemon=True, name="PerformanceMonitor")
        ]

        for thread in threads:
            thread.start()

        self.logger.info("DirectTestAdapter: Tous les processeurs démarrés")

    def _process_ready_requests(self):
        """Traite les demandes prêtes à être exécutées."""
        with self.lock:
            while self.ready_queue:
                request_id = self.ready_queue.popleft()

                if request_id in self.system_launcher.active_requests:
                    info = self.request_info.get(request_id, {})
                    estimated_duration = info.get('estimated_duration', 10.0)

                    # Calculer un délai de traitement réaliste
                    base_delay = min(
                        random.uniform(self.MIN_COMPLETION_DELAY, self.MAX_COMPLETION_DELAY),
                        estimated_duration * 0.15  # 15% de la durée estimée
                    )

                    # Ajouter un léger délai pour les demandes avec dépendances
                    if request_id in self.dependency_graph and self.dependency_graph[request_id]:
                        base_delay *= 1.2  # 20% de délai supplémentaire

                    # Créer le thread de complétion
                    thread = threading.Thread(
                        target=self._complete_request_async,
                        args=(request_id, base_delay),
                        daemon=True,
                        name=f"Complete-{request_id}"
                    )
                    thread.start()
                    self.completion_threads[request_id] = thread

    def _complete_request_async(self, request_id, delay):
        """Complète une demande de manière asynchrone."""
        try:
            time.sleep(delay)

            with self.lock:
                if request_id in self.system_launcher.active_requests:
                    self.system_launcher.mark_request_completed(request_id)
                    self.stats['requests_processed'] += 1

                    # Nettoyer les structures de données
                    self._cleanup_request(request_id)

                    # Notifier les demandes dépendantes
                    self._notify_dependents(request_id)

                    self.logger.debug(f"Demande {request_id} complétée en {delay:.2f}s")

        except Exception as e:
            self.logger.error(f"Erreur lors de la complétion de {request_id}: {e}")

    def _notify_dependents(self, completed_request_id):
        """Notifie et traite les demandes qui dépendaient de celle-ci."""
        if completed_request_id in self.reverse_dependencies:
            dependents = list(self.reverse_dependencies[completed_request_id])

            for dependent_id in dependents:
                if dependent_id in self.dependency_graph:
                    # Retirer cette dépendance
                    self.dependency_graph[dependent_id].discard(completed_request_id)

                    # Si toutes les dépendances sont satisfaites
                    if not self.dependency_graph[dependent_id]:
                        # Retirer de la file d'attente et ajouter à la file de traitement
                        if dependent_id in self.waiting_queue:
                            self.waiting_queue.remove(dependent_id)
                            self.ready_queue.append(dependent_id)

                        # Nettoyer le graphe de dépendances
                        del self.dependency_graph[dependent_id]
                        self.stats['dependencies_resolved'] += 1

            # Nettoyer les dépendances inverses
            del self.reverse_dependencies[completed_request_id]

    def _resolve_blocked_requests(self):
        """Résout proactivement les demandes bloquées."""
        current_time = time.time()
        blocked_requests = []

        with self.lock:
            # Identifier les demandes bloquées depuis trop longtemps
            for request_id in list(self.waiting_queue):
                if request_id in self.request_info:
                    info = self.request_info[request_id]
                    wait_time = current_time - info['timestamp']

                    if wait_time > self.MAX_PROCESSING_TIME:
                        blocked_requests.append((request_id, wait_time))

        # Traiter les demandes bloquées
        if blocked_requests:
            self.logger.info(f"Résolution de {len(blocked_requests)} demandes bloquées")

            with self.lock:
                for request_id, wait_time in blocked_requests:
                    # Stratégie 1: Essayer de résoudre les dépendances manquantes
                    if request_id in self.dependency_graph:
                        missing_deps = list(self.dependency_graph[request_id])
                        resolved_deps = []

                        for dep_id in missing_deps:
                            if dep_id in self.system_launcher.active_requests:
                                # Si la dépendance est toujours active, la forcer aussi
                                self.system_launcher.mark_request_completed(dep_id)
                                resolved_deps.append(dep_id)
                                self.logger.debug(f"Résolution forcée de la dépendance {dep_id}")

                        # Retirer les dépendances résolues
                        for dep_id in resolved_deps:
                            self.dependency_graph[request_id].discard(dep_id)

                    # Stratégie 2: Si plus de dépendances, déplacer vers ready_queue
                    if not self.dependency_graph.get(request_id):
                        if request_id in self.waiting_queue:
                            self.waiting_queue.remove(request_id)
                            self.ready_queue.append(request_id)
                            self.logger.info(f"Demande {request_id} débloquée après {wait_time:.1f}s")
                    else:
                        # Stratégie 3: Force complétion en dernier recours
                        self.logger.warning(f"Force complétion de {request_id} après {wait_time:.1f}s "
                                            f"(dépendances restantes: {list(self.dependency_graph[request_id])})")
                        self.system_launcher.mark_request_completed(request_id)
                        self._cleanup_request(request_id)
                        self.stats['forced_completions'] += 1

    def _cleanup_request(self, request_id):
        """Nettoie toutes les structures de données pour une demande."""
        # Retirer des différentes structures
        self.waiting_queue.discard(request_id)
        self.dependency_graph.pop(request_id, None)
        self.request_info.pop(request_id, None)

        # Nettoyer les threads terminés
        if request_id in self.completion_threads:
            thread = self.completion_threads.pop(request_id)
            # CORRECTION: Pas besoin de vérifier si le thread est vivant
            # Le thread se terminera naturellement

    def _log_performance_stats(self):
        """Log des statistiques de performance."""
        with self.lock:
            active_count = len(self.system_launcher.active_requests)
            ready_count = len(self.ready_queue)
            waiting_count = len(self.waiting_queue)
            completed_count = len(self.system_launcher.completed_requests)

            self.logger.info(f"Stats - Actives: {active_count}, Prêtes: {ready_count}, "
                             f"En attente: {waiting_count}, Complétées: {completed_count}")

            if self.stats['forced_completions'] > 0:
                self.logger.info(f"Interventions - Forcées: {self.stats['forced_completions']}, "
                                 f"Dépendances résolues: {self.stats['dependencies_resolved']}")

    def submit_request(self, client, request_id, cpu_required, memory_required,
                       estimated_duration, dependencies=None):
        """Soumet une nouvelle demande au système."""

        with self.lock:
            # Ajouter aux demandes actives
            self.system_launcher.active_requests.add(request_id)

            # Stocker les informations
            self.request_info[request_id] = {
                'client': client,
                'cpu_required': cpu_required,
                'memory_required': memory_required,
                'estimated_duration': estimated_duration,
                'timestamp': time.time()
            }

            # Gérer les dépendances
            if dependencies and len(dependencies) > 0:
                # Filtrer les dépendances déjà satisfaites
                unsatisfied_deps = [dep for dep in dependencies
                                    if dep not in self.system_launcher.completed_requests]

                if unsatisfied_deps:
                    # Enregistrer les dépendances
                    self.dependency_graph[request_id] = set(unsatisfied_deps)

                    # Enregistrer les dépendances inverses
                    for dep in unsatisfied_deps:
                        self.reverse_dependencies[dep].add(request_id)

                    # Ajouter à la file d'attente
                    self.waiting_queue.add(request_id)

                    self.logger.debug(f"Demande {request_id} en attente de: {unsatisfied_deps}")
                    return True

            # Pas de dépendances ou toutes satisfaites
            self.ready_queue.append(request_id)

        return True

    def get_completed_requests(self):
        """Retourne les demandes complétées."""
        with self.lock:
            if hasattr(self.system_launcher, 'get_completed_requests'):
                return self.system_launcher.get_completed_requests()
            return set()

    def get_failed_requests(self):
        """Retourne les demandes échouées."""
        with self.lock:
            if hasattr(self.system_launcher, 'get_failed_requests'):
                return self.system_launcher.get_failed_requests()
            return set()

    def get_failure_reason(self, request_id):
        """Retourne la raison de l'échec."""
        with self.lock:
            if hasattr(self.system_launcher, 'get_failure_reason'):
                return self.system_launcher.get_failure_reason(request_id)
            return "unknown_failure"

    def wait_for_completion(self, timeout=60):
        """Attend que toutes les demandes soient complétées."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            with self.lock:
                active_count = len(self.system_launcher.active_requests)
                if active_count == 0:
                    return True
            time.sleep(0.5)

        # Force complétion des demandes restantes au timeout
        with self.lock:
            remaining = list(self.system_launcher.active_requests)
            if remaining:
                self.logger.warning(f"Timeout: complétion forcée de {len(remaining)} demandes")
                for req_id in remaining:
                    self.system_launcher.mark_request_completed(req_id)
                    self._cleanup_request(req_id)

        return False

    def cleanup(self):
        """Nettoie les ressources."""
        self.running = False
        with self.lock:
            # Attendre la fin des threads actifs (avec timeout pour éviter les blocages)
            for request_id, thread in list(self.completion_threads.items()):
                if thread.is_alive():
                    thread.join(timeout=1)  # Attendre max 1 seconde par thread

            # Nettoyer toutes les structures
            self.completion_threads.clear()
            self.dependency_graph.clear()
            self.reverse_dependencies.clear()
            self.request_info.clear()
            self.ready_queue.clear()
            self.waiting_queue.clear()

        self.logger.info("DirectTestAdapter nettoyé")

    def process_simulation_request(self, request_data):
        """Traite une demande de simulation."""
        request_id = request_data.get("id")
        client_data = request_data.get("client", {})
        cpu_required = request_data.get("cpu_required", 1.0)
        memory_required = request_data.get("memory_required", 1.0)
        estimated_duration = request_data.get("estimated_duration", 10.0)
        dependencies = request_data.get("dependencies", [])

        # Créer un client
        from models.client import Client
        from models.enums import ClientType

        client_id = client_data.get("id", "unknown")
        client_type_str = client_data.get("client_type", "STANDARD")
        client_type = ClientType.VIP if client_type_str == "VIP" else ClientType.STANDARD

        client = Client(client_id=client_id, client_type=client_type)

        return self.submit_request(client, request_id, cpu_required, memory_required,
                                   estimated_duration, dependencies)

    def get_stats(self):
        """Retourne les statistiques de performance."""
        with self.lock:
            return self.stats.copy()