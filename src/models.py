"""台灣租屋爬蟲 - 核心模塊"""

from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime


@dataclass
class Location:
    """位置信息"""
    county: str
    district: str
    area: Optional[str] = None


@dataclass
class Contact:
    """聯絡信息"""
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass
class HousingData:
    """房源數據模型"""
    id: str
    platform: str
    title: str
    price: int
    location: Location
    room_type: str
    bedrooms: int
    bathrooms: int
    floor_area: Optional[float]
    floor: Optional[str]
    contact: Contact
    images: List[str]
    description: str
    url: str
    scraped_at: datetime
    updated_at: datetime

    def to_dict(self):
        """轉換為字典（flatten Location和Contact）"""
        data = asdict(self)
        # 展平 Location
        location = data.pop('location')
        data['location_county'] = location['county']
        data['location_district'] = location['district']
        data['location_area'] = location['area']
        # 展平 Contact
        contact = data.pop('contact')
        data['contact_name'] = contact['name']
        data['contact_phone'] = contact['phone']
        data['contact_email'] = contact['email']
        # 轉換日期為字符串
        data['scraped_at'] = data['scraped_at'].isoformat()
        data['updated_at'] = data['updated_at'].isoformat()
        # 圖片列表轉為逗號分隔
        data['images'] = ','.join(data['images'])
        return data


if __name__ == "__main__":
    # 示例
    sample = HousingData(
        id="591-test-001",
        platform="591",
        title="台北市大同區套房出租",
        price=15000,
        location=Location(county="台北市", district="大同區", area="民雄街"),
        room_type="整套房",
        bedrooms=1,
        bathrooms=1,
        floor_area=25.0,
        floor="3F",
        contact=Contact(name="王小明", phone="0901-234-567"),
        images=["http://example.com/img1.jpg", "http://example.com/img2.jpg"],
        description="新裝潢套房，靠近捷運站",
        url="https://www.591.com.tw/rent/detail/xxxxx",
        scraped_at=datetime.now(),
        updated_at=datetime.now()
    )
    print("✅ 數據模型測試通過")
    print(sample)
