from extensions import oauth
from config import Config


client_domain = Config.ISERV_CLIENT_DOMAIN
client_id = Config.ISERV_CLIENT_ID
client_secret = Config.ISERV_CLIENT_SECRET


iserv = oauth.register(
    name='iserv',
    client_id=client_id,
    client_secret=client_secret,
    authorize_url=f'https://{client_domain}/iserv/oauth/v2/auth',
    access_token_url=f'https://{client_domain}/iserv/oauth/v2/token',
    userinfo_endpoint=f'https://{client_domain}/iserv/public/oauth/userinfo',           # User-Daten holen
    server_metadata_url=f'https://{client_domain}/.well-known/openid-configuration',    
    client_kwargs={'scope': 'openid profile groups roles'}                              # Angefragte Scopes
)

