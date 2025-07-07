# config/enhanced_production_config.py
"""
Configuration améliorée pour le système multi-agents en production.
Basée sur les retours d'expérience et les bonnes pratiques industrielles.
"""

import os
from typing import Dict, Any

# Configuration principale du système (Dimensionnement réaliste)
SYSTEM_CONFIG = {
    # Capacités de traitement
    "max_requests_per_second": 15,  # Légèrement augmenté
    "burst_capacity_multiplier": 1.5,  # Capacité pic = 22.5 req/s

    # Pool de ressources (Dimensionnement plus réaliste)
    "cpu_pool_size": 500.0,  # 500 CPU virtuels
    "memory_pool_size": 1000.0,  # 1000 GB de RAM
    "storage_pool_size": 10000.0,  # 10 TB de stockage

    # Files d'attente (Tailles industrielles)
    "vip_queue_size": 10000,  # 10K pour VIP
    "standard_queue_size": 50000,  # 50K pour standard
    "priority_queue_size": 5000,  # 5K pour haute priorité
    "batch_queue_size": 100000,  # 100K pour traitement batch

    # Timeouts et délais
    "request_timeout": 120,  # 2 minutes max par demande
    "dependency_timeout": 300,  # 5 minutes pour dépendances
    "connection_timeout": 30,  # 30s pour connexions
    "health_check_timeout": 10,  # 10s pour health checks

    # Mécanisme de vieillissement optimisé
    "aging_factor": 0.3,  # Plus conservateur
    "aging_interval": 5,  # Recalcul toutes les 5 secondes
    "max_aging_boost": 3.0,  # Max 3x boost de priorité
    "aging_decay_rate": 0.95,  # Décroissance progressive

    # Équilibrage de charge avancé
    "load_balancer_algorithm": "weighted_round_robin",
    "load_balancer_check_interval": 15,
    "server_weight_adjustment": True,
    "auto_scaling_enabled": True,
    "scale_up_threshold": 0.80,  # Scale up à 80%
    "scale_down_threshold": 0.30,  # Scale down à 30%

    # Monitoring et observabilité
    "monitoring_interval": 10,
    "metrics_retention_days": 30,
    "dashboard_update_interval": 2,
    "enable_distributed_tracing": True,
    "log_sampling_rate": 0.1,  # Échantillonnage 10%

    # Gestion des pannes et récupération
    "circuit_breaker_enabled": True,
    "circuit_breaker_threshold": 0.5,  # 50% d'échecs
    "circuit_breaker_timeout": 60,  # 1 minute
    "retry_attempts": 3,
    "retry_backoff_factor": 2.0,
    "dead_letter_queue_enabled": True,

    # Sécurité
    "rate_limiting_enabled": True,
    "rate_limit_per_client": 100,  # 100 req/min par client
    "authentication_required": True,
    "audit_logging_enabled": True,
}

# Seuils d'alerte et métriques (Plus granulaires)
ALERT_THRESHOLDS = {
    # Performance
    "min_success_rate": 0.95,
    "max_response_time_p50": 5.0,  # Médiane
    "max_response_time_p95": 15.0,  # 95ème percentile
    "max_response_time_p99": 30.0,  # 99ème percentile
    "max_vip_response_time": 10.0,
    "max_standard_response_time": 25.0,

    # Équité
    "max_equity_ratio": 1.8,
    "min_vip_priority_ratio": 0.75,  # VIP traités 75% plus vite
    "max_starvation_time": 300,  # Max 5 min d'attente

    # Ressources
    "max_cpu_utilization": 0.85,
    "max_memory_utilization": 0.80,
    "max_storage_utilization": 0.90,
    "max_network_utilization": 0.75,

    # Files d'attente
    "vip_queue_warning": 1000,  # 10% de la capacité
    "vip_queue_critical": 5000,  # 50% de la capacité
    "standard_queue_warning": 10000,  # 20% de la capacité
    "standard_queue_critical": 35000,  # 70% de la capacité

    # Système
    "max_error_rate": 0.05,  # 5% d'erreurs max
    "min_throughput": 10,  # Min 10 req/s
    "max_latency_variance": 2.0,  # Variance max 2x
}

