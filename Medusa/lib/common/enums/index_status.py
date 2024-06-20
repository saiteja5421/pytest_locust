from enum import Enum


class IndexStatus(Enum):
    INDEXED = "INDEXED"
    PARTIALLY_INDEXED = "PARTIALLY_INDEXED"
    NOT_INDEXED = "NOT_INDEXED"
    INDEXING = "INDEXING"
