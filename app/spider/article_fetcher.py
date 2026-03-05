"""
微信公众号文章列表获取器
使用 wechatarticles 库通过公众号后台 API 获取全部历史文章
"""
import asyncio
import time
from typing import List, Dict, Optional, Callable
from datetime import datetime
import logging

from wechatarticles import PublicAccountsWeb
from ..models import Article, OfficialAccount


class ArticleFetcher:
    """
    微信公众号文章列表获取器

    采用速率控制和指数退避策略以避免被封禁
    """

    def __init__(self, cookie: str = None, token: str = None):
        """
        初始化获取器

        Args:
            cookie: 公众号后台 cookie
            token: 公众号后台 token
        """
        self.cookie = cookie
        self.token = token
        self.api = None
        if cookie and token:
            self._init_api()

        # 速率控制参数
        self.min_delay_between_requests = 180  # 3分钟最小间隔
        self.max_delay_between_requests = 300  # 5分钟最大间隔
        self.batch_size = 30  # 每批处理的文章数量
        self.batch_pause_duration = 1800  # 批次间暂停时间（秒）

        # 指数退避参数
        self.initial_backoff = 300  # 5分钟初始退避时间
        self.max_backoff = 7200  # 2小时最大退避时间
        self.backoff_factor = 2  # 退避倍数因子

        self.logger = logging.getLogger(__name__)

    def _init_api(self):
        """初始化 API 接口"""
        if not self.cookie or not self.token:
            raise ValueError("Cookie 和 Token 都不能为空")

        self.api = PublicAccountsWeb(cookie=self.cookie, token=self.token)

    def set_credentials(self, cookie: str, token: str):
        """设置认证信息"""
        self.cookie = cookie
        self.token = token
        self._init_api()

    async def get_total_articles_count(self, nickname: str) -> int:
        """
        获取公众号文章总数

        Args:
            nickname: 公众号昵称

        Returns:
            文章总数
        """
        if not self.api:
            raise RuntimeError("API 未初始化，请先设置认证信息")

        try:
            # 先获取任意一页以获取总数
            result = await self.api.get_urls(nickname=nickname, begin=0, count=1)
            if result and 'app_msg_cnt' in result:
                return result['app_msg_cnt']
            else:
                raise RuntimeError("无法获取文章总数")
        except Exception as e:
            self.logger.error(f"获取文章总数失败: {e}")
            raise

    async def get_article_list_batch(
        self,
        nickname: str,
        begin: int,
        count: int
    ) -> List[Dict]:
        """
        分批获取文章列表

        Args:
            nickname: 公众号昵称
            begin: 起始位置
            count: 获取数量

        Returns:
            文章列表
        """
        if not self.api:
            raise RuntimeError("API 未初始化，请先设置认证信息")

        try:
            result = await self.api.get_urls(nickname=nickname, begin=begin, count=count)

            if not result or 'app_msg_list' not in result:
                raise RuntimeError(f"获取文章列表失败: {result}")

            return result['app_msg_list']
        except Exception as e:
            self.logger.error(f"获取文章列表批次失败 (begin={begin}, count={count}): {e}")
            raise

    async def get_all_articles(
        self,
        nickname: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Dict]:
        """
        获取公众号全部历史文章列表

        Args:
            nickname: 公众号昵称
            progress_callback: 进度回调函数 (current, total)

        Returns:
            所有文章列表
        """
        if not self.api:
            raise RuntimeError("API 未初始化，请先设置认证信息")

        # 获取文章总数
        total_count = await self.get_total_articles_count(nickname)
        self.logger.info(f"公众号 {nickname} 共有 {total_count} 篇文章")

        all_articles = []
        begin = 0

        # 计算需要多少批次
        num_batches = (total_count + self.batch_size - 1) // self.batch_size

        # 指数退避计数器
        consecutive_failures = 0
        current_backoff = self.initial_backoff

        for batch_idx in range(num_batches):
            # 计算本次批次的起始位置和数量
            current_begin = begin
            current_count = min(self.batch_size, total_count - current_begin)

            try:
                # 获取当前批次文章
                batch_articles = await self.get_article_list_batch(
                    nickname=nickname,
                    begin=current_begin,
                    count=current_count
                )

                all_articles.extend(batch_articles)

                # 调用进度回调
                if progress_callback:
                    progress_callback(len(all_articles), total_count)

                self.logger.info(f"批次 {batch_idx + 1}/{num_batches}: "
                               f"获取了 {len(batch_articles)} 篇文章，累计 {len(all_articles)} 篇")

                # 重置失败计数
                consecutive_failures = 0
                current_backoff = self.initial_backoff

                # 计算下一批次的位置
                begin += current_count

                # 每批之间需要暂停
                if batch_idx < num_batches - 1:  # 不是最后一批才暂停
                    # 随机延迟以模拟真实行为
                    delay = self.min_delay_between_requests + (
                        (self.max_delay_between_requests - self.min_delay_between_requests) *
                        (0.8 + 0.2 * (batch_idx % 3))  # 稍微变化的延迟
                    )

                    self.logger.info(f"批次间暂停 {delay:.0f} 秒...")
                    await asyncio.sleep(delay)

            except Exception as e:
                self.logger.warning(f"批次 {batch_idx + 1}/{num_batches} 获取失败: {e}")

                # 增加失败计数
                consecutive_failures += 1

                # 使用指数退避策略
                if consecutive_failures >= 3:  # 连续3次失败后启用退避
                    backoff_time = min(current_backoff, self.max_backoff)
                    self.logger.warning(f"检测到频繁失败，启用退避机制，暂停 {backoff_time} 秒...")
                    await asyncio.sleep(backoff_time)

                    # 增加下次退避时间
                    current_backoff *= self.backoff_factor

                # 如果失败，稍等后再试
                retry_delay = min(60, 10 * consecutive_failures)  # 递增重试延迟
                await asyncio.sleep(retry_delay)

                # 重新尝试获取当前批次
                continue  # 继续下一次循环，不增加 begin

        self.logger.info(f"成功获取公众号 {nickname} 的全部 {len(all_articles)} 篇文章")
        return all_articles

    async def get_articles_in_batches(
        self,
        nickname: str,
        batch_callback: Callable[[List[Dict], int, int], None],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> None:
        """
        分批次获取文章并逐一处理，避免内存占用过大

        Args:
            nickname: 公众号昵称
            batch_callback: 批次处理回调函数 (articles_batch, batch_index, total_batches)
            progress_callback: 进度回调函数 (current, total)
        """
        if not self.api:
            raise RuntimeError("API 未初始化，请先设置认证信息")

        # 获取文章总数
        total_count = await self.get_total_articles_count(nickname)
        self.logger.info(f"公众号 {nickname} 共有 {total_count} 篇文章")

        begin = 0
        batch_idx = 0
        total_batches = (total_count + self.batch_size - 1) // self.batch_size

        # 指数退避计数器
        consecutive_failures = 0
        current_backoff = self.initial_backoff

        while begin < total_count:
            # 计算当前批次的数量
            current_count = min(self.batch_size, total_count - begin)

            try:
                # 获取当前批次文章
                batch_articles = await self.get_article_list_batch(
                    nickname=nickname,
                    begin=begin,
                    count=current_count
                )

                # 调用批次处理回调
                batch_callback(batch_articles, batch_idx, total_batches)

                # 调用总体进度回调
                if progress_callback:
                    progress_callback(begin + len(batch_articles), total_count)

                self.logger.info(f"批次 {batch_idx + 1}/{total_batches}: "
                               f"处理了 {len(batch_articles)} 篇文章，累计 {begin + len(batch_articles)} 篇")

                # 重置失败计数
                consecutive_failures = 0
                current_backoff = self.initial_backoff

                # 计算下一批次的位置
                begin += current_count
                batch_idx += 1

                # 每批之间需要暂停
                if begin < total_count:  # 还有后续批次才暂停
                    # 随机延迟以模拟真实行为
                    delay = self.min_delay_between_requests + (
                        (self.max_delay_between_requests - self.min_delay_between_requests) *
                        (0.8 + 0.2 * (batch_idx % 3))
                    )

                    self.logger.info(f"批次间暂停 {delay:.0f} 秒...")
                    await asyncio.sleep(delay)

            except Exception as e:
                self.logger.warning(f"批次 {batch_idx + 1}/{total_batches} 获取失败: {e}")

                # 增加失败计数
                consecutive_failures += 1

                # 使用指数退避策略
                if consecutive_failures >= 3:  # 连续3次失败后启用退避
                    backoff_time = min(current_backoff, self.max_backoff)
                    self.logger.warning(f"检测到频繁失败，启用退避机制，暂停 {backoff_time} 秒...")
                    await asyncio.sleep(backoff_time)

                    # 增加下次退避时间
                    current_backoff *= self.backoff_factor

                # 如果失败，稍等后再试
                retry_delay = min(60, 10 * consecutive_failures)
                await asyncio.sleep(retry_delay)

                # 不增加 begin，重新尝试当前批次
                continue