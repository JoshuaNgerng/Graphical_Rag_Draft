import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker

from app.core.config import get_config, Config

def setup_dramatiq(config: Config):
    broker = RabbitmqBroker(
        host=config.RABBITMQ_HOST,
        port=config.RABBITMQ_PORT,
    )

    dramatiq.set_broker(broker)

setup_dramatiq(get_config())