# config/production_config.py

"""
Configuration optimale pour le système multi-agents en production
Basée sur les résultats des tests de performance et dimensionnement professionnel.
"""

# Configuration principale du système
SYSTEM_CONFIG = {
    # Capacité maximale recommandée (avec marge de sécurité)
    "max_requests_per_second": 17,  # Basé sur vos tests réels

    # Gestion des ressources (augmentées pour supporter la charge)
    "cpu_pool_size": 500.0,  # Considérablement augmenté
    "memory_pool_size": 500.0,

    # Configuration des timeouts
    "request_timeout": 120,  # Augmenté pour gérer les pics
    "dependency_timeout": 300,  # 5 minutes pour dépendances complexes

    # Files d'attente - DIMENSIONNEMENT PROFESSIONNEL
    "vip_queue_size": 5000,  # Peut gérer ~5 min à charge max VIP
    "standard_queue_size": 50000,  # Peut gérer ~1h à charge max standard
    "priority_queue_size": 1000,  # File haute priorité d'urgence

    # Seuils d'alerte pour les files
    "vip_queue_alert_threshold": 1000,  # 20% de la capacité
    "standard_queue_alert_threshold": 10000,  # 20% de la capacité
    "vip_queue_critical_threshold": 2500,  # 50% de la capacité
    "standard_queue_critical_threshold": 25000,  # 50% de la capacité

    # Mécanisme de vieillissement optimisé
    "aging_factor": 0.3,  # Réduit pour éviter l'over-aging
    "aging_interval": 5,  # Plus fréquent pour meilleure réactivité
    "aging_max_boost": 200,  # Limite maximum du boost de priorité

    # Équilibrage de charge
    "load_balancer_check_interval": 15,  # Plus fréquent
    "server_timeout_threshold": 30,  # Plus strict
    "auto_scaling_enabled": True,
    "scale_up_threshold": 0.80,  # Déclencher scale-up à 80%
    "scale_down_threshold": 0.30,  # Déclencher scale-down à 30%

    # Monitoring avancé
    "monitoring_interval": 5,  # Monitoring plus fréquent
    "dashboard_update_interval": 2,  # Mise à jour dashboard plus rapide
    "metrics_retention_hours": 72,  # Garder 3 jours d'historique

    # Gestion des pics de charge
    "burst_protection_enabled": True,
    "burst_threshold": 25,  # req/s pour déclencher la protection
    "burst_max_duration": 60,  # secondes max de pic toléré
    "burst_recovery_factor": 0.7,  # Réduction temporaire d'acceptation
}

# Seuils d'alerte et d'intervention PROFESSIONNELS
ALERT_THRESHOLDS = {
    # Taux de réussite minimum acceptable
    "min_success_rate": 0.95,  # 95%
    "critical_success_rate": 0.85,  # 85% = critique

    # Temps de réponse maximum (basé sur vos résultats)
    "max_response_time_vip": 20.0,  # 20 secondes pour VIP
    "max_response_time_standard": 60.0,  # 60 secondes pour standard
    "critical_response_time_vip": 45.0,  # 45s = critique pour VIP
    "critical_response_time_standard": 120.0,  # 2min = critique pour std

    # Ratio d'équité (basé sur vos tests : ratio=0.93 est excellent)
    "max_equity_ratio": 2.0,  # Standard max 2x VIP
    "optimal_equity_ratio": 1.5,  # Objectif optimal

    # Utilisation des ressources
    "max_cpu_utilization": 0.85,  # 85% max
    "max_memory_utilization": 0.85,
    "critical_cpu_utilization": 0.95,  # 95% = critique
    "critical_memory_utilization": 0.95,

    # Throughput (basé sur vos capacités testées)
    "min_throughput_rps": 15,  # En dessous = alerte
    "optimal_throughput_rps": 17,  # Objectif optimal
    "max_throughput_rps": 20,  # Au-dessus = surcharge
}

# SCÉNARIOS DE TEST MULTIPLES (suggestion de votre ancien)
TEST_SCENARIOS = {
    # Scénario 1: Charge légère mais soutenue
    "light_sustained": {
        "duration": 1800,  # 30 minutes
        "base_rps": 3,
        "variation": 0.2,  # ±20% de variation
        "vip_ratio": 0.15,
        "dependency_ratio": 0.2,
        "expected_success_rate": 0.98,
        "max_response_time": 15.0
    },

    # Scénario 2: Charge normale métier
    "business_normal": {
        "duration": 900,  # 15 minutes
        "base_rps": 8,
        "variation": 0.3,
        "vip_ratio": 0.25,
        "dependency_ratio": 0.3,
        "expected_success_rate": 0.95,
        "max_response_time": 25.0
    },

    # Scénario 3: Pic métier (black friday, etc.)
    "business_peak": {
        "duration": 600,  # 10 minutes
        "base_rps": 15,
        "burst_rps": 25,
        "burst_frequency": 120,  # Pic toutes les 2 minutes
        "burst_duration": 30,
        "vip_ratio": 0.4,  # Plus de VIP pendant les pics
        "dependency_ratio": 0.4,
        "expected_success_rate": 0.90,
        "max_response_time": 45.0
    },

    # Scénario 4: Stress test - limite système
    "stress_test": {
        "duration": 300,  # 5 minutes
        "base_rps": 20,
        "max_rps": 35,
        "ramp_duration": 60,  # Montée progressive
        "vip_ratio": 0.3,
        "dependency_ratio": 0.5,
        "expected_success_rate": 0.75,  # Acceptable en stress
        "max_response_time": 120.0
    },

    # Scénario 5: Résilience - panne et récupération
    "resilience_test": {
        "duration": 900,  # 15 minutes
        "base_rps": 10,
        "failure_injection": True,
        "failure_duration": 60,  # Panne simulée de 1 minute
        "recovery_time": 180,  # Temps de récupération max
        "vip_ratio": 0.2,
        "dependency_ratio": 0.3,
        "expected_success_rate": 0.85,  # Avec panne incluse
    }
}

