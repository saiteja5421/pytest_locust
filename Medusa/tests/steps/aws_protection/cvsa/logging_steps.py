import logging

from lib.platform.kafka.kafka_manager import KafkaManager


def get_logging_formatter(kafka_mgr: KafkaManager) -> logging.Formatter:
    message = "%(message)s"
    stream_formatter = logging.Formatter(
        '{"time":"%(asctime)s","trace_id":"'
        + kafka_mgr.trace_id
        + '","tc_id":"'
        + str(kafka_mgr.tc_id)
        + '","customer_id":"'
        + str(kafka_mgr.account_id.decode("utf-8"))
        + '","cvsa_id":"'
        + str(kafka_mgr.cvsa_id)
        + '","cam_account_id":"'
        + str(kafka_mgr.cam_account_id.decode("utf-8"))
        + '","csp_account_id":"'
        + str(kafka_mgr.csp_account_id.decode("utf-8"))
        + '","level":"%(levelname)s","path":"%(filename)s:%(funcName)s:%(lineno)d","message":"'
        + message.replace("\\", "")
        + '"}'
    )
    return stream_formatter


def set_logged_cvsa_id(kafka_mgr: KafkaManager) -> None:
    logger = logging.getLogger()
    logger.handlers[0].setFormatter(get_logging_formatter(kafka_mgr))