# Configuration par environnement
ENVIRONMENT_CONFIGS = {
    "development": {
        "max_requests_per_second": 5,
        "vip_queue_size": 100,
        "standard_queue_size": 500,
        "cpu_pool_size": 50.0,
        "memory_pool_size": 100.0,
        "debug_mode": True,
        "log_level": "DEBUG",
        "monitoring_interval": 5,
        "enable_simulation": True,
        "enable_distributed_tracing": False,
        "authentication_required": False,
    },

    "staging": {
        "max_requests_per_second": 10,
        "vip_queue_size": 2000,
        "standard_queue_size": 10000,
        "cpu_pool_size": 200.0,
        "memory_pool_size": 500.0,
        "debug_mode": False,
        "log_level": "INFO",
        "monitoring_interval": 10,
        "enable_simulation": False,
        "enable_distributed_tracing": True,
        "authentication_required": True,
    },

    "production": {
        "max_requests_per_second": 15,
        "vip_queue_size": 10000,
        "standard_queue_size": 50000,
        "cpu_pool_size": 500.0,
        "memory_pool_size": 1000.0,
        "debug_mode": False,
        "log_level": "WARNING",
        "monitoring_interval": 10,
        "enable_simulation": False,
        "enable_distributed_tracing": True,
        "authentication_required": True,
        "audit_logging_enabled": True,
        "auto_scaling_enabled": True,
    },

    "load_testing": {
        "max_requests_per_second": 25,  # Plus élevé pour les tests
        "vip_queue_size": 20000,
        "standard_queue_size": 100000,
        "cpu_pool_size": 1000.0,
        "memory_pool_size": 2000.0,
        "debug_mode": False,
        "log_level": "INFO",
        "monitoring_interval": 2,  # Plus fréquent
        "enable_simulation": False,
        "enable_distributed_tracing": True,
        "authentication_required": False,  # Simplifié pour les tests
        "circuit_breaker_enabled": False,  # Désactivé pour tests purs
    }
}

# Scénarios de tests de performance réorganisés
PERFORMANCE_SCENARIOS = {
    "scenario_1_baseline": {
        "name": "Performance de Base",
        "description": "Établit les performances de référence",
        "config": {
            "requests_per_second": 3,
            "duration": 180,
            "vip_ratio": 0.2,
            "dependency_ratio": 0.1
        },
        "success_criteria": {
            "min_success_rate": 0.98,
            "max_avg_response_time": 10.0,
            "max_vip_response_time": 5.0,
            "max_equity_ratio": 1.3
        }
    },

    "scenario_2_scalability": {
        "name": "Validation de Scalabilité",
        "description": "Teste la consistance sur différents volumes",
        "config": {
            "test_volumes": [100, 500, 1000, 2000, 5000],
            "requests_per_second": 5,
            "vip_ratio": 0.2,
            "dependency_ratio": 0.2
        },
        "success_criteria": {
            "max_performance_variance": 0.15,  # 15% de variance max
            "min_success_rate": 0.92,
            "consistency_required": True
        }
    },

    "scenario_3_load_spikes": {
        "name": "Résilience aux Pics",
        "description": "Teste la gestion des pics de charge",
        "config": {
            "base_rps": 3,
            "burst_rps": 12,
            "burst_duration": 30,
            "recovery_duration": 240,
            "vip_ratio": 0.3,
            "dependency_ratio": 0.2
        },
        "success_criteria": {
            "min_overall_success_rate": 0.80,
            "min_burst_success_rate": 0.65,
            "max_recovery_time": 180,
            "max_performance_degradation": 0.35
        }
    },

    "scenario_4_dependencies": {
        "name": "Gestion des Dépendances",
        "description": "Valide l'algorithme de tri topologique",
        "config": {
            "num_graphs": 15,
            "base_rps": 2,
            "max_depth": 6,
            "max_width": 5,
            "vip_ratio": 0.25,
            "complex_dependencies": True
        },
        "success_criteria": {
            "min_success_rate": 0.95,
            "max_dependency_overhead": 2.5,
            "no_deadlocks": True,
            "max_avg_response_time": 45.0
        }
    },

    "scenario_5_equity": {
        "name": "Équité VIP/Standard",
        "description": "Teste le mécanisme de vieillissement",
        "config": {
            "duration": 300,
            "requests_per_second": 6,
            "vip_ratio": 0.3,
            "aging_factor": 0.3,
            "dependency_ratio": 0.25
        },
        "success_criteria": {
            "min_success_rate": 0.90,
            "max_equity_ratio": 2.0,
            "min_vip_priority": 0.75,
            "max_standard_starvation": 0.05
        }
    },

    "scenario_6_saturation": {
        "name": "Saturation des Ressources",
        "description": "Teste le comportement en limite de capacité",
        "config": {
            "target_cpu_utilization": 0.90,
            "target_memory_utilization": 0.85,
            "duration": 300,
            "ramp_up_time": 90,
            "vip_ratio": 0.2,
            "dependency_ratio": 0.3
        },
        "success_criteria": {
            "min_success_rate": 0.70,
            "max_response_time": 60.0,
            "system_stability": True,
            "graceful_degradation": True
        }
    },

    "scenario_7_recovery": {
        "name": "Capacité de Récupération",
        "description": "Teste la récupération après incidents",
        "config": {
            "normal_rps": 4,
            "overload_rps": 20,
            "overload_duration": 60,
            "recovery_observation_time": 300,
            "vip_ratio": 0.25,
            "dependency_ratio": 0.2
        },
        "success_criteria": {
            "max_recovery_time": 180,
            "recovery_success_rate": 0.85,
            "no_permanent_degradation": True,
            "queue_stabilization": True
        }
    }
}

