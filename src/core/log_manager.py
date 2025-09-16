"""
SMARTFIX Tool Enforcement - Log Manager
Sistema de logging estructurado para el sistema de auto-reparación
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pythonjsonlogger import jsonlogger
from django.conf import settings

class StructuredLogger:
    """Logger estructurado para SMARTFIX Tool Enforcement"""
    
    def __init__(self, name: str = "smartfix"):
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Configurar el logger con formato JSON"""
        # Eliminar handlers existentes
        self.logger.handlers.clear()
        
        # Configurar nivel de log
        log_level = getattr(settings, 'LOG_LEVEL', 'INFO')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Configurar formato JSON
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s %(module)s %(funcName)s %(lineno)d'
        )
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Configurar logging para archivo si está habilitado
        if getattr(settings, 'LOG_TO_FILE', False):
            file_handler = logging.FileHandler(
                getattr(settings, 'LOG_FILE_PATH', 'smartfix.log')
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log_event(self, level: str, event: str, details: Dict[str, Any], 
                 context: Optional[Dict[str, Any]] = None):
        """
        Registrar evento estructurado
        
        Args:
            level: Nivel de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            event: Tipo de evento
            details: Detalles del evento
            context: Contexto adicional
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level.upper(),
            'event': event,
            'details': details,
            'context': context or {},
            'system': 'smartfix-tool-enforcement',
            'version': getattr(settings, 'APP_VERSION', '0.1.0')
        }
        
        # Añadir información de entorno si está disponible
        if hasattr(settings, 'ENVIRONMENT'):
            log_data['environment'] = settings.ENVIRONMENT
        
        # Loggear según el nivel
        if level.upper() == 'DEBUG':
            self.logger.debug(json.dumps(log_data))
        elif level.upper() == 'INFO':
            self.logger.info(json.dumps(log_data))
        elif level.upper() == 'WARNING':
            self.logger.warning(json.dumps(log_data))
        elif level.upper() == 'ERROR':
            self.logger.error(json.dumps(log_data))
        elif level.upper() == 'CRITICAL':
            self.logger.critical(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))
    
    def debug(self, event: str, details: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Loggear evento de nivel DEBUG"""
        self.log_event('DEBUG', event, details, context)
    
    def info(self, event: str, details: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Loggear evento de nivel INFO"""
        self.log_event('INFO', event, details, context)
    
    def warning(self, event: str, details: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Loggear evento de nivel WARNING"""
        self.log_event('WARNING', event, details, context)
    
    def error(self, event: str, details: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Loggear evento de nivel ERROR"""
        self.log_event('ERROR', event, details, context)
    
    def critical(self, event: str, details: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Loggear evento de nivel CRITICAL"""
        self.log_event('CRITICAL', event, details, context)
    
    def log_repair_attempt(self, repair_data: Dict[str, Any], 
                          status: str, 
                          result: Optional[Dict[str, Any]] = None):
        """
        Loggear intento de reparación
        
        Args:
            repair_data: Datos de la reparación
            status: Estado del intento (success, failed, partial)
            result: Resultado de la reparación
        """
        self.info(
            event="repair_attempt",
            details={
                "repair_id": repair_data.get('id', 'unknown'),
                "type": repair_data.get('type', 'unknown'),
                "file": repair_data.get('file', 'unknown'),
                "line": repair_data.get('line', 'unknown'),
                "status": status,
                "result": result or {}
            }
        )
    
    def log_approval_request(self, approval_id: str, 
                            repair_data: Dict[str, Any], 
                            recipients: list):
        """
        Loggear solicitud de aprobación
        
        Args:
            approval_id: ID de la aprobación
            repair_data: Datos de la reparación
            recipients: Lista de destinatarios
        """
        self.info(
            event="approval_request",
            details={
                "approval_id": approval_id,
                "repair_id": repair_data.get('id', 'unknown'),
                "recipients": recipients,
                "repair_type": repair_data.get('type', 'unknown')
            }
        )
    
    def log_approval_response(self, approval_id: str, 
                             decision: str, 
                             responder: str):
        """
        Loggear respuesta de aprobación
        
        Args:
            approval_id: ID de la aprobación
            decision: Decisión (approve/reject)
            responder: Persona que respondió
        """
        self.info(
            event="approval_response",
            details={
                "approval_id": approval_id,
                "decision": decision,
                "responder": responder
            }
        )

# Singleton para uso global
_log_manager = None

def get_log_manager() -> StructuredLogger:
    """Obtener instancia singleton del gestor de logs"""
    global _log_manager
    
    if _log_manager is None:
        _log_manager = StructuredLogger()
    
    return _log_manager