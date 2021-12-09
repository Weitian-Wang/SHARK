class UserType(object):
    INDIVIDUAL = 1
    PROPERTY = 2
    ADMIN = 3
    MODERATOR = 4
    SUPER_ADMIN = 5

class SpotType(object):
    INDIVIDUAL = 1
    PROPERTY = 2
    MIXED = 3

class SpotStatus(object):
    AVAILABLE = 1
    RESERVED = 2
    USING = 3
    NOT_AVAILABLE = 4

class OrderStatus(object):
    PLACED = 1
    USING_SPOT = 2
    COMPLETED = 3
    ABNORMAL = 4

class PaymentStatus(object):
    UNPAID = 0
    PAID = 1