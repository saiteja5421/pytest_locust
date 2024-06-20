from lib.platform.kafka.kafka_manager import KafkaManager
from typing import Optional


def new_kafka_lifecycle_events(tc_id: int, account_id: Optional[str] = None) -> KafkaManager:
    return KafkaManager(
        topic="cvsa.lifecycle.events",
        tc_id=tc_id,
        event_json_preserving_proto_field_name=False,
        event_json_use_integers_for_enums=False,
        account_id=account_id,
    )
