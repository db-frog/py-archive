class OidcClient:
    def __init__(self, client_id, client_secret, authority_url, redirect_url, frontend_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.authority_url = authority_url
        self.redirect_url = redirect_url
        self.frontend_url = frontend_url
