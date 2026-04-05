"""
IceX Verify Enterprise - Sistema de Segurança
==============================================
Anti-fake, rate limit, blacklist e detecção de suspeitas.
"""

import time
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from collections import defaultdict

from config import get_config
from modules.logger import Logger, LogStatus


class RateLimitEntry:
    """Entrada de rate limit para um IP."""
    
    def __init__(self):
        self.attempts: List[float] = []
        self.blocked_until: Optional[float] = None
    
    def is_blocked(self) -> bool:
        """Verifica se o IP está bloqueado."""
        if self.blocked_until and time.time() < self.blocked_until:
            return True
        return False
    
    def get_remaining_block_time(self) -> int:
        """Retorna tempo restante de bloqueio em segundos."""
        if self.blocked_until:
            remaining = int(self.blocked_until - time.time())
            return max(0, remaining)
        return 0


class SecurityManager:
    """Gerenciador de segurança do sistema."""
    
    def __init__(self):
        """Inicializa o gerenciador de segurança."""
        self.config = get_config()
        self.logger = Logger('icex-security')
        
        # Rate limiting em memória
        self._rate_limits: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        
        # Estados OAuth ativos
        self._oauth_states: Dict[str, Dict[str, Any]] = {}
    
    def generate_oauth_state(self, ip: str) -> str:
        """
        Gera um state único para OAuth2.
        
        Args:
            ip: IP do usuário
            
        Returns:
            State hash
        """
        timestamp = str(time.time())
        state_data = f"{ip}:{timestamp}:{self.config.SECRET_KEY}"
        state = hashlib.sha256(state_data.encode()).hexdigest()[:32]
        
        # Armazena o state com timestamp
        self._oauth_states[state] = {
            'ip': ip,
            'created_at': time.time(),
            'used': False
        }
        
        # Limpa states antigos (mais de 10 minutos)
        self._cleanup_old_states()
        
        return state
    
    def validate_oauth_state(self, state: str, current_ip: str) -> bool:
        """
        Valida um state OAuth2.
        
        Args:
            state: State recebido
            current_ip: IP atual do usuário
            
        Returns:
            True se válido
        """
        if not state or state not in self._oauth_states:
            self.logger.security_log(f"State inválido ou não encontrado: {state}")
            return False
        
        state_data = self._oauth_states[state]
        
        # Verifica se já foi usado
        if state_data['used']:
            self.logger.security_log(f"State reutilizado: {state}")
            return False
        
        # Verifica se expirou (10 minutos)
        if time.time() - state_data['created_at'] > 600:
            self.logger.security_log(f"State expirado: {state}")
            return False
        
        # Opcional: verificar consistência de IP
        # if state_data['ip'] != current_ip:
        #     self.logger.security_log(f"IP inconsistente no state: {state}")
        #     return False
        
        # Marca como usado
        state_data['used'] = True
        
        return True
    
    def _cleanup_old_states(self) -> None:
        """Remove states OAuth antigos."""
        current_time = time.time()
        expired = [
            state for state, data in self._oauth_states.items()
            if current_time - data['created_at'] > 600
        ]
        for state in expired:
            del self._oauth_states[state]
    
    def check_rate_limit(self, ip: str) -> tuple[bool, int]:
        """
        Verifica e aplica rate limit.
        
        Args:
            ip: Endereço IP
            
        Returns:
            Tuple (permitido, tempo_espera)
        """
        entry = self._rate_limits[ip]
        
        # Verifica se está bloqueado
        if entry.is_blocked():
            remaining = entry.get_remaining_block_time()
            self.logger.security_log(
                f"Rate limit bloqueado para IP {ip}, aguardar {remaining}s"
            )
            return False, remaining
        
        # Limpa tentativas antigas
        current_time = time.time()
        window = self.config.RATE_LIMIT_WINDOW_SECONDS
        entry.attempts = [
            t for t in entry.attempts 
            if current_time - t < window
        ]
        
        # Verifica limite
        if len(entry.attempts) >= self.config.RATE_LIMIT_MAX_REQUESTS:
            # Bloqueia por 5 minutos
            entry.blocked_until = current_time + 300
            self.logger.security_log(
                f"Rate limit excedido para IP {ip}, bloqueado por 5 minutos"
            )
            return False, 300
        
        # Registra tentativa
        entry.attempts.append(current_time)
        
        return True, 0
    
    def calculate_account_age(self, user_data: Dict[str, Any]) -> int:
        """
        Calcula a idade da conta Discord em dias.
        
        Args:
            user_data: Dados do usuário da API Discord
            
        Returns:
            Idade em dias
        """
        try:
            # Discord snowflake timestamp
            discord_epoch = 1420070400000  # 2015-01-01
            user_id = int(user_data.get('id', 0))
            
            if user_id == 0:
                return 0
            
            # Extrai timestamp do snowflake
            timestamp_ms = ((user_id >> 22) + discord_epoch)
            created_at = datetime.fromtimestamp(timestamp_ms / 1000)
            
            # Calcula diferença
            age = datetime.utcnow() - created_at
            return max(0, age.days)
            
        except (ValueError, TypeError) as e:
            self.logger.error(f"Erro ao calcular idade da conta: {e}")
            return 0
    
    def analyze_user_risk(
        self,
        user_data: Dict[str, Any],
        ip: str,
        db_manager
    ) -> Dict[str, Any]:
        """
        Analisa o risco de um usuário.
        
        Args:
            user_data: Dados do usuário Discord
            ip: Endereço IP
            db_manager: Instância do DatabaseManager
            
        Returns:
            Dicionário com análise de risco
        """
        risk_factors = []
        is_suspect = False
        
        # 1. Idade da conta
        account_age = self.calculate_account_age(user_data)
        if account_age < self.config.MIN_ACCOUNT_AGE_DAYS:
            risk_factors.append(f"Conta recente ({account_age} dias)")
            is_suspect = True
        
        # 2. Reutilização de IP
        ip_user_count = db_manager.count_users_by_ip(ip)
        ip_reused = ip_user_count >= self.config.MAX_IP_REUSES
        
        if ip_reused:
            risk_factors.append(f"IP reutilizado ({ip_user_count} usuários)")
            is_suspect = True
        
        # 3. Verificar blacklist
        user_id = user_data.get('id')
        is_blacklisted = db_manager.is_blacklisted(user_id=user_id, ip=ip)
        
        if is_blacklisted:
            risk_factors.append("Usuário/IP na blacklist")
        
        return {
            'is_suspect': is_suspect,
            'is_blacklisted': is_blacklisted,
            'account_age_days': account_age,
            'ip_reused': ip_reused,
            'ip_user_count': ip_user_count,
            'risk_factors': risk_factors
        }
    
    def get_client_info(self, request) -> Dict[str, str]:
        """
        Extrai informações do cliente da requisição.
        
        Args:
            request: Objeto request do Flask
            
        Returns:
            Dicionário com IP e User-Agent
        """
        # Obtém IP real (considerando proxies)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
        
        user_agent = request.headers.get('User-Agent', '')
        
        return {
            'ip': ip or 'unknown',
            'user_agent': user_agent
        }
    
    def cleanup_rate_limits(self) -> int:
        """
        Limpa entradas antigas de rate limit.
        
        Returns:
            Número de entradas removidas
        """
        current_time = time.time()
        to_remove = []
        
        for ip, entry in self._rate_limits.items():
            # Remove se não há tentativas recentes e não está bloqueado
            if not entry.attempts and not entry.is_blocked():
                to_remove.append(ip)
            # Remove tentativas antigas
            else:
                entry.attempts = [
                    t for t in entry.attempts
                    if current_time - t < self.config.RATE_LIMIT_WINDOW_SECONDS
                ]
        
        for ip in to_remove:
            del self._rate_limits[ip]
        
        return len(to_remove)
