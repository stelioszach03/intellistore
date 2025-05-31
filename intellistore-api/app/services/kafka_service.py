"""
Kafka service for publishing access logs and tiering events
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional

import structlog
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

logger = structlog.get_logger(__name__)


class KafkaService:
    """Service for interacting with Apache Kafka"""
    
    def __init__(self, bootstrap_servers: List[str], access_logs_topic: str = "access-logs"):
        self.bootstrap_servers = bootstrap_servers
        self.access_logs_topic = access_logs_topic
        self.tiering_topic = "tiering-requests"
        self.migration_topic = "tier-migrations"
        self.producer = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Kafka producer"""
        try:
            # Create Kafka producer
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                compression_type='gzip'
            )
            
            self._initialized = True
            logger.info("Kafka service initialized successfully", 
                       servers=self.bootstrap_servers,
                       topics=[self.access_logs_topic, self.tiering_topic, self.migration_topic])
            
        except Exception as e:
            logger.error("Failed to initialize Kafka service", error=str(e))
            raise
    
    async def publish_access_log(self, event: Dict[str, Any]):
        """Publish access log event to Kafka"""
        if not self._initialized:
            raise Exception("Kafka service not initialized")
        
        try:
            # Add common fields
            event.update({
                "service": "intellistore-api",
                "version": "1.0.0",
                "timestamp": event.get("timestamp", time.time())
            })
            
            # Create message key for partitioning
            key = f"{event.get('user', 'unknown')}:{event.get('bucket', 'unknown')}"
            
            # Send message
            future = self.producer.send(
                topic=self.access_logs_topic,
                key=key,
                value=event
            )
            
            # Wait for send to complete (with timeout)
            record_metadata = future.get(timeout=10)
            
            logger.debug("Access log published", 
                        topic=record_metadata.topic,
                        partition=record_metadata.partition,
                        offset=record_metadata.offset,
                        user=event.get('user'),
                        action=event.get('action'))
            
        except KafkaError as e:
            logger.error("Failed to publish access log", error=str(e), event=event)
            raise
        except Exception as e:
            logger.error("Unexpected error publishing access log", error=str(e), event=event)
            raise
    
    async def publish_tiering_request(self, event: Dict[str, Any]):
        """Publish tiering analysis request to Kafka"""
        if not self._initialized:
            raise Exception("Kafka service not initialized")
        
        try:
            # Add common fields
            event.update({
                "service": "intellistore-api",
                "version": "1.0.0",
                "timestamp": event.get("timestamp", time.time()),
                "event_type": "tiering_request"
            })
            
            # Create message key
            key = f"{event.get('bucket_name')}:{event.get('object_key')}"
            
            # Send message
            future = self.producer.send(
                topic=self.tiering_topic,
                key=key,
                value=event
            )
            
            record_metadata = future.get(timeout=10)
            
            logger.debug("Tiering request published", 
                        topic=record_metadata.topic,
                        partition=record_metadata.partition,
                        offset=record_metadata.offset,
                        bucket=event.get('bucket_name'),
                        object=event.get('object_key'))
            
        except KafkaError as e:
            logger.error("Failed to publish tiering request", error=str(e), event=event)
            raise
        except Exception as e:
            logger.error("Unexpected error publishing tiering request", error=str(e), event=event)
            raise
    
    async def publish_tier_migration_request(self, event: Dict[str, Any]):
        """Publish tier migration request to Kafka"""
        if not self._initialized:
            raise Exception("Kafka service not initialized")
        
        try:
            # Add common fields
            event.update({
                "service": "intellistore-api",
                "version": "1.0.0",
                "timestamp": event.get("timestamp", time.time()),
                "event_type": "tier_migration"
            })
            
            # Create message key
            key = f"{event.get('bucket_name')}:{event.get('object_key')}"
            
            # Send message
            future = self.producer.send(
                topic=self.migration_topic,
                key=key,
                value=event
            )
            
            record_metadata = future.get(timeout=10)
            
            logger.info("Tier migration request published", 
                       topic=record_metadata.topic,
                       partition=record_metadata.partition,
                       offset=record_metadata.offset,
                       bucket=event.get('bucket_name'),
                       object=event.get('object_key'),
                       from_tier=event.get('from_tier'),
                       to_tier=event.get('to_tier'))
            
        except KafkaError as e:
            logger.error("Failed to publish tier migration request", error=str(e), event=event)
            raise
        except Exception as e:
            logger.error("Unexpected error publishing tier migration request", error=str(e), event=event)
            raise
    
    async def publish_notification(self, event: Dict[str, Any]):
        """Publish notification event for WebSocket clients"""
        if not self._initialized:
            raise Exception("Kafka service not initialized")
        
        try:
            # Add common fields
            event.update({
                "service": "intellistore-api",
                "version": "1.0.0",
                "timestamp": event.get("timestamp", time.time()),
                "event_type": "notification"
            })
            
            # Send to notifications topic
            future = self.producer.send(
                topic="notifications",
                value=event
            )
            
            record_metadata = future.get(timeout=10)
            
            logger.debug("Notification published", 
                        topic=record_metadata.topic,
                        notification_type=event.get('type'),
                        message=event.get('message'))
            
        except KafkaError as e:
            logger.error("Failed to publish notification", error=str(e), event=event)
            raise
        except Exception as e:
            logger.error("Unexpected error publishing notification", error=str(e), event=event)
            raise
    
    def create_consumer(self, topics: List[str], group_id: str, **kwargs) -> KafkaConsumer:
        """Create a Kafka consumer"""
        try:
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                **kwargs
            )
            
            logger.info("Kafka consumer created", 
                       topics=topics, 
                       group_id=group_id)
            
            return consumer
            
        except Exception as e:
            logger.error("Failed to create Kafka consumer", 
                        topics=topics, 
                        group_id=group_id, 
                        error=str(e))
            raise
    
    async def consume_messages(self, 
                             topics: List[str], 
                             group_id: str, 
                             message_handler,
                             max_messages: Optional[int] = None):
        """Consume messages from Kafka topics"""
        consumer = None
        try:
            consumer = self.create_consumer(topics, group_id)
            
            message_count = 0
            logger.info("Starting message consumption", 
                       topics=topics, 
                       group_id=group_id)
            
            for message in consumer:
                try:
                    # Process message
                    await message_handler(message)
                    
                    message_count += 1
                    if max_messages and message_count >= max_messages:
                        break
                        
                except Exception as e:
                    logger.error("Error processing message", 
                                topic=message.topic,
                                partition=message.partition,
                                offset=message.offset,
                                error=str(e))
                    continue
            
        except Exception as e:
            logger.error("Error consuming messages", 
                        topics=topics, 
                        group_id=group_id, 
                        error=str(e))
            raise
        finally:
            if consumer:
                consumer.close()
    
    async def get_topic_info(self, topic: str) -> Dict[str, Any]:
        """Get information about a Kafka topic"""
        try:
            # Create a temporary consumer to get metadata
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                consumer_timeout_ms=1000
            )
            
            # Get topic metadata
            metadata = consumer.list_consumer_group_offsets()
            partitions = consumer.partitions_for_topic(topic)
            
            consumer.close()
            
            return {
                "topic": topic,
                "partitions": list(partitions) if partitions else [],
                "partition_count": len(partitions) if partitions else 0
            }
            
        except Exception as e:
            logger.error("Failed to get topic info", topic=topic, error=str(e))
            return {"topic": topic, "error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Kafka service health"""
        try:
            if not self.producer:
                return {"status": "unhealthy", "error": "Producer not initialized"}
            
            # Try to get metadata (this will fail if Kafka is down)
            metadata = self.producer.bootstrap_connected()
            
            return {
                "status": "healthy" if metadata else "unhealthy",
                "bootstrap_servers": self.bootstrap_servers,
                "topics": {
                    "access_logs": self.access_logs_topic,
                    "tiering": self.tiering_topic,
                    "migration": self.migration_topic
                }
            }
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Close Kafka service"""
        if self.producer:
            try:
                # Flush any pending messages
                self.producer.flush(timeout=10)
                self.producer.close(timeout=10)
            except Exception as e:
                logger.error("Error closing Kafka producer", error=str(e))
            finally:
                self.producer = None
        
        self._initialized = False
        logger.info("Kafka service closed")


class KafkaMessageHandler:
    """Base class for Kafka message handlers"""
    
    def __init__(self, kafka_service: KafkaService):
        self.kafka_service = kafka_service
        self.logger = structlog.get_logger(self.__class__.__name__)
    
    async def handle_message(self, message):
        """Handle a Kafka message - to be implemented by subclasses"""
        raise NotImplementedError
    
    async def start_consuming(self, topics: List[str], group_id: str):
        """Start consuming messages"""
        await self.kafka_service.consume_messages(
            topics=topics,
            group_id=group_id,
            message_handler=self.handle_message
        )


class AccessLogHandler(KafkaMessageHandler):
    """Handler for access log messages"""
    
    async def handle_message(self, message):
        """Process access log message"""
        try:
            event = message.value
            
            # Log the access event
            self.logger.info("Access event processed",
                           user=event.get('user'),
                           action=event.get('action'),
                           bucket=event.get('bucket'),
                           object=event.get('object'),
                           timestamp=event.get('timestamp'))
            
            # Here you could:
            # - Store in a database for analytics
            # - Update user activity metrics
            # - Trigger alerts for suspicious activity
            # - Feed data to ML models
            
        except Exception as e:
            self.logger.error("Failed to process access log", error=str(e))
            raise


class TieringRequestHandler(KafkaMessageHandler):
    """Handler for tiering request messages"""
    
    async def handle_message(self, message):
        """Process tiering request message"""
        try:
            event = message.value
            
            self.logger.info("Tiering request processed",
                           bucket=event.get('bucket_name'),
                           object=event.get('object_key'),
                           current_tier=event.get('current_tier'),
                           timestamp=event.get('timestamp'))
            
            # Here you could:
            # - Send to ML inference service
            # - Apply business rules for tiering
            # - Queue for batch processing
            
        except Exception as e:
            self.logger.error("Failed to process tiering request", error=str(e))
            raise