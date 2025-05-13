# Système Multi-Agents pour l'Allocation de Ressources Cloud

Ce projet implémente un système multi-agents décentralisé pour l'allocation efficace et équitable des ressources dans un environnement cloud. Le système utilise l'algorithme HRRN (Highest Response Ratio Next) pour l'ordonnancement des demandes et le tri topologique pour gérer les dépendances entre tâches.

## Caractéristiques

- **Architecture décentralisée** : 4 agents spécialisés collaborant pour optimiser l'allocation des ressources
- **Mécanisme d'équité** : Algorithme HRRN garantissant l'équité entre demandes VIP et standard
- **Gestion des dépendances** : Tri topologique pour optimiser l'ordre d'exécution des tâches interdépendantes
- **Tableau de bord web** : Interface de visualisation en temps réel des métriques du système
- **Hautement configurable** : Paramètres ajustables via un fichier de configuration YAML

## Architecture

Le système est composé de quatre agents principaux :

1. **ClientManagerAgent (CMA)** : Gère les files d'attente des demandes et implémente l'algorithme HRRN
2. **ResourceManagerAgent (RMA)** : Gère l'allocation effective des ressources et les dépendances via le tri topologique
3. **LoadBalancerAgent (LBA)** : Optimise le placement des ressources et équilibre les charges
4. **MonitorAgent (MA)** : Surveille l'état du système et génère des rapports

## Prérequis

- Python 3.9+
- Prosody ou un autre serveur XMPP pour la communication entre agents
- Bibliothèques listées dans `requirements.txt`

## Installation

1. Cloner le dépôt :
   ```
   git clone https://github.com/yourusername/cloud-mas.git
   cd cloud-mas
   ```

2. Installer les dépendances :
   ```
   pip install -r requirements.txt
   ```

3. Configurer un serveur XMPP (si non disponible) :
   ```
   # Installation de Prosody sur Ubuntu
   sudo apt-get install prosody
   
   # Configuration minimale
   sudo nano /etc/prosody/prosody.cfg.lua
   
   # Ajouter un hôte virtuel
   VirtualHost "localhost"
       authentication = "internal_plain"
       allow_registration = true
   
   # Redémarrer Prosody
   sudo systemctl restart prosody
   ```

4. Créer des comptes pour les agents :
   ```
   # Dans l'interpréteur de commandes Prosody
   sudo prosodyctl adduser client_manager@localhost
   sudo prosodyctl adduser resource_manager@localhost
   sudo prosodyctl adduser load_balancer@localhost
   sudo prosodyctl adduser monitor_agent@localhost
   ```

## Configuration

Créer un fichier `config.yaml` à la racine du projet :

```yaml
# Serveur XMPP
xmpp_server: "localhost"
xmpp_domain: "localhost"
xmpp_password: "password"

# Durée de la simulation (en secondes)
simulation_duration: 300

# Clients simulés
vip_clients: 5
standard_clients: 20
request_rate: 0.2  # Demandes par seconde

# Configuration des ressources
resource_config:
  available_cpu: 100.0
  available_memory: 256.0
  available_storage: 1000.0

# Configuration de l'ordonnanceur
scheduler_config:
  vip_priority_factor: 2.0
  aging_factor: 0.5

# URL du tableau de bord
dashboard_url: "http://localhost:5000"
```

## Utilisation

1. Démarrer le tableau de bord :
   ```
   python dashboard/app.py
   ```

2. Lancer la simulation :
   ```
   python run_simulation.py config.yaml
   ```

3. Accéder au tableau de bord à l'adresse http://localhost:5000

## Structure du Projet

```
cloud-mas/
├── README.md                   # Documentation principale du projet
├── requirements.txt            # Dépendances du projet
├── config.yaml                 # Configuration du système
├── run_simulation.py           # Point d'entrée principal pour lancer la simulation
├── dashboard/                  # Interface web pour la visualisation et le contrôle
│   ├── app.py                  # Application Flask pour le tableau de bord
│   ├── static/                 # Ressources statiques (CSS, JS)
│   └── templates/              # Templates HTML
├── agents/                     # Implémentation des agents
│   ├── __init__.py             
│   ├── base_agent.py           # Classe de base pour tous les agents
│   ├── client_manager_agent.py # Gestion des files d'attente et priorités
│   ├── resource_manager_agent.py # Allocation de ressources et gestion des dépendances
│   ├── load_balancer_agent.py  # Optimisation du placement des ressources
│   ├── monitor_agent.py        # Surveillance et adaptation du système
│   └── behaviors/              # Comportements spécifiques des agents
├── models/                     # Modèles de données du système
│   ├── __init__.py
│   ├── resource_request.py     # Demandes de ressources
│   ├── client.py               # Clients (VIP/Standard)
│   ├── system_state.py         # État global du système
│   └── enums.py                # Énumérations (ClientType, RequestStatus, etc.)
├── utils/                      # Utilitaires
│   ├── __init__.py
│   ├── topological_sorter.py   # Implémentation du tri topologique
│   ├── hrrn_scheduler.py       # Implémentation de l'algorithme HRRN
│   └── metrics_collector.py    # Collecte et analyse des métriques
└── tests/                      # Tests unitaires et d'intégration
```

## Algorithmes Principaux

### 1. HRRN (Highest Response Ratio Next)

L'algorithme HRRN calcule une priorité pour chaque demande selon la formule :

```
Priorité = (Temps d'attente + Temps d'exécution estimé) / Temps d'exécution estimé
```

Notre implémentation ajoute un facteur de priorité et un mécanisme de vieillissement :

```
Priorité effective = Base priorité × HRRN + (Facteur vieillissement × Temps d'attente)
```

### 2. Tri Topologique

Le tri topologique est utilisé pour déterminer un ordre d'exécution valide respectant toutes les dépendances. Notre implémentation utilise l'algorithme de Kahn :

1. Identifier les nœuds sans prédécesseurs (sources)
2. Ajouter ces nœuds à la solution
3. Retirer ces nœuds et leurs arêtes sortantes du graphe
4. Répéter jusqu'à ce que le graphe soit vide

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

## Contributeurs

- Votre Nom (@votre-username)

## Remerciements

- Remerciements à l'équipe de développement de SPADE pour leur excellente plateforme multi-agents
- Merci au professeur XXX pour ses conseils et retours précieux