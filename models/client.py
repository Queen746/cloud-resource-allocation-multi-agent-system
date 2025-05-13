from models.enums import ClientType


class Client:
    """
    Représente un client du système cloud avec un type spécifique.
    """

    def __init__(self, client_id, client_type=ClientType.STANDARD):
        """
        Initialise un nouveau client.

        Args:
            client_id (str): Identifiant unique du client
            client_type (ClientType): Type de client (VIP ou STANDARD)
        """
        self.id = client_id
        self.client_type = client_type

    def is_vip(self):
        """
        Vérifie si le client est de type VIP.

        Returns:
            bool: True si le client est VIP, False sinon
        """
        return self.client_type == ClientType.VIP

    def to_dict(self):
        """
        Convertit l'objet Client en dictionnaire pour la sérialisation.

        Returns:
            dict: Représentation du client
        """
        return {
            "id": self.id,
            "client_type": self.client_type.name
        }

    @staticmethod
    def from_dict(data):
        """
        Crée un objet Client à partir d'un dictionnaire.

        Args:
            data (dict): Dictionnaire contenant les données du client

        Returns:
            Client: Instance de Client créée à partir des données
        """
        return Client(
            client_id=data.get('id'),
            client_type=ClientType[data.get('client_type', 'STANDARD')]
        )