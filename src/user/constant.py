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
    COMPLETED = 3
    ABNORMAL = 4

class PaymentStatus(object):
    UNPAID = 0
    PAID = 1