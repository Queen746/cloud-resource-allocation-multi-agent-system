from enum import Enum, auto

class ClientType(Enum):
    """Types de clients supportés par le système."""
    STANDARD = auto()
    VIP = auto()

class RequestStatus(Enum):
    """États possibles d'une demande de ressources."""
    CREATED = auto()      # Demande créée mais pas encore en file d'attente
    PENDING = auto()      # En file d'attente
    WAITING_DEPS = auto() # En attente de dépendances
    IN_PROGRESS = auto()  # En cours de traitement
    COMPLETED = auto()    # Terminée avec succès
    FAILED = auto()       # Échouée