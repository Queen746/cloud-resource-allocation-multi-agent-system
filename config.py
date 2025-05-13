"""
Configuration globale pour le système multi-agents.
"""

import os
from pathlib import Path

# Répertoire racine du projet
ROOT_DIR = Path(__file__).parent.absolute()

# Configuration XMPP
XMPP = {
    "host": os.environ.get("CLOUD_MAS_XMPP_HOST", "localhost"),
    "server": os.environ.get("CLOUD_MAS_XMPP_SERVER", "localhost"),
    "password": os.environ.get("CLOUD_MAS_XMPP_PASSWORD", "password")
}

# Configuration des agents
AGENTS = {
    "client_manager": {
        "vip_weight": 10.0,
        "aging_factor": 0.5,
        "max_standard_age": 180  # Secondes avant promotion d'une demande standard
    },
    "resource_manager": {
        "total_cpu": float(os.environ.get("CLOUD_MAS_TOTAL_CPU", "100.0")),
        "total_memory": float(os.environ.get("CLOUD_MAS_TOTAL_MEMORY", "100.0")),
        "simulation_speed": float(os.environ.get("CLOUD_MAS_SIM_SPEED", "10.0"))
    },
    "load_balancer": {
        "server_count": int(os.environ.get("CLOUD_MAS_SERVER_COUNT", "5"))
    },
    "monitor": {
        "history_length": int(os.environ.get("CLOUD_MAS_HISTORY_LENGTH", "100"))
    }
}

# Configuration du tableau de bord
DASHBOARD = {
    "port": int(os.environ.get("CLOUD_MAS_DASHBOARD_PORT", "8080")),
    "host": os.environ.get("CLOUD_MAS_DASHBOARD_HOST", "0.0.0.0"),
    "refresh_interval": int(os.environ.get("CLOUD_MAS_DASHBOARD_REFRESH", "5"))  # Secondes
}

# Configuration de la simulation
SIMULATION = {
    "enabled": os.environ.get("CLOUD_MAS_SIM_ENABLED", "1") == "1",
    "duration": int(os.environ.get("CLOUD_MAS_SIM_DURATION", "3600")),  # Secondes
    "request_interval": float(os.environ.get("CLOUD_MAS_SIM_INTERVAL", "5.0")),  # Secondes
    "vip_client_count": int(os.environ.get("CLOUD_MAS_SIM_VIP_CLIENTS", "5")),
    "standard_client_count": int(os.environ.get("CLOUD_MAS_SIM_STD_CLIENTS", "15"))
}

# Seuils d'alerte
ALERT_THRESHOLDS = {
    "vip_queue_size": int(os.environ.get("CLOUD_MAS_ALERT_VIP_QUEUE", "10")),
    "standard_queue_size": int(os.environ.get("CLOUD_MAS_ALERT_STD_QUEUE", "20")),
    "cpu_utilization": float(os.environ.get("CLOUD_MAS_ALERT_CPU", "80.0")),
    "memory_utilization": float(os.environ.get("CLOUD_MAS_ALERT_MEMORY", "80.0")),
    "vip_avg_wait_time": float(os.environ.get("CLOUD_MAS_ALERT_VIP_WAIT", "60.0")),
    "standard_avg_wait_time": float(os.environ.get("CLOUD_MAS_ALERT_STD_WAIT", "180.0")),
    "load_imbalance": float(os.environ.get("CLOUD_MAS_ALERT_IMBALANCE", "20.0"))
}

# Configuration de la journalisation
LOGGING = {
    "level": os.environ.get("CLOUD_MAS_LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": os.path.join(ROOT_DIR, "cloud_mas.log")
}