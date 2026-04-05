"""爬蟲基類"""

import time
import random
import logging
from abc import ABC, abstractmethod
from typing import List
from bs4 import BeautifulSoup
import requests

from ..models import HousingData

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """爬蟲基類"""

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
    ]

    def __init__(self, name: str, delay: float = 1.0):
        """
        初始化爬蟲
        
        Args:
            name: 爬蟲名字
            delay: 請求間隔延遲(秒)
        """
        self.name = name
        self.delay = delay
        self.session = requests.Session()

    def _get_random_ua(self) -> str:
        """獲取隨機 User-Agent"""
        return random.choice(self.USER_AGENTS)

    def _get_headers(self) -> dict:
        """獲取請求頭"""
        return {
            'User-Agent': self._get_random_ua(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/',
        }

    def _fetch_url(self, url: str, **kwargs) -> requests.Response:
        """
        獲取URL內容（帶延遲和錯誤處理）
        
        Args:
            url: 目標URL
            **kwargs: requests 參數
            
        Returns:
            Response 對象
        """
        try:
            time.sleep(random.uniform(self.delay * 0.8, self.delay * 1.2))
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=10,
                **kwargs
            )
            response.raise_for_status()
            logger.info(f"✓ {self.name}: 成功獲取 {url}")
            return response
        except requests.RequestException as e:
            logger.error(f"✗ {self.name}: 獲取失敗 {url} - {e}")
            raise

    def _parse_html(self, html: str) -> BeautifulSoup:
        """解析 HTML"""
        return BeautifulSoup(html, 'html.parser')

    @abstractmethod
    def scrape(self, **kwargs) -> List[HousingData]:
        """
        爬取房源數據（必須由子類實現）
        
        Returns:
            HousingData 列表
        """
        pass

    def close(self):
        """關閉 Session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


if __name__ == "__main__":
    print("✅ 基礎爬蟲類定義完成")
