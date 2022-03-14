import traceback

class ErrorCode(Exception):
    def __init__(self, success=1, error_code=500, message="System internal error.", data=None):
        super().__init__()
        self._success = success
        self._error_code = error_code
        self._message = message
        self._data = data if data is not None else {}
        self._result = {}

    def to_dict(self):
        self._result['success'] = self._success
        self._result['error_code'] = self._error_code
        self._result['message'] = self._message
        self._result['data'] = self._data
        return self._result

    def set_data(self, data):
        self._data = data
        self._result['data'] = self._data

class ResultSuccess(ErrorCode):
    def __init__(self, data=None, message="SUCCESS"):
        super().__init__(success=0, error_code=0, message=message, data=data)

class GeneralError(ErrorCode):
    def __init__(self, message):
        # super().__init__(error_code=1, message="customizable")
        super().__init__(error_code=1, message=message)

class UserExistError(ErrorCode):
    def __init__(self):
        # super().__init__(error_code=100, message="Tel was registered")
        super().__init__(error_code=100, message="手机号已被注册")


class UserNotExistError(ErrorCode):
    def __init__(self):
        # super().__init__(error_code=101, message="User does not exist")
        super().__init__(error_code=101, message="用户不存在")


class NetError(ErrorCode):
    def __init__(self):
        # super().__init__(error_code=102, message="Network error, retry request.")
        super().__init__(error_code=102, message="网络异常")


class PasswordError(ErrorCode):
    def __init__(self):
        # super().__init__(error_code=103, message="Wrong password.")
        super().__init__(error_code=103, message="密码错误")


class ParamError(ErrorCode):
    def __init__(self):
        # super().__init__(error_code=104, message="Param error.")
        super().__init__(error_code=104, message="参数错误")

class InvalidPeriod(ErrorCode):
    def __init__(self):
        # super().__init__(error_code=105, message="Spot unavailable durning period.")
        super().__init__(error_code=105, message="期间车位没空")

class WaitingSync(ErrorCode):
    def __init__(self):
        # super().__init__(error_code=106, message="Critical resource is being accessed by another user.")
        super().__init__(error_code=106, message="等待资源同步")

class UnauthorizedOperation(ErrorCode):
    def __init__(self):
        # super().__init__(error_code=107, message="Operation unauthorized")
        super().__init__(error_code=107, message="无权进行此操作")

class SystemInternalError(ErrorCode):
    # def __init__(self, message="System internal error."):
    def __init__(self, message="系统内部错误"):
        super().__init__(error_code=500, message=message, data=traceback.format_exc())


class TokenError(ErrorCode):
    def __init__(self):
        # super().__init__(error_code=1000, message="Token invalid.")
        super().__init__(error_code=1000, message="登录无效")


class TokenExpiredError(ErrorCode):
    def __init__(self):
        # super().__init__(error_code=1001, message="Token Expired.")
        super().__init__(error_code=1001, message="登录过期")
