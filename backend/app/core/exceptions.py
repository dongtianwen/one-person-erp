from fastapi import HTTPException, status


class AccountLockedException(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_423_LOCKED, detail="账户已锁定，请30分钟后重试")


class InvalidCredentialsException(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")


class AuthenticationRequiredException(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证失败，请重新登录")
