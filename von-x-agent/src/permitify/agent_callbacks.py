import time
import threading
import os
import json


####################################################
# run background services to receive web hooks
####################################################
# agent webhook callbacks
class webhooks_base:
    def POST(self, topic, message):

        # dispatch based on the topic type
        if topic == "connections":
            return self.handle_connections(message["state"], message)

        elif topic == "credentials":
            return self.handle_credentials(message["state"], message)

        elif topic == "presentations":
            return self.handle_presentations(message["state"], message)

        elif topic == "get-active-menu":
            return self.handle_get_active_menu(message)

        elif topic == "perform-menu-action":
            return self.handle_perform_menu_action(message)

        else:
            s_print("Callback: topic=", topic, ", message=", message)
            return ""

            return self.handle_connections(message["state"], message)

    def handle_connections(self, state, message):
        conn_id = message["connection_id"]
        s_print("Connection: state=", state, ", connection_id=", conn_id)
        return ""

    def handle_credentials(self, state, message):
        credential_exchange_id = message["credential_exchange_id"]
        s_print(
            "Credential: state=",
            state,
            ", credential_exchange_id=",
            credential_exchange_id,
        )
        return ""

    def handle_presentations(self, state, message):
        presentation_exchange_id = message["presentation_exchange_id"]
        s_print(
            "Presentation: state=",
            state,
            ", presentation_exchange_id=",
            presentation_exchange_id,
        )
        return ""

    def handle_get_active_menu(self, message):
        s_print("Get active menu: message=", message)
        return ""

    def handle_perform_menu_action(self, message):
        s_print("Handle menu action: message=", message)
        return ""

