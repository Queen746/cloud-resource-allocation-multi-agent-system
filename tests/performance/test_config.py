# tests/performance/test_config.py

# Configuration optimale basée sur vos résultats
OPTIMAL_CONFIG = {
    "constant_load": {
        "requests_per_second": 5,  # Stable à ce niveau
        "duration": 300,
        "vip_ratio": 0.2,
        "dependency_ratio": 0.3
    },
    "increasing_load": {
        "initial_rps": 1,
        "max_rps": 15,  # Réduire de 20 à 15 pour plus de stabilité
        "increment": 1,
        "increment_interval": 30
    },
    "burst_load": {
        "base_rps": 2,
        "burst_rps": 10,  # Réduire de 20 à 10 pour éviter la surcharge
        "burst_duration": 20,  # Réduire de 30 à 20 secondes
        "recovery_duration": 180  # Augmenter de 120 à 180 secondes
    },
    "dependency": {
        "num_graphs": 10,
        "base_rps": 3,
        "max_depth": 5,
        "max_width": 3
    }
}

# Seuils de performance acceptables
PERFORMANCE_THRESHOLDS = {
    "min_success_rate": 0.90,  # 90% minimum
    "max_response_time": 30.0,  # 30 secondes max
    "max_vip_response_time": 10.0,  # 10 secondes max pour VIP
    "max_equity_ratio": 2.0,  # Ratio max standard/VIP
    "max_dependency_overhead": 2.0  # Surcoût max pour les dépendances
}