import logging
logger = logging.getLogger(__name__)
try:
    from paho.mqtt.client import Client

    from cndi.binders.message.utils import MessageChannel


    class MqttProducerBinding(MessageChannel):
        def __init__(self, mqttClient: Client):
            self.mqttClient = mqttClient
            self.topic = None

        def send(self, message) -> None:
            self.mqttClient.publish(self.topic, message)

        def close(self):
            self.mqttClient.loop_stop(force=True)

except ImportError:
    logger.info("paho-mqtt library is required to use MQTT binder. Please install it using 'pip install paho-mqtt'.")