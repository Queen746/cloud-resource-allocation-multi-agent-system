# tests/performance/scalability_test.py
"""
Test de scalabilité pour valider la consistance des performances
à différents volumes de requêtes.
"""

import logging
import time
from pathlib import Path
from datetime import datetime


class ScalabilityTest:
    """Test de scalabilité multi-volumes."""

    def __init__(self, test_adapter, target_volume, requests_per_second,
                 duration_seconds, vip_ratio=0.2, dependency_ratio=0.2):
        self.test_adapter = test_adapter
        self.target_volume = target_volume
        self.requests_per_second = requests_per_second
        self.duration_seconds = duration_seconds
        self.vip_ratio = vip_ratio
        self.dependency_ratio = dependency_ratio
        self.logger = logging.getLogger("ScalabilityTest")

    def run(self):
        """Exécute le test de scalabilité."""
        # Utiliser le test de charge constante existant
        from tests.performance.constant_load_test import ConstantLoadTest

        test = ConstantLoadTest(
            test_adapter=self.test_adapter,
            requests_per_second=self.requests_per_second,
            duration_seconds=self.duration_seconds,
            vip_ratio=self.vip_ratio,
            dependency_ratio=self.dependency_ratio
        )

        return test.run()


# tests/performance/equity_test.py
"""
Test d'équité pour valider le mécanisme de vieillissement
entre clients VIP et Standard.
"""

import logging
import time
from pathlib import Path
from datetime import datetime


class EquityTest:
    """Test d'équité VIP/Standard."""

    def __init__(self, test_adapter, duration_seconds, requests_per_second,
                 vip_ratio=0.3, aging_factor=0.3, dependency_ratio=0.25):
        self.test_adapter = test_adapter
        self.duration_seconds = duration_seconds
        self.requests_per_second = requests_per_second
        self.vip_ratio = vip_ratio
        self.aging_factor = aging_factor
        self.dependency_ratio = dependency_ratio
        self.logger = logging.getLogger("EquityTest")

    def run(self):
        """Exécute le test d'équité."""
        # Utiliser le test de charge constante avec focus sur l'équité
        from tests.performance.constant_load_test import ConstantLoadTest

        test = ConstantLoadTest(
            test_adapter=self.test_adapter,
            requests_per_second=self.requests_per_second,
            duration_seconds=self.duration_seconds,
            vip_ratio=self.vip_ratio,
            dependency_ratio=self.dependency_ratio
        )

        return test.run()


# tests/performance/saturation_test.py
"""
Test de saturation des ressources pour tester le comportement
du système en limite de capacité.
"""

import logging
import time
from pathlib import Path
from datetime import datetime


class SaturationTest:
    """Test de saturation des ressources."""

    def __init__(self, test_adapter, target_cpu_utilization, target_memory_utilization,
                 duration_seconds, ramp_up_time=60, vip_ratio=0.2, dependency_ratio=0.3):
        self.test_adapter = test_adapter
        self.target_cpu_utilization = target_cpu_utilization
        self.target_memory_utilization = target_memory_utilization
        self.duration_seconds = duration_seconds
        self.ramp_up_time = ramp_up_time
        self.vip_ratio = vip_ratio
        self.dependency_ratio = dependency_ratio
        self.logger = logging.getLogger("SaturationTest")

    def run(self):
        """Exécute le test de saturation."""
        # Utiliser un test de charge progressive
        from tests.performance.increasing_load_test import IncreasingLoadTest

        test = IncreasingLoadTest(
            test_adapter=self.test_adapter,
            initial_rps=1,
            max_rps=20,  # RPS élevé pour saturation
            increment=2,
            increment_interval=self.ramp_up_time // 10,
            vip_ratio=self.vip_ratio,
            dependency_ratio=self.dependency_ratio
        )

        return test.run()


# tests/performance/recovery_test.py
"""
Test de capacité de récupération pour valider la récupération
du système après des incidents ou surcharges.
"""

import logging
import time
from pathlib import Path
from datetime import datetime


class RecoveryTest:
    """Test de capacité de récupération."""

    def __init__(self, test_adapter, normal_rps, overload_rps, overload_duration,
                 recovery_observation_time, vip_ratio=0.25, dependency_ratio=0.2):
        self.test_adapter = test_adapter
        self.normal_rps = normal_rps
        self.overload_rps = overload_rps
        self.overload_duration = overload_duration
        self.recovery_observation_time = recovery_observation_time
        self.vip_ratio = vip_ratio
        self.dependency_ratio = dependency_ratio
        self.logger = logging.getLogger("RecoveryTest")

    def run(self):
        """Exécute le test de récupération."""
        # Simuler un test de pic suivi d'observation de récupération
        from tests.performance.burst_load_test import BurstLoadTest

        test = BurstLoadTest(
            test_adapter=self.test_adapter,
            base_rps=self.normal_rps,
            burst_rps=self.overload_rps,
            burst_duration=self.overload_duration,
            recovery_duration=self.recovery_observation_time,
            vip_ratio=self.vip_ratio,
            dependency_ratio=self.dependency_ratio
        )

        return test.run()


# tests/performance/test_adapter.py (version simplifiée si manquante)
"""
Adaptateur de test pour interfacer avec le système multi-agents réel.
"""

import logging


class TestAdapter:
    """Adaptateur pour interfacer les tests avec le système réel."""

    def __init__(self, system_launcher):
        self.system_launcher = system_launcher
        self.logger = logging.getLogger("TestAdapter")

    def submit_request(self, client, request_id, cpu_required, memory_required,
                       estimated_duration, dependencies=None):
        """Soumet une demande au système."""
        return self.system_launcher.submit_request(
            client, request_id, cpu_required, memory_required,
            estimated_duration, dependencies
        )

    def get_completed_requests(self):
        """Récupère les demandes complétées."""
        return self.system_launcher.get_completed_requests()

    def get_failed_requests(self):
        """Récupère les demandes échouées."""
        return self.system_launcher.get_failed_requests()

    def get_failure_reason(self, request_id):
        """Récupère la raison de l'échec d'une demande."""
        return self.system_launcher.get_failure_reason(request_id)