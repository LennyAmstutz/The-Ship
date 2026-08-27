import json
import pika
from config import consume_host, consume_port, SCAN_QUEUE, RABBITMQ_USER, RABBITMQ_PASS


def _connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=consume_host,
        port=consume_port,
        credentials=credentials,
    )
    return pika.BlockingConnection(parameters)


def listen_for_scans(on_scan):

    connection = _connection()
    channel = connection.channel()
    channel.queue_declare(queue=SCAN_QUEUE, durable=True)

    def _callback(ch, method, properties, body):
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = body.decode()
        on_scan(data)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=SCAN_QUEUE, on_message_callback=_callback)

    print(f"[scanner] warte auf Nachrichten auf '{SCAN_QUEUE}' ...")
    channel.start_consuming()