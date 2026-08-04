import pika
import json
import os
from dotenv import load_dotenv

load_dotenv()

def callback(ch, method, properties, body):
    """Callback function triggered when a message arrives."""
    try:
        data = json.loads(body)
        routing_key = method.routing_key
        
        if routing_key == "product.price_updated":
            print(f"🏷️ [ESL] Updating shelf for product {data.get('barcode')} to KES {data.get('new_price')}")
            print(f"🌐 [Marketplace] Sending HTTP PATCH to external API for SKU: {data.get('barcode')}")
            print(f"   → Store ID: {data.get('store_id')}")
            print("   → ESL sync status: PENDING\n")
            
        elif routing_key == "product.created":
            print(f"📦 [Inventory] New product added: {data.get('name')} (Barcode: {data.get('barcode')})")
            print(f"   → Shard: {data.get('shard')}\n")
            
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse message: {e}")

def start_consumer():
    """Starts the RabbitMQ consumer."""
    url = os.getenv("RABBITMQ_URL")
    if not url:
        raise ValueError("RABBITMQ_URL not set in .env file!")
    
    params = pika.URLParameters(url)
    params.heartbeat = 600
    
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    
    # Declare exchange (same as publisher)
    channel.exchange_declare(
        exchange='retail.events',
        exchange_type='topic',
        durable=True
    )
    
    # Declare queue and bind to routing keys
    queue = channel.queue_declare('esl_queue', durable=True)
    channel.queue_bind(exchange='retail.events', queue='esl_queue', routing_key='product.*')
    
    # Start consuming
    channel.basic_consume(
        queue='esl_queue',
        on_message_callback=callback,
        auto_ack=True
    )
    
    print("=" * 60)
    print("🎧 ESL/Marketplace Consumer is running.")
    print("📡 Listening for events on exchange: retail.events")
    print("🔗 Routing keys: product.*")
    print("=" * 60)
    print("Waiting for price updates or product creations...\n")
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n🛑 Consumer stopped by user.")
        connection.close()

if __name__ == "__main__":
    start_consumer()