# Configuration de récupération et auto-healing
RECOVERY_CONFIG = {
    # Détection automatique des problèmes
    "auto_detection": {
        "success_rate_threshold": 0.85,
        "response_time_threshold": 45.0,
        "queue_size_threshold": 0.8,  # 80% de la capacité
        "resource_utilization_threshold": 0.90,
        "check_interval": 30  # secondes
    },

    # Actions de récupération graduées
    "recovery_actions": [
        {
            "level": 1,
            "name": "Optimisation légère",
            "actions": [
                "reduce_acceptance_rate:0.9",
                "increase_aging_factor:1.2",
                "prioritize_vip:enhanced"
            ]
        },
        {
            "level": 2,
            "name": "Limitation de charge",
            "actions": [
                "reduce_acceptance_rate:0.7",
                "increase_timeout:1.5",
                "enable_circuit_breaker",
                "defer_non_critical"
            ]
        },
        {
            "level": 3,
            "name": "Mode dégradé",
            "actions": [
                "reduce_acceptance_rate:0.5",
                "vip_only_mode",
                "emergency_completion",
                "scale_up_resources"
            ]
        }
    ],

    # Paramètres de récupération
    "recovery_timeouts": {
        "level_1_duration": 120,  # 2 minutes
        "level_2_duration": 300,  # 5 minutes
        "level_3_duration": 600,  # 10 minutes
        "cooldown_period": 900  # 15 minutes avant nouvelle intervention
    }
}

# Métriques de succès globales
GLOBAL_SUCCESS_CRITERIA = {
    # Performance minimale acceptable
    "min_overall_success_rate": 0.90,
    "max_overall_response_time": 20.0,
    "max_vip_response_time": 8.0,
    "max_standard_response_time": 30.0,

    # Équité et fairness
    "max_equity_ratio": 1.8,
    "min_vip_advantage": 0.6,  # VIP au moins 60% plus rapide
    "max_starvation_incidents": 0.02,  # Max 2% de famine

    # Scalabilité
    "min_linear_scalability": 0.8,  # 80% de scalabilité linéaire
    "max_scalability_overhead": 0.3,  # 30% d'overhead max

    # Résilience
    "max_recovery_time": 300,  # 5 minutes max
    "min_availability": 0.995,  # 99.5% de disponibilité
    "max_cascading_failures": 0.05  # 5% de pannes en cascade max
}

# Configuration AWS pour déploiement cloud
AWS_CONFIG = {
    # Infrastructure
    "regions": ["us-east-1", "eu-west-1", "ap-southeast-1"],
    "availability_zones": 3,

    # Instances EC2
    "instance_types": {
        "application": "c5.2xlarge",  # 8 vCPU, 16 GB RAM
        "database": "r5.xlarge",  # 4 vCPU, 32 GB RAM
        "cache": "r6g.large"  # 2 vCPU, 16 GB RAM
    },

    # Auto Scaling
    "auto_scaling": {
        "min_instances": 3,
        "max_instances": 20,
        "target_cpu_utilization": 70,
        "scale_up_cooldown": 300,
        "scale_down_cooldown": 600
    },

    # Load Balancer
    "load_balancer": {
        "type": "application",
        "scheme": "internet-facing",
        "health_check": {
            "path": "/health",
            "interval": 30,
            "timeout": 5,
            "healthy_threshold": 2,
            "unhealthy_threshold": 3
        }
    },

    # Monitoring et alertes
    "cloudwatch": {
        "custom_metrics": True,
        "detailed_monitoring": True,
        "log_retention_days": 30,
        "alerts": [
            "CPUUtilization > 80%",
            "ResponseTime > 10s",
            "ErrorRate > 5%",
            "QueueDepth > 1000"
        ]
    },

    # Coûts estimés (par mois)
    "cost_estimation": {
        "compute": 2500,  # USD
        "storage": 500,  # USD
        "network": 300,  # USD
        "monitoring": 200,  # USD
        "total_monthly": 3500  # USD
    }
}