# DIMENSIONNEMENT PAR CHARGE (réponse à la question 100 vs 1000 requêtes)
LOAD_SCALABILITY_CONFIG = {
    # Configuration pour 100 requêtes
    "small_load": {
        "max_concurrent_requests": 100,
        "vip_queue_size": 500,
        "standard_queue_size": 2000,
        "cpu_pool_size": 50.0,
        "memory_pool_size": 50.0,
        "expected_avg_response_time": 15.0,
        "expected_success_rate": 0.98
    },

    # Configuration pour 1000 requêtes
    "medium_load": {
        "max_concurrent_requests": 1000,
        "vip_queue_size": 2000,
        "standard_queue_size": 8000,
        "cpu_pool_size": 200.0,
        "memory_pool_size": 200.0,
        "expected_avg_response_time": 15.0,  # MÊME PERFORMANCE!
        "expected_success_rate": 0.98  # MÊME PERFORMANCE!
    },

    # Configuration pour 10000 requêtes
    "large_load": {
        "max_concurrent_requests": 10000,
        "vip_queue_size": 5000,
        "standard_queue_size": 25000,
        "cpu_pool_size": 1000.0,
        "memory_pool_size": 1000.0,
        "expected_avg_response_time": 15.0,  # MÊME PERFORMANCE!
        "expected_success_rate": 0.98  # MÊME PERFORMANCE!
    }
}

# Configuration par environnement MISE À JOUR
ENVIRONMENT_CONFIGS = {
    "development": {
        "max_requests_per_second": 5,
        "vip_queue_size": 500,
        "standard_queue_size": 2000,
        "debug_mode": True,
        "log_level": "DEBUG",
        "enable_simulation": True,
        "cpu_pool_size": 50.0,
        "memory_pool_size": 50.0
    },

    "staging": {
        "max_requests_per_second": 12,
        "vip_queue_size": 2000,
        "standard_queue_size": 10000,
        "debug_mode": False,
        "log_level": "INFO",
        "enable_simulation": False,
        "cpu_pool_size": 200.0,
        "memory_pool_size": 200.0
    },

    "production": {
        "max_requests_per_second": 17,
        "vip_queue_size": 5000,
        "standard_queue_size": 50000,
        "debug_mode": False,
        "log_level": "WARNING",
        "enable_simulation": False,
        "enable_monitoring": True,
        "enable_alerts": True,
        "cpu_pool_size": 500.0,
        "memory_pool_size": 500.0,
        "auto_scaling_enabled": True
    }
}

# Tests de performance AMÉLIORÉS avec scénarios multiples
PERFORMANCE_TEST_CONFIG = {
    "constant_load": {
        "requests_per_second": 8,  # Basé sur vos résultats
        "duration": 600,  # 10 minutes
        "vip_ratio": 0.2,
        "dependency_ratio": 0.3,
        "expected_success_rate": 0.95
    },

    "increasing_load": {
        "initial_rps": 1,
        "max_rps": 20,  # Basé sur vos tests
        "increment": 1,
        "increment_interval": 30,
        "expected_stable_until": 17  # Vos résultats
    },

    "burst_load": {
        "base_rps": 5,
        "burst_rps": 25,  # Plus agressif
        "burst_duration": 45,
        "recovery_duration": 300,  # 5 minutes de récupération
        "expected_min_success_rate": 0.75
    },

    "dependency_complex": {
        "num_graphs": 20,  # Plus de graphes
        "base_rps": 5,
        "max_depth": 7,  # Dépendances plus profondes
        "max_width": 6,  # Graphes plus larges
        "expected_success_rate": 0.98
    },

    # NOUVEAU: Test de scalabilité
    "scalability_test": {
        "load_levels": [100, 500, 1000, 2500, 5000],
        "duration_per_level": 300,  # 5 minutes par niveau
        "expected_consistent_performance": True,
        "max_performance_degradation": 0.05  # 5% max
    }
}

