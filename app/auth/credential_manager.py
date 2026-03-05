"""
微信公众号认证信息管理器
负责管理公众号后台的 Cookie 和 Token 信息
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class AuthCredential:
    """认证凭证数据类"""
    id: str
    account_nickname: str
    cookie: str
    token: str
    created_at: datetime
    expires_at: datetime
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    is_active: bool = True
    notes: Optional[str] = None


class CredentialManager:
    """认证信息管理器"""

    def __init__(self):
        self.credentials = {}  # 存储认证信息 (内存中，实际应用中应使用数据库)
        self.token_pattern = re.compile(r'[a-fA-F0-9]{6,10}')

    def validate_cookie(self, cookie: str) -> bool:
        """
        验证 Cookie 格式是否正确

        Args:
            cookie: Cookie 字符串

        Returns:
            是否有效
        """
        if not cookie or len(cookie) < 50:  # 基本长度验证
            return False

        # 检查是否包含必要的微信 Cookie 组件
        required_components = ['wxuin', 'wxsid', 'mm_lang', 'rewardsn']
        for component in required_components:
            if f"{component}=" not in cookie:
                # 某些组件可能不是必需的，我们采用较宽松的检查
                pass

        return True

    def validate_token(self, token: str) -> bool:
        """
        验证 Token 格式是否正确

        Args:
            token: Token 字符串

        Returns:
            是否有效
        """
        if not token:
            return False

        # Token 通常是数字和字母的组合，长度在6-10位左右
        return bool(self.token_pattern.search(token))

    def add_credential(
        self,
        account_nickname: str,
        cookie: str,
        token: str,
        notes: Optional[str] = None
    ) -> AuthCredential:
        """
        添加认证信息

        Args:
            account_nickname: 公众号昵称
            cookie: Cookie
            token: Token
            notes: 备注

        Returns:
            创建的认证凭证对象
        """
        if not self.validate_cookie(cookie):
            raise ValueError("Cookie 格式无效")

        if not self.validate_token(token):
            raise ValueError("Token 格式无效")

        # 生成唯一ID
        cred_id = f"cred_{len(self.credentials) + 1:04d}"

        # Token 一般有效期4小时
        expires_at = datetime.now() + timedelta(hours=4)

        credential = AuthCredential(
            id=cred_id,
            account_nickname=account_nickname,
            cookie=cookie,
            token=token,
            created_at=datetime.now(),
            expires_at=expires_at,
            notes=notes
        )

        self.credentials[cred_id] = credential
        return credential

    def get_credential(self, cred_id: str) -> Optional[AuthCredential]:
        """
        获取认证信息

        Args:
            cred_id: 认证ID

        Returns:
            认证凭证对象或 None
        """
        credential = self.credentials.get(cred_id)
        if credential and self.is_expired(credential):
            # 如果已过期，标记为非活跃
            credential.is_active = False
            return None
        return credential

    def get_credential_by_nickname(self, nickname: str) -> Optional[AuthCredential]:
        """
        根据公众号昵称获取认证信息

        Args:
            nickname: 公众号昵称

        Returns:
            认证凭证对象或 None
        """
        for credential in self.credentials.values():
            if credential.account_nickname == nickname and credential.is_active and not self.is_expired(credential):
                return credential
        return None

    def update_usage(self, cred_id: str):
        """
        更新认证信息的使用统计

        Args:
            cred_id: 认证ID
        """
        credential = self.credentials.get(cred_id)
        if credential:
            credential.last_used_at = datetime.now()
            credential.usage_count += 1

    def is_expired(self, credential: AuthCredential) -> bool:
        """
        检查认证信息是否已过期

        Args:
            credential: 认证凭证对象

        Returns:
            是否已过期
        """
        return datetime.now() > credential.expires_at

    def get_expiration_warning_time(self, credential: AuthCredential) -> Optional[datetime]:
        """
        获取过期警告时间（通常在到期前30分钟警告）

        Args:
            credential: 认证凭证对象

        Returns:
            警告时间或 None
        """
        warning_time = credential.expires_at - timedelta(minutes=30)
        return warning_time if datetime.now() >= warning_time else None

    def list_credentials(self) -> List[AuthCredential]:
        """
        列出所有认证信息

        Returns:
            认证凭证列表
        """
        return list(self.credentials.values())

    def remove_credential(self, cred_id: str) -> bool:
        """
        删除认证信息

        Args:
            cred_id: 认证ID

        Returns:
            是否删除成功
        """
        if cred_id in self.credentials:
            del self.credentials[cred_id]
            return True
        return False

    def refresh_credential(self, cred_id: str, new_cookie: str, new_token: str) -> bool:
        """
        刷新认证信息

        Args:
            cred_id: 认证ID
            new_cookie: 新 Cookie
            new_token: 新 Token

        Returns:
            是否刷新成功
        """
        if not self.validate_cookie(new_cookie) or not self.validate_token(new_token):
            return False

        credential = self.credentials.get(cred_id)
        if not credential:
            return False

        credential.cookie = new_cookie
        credential.token = new_token
        credential.expires_at = datetime.now() + timedelta(hours=4)
        credential.is_active = True
        return True

    def get_expiry_status(self) -> Dict[str, Dict]:
        """
        获取所有认证信息的过期状态

        Returns:
            过期状态字典
        """
        status = {}
        now = datetime.now()

        for cred_id, credential in self.credentials.items():
            remaining_time = credential.expires_at - now
            is_expired = self.is_expired(credential)
            warning_time = self.get_expiration_warning_time(credential)

            status[cred_id] = {
                "is_expired": is_expired,
                "remaining_seconds": max(0, int(remaining_time.total_seconds())),
                "is_warning": warning_time is not None,
                "account_nickname": credential.account_nickname,
                "expires_at": credential.expires_at.isoformat()
            }

        return status