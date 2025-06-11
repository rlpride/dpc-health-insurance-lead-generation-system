"""Base worker class for processing tasks from message queue."""

import json
import logging
import signal
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from uuid import uuid4

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseWorker(ABC):
    """Abstract base class for all workers."""
    
    def __init__(self, worker_id: Optional[str] = None):
        """Initialize the base worker."""
        self.worker_id = worker_id or f"{self.worker_name}_{uuid4().hex[:8]}"
        self.settings = settings
        self.connection = None
        self.channel = None
        self.running = False
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    @property
    @abstractmethod
    def worker_name(self) -> str:
        """Return the name of this worker type."""
        pass
    
    @property
    @abstractmethod
    def queue_name(self) -> str:
        """Return the name of the queue this worker consumes from."""
        pass
    
    @property
    def exchange_name(self) -> str:
        """Return the name of the exchange to use."""
        return "lead_generation"
    
    @property
    def routing_key(self) -> str:
        """Return the routing key for this worker's queue."""
        return f"{self.queue_name}.tasks"
    
    def connect(self) -> None:
        """Connect to RabbitMQ."""
        try:
            parameters = pika.URLParameters(str(self.settings.rabbitmq_url))
            parameters.heartbeat = self.settings.rabbitmq_heartbeat
            parameters.connection_attempts = self.settings.rabbitmq_connection_attempts
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='topic',
                durable=True
            )
            
            # Declare queue
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True,
                arguments={
                    'x-max-length': 10000,
                    'x-message-ttl': 86400000,  # 24 hours
                    'x-dead-letter-exchange': f'{self.exchange_name}.dlx'
                }
            )
            
            # Bind queue to exchange
            self.channel.queue_bind(
                exchange=self.exchange_name,
                queue=self.queue_name,
                routing_key=self.routing_key
            )
            
            # Set QoS
            self.channel.basic_qos(prefetch_count=1)
            
            logger.info(f"{self.worker_name} connected to RabbitMQ")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from RabbitMQ."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info(f"{self.worker_name} disconnected from RabbitMQ")
    
    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"{self.worker_name} received signal {signum}, shutting down...")
        self.running = False
        self.disconnect()
        sys.exit(0)
    
    def consume_messages(self, callback: Callable) -> None:
        """Start consuming messages from the queue."""
        try:
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=callback,
                auto_ack=False
            )
            
            logger.info(f"{self.worker_name} started consuming from {self.queue_name}")
            self.running = True
            self.channel.start_consuming()
            
        except Exception as e:
            logger.error(f"Error consuming messages: {str(e)}")
            raise
    
    def acknowledge_message(self, delivery_tag: int) -> None:
        """Acknowledge a message."""
        self.channel.basic_ack(delivery_tag=delivery_tag)
    
    def reject_message(self, delivery_tag: int, requeue: bool = False) -> None:
        """Reject a message."""
        self.channel.basic_reject(delivery_tag=delivery_tag, requeue=requeue)
    
    def publish_message(self, message: Dict[str, Any], routing_key: str, 
                       exchange: Optional[str] = None) -> None:
        """Publish a message to an exchange."""
        exchange = exchange or self.exchange_name
        
        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(message),
            properties=BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json',
                timestamp=int(datetime.utcnow().timestamp())
            )
        )
    
    @abstractmethod
    def process_message(self, body: Dict[str, Any]) -> bool:
        """
        Process a single message.
        
        Returns:
            bool: True if message was processed successfully, False otherwise
        """
        pass
    
    def handle_message(self, channel: BlockingChannel, method: Basic.Deliver,
                      properties: BasicProperties, body: bytes) -> None:
        """Handle incoming message from RabbitMQ."""
        try:
            # Parse message body
            message = json.loads(body)
            logger.info(f"{self.worker_name} processing message: {method.delivery_tag}")
            
            # Process the message
            success = self.process_message(message)
            
            if success:
                # Acknowledge the message
                self.acknowledge_message(method.delivery_tag)
                logger.info(f"{self.worker_name} successfully processed message: {method.delivery_tag}")
            else:
                # Reject and requeue the message
                self.reject_message(method.delivery_tag, requeue=True)
                logger.warning(f"{self.worker_name} failed to process message: {method.delivery_tag}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {str(e)}")
            self.reject_message(method.delivery_tag, requeue=False)
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            self.reject_message(method.delivery_tag, requeue=True)
    
    def run(self) -> None:
        """Run the worker."""
        logger.info(f"Starting {self.worker_name} with ID: {self.worker_id}")
        
        try:
            self.connect()
            self.consume_messages(self.handle_message)
            
        except KeyboardInterrupt:
            logger.info(f"{self.worker_name} interrupted by user")
            
        except Exception as e:
            logger.error(f"{self.worker_name} error: {str(e)}")
            
        finally:
            self.disconnect() 