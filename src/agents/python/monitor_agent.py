"""
SMARTFIX Tool Enforcement - Python Monitor Agent
Agente de monitoreo para aplicaciones Python
"""

import logging
import sys
import traceback
import threading
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger("smartfix.agent.python")

class PythonMonitorAgent:
    """Agente de monitoreo para aplicaciones Python"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_monitoring = False
        self.original_excepthook = None
        self.error_callbacks = []
        self.performance_metrics = {}
        self.thread = None
        
        # Configuración por defecto
        self.check_interval = config.get('check_interval', 30)
        self.max_memory_usage = config.get('max_memory_usage', 85)  # Porcentaje
        self.max_cpu_usage = config.get('max_cpu_usage', 80)  # Porcentaje
        
        logger.info("Python Monitor Agent inicializado")
    
    def start_monitoring(self):
        """Iniciar monitoreo de la aplicación"""
        if self.is_monitoring:
            logger.warning("El monitoreo ya está en ejecución")
            return False
        
        try:
            # Configurar hook para excepciones no capturadas
            self._setup_exception_hook()
            
            # Iniciar monitoreo de rendimiento
            self._start_performance_monitoring()
            
            # Iniciar monitoreo de dependencias
            self._start_dependency_monitoring()
            
            self.is_monitoring = True
            logger.info("Monitoreo de aplicación iniciado")
            return True
            
        except Exception as e:
            logger.error(f"Error iniciando monitoreo: {str(e)}")
            return False
    
    def stop_monitoring(self):
        """Detener monitoreo de la aplicación"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        # Restaurar hook original de excepciones
        if self.original_excepthook:
            sys.excepthook = self.original_excepthook
        
        # Detener hilos de monitoreo
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        logger.info("Monitoreo de aplicación detenido")
    
    def register_error_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Registrar callback para manejo de errores
        
        Args:
            callback: Función a llamar cuando se detecte un error
        """
        self.error_callbacks.append(callback)
        logger.info(f"Callback de error registrado: {callback.__name__}")
    
    def _setup_exception_hook(self):
        """Configurar hook para capturar excepciones no capturadas"""
        self.original_excepthook = sys.excepthook
        
        def smartfix_excepthook(exctype, value, tb):
            # Capturar información de la excepción
            error_info = self._capture_exception_info(exctype, value, tb)
            
            # Llamar callbacks registrados
            for callback in self.error_callbacks:
                try:
                    callback(error_info)
                except Exception as e:
                    logger.error(f"Error en callback de error: {str(e)}")
            
            # Llamar al excepthook original
            self.original_excepthook(exctype, value, tb)
        
        sys.excepthook = smartfix_excepthook
        logger.debug("Hook de excepciones configurado")
    
    def _capture_exception_info(self, exctype, value, tb) -> Dict[str, Any]:
        """Capturar información de una excepción"""
        try:
            # Obtener traceback completo
            tb_lines = traceback.format_exception(exctype, value, tb)
            traceback_text = ''.join(tb_lines)
            
            # Extraer información del frame actual
            frame = tb.tb_frame if tb else None
            frame_info = self._extract_frame_info(frame) if frame else {}
            
            # Crear estructura de información de error
            error_info = {
                'timestamp': datetime.now().isoformat(),
                'type': exctype.__name__ if exctype else 'Unknown',
                'message': str(value) if value else 'No message',
                'traceback': traceback_text,
                'file': frame_info.get('file', 'unknown'),
                'line': frame_info.get('line', 'unknown'),
                'function': frame_info.get('function', 'unknown'),
                'code_context': frame_info.get('code_context', []),
                'locals': self._sanitize_locals(frame_info.get('locals', {})),
                'language': 'python',
                'severity': 'high'
            }
            
            logger.info(f"Excepción capturada: {error_info['type']} - {error_info['message']}")
            return error_info
            
        except Exception as e:
            logger.error(f"Error capturando información de excepción: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'type': 'monitoring_error',
                'message': f'Error capturing exception: {str(e)}',
                'language': 'python',
                'severity': 'medium'
            }
    
    def _extract_frame_info(self, frame) -> Dict[str, Any]:
        """Extraer información de un frame de ejecución"""
        try:
            frame_info = {
                'file': frame.f_code.co_filename,
                'line': frame.f_lineno,
                'function': frame.f_code.co_name,
                'locals': {}
            }
            
            # Capturar variables locales (con sanitización)
            for var_name, var_value in frame.f_locals.items():
                try:
                    # Limitar el tamaño de los valores y evitar datos sensibles
                    if isinstance(var_value, (str, bytes)):
                        if len(str(var_value)) > 100:
                            frame_info['locals'][var_name] = f"{str(var_value)[:100]}... [truncated]"
                        else:
                            frame_info['locals'][var_name] = str(var_value)
                    else:
                        frame_info['locals'][var_name] = str(type(var_value))
                except:
                    frame_info['locals'][var_name] = '[unserializable]'
            
            # Obtener contexto de código
            try:
                import linecache
                lines = linecache.getlines(frame.f_code.co_filename)
                start_line = max(0, frame.f_lineno - 3)
                end_line = min(len(lines), frame.f_lineno + 2)
                frame_info['code_context'] = [
                    f"{i}: {line.strip()}" for i, line in enumerate(lines[start_line:end_line], start_line + 1)
                ]
            except:
                frame_info['code_context'] = []
            
            return frame_info
            
        except Exception as e:
            logger.error(f"Error extrayendo información de frame: {str(e)}")
            return {
                'file': 'unknown',
                'line': 'unknown',
                'function': 'unknown',
                'locals': {},
                'code_context': []
            }
    
    def _sanitize_locals(self, locals_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizar variables locales para evitar datos sensibles"""
        sanitized = {}
        sensitive_patterns = [
            'password', 'secret', 'key', 'token', 'auth', 
            'credential', 'api_key', 'access_key'
        ]
        
        for name, value in locals_dict.items():
            # Omitir variables potencialmente sensibles
            if any(pattern in name.lower() for pattern in sensitive_patterns):
                sanitized[name] = '***REDACTED***'
            else:
                sanitized[name] = value
        
        return sanitized
    
    def _start_performance_monitoring(self):
        """Iniciar monitoreo de rendimiento"""
        def performance_monitor():
            while self.is_monitoring:
                try:
                    self._check_performance()
                    time.sleep(self.check_interval)
                except Exception as e:
                    logger.error(f"Error en monitoreo de rendimiento: {str(e)}")
                    time.sleep(60)  # Esperar antes de reintentar
        
        self.thread = threading.Thread(target=performance_monitor, daemon=True)
        self.thread.start()
        logger.debug("Monitoreo de rendimiento iniciado")
    
    def _check_performance(self):
        """Verificar métricas de rendimiento"""
        try:
            import psutil
            process = psutil.Process()
            
            # Obtener métricas
            memory_usage = process.memory_percent()
            cpu_usage = process.cpu_percent(interval=1)
            thread_count = process.num_threads()
            file_handles = len(process.open_files())
            
            # Almacenar métricas
            self.performance_metrics = {
                'memory_usage': memory_usage,
                'cpu_usage': cpu_usage,
                'thread_count': thread_count,
                'file_handles': file_handles,
                'timestamp': datetime.now().isoformat()
            }
            
            # Verificar umbrales
            if memory_usage > self.max_memory_usage:
                self._handle_performance_issue('high_memory_usage', 
                                              f"Memory usage exceeded threshold: {memory_usage}%")
            
            if cpu_usage > self.max_cpu_usage:
                self._handle_performance_issue('high_cpu_usage', 
                                              f"CPU usage exceeded threshold: {cpu_usage}%")
            
            logger.debug(f"Métricas de rendimiento: {self.performance_metrics}")
            
        except ImportError:
            logger.warning("psutil no instalado, monitoreo de rendimiento limitado")
        except Exception as e:
            logger.error(f"Error verificando rendimiento: {str(e)}")
    
    def _handle_performance_issue(self, issue_type: str, message: str):
        """Manejar issue de rendimiento"""
        performance_issue = {
            'type': issue_type,
            'message': message,
            'metrics': self.performance_metrics,
            'timestamp': datetime.now().isoformat(),
            'severity': 'medium',
            'language': 'python'
        }
        
        # Notificar a callbacks registrados
        for callback in self.error_callbacks:
            try:
                callback(performance_issue)
            except Exception as e:
                logger.error(f"Error en callback de rendimiento: {str(e)}")
    
    def _start_dependency_monitoring(self):
        """Iniciar monitoreo de dependencias"""
        # Implementar monitoreo de versiones de dependencias
        # y detección de vulnerabilidades
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado actual del agente"""
        return {
            'is_monitoring': self.is_monitoring,
            'error_callbacks_count': len(self.error_callbacks),
            'performance_metrics': self.performance_metrics,
            'check_interval': self.check_interval,
            'config': self.config
        }

# Singleton para uso global
_python_agent = None

def get_python_agent(config: Optional[Dict[str, Any]] = None) -> PythonMonitorAgent:
    """Obtener instancia singleton del agente Python"""
    global _python_agent
    
    if _python_agent is None and config is not None:
        _python_agent = PythonMonitorAgent(config)
    
    return _python_agent