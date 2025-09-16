"""
SMARTFIX Tool Enforcement - Error Processor
Procesamiento y clasificación de errores para el sistema de auto-reparación
"""

import re
import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime

logger = logging.getLogger("smartfix.error_processor")

class ErrorSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ErrorCategory(Enum):
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    LOGIC = "logic"
    SECURITY = "security"
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    NETWORK = "network"
    DATABASE = "database"
    INTEGRATION = "integration"
    CONFIGURATION = "configuration"

class ErrorProcessor:
    """Procesador de errores para SMARTFIX Tool Enforcement"""
    
    def __init__(self):
        self.patterns = self._initialize_patterns()
        self.severity_rules = self._initialize_severity_rules()
        self.category_patterns = self._initialize_category_patterns()
    
    def _initialize_patterns(self) -> Dict[str, Any]:
        """Inicializar patrones de detección de errores"""
        return {
            'python': {
                'syntax_error': r'SyntaxError: (.*)',
                'name_error': r'NameError: (.*)',
                'type_error': r'TypeError: (.*)',
                'value_error': r'ValueError: (.*)',
                'index_error': r'IndexError: (.*)',
                'key_error': r'KeyError: (.*)',
                'attribute_error': r'AttributeError: (.*)',
                'import_error': r'ImportError: (.*)',
                'io_error': r'IOError: (.*)',
                'os_error': r'OSError: (.*)',
            },
            'javascript': {
                'syntax_error': r'SyntaxError: (.*)',
                'type_error': r'TypeError: (.*)',
                'reference_error': r'ReferenceError: (.*)',
                'range_error': r'RangeError: (.*)',
                'uri_error': r'URIError: (.*)',
                'eval_error': r'EvalError: (.*)',
            },
            'java': {
                'null_pointer': r'NullPointerException',
                'array_index': r'ArrayIndexOutOfBoundsException',
                'class_cast': r'ClassCastException',
                'io_exception': r'IOException',
                'sql_exception': r'SQLException',
            },
            'general': {
                'timeout': r'timeout|timed out|time out',
                'connection': r'connection refused|connection reset|connection failed',
                'memory': r'out of memory|memory leak',
                'disk': r'disk full|no space left',
                'permission': r'permission denied|access denied',
            }
        }
    
    def _initialize_severity_rules(self) -> Dict[str, List[str]]:
        """Inicializar reglas de severidad"""
        return {
            ErrorSeverity.CRITICAL.value: [
                'out of memory', 'disk full', 'connection refused', 
                'nullpointerexception', 'timeout'
            ],
            ErrorSeverity.HIGH.value: [
                'typeerror', 'valueerror', 'sqlexception', 
                'ioexception', 'classcastexception'
            ],
            ErrorSeverity.MEDIUM.value: [
                'attributeerror', 'importerror', 'referenceerror',
                'rangeerror', 'urierror'
            ],
            ErrorSeverity.LOW.value: [
                'warning', 'deprecated', 'info'
            ]
        }
    
    def _initialize_category_patterns(self) -> Dict[str, List[str]]:
        """Inicializar patrones de categoría"""
        return {
            ErrorCategory.SYNTAX.value: ['syntaxerror', 'parseerror'],
            ErrorCategory.RUNTIME.value: ['typeerror', 'valueerror', 'nullpointer'],
            ErrorCategory.SECURITY.value: ['access denied', 'permission denied', 'security'],
            ErrorCategory.PERFORMANCE.value: ['timeout', 'slow', 'performance'],
            ErrorCategory.RESOURCE.value: ['out of memory', 'disk full', 'resource'],
            ErrorCategory.NETWORK.value: ['connection', 'network', 'http', 'https'],
            ErrorCategory.DATABASE.value: ['database', 'sql', 'query', 'transaction'],
            ErrorCategory.INTEGRATION.value: ['api', 'integration', 'webhook', 'service'],
            ErrorCategory.CONFIGURATION.value: ['config', 'setting', 'property', 'environment'],
        }
    
    def process_error(self, error_message: str, 
                     language: str = 'python',
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Procesar un error y extraer información estructurada
        
        Args:
            error_message: Mensaje de error completo
            language: Lenguaje de programación
            context: Contexto adicional del error
            
        Returns:
            Información estructurada del error
        """
        try:
            # Extraer información básica del error
            error_info = self._extract_error_info(error_message, language)
            
            # Determinar severidad
            severity = self._determine_severity(error_message, error_info)
            
            # Determinar categoría
            category = self._determine_category(error_message, error_info)
            
            # Crear estructura de error procesado
            processed_error = {
                'id': self._generate_error_id(),
                'raw_message': error_message,
                'language': language,
                'type': error_info.get('type', 'unknown'),
                'message': error_info.get('message', error_message),
                'severity': severity.value,
                'category': category.value,
                'timestamp': datetime.now().isoformat(),
                'context': context or {},
                'suggested_actions': self._suggest_actions(error_info, severity, category),
                'patterns_found': error_info.get('patterns', [])
            }
            
            logger.info(f"Error procesado: {processed_error['id']} - {processed_error['type']}")
            return processed_error
            
        except Exception as e:
            logger.error(f"Error procesando error: {str(e)}")
            return {
                'id': self._generate_error_id(),
                'raw_message': error_message,
                'language': language,
                'type': 'processing_error',
                'message': f'Error processing original error: {str(e)}',
                'severity': ErrorSeverity.HIGH.value,
                'category': ErrorCategory.RUNTIME.value,
                'timestamp': datetime.now().isoformat(),
                'context': context or {},
                'suggested_actions': ['review_manually'],
                'patterns_found': []
            }
    
    def _extract_error_info(self, error_message: str, language: str) -> Dict[str, Any]:
        """Extraer información específica del error"""
        error_info = {
            'type': 'unknown',
            'message': error_message,
            'patterns': []
        }
        
        # Buscar patrones específicos del lenguaje
        if language in self.patterns:
            for error_type, pattern in self.patterns[language].items():
                match = re.search(pattern, error_message, re.IGNORECASE)
                if match:
                    error_info['type'] = error_type
                    error_info['message'] = match.group(1) if match.groups() else error_message
                    error_info['patterns'].append(error_type)
                    break
        
        # Buscar patrones generales si no se encontró uno específico
        if error_info['type'] == 'unknown':
            for error_type, pattern in self.patterns['general'].items():
                match = re.search(pattern, error_message, re.IGNORECASE)
                if match:
                    error_info['type'] = error_type
                    error_info['patterns'].append(error_type)
                    break
        
        return error_info
    
    def _determine_severity(self, error_message: str, error_info: Dict[str, Any]) -> ErrorSeverity:
        """Determinar la severidad del error"""
        error_lower = error_message.lower()
        error_type_lower = error_info['type'].lower()
        
        # Verificar reglas de severidad crítica
        for pattern in self.severity_rules[ErrorSeverity.CRITICAL.value]:
            if pattern in error_lower or pattern in error_type_lower:
                return ErrorSeverity.CRITICAL
        
        # Verificar reglas de severidad alta
        for pattern in self.severity_rules[ErrorSeverity.HIGH.value]:
            if pattern in error_lower or pattern in error_type_lower:
                return ErrorSeverity.HIGH
        
        # Verificar reglas de severidad media
        for pattern in self.severity_rules[ErrorSeverity.MEDIUM.value]:
            if pattern in error_lower or pattern in error_type_lower:
                return ErrorSeverity.MEDIUM
        
        # Verificar reglas de severidad baja
        for pattern in self.severity_rules[ErrorSeverity.LOW.value]:
            if pattern in error_lower or pattern in error_type_lower:
                return ErrorSeverity.LOW
        
        # Severidad por defecto
        return ErrorSeverity.MEDIUM
    
    def _determine_category(self, error_message: str, error_info: Dict[str, Any]) -> ErrorCategory:
        """Determinar la categoría del error"""
        error_lower = error_message.lower()
        
        # Buscar coincidencias en patrones de categoría
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if pattern in error_lower:
                    return ErrorCategory(category)
        
        # Categoría por defecto basada en el tipo de error
        error_type = error_info['type']
        if 'syntax' in error_type:
            return ErrorCategory.SYNTAX
        elif 'timeout' in error_type or 'performance' in error_type:
            return ErrorCategory.PERFORMANCE
        elif 'connection' in error_type or 'network' in error_type:
            return ErrorCategory.NETWORK
        elif 'memory' in error_type or 'disk' in error_type:
            return ErrorCategory.RESOURCE
        elif 'permission' in error_type or 'security' in error_type:
            return ErrorCategory.SECURITY
        elif 'sql' in error_type or 'database' in error_type:
            return ErrorCategory.DATABASE
        else:
            return ErrorCategory.RUNTIME
    
    def _suggest_actions(self, error_info: Dict[str, Any], 
                        severity: ErrorSeverity, 
                        category: ErrorCategory) -> List[str]:
        """Sugerir acciones basadas en el error"""
        actions = []
        error_type = error_info['type']
        
        # Acciones generales basadas en severidad
        if severity == ErrorSeverity.CRITICAL:
            actions.append('immediate_attention')
            actions.append('notify_team')
        elif severity == ErrorSeverity.HIGH:
            actions.append('review_urgently')
        
        # Acciones específicas basadas en tipo de error
        if 'syntax' in error_type:
            actions.append('check_code_syntax')
            actions.append('validate_variables')
        elif 'type' in error_type:
            actions.append('validate_data_types')
            actions.append('check_variable_assignment')
        elif 'null' in error_type:
            actions.append('add_null_checks')
            actions.append('validate_object_existence')
        elif 'memory' in error_type:
            actions.append('check_memory_usage')
            actions.append('review_resource_allocation')
        elif 'timeout' in error_type:
            actions.append('increase_timeout')
            actions.append('optimize_performance')
        elif 'permission' in error_type:
            actions.append('check_file_permissions')
            actions.append('validate_user_access')
        
        # Acción por defecto si no hay acciones específicas
        if not actions:
            actions.append('review_manually')
        
        return actions
    
    def _generate_error_id(self) -> str:
        """Generar ID único para el error"""
        import uuid
        return f"err_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
    
    def batch_process_errors(self, error_messages: List[str], 
                           language: str = 'python') -> List[Dict[str, Any]]:
        """
        Procesar múltiples errores en lote
        
        Args:
            error_messages: Lista de mensajes de error
            language: Lenguaje de programación
            
        Returns:
            Lista de errores procesados
        """
        processed_errors = []
        
        for error_message in error_messages:
            processed_error = self.process_error(error_message, language)
            processed_errors.append(processed_error)
        
        return processed_errors

# Singleton para uso global
_error_processor = None

def get_error_processor() -> ErrorProcessor:
    """Obtener instancia singleton del procesador de errores"""
    global _error_processor
    
    if _error_processor is None:
        _error_processor = ErrorProcessor()
    
    return _error_processor