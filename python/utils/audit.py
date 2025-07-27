"""
Comprehensive Audit Logging System
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import asyncio
import aiopg

@dataclass
class AuditEvent:
    timestamp: float
    event_type: str
    user_id: Optional[str]
    resource_type: str
    resource_id: str
    action: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

class AuditLogger:
    """Comprehensive audit logging"""
    
    def __init__(self, db_connection_string: str):
        self.db_connection_string = db_connection_string
        self.logger = logging.getLogger('audit')
        self.queue = asyncio.Queue(maxsize=1000)
        self.running = False
    
    async def start(self):
        """Start audit logging service"""
        self.running = True
        asyncio.create_task(self._process_queue())
    
    async def stop(self):
        """Stop audit logging service"""
        self.running = False
    
    async def log_event(self, event: AuditEvent):
        """Log an audit event"""
        try:
            await self.queue.put(event)
        except asyncio.QueueFull:
            self.logger.error("Audit queue full, dropping event")
    
    async def log_trade(self, action: str, token_address: str, amount: float, 
                       whale_wallet: str, success: bool = True, 
                       error: Optional[str] = None):
        """Log trading activity"""
        event = AuditEvent(
            timestamp=time.time(),
            event_type='TRADE',
            user_id='system',
            resource_type='token',
            resource_id=token_address,
            action=action,
            details={
                'amount': amount,
                'whale_wallet': whale_wallet,
                'timestamp': datetime.now().isoformat()
            },
            success=success,
            error_message=error
        )
        await self.log_event(event)
    
    async def log_api_call(self, api_name: str, endpoint: str, 
                          success: bool = True, error: Optional[str] = None):
        """Log API calls"""
        event = AuditEvent(
            timestamp=time.time(),
            event_type='API_CALL',
            user_id='system',
            resource_type='api',
            resource_id=api_name,
            action=endpoint,
            details={
                'endpoint': endpoint,
                'timestamp': datetime.now().isoformat()
            },
            success=success,
            error_message=error
        )
        await self.log_event(event)
    
    async def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security events"""
        event = AuditEvent(
            timestamp=time.time(),
            event_type='SECURITY',
            user_id='system',
            resource_type='security',
            resource_id=event_type,
            action=event_type,
            details=details
        )
        await self.log_event(event)
    
    async def _process_queue(self):
        """Process audit log queue"""
        while self.running:
            try:
                # Get event from queue
                event = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                # Log to file
                self._log_to_file(event)
                
                # Log to database
                await self._log_to_database(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing audit event: {e}")
    
    def _log_to_file(self, event: AuditEvent):
        """Log event to file"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(event.timestamp).isoformat(),
            'event': asdict(event)
        }
        
        # Use structured logging
        self.logger.info(json.dumps(log_entry))
    
    async def _log_to_database(self, event: AuditEvent):
        """Log event to database"""
        try:
            async with aiopg.connect(self.db_connection_string) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO audit_log 
                        (timestamp, event_type, user_id, resource_type, resource_id, 
                         action, details, ip_address, user_agent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        datetime.fromtimestamp(event.timestamp),
                        event.event_type,
                        event.user_id,
                        event.resource_type,
                        event.resource_id,
                        event.action,
                        json.dumps(event.details),
                        event.ip_address,
                        event.user_agent
                    ))
        except Exception as e:
            self.logger.error(f"Failed to log to database: {e}")

# Global audit logger
audit_logger = None

def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global audit_logger
    if audit_logger is None:
        # This should be initialized with actual DB connection
        audit_logger = AuditLogger("postgresql://user:pass@localhost/db")
    return audit_logger
