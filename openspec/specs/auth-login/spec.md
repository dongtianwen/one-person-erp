# auth-login Specification

## Purpose
管理员用户认证系统，保障系统安全访问。

## Requirements

### Requirement: User authentication
系统 SHALL 支持用户名密码认证。

#### Scenario: Successful login
- GIVEN 用户已注册账户
- WHEN 用户输入正确的用户名和密码
- THEN 系统返回有效的 JWT Access Token 和 Refresh Token

#### Scenario: Failed login - wrong password
- GIVEN 用户已注册账户
- WHEN 用户输入错误的密码
- THEN 系统返回 401 错误
- AND 提示"用户名或密码错误"

#### Scenario: Failed login - user not found
- GIVEN 用户不存在
- WHEN 用户尝试登录
- THEN 系统返回 401 错误
- AND 提示"用户名或密码错误"（不暴露用户是否存在）

### Requirement: Password security
系统 SHALL 安全存储用户密码。

#### Scenario: Password hashing
- GIVEN 用户创建或修改密码
- WHEN 密码被存储
- THEN 密码使用 bcrypt 哈希存储
- AND 明文密码不被存储或记录

#### Scenario: Password validation
- GIVEN 用户设置密码
- WHEN 密码长度小于6位或大于20位
- THEN 系统拒绝并提示密码格式要求
- WHEN 密码不包含字母和数字
- THEN 系统拒绝并提示密码格式要求

### Requirement: Session management
系统 SHALL 管理用户会话生命周期。

#### Scenario: Access token expiration
- GIVEN 用户已登录
- WHEN 30分钟无活动
- THEN Access Token 过期
- AND 用户使用 Refresh Token 获取新 Access Token

#### Scenario: Refresh token expiration
- GIVEN 用户已登录
- WHEN 7天过去
- THEN Refresh Token 过期
- AND 用户需要重新登录

#### Scenario: Logout
- GIVEN 用户已登录
- WHEN 用户执行登出
- THEN 系统清除本地 Token
- AND 用户无法访问受保护页面

### Requirement: Account lockout
系统 SHALL 防止暴力破解攻击。

#### Scenario: Account lockout after failed attempts
- GIVEN 用户尝试登录
- WHEN 连续失败5次
- THEN 账户锁定30分钟
- AND 提示"账户已锁定，请30分钟后重试"

### Requirement: Default admin user
系统 SHALL 在首次启动时创建默认管理员账户。

#### Scenario: Initial admin creation
- GIVEN 系统首次启动
- WHEN 数据库中无用户记录
- THEN 系统自动创建管理员账户
- AND 用户名: admin, 密码: admin123
- AND 提示用户首次登录后修改密码
