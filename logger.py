"""
IceX Verify Enterprise - Sistema de Logs Avançado
=================================================
Logging detalhado para todas as operações do sistema.
"""

import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class LogStatus(Enum):
    """Status possíveis para logs de verificação."""
    SUCCESS = 'success'
    BLOCKED = 'blocked'
    ERROR = 'error'
    RATE_LIMITED = 'rate_limited'
    SUSPECT = 'suspect'
    ALREADY_VERIFIED = 'already_verified'


class Logger:
    """Sistema de logging avançado para o IceX Verify."""
    
    # Cores para console
    COLORS = {
        'RESET': '\033[0m',
        'GREEN': '\033[92m',
        'RED': '\033[91m',
        'YELLOW': '\033[93m',
        'BLUE': '\033[94m',
        'MAGENTA': '\033[95m',
        'CYAN': '\033[96m',
        'WHITE': '\033[97m'
    }
    
    def __init__(self, name: str = 'icex-verify'):
        """
        Inicializa o logger.
        
        Args:
            name: Nome do logger
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Evita handlers duplicados
        if not self.logger.handlers:
            # Handler para console
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            # Formato personalizado
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def _colorize(self, message: str, color: str) -> str:
        """Adiciona cor a uma mensagem para console."""
        return f"{self.COLORS.get(color, '')}{message}{self.COLORS['RESET']}"
    
    def info(self, message: str) -> None:
        """Log de informação."""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log de aviso."""
        self.logger.warning(self._colorize(message, 'YELLOW'))
    
    def error(self, message: str) -> None:
        """Log de erro."""
        self.logger.error(self._colorize(message, 'RED'))
    
    def success(self, message: str) -> None:
        """Log de sucesso."""
        self.logger.info(self._colorize(message, 'GREEN'))
    
    def verification_log(
        self,
        user_id: str,
        username: str,
        status: LogStatus,
        ip: str,
        user_agent: str = '',
        is_suspect: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cria um log estruturado de verificação.
        
        Args:
            user_id: ID do usuário Discord
            username: Nome de usuário
            status: Status da verificação
            ip: Endereço IP
            user_agent: User agent do navegador
            is_suspect: Se é suspeito
            details: Detalhes adicionais
            
        Returns:
            Dicionário do log criado
        """
        log_entry = {
            'user_id': user_id,
            'username': username,
            'status': status.value,
            'ip': ip,
            'timestamp': datetime.utcnow(),
            'user_agent': user_agent[:500] if user_agent else '',
            'is_suspect': is_suspect,
            'details': details or {}
        }
        
        # Log no console com cor apropriada
        color_map = {
            LogStatus.SUCCESS: 'GREEN',
            LogStatus.BLOCKED: 'RED',
            LogStatus.ERROR: 'RED',
            LogStatus.RATE_LIMITED: 'YELLOW',
            LogStatus.SUSPECT: 'MAGENTA',
            LogStatus.ALREADY_VERIFIED: 'CYAN'
        }
        
        icon_map = {
            LogStatus.SUCCESS: '✓',
            LogStatus.BLOCKED: '✗',
            LogStatus.ERROR: '⚠',
            LogStatus.RATE_LIMITED: '⏱',
            LogStatus.SUSPECT: '👁',
            LogStatus.ALREADY_VERIFIED: '✓'
        }
        
        color = color_map.get(status, 'WHITE')
        icon = icon_map.get(status, '•')
        
        suspect_tag = ' [SUSPEITO]' if is_suspect else ''
        console_msg = f"{icon} VERIFICAÇÃO | {username} ({user_id}) | {status.value.upper()}{suspect_tag}"
        
        self.logger.info(self._colorize(console_msg, color))
        
        return log_entry
    
    def security_log(self, message: str, level: str = 'warning') -> None:
        """
        Log específico para eventos de segurança.
        
        Args:
            message: Mensagem do log
            level: Nível do log (info, warning, error)
        """
        prefix = self._colorize('[SEGURANÇA]', 'MAGENTA')
        
        if level == 'error':
            self.logger.error(f"{prefix} {message}")
        elif level == 'warning':
            self.logger.warning(f"{prefix} {message}")
        else:
            self.logger.info(f"{prefix} {message}")
    
    def database_log(self, operation: str, collection: str, success: bool) -> None:
        """
        Log de operações no banco de dados.
        
        Args:
            operation: Operação realizada
            collection: Coleção afetada
            success: Se foi bem-sucedido
        """
        status = self._colorize('OK', 'GREEN') if success else self._colorize('FALHA', 'RED')
        self.logger.info(f"[DB] {operation} em '{collection}' | {status}")
    
    def oauth_log(self, stage: str, user_id: Optional[str] = None, success: bool = True) -> None:
        """
        Log de eventos OAuth2.
        
        Args:
            stage: Etapa do OAuth (authorize, callback, token, etc)
            user_id: ID do usuário (se disponível)
            success: Se foi bem-sucedido
        """
        user_str = f" | User: {user_id}" if user_id else ""
        status = self._colorize('✓', 'GREEN') if success else self._colorize('✗', 'RED')
        self.logger.info(f"[OAuth] {stage} {status}{user_str}")