# Fonctions utilitaires

def get_config(environment: str = "production") -> Dict[str, Any]:
    """
    Retourne la configuration complète pour l'environnement spécifié.

    Args:
        environment: "development", "staging", "production", ou "load_testing"

    Returns:
        Configuration complète avec tous les paramètres
    """
    # Configuration de base
    config = SYSTEM_CONFIG.copy()

    # Surcharge avec la configuration d'environnement
    env_config = ENVIRONMENT_CONFIGS.get(environment, {})
    config.update(env_config)

    # Ajouter les autres configurations
    config["alerts"] = ALERT_THRESHOLDS
    config["recovery"] = RECOVERY_CONFIG
    config["scenarios"] = PERFORMANCE_SCENARIOS
    config["success_criteria"] = GLOBAL_SUCCESS_CRITERIA
    config["aws"] = AWS_CONFIG
    config["environment"] = environment

    return config

def get_scenario_config(scenario_name: str) -> Dict[str, Any]:
    """
    Retourne la configuration d'un scénario spécifique.

    Args:
        scenario_name: Nom du scénario (ex: "scenario_1_baseline")

    Returns:
        Configuration du scénario
    """
    return PERFORMANCE_SCENARIOS.get(scenario_name, {})

def validate_environment_config(environment: str) -> bool:
    """
    Valide la configuration d'un environnement.

    Args:
        environment: Nom de l'environnement

    Returns:
        True si la configuration est valide
    """
    config = get_config(environment)

    # Vérifications de base
    required_keys = [
        "max_requests_per_second",
        "vip_queue_size",
        "standard_queue_size",
        "cpu_pool_size",
        "memory_pool_size"
    ]

    for key in required_keys:
        if key not in config or config[key] <= 0:
            return False

    # Vérifications de cohérence
    if config["vip_queue_size"] >= config["standard_queue_size"]:
        return False

    if config["max_requests_per_second"] > config["cpu_pool_size"] / 10:
        return False  # Ratio CPU/RPS trop faible

    return True

def calculate_recommended_resources(target_rps: int, vip_ratio: float = 0.2) -> Dict[str, Any]:
    """
    Calcule les ressources recommandées pour un débit cible.

    Args:
        target_rps: Débit cible en requêtes par seconde
        vip_ratio: Proportion de clients VIP

    Returns:
        Recommandations de ressources
    """
    # Formules basées sur l'expérience et les tests
    cpu_per_rps = 15  # 15 CPU virtuels par req/s
    memory_per_rps = 25  # 25 GB RAM par req/s

    # Facteur VIP (les VIP consomment plus de ressources)
    vip_factor = 1 + (vip_ratio * 0.5)

    recommendations = {
        "cpu_pool_size": target_rps * cpu_per_rps * vip_factor,
        "memory_pool_size": target_rps * memory_per_rps * vip_factor,
        "vip_queue_size": target_rps * 300,  # 5 min de buffer
        "standard_queue_size": target_rps * 1500,  # 25 min de buffer
        "estimated_monthly_cost": target_rps * 150,  # 150 USD par req/s/mois
        "recommended_instance_count": max(3, target_rps // 5)
    }

    return recommendations

# Validation de la configuration au chargement
if __name__ == "__main__":
    # Tests de validation
    environments = ["development", "staging", "production", "load_testing"]

    print("Validation des configurations d'environnement:")
    for env in environments:
        is_valid = validate_environment_config(env)
        status = "✅ Valide" if is_valid else "❌ Invalide"
        print(f"  {env}: {status}")

    # Test des recommandations de ressources
    print("\nRecommandations pour différents débits:")
    for rps in [5, 10, 15, 25]:
        reco = calculate_recommended_resources(rps)
        print(f"  {rps} req/s: {reco['cpu_pool_size']:.0f} CPU, "
              f"{reco['memory_pool_size']:.0f} GB RAM, "
              f"${reco['estimated_monthly_cost']:.0f}/mois")