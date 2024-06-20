from typing import Callable

from kafka.protocol.message import Message

EventFilter = Callable[[Message], bool]


def event_filters_reduce(event_filters: list[EventFilter], events: list[Message]) -> list[Message]:
    return [event for event in events if _reduce_one(event_filters, event)]


def _reduce_one(event_filters: list[EventFilter], event: Message) -> bool:
    event_filters_satisfied = True
    for ef in event_filters:
        if not ef(event):
            event_filters_satisfied = False
            break
    return event_filters_satisfied
