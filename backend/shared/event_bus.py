import pika
import json
import os
from dotenv import load_dotenv

load_dotenv()

class EventBus:
    def __init__(self):
        self.url = os.getenv("RABBITMQ_URL")
        if not self.url:
            raise ValueError("RABBITMQ_URL not set in .env file!")
        
        # CloudAMQP uses AMQPS (SSL)
        params = pika.URLParameters(self.url)
        params.heartbeat = 600
        
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()
        self.channel.exchange_declare(
            exchange='retail.events', 
            exchange_type='topic', 
            durable=True
        )

    def publish(self, routing_key: str, data: dict):
        self.channel.basic_publish(
            exchange='retail.events',
            routing_key=routing_key,
            body=json.dumps(data),
            properties=pika.BasicProperties(delivery_mode=2)  # Persistent
        )
        print(f"📤 [Event Bus] Published: {routing_key} -> {data.get('barcode', 'unknown')}")

# Global instance
event_bus = EventBus()