# Configuration de récupération AMÉLIORÉE
RECOVERY_CONFIG = {
    # Conditions de déclenchement plus granulaires
    "trigger_conditions": {
        "success_rate_below": 0.90,
        "response_time_above": 60.0,
        "vip_queue_size_above": 2000,
        "standard_queue_size_above": 20000,
        "cpu_utilization_above": 0.90,
        "memory_utilization_above": 0.90,
        "throughput_below": 10  # req/s
    },

    # Actions de récupération graduées
    "recovery_actions": {
        "level_1": {  # Récupération douce
            "reduce_acceptance_rate": 0.9,
            "increase_aging_factor": 1.5,
            "prioritize_vip": True
        },
        "level_2": {  # Récupération modérée
            "reduce_acceptance_rate": 0.7,
            "increase_timeout": 1.5,
            "enable_emergency_completion": True,
            "pause_low_priority_tasks": True
        },
        "level_3": {  # Récupération d'urgence
            "reduce_acceptance_rate": 0.5,
            "vip_only_mode": True,
            "emergency_resource_allocation": True,
            "alert_administrators": True
        }
    },

    # Durées adaptatives
    "recovery_duration": {
        "level_1": 120,  # 2 minutes
        "level_2": 300,  # 5 minutes
        "level_3": 600  # 10 minutes
    },
    "cooldown_period": 300  # 5 minutes entre interventions
}


def get_config(environment="production", load_level="medium_load"):
    """
    Retourne la configuration pour l'environnement et la charge spécifiés.

    Args:
        environment (str): "development", "staging", ou "production"
        load_level (str): "small_load", "medium_load", ou "large_load"

    Returns:
        dict: Configuration complète adaptée
    """
    config = SYSTEM_CONFIG.copy()

    # Appliquer la configuration d'environnement
    config.update(ENVIRONMENT_CONFIGS.get(environment, {}))

    # Appliquer la configuration de charge
    load_config = LOAD_SCALABILITY_CONFIG.get(load_level, {})
    config.update(load_config)

    # Ajouter les configurations spécialisées
    config["alerts"] = ALERT_THRESHOLDS
    config["recovery"] = RECOVERY_CONFIG
    config["test_scenarios"] = TEST_SCENARIOS

    return config


def calculate_optimal_queue_sizes(max_rps, avg_processing_time=15.0, vip_ratio=0.2):
    """
    Calcule les tailles optimales des files d'attente basées sur la charge.

    Args:
        max_rps (int): Requests per second maximum
        avg_processing_time (float): Temps de traitement moyen en secondes
        vip_ratio (float): Proportion de clients VIP

    Returns:
        dict: Tailles de files recommandées
    """
    # Calcul basé sur la théorie des files d'attente (Little's Law)
    # L = λ × W (où L=longueur, λ=taux d'arrivée, W=temps d'attente)

    buffer_factor = 5  # Factor de sécurité

    vip_rps = max_rps * vip_ratio
    std_rps = max_rps * (1 - vip_ratio)

    # Taille pour gérer 10 minutes de pointe
    vip_queue_size = int(vip_rps * avg_processing_time * buffer_factor * 10)
    std_queue_size = int(std_rps * avg_processing_time * buffer_factor * 10)

    return {
        "vip_queue_size": max(vip_queue_size, 1000),  # Minimum 1000
        "standard_queue_size": max(std_queue_size, 5000),  # Minimum 5000
        "total_capacity": vip_queue_size + std_queue_size
    }


def validate_scalability_performance(results_100, results_1000):
    """
    Valide que les performances sont cohérentes entre différentes charges.

    Args:
        results_100: Résultats avec 100 requêtes
        results_1000: Résultats avec 1000 requêtes

    Returns:
        tuple: (bool, dict) - (Validation OK, Détails de comparaison)
    """
    comparison = {}
    issues = []

    # Comparer les temps de réponse
    time_100 = results_100.get("avg_response_time", 0)
    time_1000 = results_1000.get("avg_response_time", 0)
    time_ratio = time_1000 / max(time_100, 0.1)

    comparison["response_time_ratio"] = time_ratio
    if time_ratio > 1.2:  # Plus de 20% de dégradation
        issues.append(f"Dégradation temps de réponse: {time_ratio:.2f}x")

    # Comparer les taux de réussite
    success_100 = results_100.get("success_rate", 0)
    success_1000 = results_1000.get("success_rate", 0)
    success_diff = abs(success_100 - success_1000)

    comparison["success_rate_difference"] = success_diff
    if success_diff > 0.05:  # Plus de 5% de différence
        issues.append(f"Différence taux de réussite: {success_diff:.2%}")

    # Comparer l'équité
    equity_100 = results_100.get("equity_ratio", 1.0)
    equity_1000 = results_1000.get("equity_ratio", 1.0)
    equity_diff = abs(equity_100 - equity_1000)

    comparison["equity_difference"] = equity_diff
    if equity_diff > 0.3:  # Plus de 0.3 de différence
        issues.append(f"Différence ratio d'équité: {equity_diff:.2f}")

    return len(issues) == 0, comparison, issues