import logging
import time
import uuid
import random
import threading


class AWSResourceSimulator:
    """
    Simulateur des ressources AWS pour démonstration.
    """

    def __init__(self):
        """Initialise le simulateur."""
        self.instances = {}  # {instance_id: instance_info}
        self.load_balancers = {}  # {lb_id: lb_info}
        self.auto_scaling_groups = {}  # {asg_id: asg_info}

        self.costs = {
            "t3.small": 0.0208,  # $/heure
            "t3.medium": 0.0416,
            "t3.large": 0.0832,
            "load_balancer": 0.025,
            "auto_scaling": 0.01
        }

        self.start_time = time.time()
        self.end_time = None

        # Configuration du logger
        self.logger = logging.getLogger("AWSSimulator")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def create_instance(self, instance_type, name=None):
        """Crée une nouvelle instance AWS simulée."""
        instance_id = f"i-{uuid.uuid4().hex[:8]}"

        self.instances[instance_id] = {
            "id": instance_id,
            "type": instance_type,
            "name": name or f"instance-{instance_id}",
            "state": "pending",
            "creation_time": time.time()
        }

        self.logger.info(f"Instance {instance_id} ({instance_type}) créée")

        # Démarrer l'instance en arrière-plan (thread)
        threading.Thread(target=self._run_instance_start, args=(instance_id,)).start()

        return self.instances[instance_id]

    def _run_instance_start(self, instance_id):
        """Exécute le démarrage d'instance dans un thread"""
        time.sleep(2)  # Simuler un délai de démarrage
        if instance_id in self.instances:
            self.instances[instance_id]["state"] = "running"
            self.logger.info(f"Instance {instance_id} démarrée")

    def terminate_instance(self, instance_id):
        """Termine une instance existante."""
        if instance_id not in self.instances:
            return False

        self.instances[instance_id]["state"] = "terminating"
        self.logger.info(f"Instance {instance_id} en cours de terminaison")

        # Terminer l'instance en arrière-plan
        threading.Thread(target=self._run_instance_termination, args=(instance_id,)).start()

        return True

    def _run_instance_termination(self, instance_id):
        """Exécute la terminaison d'instance dans un thread"""
        time.sleep(1)  # Simuler un délai de terminaison
        if instance_id in self.instances:
            self.instances[instance_id]["state"] = "terminated"
            self.logger.info(f"Instance {instance_id} terminée")

    def create_load_balancer(self, name, instances):
        """Crée un load balancer simulé."""
        lb_id = f"lb-{uuid.uuid4().hex[:8]}"

        # Créer le load balancer
        self.load_balancers[lb_id] = {
            "id": lb_id,
            "name": name,
            "state": "pending",
            "instances": [i["id"] for i in instances if isinstance(i, dict) and "id" in i],
            "creation_time": time.time()
        }

        self.logger.info(f"Load Balancer {lb_id} ({name}) créé")

        # Démarrer le load balancer en arrière-plan (thread)
        threading.Thread(target=self._run_lb_activation, args=(lb_id,)).start()

        return self.load_balancers[lb_id]

    def _run_lb_activation(self, lb_id):
        """Active un load balancer en mode synchrone (pour les threads)"""
        time.sleep(2)  # Simuler un délai d'activation
        if lb_id in self.load_balancers:
            self.load_balancers[lb_id]["state"] = "active"
            self.logger.info(f"Load Balancer {lb_id} activé")

    def create_auto_scaling_group(self, name, instance_type, min_size, max_size, desired_capacity):
        """Crée un Auto Scaling Group simulé."""
        asg_id = f"asg-{uuid.uuid4().hex[:8]}"

        # Créer l'ASG
        self.auto_scaling_groups[asg_id] = {
            "id": asg_id,
            "name": name,
            "instance_type": instance_type,
            "min_size": min_size,
            "max_size": max_size,
            "desired_capacity": desired_capacity,
            "instances": [],
            "state": "pending",
            "creation_time": time.time()
        }

        self.logger.info(f"Auto Scaling Group {asg_id} ({name}) créé")

        # Initialiser l'ASG en arrière-plan (thread)
        threading.Thread(target=self._run_asg_initialization, args=(asg_id,)).start()

        return self.auto_scaling_groups[asg_id]

    def _run_asg_initialization(self, asg_id):
        """Initialise un Auto Scaling Group en mode synchrone (pour les threads)"""
        if asg_id not in self.auto_scaling_groups:
            return

        asg = self.auto_scaling_groups[asg_id]
        time.sleep(2)  # Simuler un délai d'initialisation

        # Créer les instances initiales
        for i in range(asg["desired_capacity"]):
            instance_id = f"i-asg-{uuid.uuid4().hex[:8]}"

            # Créer l'instance
            self.instances[instance_id] = {
                "id": instance_id,
                "type": asg["instance_type"],
                "name": f"{asg['name']}-{i + 1}",
                "state": "running",
                "creation_time": time.time(),
                "asg_id": asg_id
            }

            # Ajouter l'instance à l'ASG
            asg["instances"].append(instance_id)

        # Activer l'ASG
        asg["state"] = "active"
        self.logger.info(f"Auto Scaling Group {asg_id} initialisé avec {asg['desired_capacity']} instances")

    def scale_asg(self, asg_id, desired_capacity):
        """Modifie la capacité désirée d'un Auto Scaling Group."""
        if asg_id not in self.auto_scaling_groups:
            return False

        asg = self.auto_scaling_groups[asg_id]
        old_capacity = asg["desired_capacity"]

        # Vérifier les limites
        if desired_capacity < asg["min_size"] or desired_capacity > asg["max_size"]:
            return False

        asg["desired_capacity"] = desired_capacity
        self.logger.info(f"Auto Scaling Group {asg_id} redimensionné de {old_capacity} à {desired_capacity}")

        # Ajuster le nombre d'instances
        threading.Thread(target=self._run_asg_scaling, args=(asg_id, old_capacity)).start()

        return True

    def _run_asg_scaling(self, asg_id, old_capacity):
        """Exécute le scaling d'un ASG dans un thread"""
        if asg_id not in self.auto_scaling_groups:
            return

        asg = self.auto_scaling_groups[asg_id]
        new_capacity = asg["desired_capacity"]

        if new_capacity > old_capacity:
            # Scale out (ajouter des instances)
            for i in range(old_capacity, new_capacity):
                instance_id = f"i-asg-{uuid.uuid4().hex[:8]}"

                # Créer l'instance
                self.instances[instance_id] = {
                    "id": instance_id,
                    "type": asg["instance_type"],
                    "name": f"{asg['name']}-{i + 1}",
                    "state": "pending",
                    "creation_time": time.time(),
                    "asg_id": asg_id
                }

                # Ajouter l'instance à l'ASG
                asg["instances"].append(instance_id)

                # Démarrer l'instance
                time.sleep(1)
                self.instances[instance_id]["state"] = "running"

                self.logger.info(f"Instance {instance_id} ajoutée à l'ASG {asg_id}")

        elif new_capacity < old_capacity:
            # Scale in (supprimer des instances)
            for i in range(old_capacity - new_capacity):
                if not asg["instances"]:
                    break

                # Prendre la dernière instance
                instance_id = asg["instances"].pop()

                if instance_id in self.instances:
                    self.instances[instance_id]["state"] = "terminating"
                    self.logger.info(f"Instance {instance_id} retirée de l'ASG {asg_id}")

                    # Terminer l'instance après un petit délai
                    time.sleep(1)
                    if instance_id in self.instances:
                        self.instances[instance_id]["state"] = "terminated"

    def simulate_load(self, duration, interval=30):
        """
        Simule une charge variable sur les ASGs pour une durée donnée.

        Args:
            duration (int): Durée de la simulation en secondes
            interval (int): Intervalle entre les changements de charge en secondes
        """
        end_time = time.time() + duration

        def run_simulation():
            while time.time() < end_time:
                for asg_id, asg in list(self.auto_scaling_groups.items()):
                    # Simuler une charge variable
                    load_factor = random.uniform(0.5, 1.5)
                    desired_capacity = min(
                        asg["max_size"],
                        max(
                            asg["min_size"],
                            int(asg["desired_capacity"] * load_factor)
                        )
                    )

                    # Appliquer la nouvelle capacité
                    if desired_capacity != asg["desired_capacity"]:
                        self.scale_asg(asg_id, desired_capacity)

                # Attendre le prochain intervalle
                time.sleep(interval)

        # Démarrer la simulation dans un thread séparé
        threading.Thread(target=run_simulation).start()

    def get_status_json(self):
        """
        Retourne les informations de statut pour l'API.

        Returns:
            dict: Un dictionnaire avec les informations de statut
        """
        # Filtrer les instances en cours d'exécution
        running_instances = {
            k: v for k, v in self.instances.items()
            if v["state"] == "running"
        }

        # Filtrer les ASGs actifs
        active_asgs = {
            k: v for k, v in self.auto_scaling_groups.items()
            if v["state"] == "active"
        }

        # Calculer les coûts
        uptime_hours = (time.time() - self.start_time) / 3600

        total_cost = 0.0
        for instance in self.instances.values():
            if instance["state"] in ["running", "terminated"]:
                instance_uptime = (
                                      time.time() - instance["creation_time"]
                                      if instance["state"] == "running"
                                      else instance.get("termination_time", time.time()) - instance["creation_time"]
                                  ) / 3600

                instance_cost = instance_uptime * self.costs.get(instance["type"], 0.02)
                total_cost += instance_cost

        # Ajouter le coût des load balancers
        for lb in self.load_balancers.values():
            if lb["state"] in ["active", "deleted"]:
                lb_uptime = (
                                time.time() - lb["creation_time"]
                                if lb["state"] == "active"
                                else lb.get("deletion_time", time.time()) - lb["creation_time"]
                            ) / 3600

                lb_cost = lb_uptime * self.costs["load_balancer"]
                total_cost += lb_cost

        # Ajouter le coût des ASGs
        for asg in self.auto_scaling_groups.values():
            if asg["state"] in ["active", "deleted"]:
                asg_uptime = (
                                 time.time() - asg["creation_time"]
                                 if asg["state"] == "active"
                                 else asg.get("deletion_time", time.time()) - asg["creation_time"]
                             ) / 3600

                asg_cost = asg_uptime * self.costs["auto_scaling"]
                total_cost += asg_cost

        return {
            "instances": running_instances,
            "auto_scaling_groups": active_asgs,
            "load_balancers": {k: v for k, v in self.load_balancers.items() if v["state"] == "active"},
            "uptime": int(time.time() - self.start_time),
            "total_cost": round(total_cost, 2)
        }