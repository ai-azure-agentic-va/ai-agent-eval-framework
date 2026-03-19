import subprocess
import json
import time
from azure.core.credentials import AccessToken

class CustomAzureCliCredential:
    def get_token(self, *scopes, **kwargs):
        """Retrieves an access token using 'az account get-access-token' with shell=True."""
        # Typically the first scope is the resource
        resource = scopes[0].replace("/.default", "") if scopes else "https://management.azure.com"
        
        try:
            # We use az.cmd and shell=True for maximum compatibility on Windows
            cmd = ["az.cmd", "account", "get-access-token", "--resource", resource]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=True)
            data = json.loads(result.stdout)
            
            # AccessToken expects (token, expires_on)
            # expires_on should be an int (epoch seconds)
            return AccessToken(data["accessToken"], int(data["expires_on"]))
        except Exception as e:
            raise Exception(f"CustomAzureCliCredential failed: {str(e)}")
