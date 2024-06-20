import json
import logging
import os
import secrets
import uuid
from enum import Enum
from typing import List, Dict

from google.protobuf.json_format import MessageToJson, MessageToDict
from kafka import KafkaAdminClient
from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka import TopicPartition
from kafka.protocol.message import Message as KafkaMessage

from utils.dates import get_iso8601

logger = logging.getLogger()


class TopicEncoding(Enum):
    """
    Topic Encoding arguments:
    1 - content_type
    2 - value_serializer
    3 - value_deserializer
    """

    JSON = (b"application/json", lambda v: json.dumps(v).encode("utf-8"), lambda v: json.loads(v.decode("utf-8")))
    PROTOBUF = (b"application/protobuf", None, None)
    NONE = (None, None, None)

    def __repr__(self):
        return f"{vars(self)}"


class KafkaManager:
    events: List[KafkaMessage]
    _offset_last_send: Dict[int, int]  # partition -> offset

    _event_json_preserving_proto_field_name: bool
    _event_json_use_integers_for_enums: bool

    def __init__(
        self,
        topic: str,
        host: str = "localhost:9092",
        topic_encoding: TopicEncoding = TopicEncoding.JSON,
        tc_id=0,
        account_id=None,
        event_json_preserving_proto_field_name: bool = True,
        event_json_use_integers_for_enums: bool = True,
    ):
        """
        KafkaManager class to send and retrieve messages on topic indicated in arguments.

        ARGUMENTS
        topic - topic on which we send / retrieve messages
        host - optional - Kafka host on which we want to send / retrieve messages, default: localhost:9092
        topic_encoding - optional - encoding format for messages, default: JSON

        FUNCTIONS
        send_message - send message on topic
        read_message - retrieve message from topic if message key is matching

        ENVIRONMENT VARIABLES
        KAFKA_BOOTSTRAP_SERVERS - optional - list of boostrap servers to which Kafka listen
        """
        self.tc_id = tc_id
        self.trace_id = self.generate_trace_id(tc_id)
        self.__topic_encoding = topic_encoding
        self.__content_type, self.__serializer, self.__deserializer = self.__topic_encoding.value
        self.kafka_hosts = hosts.split(",") if (hosts := os.getenv("KAFKA_BOOTSTRAP_SERVERS")) else [host]
        self.topic = topic
        self.tp = TopicPartition(topic=self.topic, partition=0)

        self.admin_client = self.__create_admin_client()
        self.producer = self.__create_producer()
        self.consumer = self.__create_consumer()
        if account_id is None:
            self.account_id = os.getenv("CVSA_APPLICATION_CUSTOMER_ID", self.generate_id_key())
        else:
            self.account_id = account_id
        self.cam_account_id = self.generate_key()
        self.csp_account_id = self.generate_key()
        self.correlation_id = self.generate_key()
        self._offset_last_send = {}
        self.cvsa_id = None

        self._event_json_preserving_proto_field_name = event_json_preserving_proto_field_name
        self._event_json_use_integers_for_enums = event_json_use_integers_for_enums

        self.events = []
        self.set_offset_last_send_to_latest()

    def __repr__(self):
        return f"{vars(self)}"

    def generate_trace_id(self, testcase_id: int):
        tc_id = str(testcase_id).zfill(4)
        trace_id = f"{tc_id[:4]}{secrets.token_hex(6)}"
        span_id = secrets.token_hex(8)
        key = f"b3={trace_id}-{span_id}"
        return key

    def generate_key(self):
        key = bytes(str(f"{uuid.uuid4()}"), "utf-8")
        return key

    def generate_id_key(self):
        key = bytes(str(f"{uuid.uuid4().hex}"), "utf-8")
        return key

    def __generate_headers(self, user_headers):
        headers_list = [(k, v) for k, v in user_headers.items()]
        const_headers = [
            ("ce_specversion", b"1.0"),
            ("content-type", self.__content_type),
            ("ce_source", bytes(f"QA_{self.topic}", "utf-8")),
            ("ce_time", bytes(get_iso8601(), "utf-8")),
            ("ce_tracestate", bytes(self.trace_id, "utf-8")),
        ]
        return [*headers_list, *const_headers]

    def __generate_settings_for_ssl(self):
        if os.getenv("KAFKA_SSL_MODE_ENABLED") == "true":
            return {"security_protocol": "SSL", "ssl_check_hostname": False}
        else:
            return {"security_protocol": "PLAINTEXT"}

    def __create_consumer(self):
        logger.info(f"Creating kafka consumer for topic {self.topic}")
        consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=self.kafka_hosts,
            consumer_timeout_ms=1000,
            value_deserializer=self.__deserializer,
            **self.__generate_settings_for_ssl(),
        )
        logger.info(f"Kafka consumer for topic {self.topic} created")
        return consumer

    def __create_admin_client(self):
        logger.info("Creating kafka admin client")
        admin_client = KafkaAdminClient(
            bootstrap_servers=self.kafka_hosts,
            **self.__generate_settings_for_ssl(),
        )
        logger.info("Kafka admin client created")
        return admin_client

    def __create_producer(self):
        logger.info("Creating kafka producer")
        producer = KafkaProducer(
            bootstrap_servers=self.kafka_hosts,
            value_serializer=self.__serializer,
            acks="all",
            **self.__generate_settings_for_ssl(),
        )
        logger.info("Kafka producer created")
        return producer

    def __serialize_message(self, event, uint64_fields: list = None):
        if self.__topic_encoding == TopicEncoding.JSON:
            json_msg = MessageToJson(
                event,
                preserving_proto_field_name=self._event_json_preserving_proto_field_name,
                use_integers_for_enums=self._event_json_use_integers_for_enums,
            )
            event_data = json.loads(json_msg)
            if uint64_fields:
                for field in uint64_fields:
                    try:
                        event_data[field] = int(event_data[field])
                    except KeyError as e:
                        logger.warn(f"missing key: {e}")
            return event_data
        if self.__topic_encoding == TopicEncoding.PROTOBUF:
            return event.SerializeToString()
        raise NotImplementedError(f"Not implemented topic encoding {self.__topic_encoding}")

    def send_message(
        self, event, user_headers: dict = None, uint64_fields: list = None, partition=None, update_offsets=True
    ):
        """
        This function is used to send message

        args:
        event - constructed from protobuf file
        user_headers - optional. Possibility to add aditional headers to basic generated headers
        uint64_fileds - optional. MessageToJson not supporting uint64. Explicity field list will be converted to python
        long.
        partition - optional. Partition on which message will be sent.
        """
        if update_offsets:
            self.set_offset_last_send_to_latest()
        event_raw = MessageToDict(event, preserving_proto_field_name=True, use_integers_for_enums=False)
        logger.info(f"Send event: {event_raw}, headers:{user_headers}")
        if user_headers is None:
            user_headers = {}
        message = self.__serialize_message(event, uint64_fields)
        headers = self.__generate_headers(user_headers)
        self.producer.send(self.topic, value=message, key=self.account_id, headers=headers, partition=partition)
        self.producer.flush()
        logger.info(f"Event sent: {event_raw}, headers:{headers}")

    def __consume_new_messages_and_update_events(self):
        try:
            for msg in self.consumer:
                if not msg.key or self.account_id not in msg.key:
                    continue
                self.events.append(msg)
        except StopIteration:
            # read all messages up until latest offset on all partitions
            pass

    def get_offsets(self) -> Dict[int, int]:
        return self._offset_last_send.copy()

    def set_offsets(self, offsets: Dict[int, int]) -> None:
        self._offset_last_send = offsets.copy()

    def set_offset_at_event(self, event: KafkaMessage) -> None:
        self._offset_last_send[event.partition] = event.offset

    def set_offset_after_event(self, event: KafkaMessage) -> None:
        self._offset_last_send[event.partition] = event.offset + 1

    def set_offset_last_send_to_latest(self):
        if not self._offset_last_send:
            self._offset_last_send = {}
        self.__consume_new_messages_and_update_events()
        for event in self.events:
            t = self._offset_last_send[event.partition] if event.partition in self._offset_last_send else 0
            self._offset_last_send[event.partition] = event.offset if event.offset > t else t

    def read_messages(self, from_offset: Dict[int, int] = None) -> List[KafkaMessage]:
        """
        This function is used to read messages on kafka and looking for matching key (account id)

        args:
        from_offset - adds filter for the returned events, based on the offset
        """
        self.__consume_new_messages_and_update_events()

        def reduce(msg) -> bool:
            if from_offset:
                if msg.partition in from_offset and from_offset[msg.partition] > msg.offset:
                    return False
            return True

        account_events = filter(lambda msg: reduce(msg), self.events)
        return list(account_events)

    def consumer_group_offset(self, group_id, partition):
        """
        This function is used to collect the offset and end-offset for a consumer group and partition

        args:
        group_id - Kafka consumer group id
        partition - Kafka partition number
        """
        offset = -1
        last_offset_per_partition = -1
        partitions = [TopicPartition(self.topic, partition)]
        topic_partitions = self.admin_client.list_consumer_group_offsets(group_id=group_id, partitions=partitions)
        for p, metadata in topic_partitions.items():
            if p[0] == self.topic:
                offset = metadata[0]
                break
        if offset != -1:
            partitions = [TopicPartition(self.topic, part) for part in self.consumer.partitions_for_topic(self.topic)]
            last_offset = self.consumer.end_offsets(partitions)
            for topic_key, value in last_offset.items():
                last_offset_per_partition = value
        return offset, last_offset_per_partition
