import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template
import logging
import asyncio
import json
import aioxmpp


class BaseAgent(Agent):
    """
    Classe de base pour tous les agents du système.
    Définit les fonctionnalités communes et la structure de base.
    """

    def __init__(self, jid, password, display_name=None):
        """
        Initialise un nouvel agent.

        Args:
            jid (str): Jabber ID de l'agent (user@domain)
            password (str): Mot de passe pour l'authentification XMPP
            display_name (str, optional): Nom lisible de l'agent
        """
        super().__init__(jid, password)
        self.display_name = display_name if display_name else self.__class__.__name__
        self.logger = logging.getLogger(f"{self.display_name}-{str(jid).split('@')[0]}")
        self.stopped = False

    async def setup(self):
        """
        Configurer l'agent lors de son démarrage.
        Cette méthode est appelée automatiquement lorsque l'agent est démarré.
        """
        self.logger.info(f"Agent {self.display_name} starting...")

        # Comportement pour gérer les messages génériques
        message_handler = self.MessageHandlerBehaviour()
        self.add_behaviour(message_handler)

        # Comportement pour le heartbeat/monitoring
        heartbeat_behaviour = self.HeartbeatBehaviour(period=30)
        self.add_behaviour(heartbeat_behaviour)  # Heartbeat toutes les 30 secondes

    class MessageHandlerBehaviour(CyclicBehaviour):
        """
        Comportement de base pour traiter les messages entrants.
        """

        async def run(self):
            msg = await self.receive(timeout=10)  # Attend au maximum 10 secondes
            if msg:
                self.agent.logger.debug(f"Received message: {msg.body}")
                await self._handle_message(msg)

        async def _handle_message(self, message):
            """
            Traite un message reçu.
            À surcharger dans les classes dérivées pour un traitement spécifique.

            Args:
                message (Message): Message SPADE à traiter
            """
            # Par défaut, log le message et n'effectue aucun traitement
            self.agent.logger.info(f"Received message type {message.metadata.get('type', 'unknown')}")

    class HeartbeatBehaviour(CyclicBehaviour):
        """
        Comportement de heartbeat pour le monitoring de l'agent.
        """

        def __init__(self, period):
            super().__init__()  # Ne pas passer period au constructeur parent
            self.period = period  # Stockez period comme attribut de classe

        async def run(self):
            self.agent.logger.debug(f"Heartbeat: Agent {self.agent.display_name} is alive")
            # Pourrait envoyer un message de statut à un agent de monitoring ici
            await asyncio.sleep(self.period)  # Attend la période définie

    async def send_message(self, to, body, metadata=None):
        """
        Envoie un message à un autre agent.

        Args:
            to (str): JID du destinataire
            body (str or dict): Contenu du message (sera converti en JSON si c'est un dict)
            metadata (dict, optional): Métadonnées supplémentaires pour le message

        Returns:
            bool: True si le message a été envoyé avec succès
        """
        if isinstance(body, dict):
            body = json.dumps(body)

        msg = Message(to=to)
        msg.body = body

        # Ajouter les métadonnées si fournies
        if metadata:
            for key, value in metadata.items():
                msg.metadata[key] = value

        self.logger.debug(f"Sending message to {to}: {body[:100]}...")
        try:
            await self.send(msg)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False

    def parse_message(self, msg):
        """
        Parse le contenu d'un message.

        Args:
            msg (Message): Message SPADE à parser

        Returns:
            dict or str: Contenu parsé du message
        """
        try:
            return json.loads(msg.body)
        except (json.JSONDecodeError, TypeError):
            return msg.body

    async def stop(self):
        """
        Arrête proprement l'agent.
        """
        self.logger.info(f"Agent {self.display_name} stopping...")
        self.stopped = True
        await super().stop()