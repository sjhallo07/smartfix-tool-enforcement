"""
SMARTFIX Tool Enforcement - Authorization Manager
Sistema de gestión de aprobaciones humanas para reparaciones automáticas
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from django.db import models
from django.conf import settings

logger = logging.getLogger("smartfix.authorization")

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class AuthorizationManager:
    """Gestor de autorizaciones para reparaciones automáticas"""
    
    def __init__(self):
        self.pending_approvals = {}
        self.notification_handlers = {
            'email': self._send_email_notification,
            'slack': self._send_slack_notification,
            'teams': self._send_teams_notification,
            'sms': self._send_sms_notification,
            'whatsapp': self._send_whatsapp_notification
        }
    
    def request_approval(self, repair_data: Dict[str, Any], 
                        recipients: List[str], 
                        channels: List[str] = ['email'],
                        timeout_hours: int = 24) -> str:
        """
        Solicitar aprobación para una reparación automática
        
        Args:
            repair_data: Datos de la reparación a aprobar
            recipients: Lista de destinatarios para la aprobación
            channels: Canales de notificación
            timeout_hours: Tiempo máximo de espera para aprobación
        
        Returns:
            ID de la solicitud de aprobación
        """
        try:
            # Generar ID único para la solicitud
            approval_id = self._generate_approval_id()
            
            # Crear registro de aprobación
            approval_record = {
                'id': approval_id,
                'repair_data': repair_data,
                'recipients': recipients,
                'channels': channels,
                'status': ApprovalStatus.PENDING.value,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=timeout_hours)).isoformat(),
                'responses': [],
                'timeout_hours': timeout_hours
            }
            
            # Almacenar solicitud
            self.pending_approvals[approval_id] = approval_record
            
            # Enviar notificaciones
            self._send_notifications(approval_record)
            
            logger.info(f"Solicitud de aprobación creada: {approval_id}")
            return approval_id
            
        except Exception as e:
            logger.error(f"Error creando solicitud de aprobación: {str(e)}")
            raise
    
    def check_approval_status(self, approval_id: str) -> Dict[str, Any]:
        """
        Verificar el estado de una solicitud de aprobación
        
        Args:
            approval_id: ID de la solicitud
            
        Returns:
            Estado actual de la aprobación
        """
        if approval_id not in self.pending_approvals:
            return {'status': 'not_found', 'message': 'Approval request not found'}
        
        approval = self.pending_approvals[approval_id]
        
        # Verificar si ha expirado
        if self._is_expired(approval):
            approval['status'] = ApprovalStatus.EXPIRED.value
            return approval
        
        return approval
    
    def process_approval_response(self, approval_id: str, 
                                 responder: str, 
                                 decision: str, 
                                 comments: str = "") -> bool:
        """
        Procesar una respuesta de aprobación
        
        Args:
            approval_id: ID de la solicitud
            responder: Persona que responde
            decision: Decisión (approve/reject)
            comments: Comentarios adicionales
            
        Returns:
            True si se procesó correctamente
        """
        try:
            if approval_id not in self.pending_approvals:
                return False
            
            approval = self.pending_approvals[approval_id]
            
            # Verificar si ya fue procesada
            if approval['status'] != ApprovalStatus.PENDING.value:
                return False
            
            # Registrar respuesta
            response = {
                'responder': responder,
                'decision': decision.lower(),
                'comments': comments,
                'timestamp': datetime.now().isoformat()
            }
            
            approval['responses'].append(response)
            
            # Actualizar estado basado en la decisión
            if decision.lower() == 'approve':
                approval['status'] = ApprovalStatus.APPROVED.value
                logger.info(f"Aprobación {approval_id} aprobada por {responder}")
            else:
                approval['status'] = ApprovalStatus.REJECTED.value
                logger.info(f"Aprobación {approval_id} rechazada por {responder}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error procesando respuesta de aprobación: {str(e)}")
            return False
    
    def _send_notifications(self, approval_record: Dict[str, Any]):
        """Enviar notificaciones por los canales configurados"""
        for channel in approval_record['channels']:
            if channel in self.notification_handlers:
                try:
                    self.notification_handlers[channel](approval_record)
                except Exception as e:
                    logger.error(f"Error enviando notificación por {channel}: {str(e)}")
    
    def _send_email_notification(self, approval_record: Dict[str, Any]):
        """Enviar notificación por email"""
        # Configuración del servidor SMTP
        smtp_config = getattr(settings, 'EMAIL_CONFIG', {})
        
        if not smtp_config:
            logger.warning("Configuración de email no encontrada")
            return
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = smtp_config.get('from_address', 'noreply@smartfix.dev')
        msg['To'] = ', '.join(approval_record['recipients'])
        msg['Subject'] = f"SMARTFIX - Aprobación Requerida para Reparación #{approval_record['id']}"
        
        # Crear cuerpo del mensaje
        body = self._generate_email_body(approval_record)
        msg.attach(MIMEText(body, 'html'))
        
        # Enviar email
        with smtplib.SMTP(smtp_config.get('smtp_server'), smtp_config.get('smtp_port', 587)) as server:
            server.starttls()
            server.login(smtp_config.get('username'), smtp_config.get('password'))
            server.send_message(msg)
        
        logger.info(f"Notificación email enviada para aprobación {approval_record['id']}")
    
    def _generate_email_body(self, approval_record: Dict[str, Any]) -> str:
        """Generar cuerpo del email de notificación"""
        repair_data = approval_record['repair_data']
        
        return f"""
        <html>
        <body>
            <h2>SMARTFIX - Aprobación de Reparación Requerida</h2>
            <p>Se requiere su aprobación para una reparación automática detectada por el sistema SMARTFIX.</p>
            
            <h3>Detalles de la Reparación:</h3>
            <ul>
                <li><strong>ID:</strong> {approval_record['id']}</li>
                <li><strong>Tipo:</strong> {repair_data.get('type', 'N/A')}</li>
                <li><strong>Archivo:</strong> {repair_data.get('file', 'N/A')}</li>
                <li><strong>Línea:</strong> {repair_data.get('line', 'N/A')}</li>
                <li><strong>Severidad:</strong> {repair_data.get('severity', 'N/A')}</li>
                <li><strong>Descripción:</strong> {repair_data.get('description', 'N/A')}</li>
            </ul>
            
            <h3>Cambios Propuestos:</h3>
            <pre>{repair_data.get('solution', 'N/A')}</pre>
            
            <h3>Acciones Requeridas:</h3>
            <p>Por favor, apruebe o rechace esta reparación antes de: {approval_record['expires_at']}</p>
            
            <p>
                <a href="{settings.BASE_URL}/approve/{approval_record['id']}?decision=approve" 
                   style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                   ✅ Aprobar Reparación
                </a>
                <a href="{settings.BASE_URL}/approve/{approval_record['id']}?decision=reject" 
                   style="background-color: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">
                   ❌ Rechazar Reparación
                </a>
            </p>
            
            <hr>
            <p><small>Este es un mensaje automático del sistema SMARTFIX Tool Enforcement. Por favor no responda a este email.</small></p>
        </body>
        </html>
        """
    
    def _send_slack_notification(self, approval_record: Dict[str, Any]):
        """Enviar notificación por Slack"""
        slack_config = getattr(settings, 'SLACK_CONFIG', {})
        
        if not slack_config:
            logger.warning("Configuración de Slack no encontrada")
            return
        
        message = {
            "text": "SMARTFIX - Aprobación de Reparación Requerida",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*SMARTFIX - Aprobación de Reparación Requerida*\n\nSe requiere su aprobación para una reparación automática."
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*ID:*\n{approval_record['id']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Tipo:*\n{approval_record['repair_data'].get('type', 'N/A')}"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Aprobar"
                            },
                            "value": f"approve_{approval_record['id']}",
                            "action_id": "approval_approve"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "❌ Rechazar"
                            },
                            "value": f"reject_{approval_record['id']}",
                            "action_id": "approval_reject"
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(
            slack_config.get('webhook_url'),
            json=message,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Notificación Slack enviada para aprobación {approval_record['id']}")
        else:
            logger.error(f"Error enviando notificación Slack: {response.status_code}")
    
    def _send_teams_notification(self, approval_record: Dict[str, Any]):
        """Enviar notificación por Microsoft Teams"""
        # Implementación para Microsoft Teams
        pass
    
    def _send_sms_notification(self, approval_record: Dict[str, Any]):
        """Enviar notificación por SMS"""
        # Implementación para SMS
        pass
    
    def _send_whatsapp_notification(self, approval_record: Dict[str, Any]):
        """Enviar notificación por WhatsApp"""
        # Implementación para WhatsApp
        pass
    
    def _generate_approval_id(self) -> str:
        """Generar ID único para la solicitud de aprobación"""
        import uuid
        return f"apr_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    
    def _is_expired(self, approval_record: Dict[str, Any]) -> bool:
        """Verificar si la solicitud ha expirado"""
        expires_at = datetime.fromisoformat(approval_record['expires_at'])
        return datetime.now() > expires_at
    
    def cleanup_expired_approvals(self):
        """Limpiar solicitudes de aprobación expiradas"""
        expired_ids = []
        
        for approval_id, approval in self.pending_approvals.items():
            if self._is_expired(approval) and approval['status'] == ApprovalStatus.PENDING.value:
                approval['status'] = ApprovalStatus.EXPIRED.value
                expired_ids.append(approval_id)
                logger.info(f"Aprobación {approval_id} marcada como expirada")
        
        return expired_ids

# Singleton para uso global
_authorization_manager = None

def get_authorization_manager() -> AuthorizationManager:
    """Obtener instancia singleton del gestor de autorizaciones"""
    global _authorization_manager
    
    if _authorization_manager is None:
        _authorization_manager = AuthorizationManager()
    
    return _authorization_manager