class UserType(object):
    INDIVIDUAL = 1
    PROPERTY = 2
    ADMIN = 3

class SpotType(object):
    INDIVIDUAL = 1
    PROPERTY = 2

class SpotStatus(object):
    NOT_AVAILABLE = 0
    AVAILABLE = 1

class OrderStatus(object):
    PLACED = 1
    USING_SPOT = 2
    DENIED = 3
    CANCELED = 4
    ABNORMAL = 5
    LEFT_UNPAID = 10
    COMPLETED = 11