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
    def __init__(self, data=None):
        super().__init__(success=0, error_code=0, message="Result is success.", data=data)

# class ParamError(ErrorCode):
#     def __init__(self):
#         super().__init__(error_code=100, message="Param error.")

class UserExistError(ErrorCode):
    def __init__(self):
        super().__init__(error_code=100, message="Tel was registered.")

class UserNotExistError(ErrorCode):
    def __init__(self):
        super().__init__(error_code=101, message="User does not exist.")

class NetError(ErrorCode):
    def __init__(self):
        super().__init__(error_code=102, message="Network error, retry request.")

class TokenError(ErrorCode):
    def __init__(self):
        super().__init__(error_code=1000, message="Token invalid.")

class TokenExpiredError(ErrorCode):
    def __init__(self):
        super().__init__(error_code=1001, message="Token Expired.")
