"""
IceX Verify Enterprise - MongoDB Manager
=========================================
Gerenciador centralizado de operações MongoDB.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from config import get_config
from modules.logger import Logger, LogStatus


class DatabaseManager:
    """Gerenciador de conexão e operações MongoDB."""
    
    def __init__(self):
        """Inicializa a conexão com MongoDB."""
        self.config = get_config()
        self.logger = Logger('icex-db')
        
        try:
            self.client = MongoClient(
                self.config.MONGO_URI,
                serverSelectionTimeoutMS=5000
            )
            self.db: Database = self.client[self.config.MONGO_DB_NAME]
            
            # Inicializa coleções
            self.users: Collection = self.db[self.config.COLLECTION_USERS]
            self.logs: Collection = self.db[self.config.COLLECTION_LOGS]
            self.blacklist: Collection = self.db[self.config.COLLECTION_BLACKLIST]
            
            # Cria índices
            self._create_indexes()
            
            self.logger.success("✓ Conexão MongoDB estabelecida com sucesso")
            
        except PyMongoError as e:
            self.logger.error(f"✗ Falha na conexão MongoDB: {e}")
            raise
    
    def _create_indexes(self) -> None:
        """Cria índices otimizados para as coleções."""
        try:
            # Índices para usuários
            self.users.create_index([('user_id', ASCENDING)], unique=True)
            self.users.create_index([('ip', ASCENDING)])
            self.users.create_index([('verified', ASCENDING)])
            self.users.create_index([('created_at', DESCENDING)])
            self.users.create_index([('is_suspect', ASCENDING)])
            
            # Índices para logs
            self.logs.create_index([('user_id', ASCENDING)])
            self.logs.create_index([('ip', ASCENDING)])
            self.logs.create_index([('timestamp', DESCENDING)])
            self.logs.create_index([('status', ASCENDING)])
            
            # TTL para logs antigos (90 dias)
            self.logs.create_index(
                [('timestamp', ASCENDING)],
                expireAfterSeconds=90 * 24 * 60 * 60
            )
            
            # Índices para blacklist
            self.blacklist.create_index([('user_id', ASCENDING)], unique=True, sparse=True)
            self.blacklist.create_index([('ip', ASCENDING)], unique=True, sparse=True)
            
            self.logger.info("✓ Índices MongoDB criados/verificados")
            
        except PyMongoError as e:
            self.logger.error(f"✗ Erro ao criar índices: {e}")
    
    def save_user(self, user_data: Dict[str, Any]) -> bool:
        """
        Salva ou atualiza um usuário no banco.
        
        Args:
            user_data: Dados do usuário
            
        Returns:
            True se sucesso, False se falha
        """
        try:
            user_id = user_data.get('user_id')
            
            # Upsert - atualiza se existe, insere se não
            result = self.users.update_one(
                {'user_id': user_id},
                {'$set': user_data, '$setOnInsert': {'created_at': datetime.utcnow()}},
                upsert=True
            )
            
            self.logger.database_log(
                'UPSERT',
                self.config.COLLECTION_USERS,
                True
            )
            
            return True
            
        except PyMongoError as e:
            self.logger.database_log(
                'UPSERT',
                self.config.COLLECTION_USERS,
                False
            )
            self.logger.error(f"Erro ao salvar usuário: {e}")
            return False
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca um usuário pelo ID.
        
        Args:
            user_id: ID do usuário Discord
            
        Returns:
            Dados do usuário ou None
        """
        try:
            return self.users.find_one({'user_id': user_id})
        except PyMongoError as e:
            self.logger.error(f"Erro ao buscar usuário: {e}")
            return None
    
    def is_user_verified(self, user_id: str) -> bool:
        """
        Verifica se um usuário já está verificado.
        
        Args:
            user_id: ID do usuário Discord
            
        Returns:
            True se verificado
        """
        try:
            user = self.users.find_one(
                {'user_id': user_id, 'verified': True},
                {'_id': 1}
            )
            return user is not None
        except PyMongoError as e:
            self.logger.error(f"Erro ao verificar status: {e}")
            return False
    
    def count_users_by_ip(self, ip: str) -> int:
        """
        Conta quantos usuários usaram o mesmo IP.
        
        Args:
            ip: Endereço IP
            
        Returns:
            Número de usuários
        """
        try:
            return self.users.count_documents({'ip': ip})
        except PyMongoError as e:
            self.logger.error(f"Erro ao contar IPs: {e}")
            return 0
    
    def add_to_blacklist(
        self,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        reason: str = ''
    ) -> bool:
        """
        Adiciona um usuário ou IP à blacklist.
        
        Args:
            user_id: ID do usuário (opcional)
            ip: Endereço IP (opcional)
            reason: Motivo do bloqueio
            
        Returns:
            True se sucesso
        """
        try:
            entry = {
                'reason': reason,
                'created_at': datetime.utcnow()
            }
            
            if user_id:
                entry['user_id'] = user_id
                self.blacklist.update_one(
                    {'user_id': user_id},
                    {'$set': entry},
                    upsert=True
                )
                
            if ip:
                entry['ip'] = ip
                self.blacklist.update_one(
                    {'ip': ip},
                    {'$set': entry},
                    upsert=True
                )
            
            self.logger.security_log(
                f"Adicionado à blacklist: user={user_id}, ip={ip}, reason={reason}"
            )
            
            return True
            
        except PyMongoError as e:
            self.logger.error(f"Erro ao adicionar à blacklist: {e}")
            return False
    
    def is_blacklisted(self, user_id: Optional[str] = None, ip: Optional[str] = None) -> bool:
        """
        Verifica se um usuário ou IP está na blacklist.
        
        Args:
            user_id: ID do usuário (opcional)
            ip: Endereço IP (opcional)
            
        Returns:
            True se estiver na blacklist
        """
        try:
            query = {'$or': []}
            
            if user_id:
                query['$or'].append({'user_id': user_id})
            if ip:
                query['$or'].append({'ip': ip})
                
            if not query['$or']:
                return False
                
            return self.blacklist.find_one(query) is not None
            
        except PyMongoError as e:
            self.logger.error(f"Erro ao verificar blacklist: {e}")
            return False
    
    def save_log(self, log_entry: Dict[str, Any]) -> bool:
        """
        Salva um log de verificação.
        
        Args:
            log_entry: Dados do log
            
        Returns:
            True se sucesso
        """
        try:
            self.logs.insert_one(log_entry)
            return True
        except PyMongoError as e:
            self.logger.error(f"Erro ao salvar log: {e}")
            return False
    
    def get_recent_logs(
        self,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Busca logs recentes.
        
        Args:
            user_id: Filtrar por usuário
            ip: Filtrar por IP
            limit: Limite de resultados
            
        Returns:
            Lista de logs
        """
        try:
            query = {}
            
            if user_id:
                query['user_id'] = user_id
            if ip:
                query['ip'] = ip
                
            return list(
                self.logs
                .find(query)
                .sort('timestamp', DESCENDING)
                .limit(limit)
            )
            
        except PyMongoError as e:
            self.logger.error(f"Erro ao buscar logs: {e}")
            return []
    
    def get_stats(self) -> Dict[str, int]:
        """
        Retorna estatísticas do banco.
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            return {
                'total_users': self.users.count_documents({}),
                'verified_users': self.users.count_documents({'verified': True}),
                'suspect_users': self.users.count_documents({'is_suspect': True}),
                'blacklisted': self.blacklist.count_documents({}),
                'total_logs': self.logs.count_documents({})
            }
        except PyMongoError as e:
            self.logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
    
    def close(self) -> None:
        """Fecha a conexão com o MongoDB."""
        if hasattr(self, 'client'):
            self.client.close()
            self.logger.info("Conexão MongoDB fechada")
