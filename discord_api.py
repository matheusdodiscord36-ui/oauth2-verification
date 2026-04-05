"""
IceX Verify Enterprise - Integração Discord API
================================================
Cliente para interação com a API do Discord.
"""

import requests
from typing import Optional, Dict, Any

from config import get_config
from modules.logger import Logger


class DiscordAPI:
    """Cliente para API do Discord."""
    
    def __init__(self):
        """Inicializa o cliente Discord."""
        self.config = get_config()
        self.logger = Logger('icex-discord')
        self.base_url = self.config.DISCORD_API_BASE
    
    def get_oauth_url(self, state: str) -> str:
        """
        Gera URL de autorização OAuth2.
        
        Args:
            state: State de segurança
            
        Returns:
            URL completa de autorização
        """
        scopes = '%20'.join(self.config.DISCORD_OAUTH_SCOPES)
        
        return (
            f"{self.base_url}/oauth2/authorize?"
            f"client_id={self.config.DISCORD_CLIENT_ID}&"
            f"redirect_uri={self.config.DISCORD_REDIRECT_URI}&"
            f"response_type=code&"
            f"scope={scopes}&"
            f"state={state}"
        )
    
    def exchange_code(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Troca o código OAuth2 por tokens.
        
        Args:
            code: Código de autorização
            
        Returns:
            Dados dos tokens ou None em caso de erro
        """
        try:
            data = {
                'client_id': self.config.DISCORD_CLIENT_ID,
                'client_secret': self.config.DISCORD_CLIENT_SECRET,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.config.DISCORD_REDIRECT_URI
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(
                f"{self.base_url}/oauth2/token",
                data=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.oauth_log('token_exchange', success=True)
                return response.json()
            else:
                self.logger.oauth_log(
                    'token_exchange',
                    success=False
                )
                self.logger.error(f"Erro na troca de token: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Erro na requisição OAuth: {e}")
            return None
    
    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações do usuário autenticado.
        
        Args:
            access_token: Token de acesso
            
        Returns:
            Dados do usuário ou None
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            response = requests.get(
                f"{self.base_url}/users/@me",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                self.logger.oauth_log(
                    'user_info',
                    user_id=user_data.get('id'),
                    success=True
                )
                return user_data
            else:
                self.logger.oauth_log('user_info', success=False)
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Erro ao obter dados do usuário: {e}")
            return None
    
    def get_avatar_url(self, user_id: str, avatar_hash: Optional[str], size: int = 256) -> str:
        """
        Gera URL do avatar do usuário.
        
        Args:
            user_id: ID do usuário
            avatar_hash: Hash do avatar
            size: Tamanho da imagem
            
        Returns:
            URL do avatar
        """
        if avatar_hash:
            # Avatar customizado
            ext = 'gif' if avatar_hash.startswith('a_') else 'png'
            return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size={size}"
        else:
            # Avatar padrão
            default_avatar = int(user_id) % 5
            return f"https://cdn.discordapp.com/embed/avatars/{default_avatar}.png"
    
    def notify_bot(self, user_id: str, verified: bool = True) -> bool:
        """
        Notifica o bot sobre uma verificação.
        
        Args:
            user_id: ID do usuário verificado
            verified: Status da verificação
            
        Returns:
            True se notificado com sucesso
        """
        try:
            payload = {
                'user_id': user_id,
                'verified': verified
            }
            
            response = requests.post(
                self.config.BOT_WEBHOOK_URL,
                json=payload,
                timeout=5
            )
            
            if response.status_code in [200, 201, 204]:
                self.logger.success(f"✓ Bot notificado: user={user_id}")
                return True
            else:
                self.logger.warning(
                    f"Bot respondeu com status {response.status_code}"
                )
                return False
                
        except requests.RequestException as e:
            self.logger.warning(f"Não foi possível notificar o bot: {e}")
            # Não falha a verificação se o bot não responder
            return False
    
    def revoke_token(self, access_token: str) -> bool:
        """
        Revoga um token de acesso.
        
        Args:
            access_token: Token a ser revogado
            
        Returns:
            True se revogado com sucesso
        """
        try:
            data = {
                'client_id': self.config.DISCORD_CLIENT_ID,
                'client_secret': self.config.DISCORD_CLIENT_SECRET,
                'token': access_token
            }
            
            response = requests.post(
                f"{self.base_url}/oauth2/token/revoke",
                data=data,
                timeout=5
            )
            
            return response.status_code in [200, 204]
            
        except requests.RequestException as e:
            self.logger.error(f"Erro ao revogar token: {e}")
            return False
