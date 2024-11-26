from burp import IBurpExtender
import time

class BurpExtender(IBurpExtender):

    def registerExtenderCallbacks(self, callbacks):
        self.callbacks = callbacks
        callbacks.setExtensionName("Oshirase Neko - Cat Notifier")
        self.collaborator_client = callbacks.createBurpCollaboratorClientContext()
        
        # Generate a Collaborator payload and print it
        payload = self.collaborator_client.generatePayload(True)
        self.callbacks.printOutput("Generated Collaborator Payload: {}".format(payload))
        
        # Poll Collaborator 5 times
        for i in range(5):
            self.callbacks.printOutput("Polling attempt {}...".format(i + 1))
            
            # Fetch any interactions with the Collaborator payload
            interactions = self.collaborator_client.fetchAllCollaboratorInteractions()
            time.sleep(1)
