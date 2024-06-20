from enum import Enum
import operator


class CompareCondition(Enum):
    greater = operator.gt
    greater_equal = operator.ge
    less = operator.lt
    less_equal = operator.le
    equal = operator.eq
