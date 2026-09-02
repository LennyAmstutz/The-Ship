import json
import pika
from config import consume_host, consume_port, RABBITMQ_USER, RABBITMQ_PASS

EXCHANGE = "scanner/detected_objects"

def detected_objects():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=consume_host,
            port=consume_port,
            credentials=credentials,
            socket_timeout=5,
        )
    )
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="fanout")
    queue = channel.queue_declare(queue="", exclusive=True).method.queue
    channel.queue_bind(exchange=EXCHANGE, queue=queue)
    for method_frame, properties, body in channel.consume(queue=queue, auto_ack=True):
        yield json.loads(body.decode("utf-8"))