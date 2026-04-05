"""
IceX Verify Enterprise - Sistema de Cache
==========================================
Cache em memória para otimizar performance e reduzir consultas.
"""

import time
import threading
from typing import Optional, Any, Dict


class CacheManager:
    """Gerenciador de cache em memória com TTL (Time To Live)."""
    
    def __init__(self, default_ttl: int = 300):
        """
        Inicializa o cache.
        
        Args:
            default_ttl: Tempo de vida padrão em segundos (default: 5 minutos)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        
    def get(self, key: str) -> Optional[Any]:
        """
        Obtém um valor do cache.
        
        Args:
            key: Chave do cache
            
        Returns:
            Valor armazenado ou None se expirado/não existir
        """
        with self._lock:
            if key not in self._cache:
                return None
                
            entry = self._cache[key]
            
            # Verifica se expirou
            if time.time() > entry['expires_at']:
                del self._cache[key]
                return None
                
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena um valor no cache.
        
        Args:
            key: Chave do cache
            value: Valor a ser armazenado
            ttl: Tempo de vida em segundos (usa default se não especificado)
        """
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': time.time() + (ttl or self._default_ttl)
            }
    
    def delete(self, key: str) -> bool:
        """
        Remove um valor do cache.
        
        Args:
            key: Chave a ser removida
            
        Returns:
            True se removido, False se não existia
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Limpa todo o cache."""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        Remove entradas expiradas do cache.
        
        Returns:
            Número de entradas removidas
        """
        current_time = time.time()
        removed = 0
        
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if current_time > entry['expires_at']
            ]
            for key in expired_keys:
                del self._cache[key]
                removed += 1
                
        return removed
    
    def is_verified(self, user_id: str) -> bool:
        """
        Verifica rapidamente se um usuário já está verificado (cache).
        
        Args:
            user_id: ID do usuário Discord
            
        Returns:
            True se verificado no cache
        """
        return self.get(f'verified:{user_id}') is True
    
    def mark_verified(self, user_id: str, ttl: Optional[int] = None) -> None:
        """
        Marca um usuário como verificado no cache.
        
        Args:
            user_id: ID do usuário Discord
            ttl: Tempo de vida (default: 1 hora)
        """
        self.set(f'verified:{user_id}', True, ttl or 3600)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache.
        
        Returns:
            Dicionário com estatísticas
        """
        with self._lock:
            return {
                'total_entries': len(self._cache),
                'verified_entries': sum(
                    1 for k in self._cache.keys() 
                    if k.startswith('verified:')
                )
            }
