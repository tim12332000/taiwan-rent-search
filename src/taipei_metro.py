"""Taipei Metro station metadata and proximity helpers.

Source:
- Taipei Open Data platform, dataset "臺北捷運車站資料服務"
  https://data.taipei/dataset/detail?id=1eefa68d-7c8d-491b-8e75-66a161947426
"""

from __future__ import annotations

import math
from typing import TypedDict


class MetroStation(TypedDict):
    name: str
    lat: float
    lon: float


TAIPEI_METRO_STATIONS: list[MetroStation] = [
    {"name": "七張", "lat": 24.9754500, "lon": 121.5429850},
    {"name": "三和國中", "lat": 25.0764600, "lon": 121.4867950},
    {"name": "三民高中", "lat": 25.0854250, "lon": 121.4733650},
    {"name": "三重", "lat": 25.0557100, "lon": 121.4842200},
    {"name": "三重國小", "lat": 25.0702750, "lon": 121.4970100},
    {"name": "中山", "lat": 25.0526210, "lon": 121.5203640},
    {"name": "中山國中", "lat": 25.0608500, "lon": 121.5442150},
    {"name": "中山國小", "lat": 25.0626650, "lon": 121.5266090},
    {"name": "中正紀念堂", "lat": 25.0327670, "lon": 121.5182730},
    {"name": "丹鳳", "lat": 25.0290730, "lon": 121.4224220},
    {"name": "亞東醫院", "lat": 24.9982800, "lon": 121.4524650},
    {"name": "信義安和", "lat": 25.0330150, "lon": 121.5523260},
    {"name": "先嗇宮", "lat": 25.0463200, "lon": 121.4716500},
    {"name": "內湖", "lat": 25.0836750, "lon": 121.5943630},
    {"name": "公館", "lat": 25.0147810, "lon": 121.5343580},
    {"name": "六張犁", "lat": 25.0238100, "lon": 121.5530200},
    {"name": "劍南路", "lat": 25.0848300, "lon": 121.5555825},
    {"name": "劍潭", "lat": 25.0842015, "lon": 121.5249545},
    {"name": "動物園", "lat": 24.9982050, "lon": 121.5795010},
    {"name": "北投", "lat": 25.1318185, "lon": 121.4986475},
    {"name": "北門", "lat": 25.0495540, "lon": 121.5101840},
    {"name": "南京三民", "lat": 25.0515880, "lon": 121.5647100},
    {"name": "南京復興", "lat": 25.0520440, "lon": 121.5443030},
    {"name": "南勢角", "lat": 24.9900650, "lon": 121.5092370},
    {"name": "南港", "lat": 25.0520350, "lon": 121.6069700},
    {"name": "南港展覽館", "lat": 25.0549190, "lon": 121.6168610},
    {"name": "南港軟體園區", "lat": 25.0599200, "lon": 121.6150000},
    {"name": "古亭", "lat": 25.0263730, "lon": 121.5228680},
    {"name": "台北101/世貿", "lat": 25.0328650, "lon": 121.5636670},
    {"name": "台北小巨蛋", "lat": 25.0515200, "lon": 121.5525490},
    {"name": "台北橋", "lat": 25.0630750, "lon": 121.5005750},
    {"name": "台北車站", "lat": 25.0463100, "lon": 121.5174150},
    {"name": "台大醫院", "lat": 25.0413990, "lon": 121.5160200},
    {"name": "台電大樓", "lat": 25.0207330, "lon": 121.5281435},
    {"name": "唭哩岸", "lat": 25.1208515, "lon": 121.5062340},
    {"name": "善導寺", "lat": 25.0446800, "lon": 121.5238850},
    {"name": "國父紀念館", "lat": 25.0413700, "lon": 121.5578150},
    {"name": "圓山", "lat": 25.0714085, "lon": 121.5200740},
    {"name": "土城", "lat": 24.9731300, "lon": 121.4443200},
    {"name": "士林", "lat": 25.0934925, "lon": 121.5262300},
    {"name": "大坪林", "lat": 24.9827205, "lon": 121.5413400},
    {"name": "大安", "lat": 25.0333110, "lon": 121.5423700},
    {"name": "大安森林公園", "lat": 25.0332250, "lon": 121.5361510},
    {"name": "大橋頭", "lat": 25.0632200, "lon": 121.5130035},
    {"name": "大湖公園", "lat": 25.0838050, "lon": 121.6022140},
    {"name": "大直", "lat": 25.0794300, "lon": 121.5467900},
    {"name": "奇岩", "lat": 25.1254705, "lon": 121.5011400},
    {"name": "小南門", "lat": 25.0355850, "lon": 121.5108800},
    {"name": "小碧潭", "lat": 24.9718800, "lon": 121.5305800},
    {"name": "市政府", "lat": 25.0411350, "lon": 121.5656850},
    {"name": "府中", "lat": 25.0084650, "lon": 121.4592760},
    {"name": "後山埤", "lat": 25.0447150, "lon": 121.5822700},
    {"name": "徐匯中學", "lat": 25.0804850, "lon": 121.4799450},
    {"name": "復興崗", "lat": 25.1374970, "lon": 121.4854560},
    {"name": "忠孝復興", "lat": 25.0417490, "lon": 121.5450260},
    {"name": "忠孝敦化", "lat": 25.0415050, "lon": 121.5504500},
    {"name": "忠孝新生", "lat": 25.0424980, "lon": 121.5332100},
    {"name": "忠義", "lat": 25.1309225, "lon": 121.4732975},
    {"name": "文德", "lat": 25.0784550, "lon": 121.5849995},
    {"name": "新北投", "lat": 25.1369315, "lon": 121.5025955},
    {"name": "新埔", "lat": 25.0232700, "lon": 121.4680550},
    {"name": "新店", "lat": 24.9576100, "lon": 121.5374600},
    {"name": "新店區公所", "lat": 24.9674400, "lon": 121.5413000},
    {"name": "新莊", "lat": 25.0360800, "lon": 121.4521800},
    {"name": "昆陽", "lat": 25.0504585, "lon": 121.5932285},
    {"name": "明德", "lat": 25.1098150, "lon": 121.5187850},
    {"name": "景安", "lat": 24.9939200, "lon": 121.5051140},
    {"name": "景美", "lat": 24.9928240, "lon": 121.5406975},
    {"name": "木柵", "lat": 24.9982400, "lon": 121.5731270},
    {"name": "東湖", "lat": 25.0674550, "lon": 121.6115350},
    {"name": "東門", "lat": 25.0338940, "lon": 121.5287660},
    {"name": "松山", "lat": 25.0501180, "lon": 121.5777060},
    {"name": "松山機場", "lat": 25.0629075, "lon": 121.5520100},
    {"name": "松江南京", "lat": 25.0526930, "lon": 121.5328500},
    {"name": "板橋", "lat": 25.0138250, "lon": 121.4623050},
    {"name": "民權西路", "lat": 25.0623500, "lon": 121.5195850},
    {"name": "永安市場", "lat": 25.0028950, "lon": 121.5112250},
    {"name": "永寧", "lat": 24.9668200, "lon": 121.4361300},
    {"name": "永春", "lat": 25.0408550, "lon": 121.5762000},
    {"name": "江子翠", "lat": 25.0302650, "lon": 121.4725700},
    {"name": "海山", "lat": 24.9853050, "lon": 121.4487300},
    {"name": "淡水", "lat": 25.1677450, "lon": 121.4458050},
    {"name": "港墘", "lat": 25.0800700, "lon": 121.5751600},
    {"name": "石牌", "lat": 25.1144550, "lon": 121.5155720},
    {"name": "科技大樓", "lat": 25.0261200, "lon": 121.5434615},
    {"name": "竹圍", "lat": 25.1369000, "lon": 121.4595500},
    {"name": "紅樹林", "lat": 25.1539900, "lon": 121.4588000},
    {"name": "芝山", "lat": 25.1027180, "lon": 121.5225460},
    {"name": "菜寮", "lat": 25.0594510, "lon": 121.4914210},
    {"name": "萬芳社區", "lat": 24.9985700, "lon": 121.5680880},
    {"name": "萬芳醫院", "lat": 24.9993200, "lon": 121.5580920},
    {"name": "萬隆", "lat": 25.0019780, "lon": 121.5390080},
    {"name": "葫洲", "lat": 25.0727100, "lon": 121.6071455},
    {"name": "蘆洲", "lat": 25.0915200, "lon": 121.4647100},
    {"name": "行天宮", "lat": 25.0592400, "lon": 121.5331500},
    {"name": "西湖", "lat": 25.0821600, "lon": 121.5672270},
    {"name": "西門", "lat": 25.0420250, "lon": 121.5081750},
    {"name": "象山", "lat": 25.0323950, "lon": 121.5701160},
    {"name": "輔大", "lat": 25.0327900, "lon": 121.4357350},
    {"name": "辛亥", "lat": 25.0054550, "lon": 121.5570455},
    {"name": "迴龍", "lat": 25.0221070, "lon": 121.4117570},
    {"name": "關渡", "lat": 25.1255100, "lon": 121.4670000},
    {"name": "雙連", "lat": 25.0575750, "lon": 121.5206850},
    {"name": "頂埔", "lat": 24.9601200, "lon": 121.4205000},
    {"name": "頂溪", "lat": 25.0138580, "lon": 121.5154620},
    {"name": "頭前庄", "lat": 25.0397350, "lon": 121.4616550},
    {"name": "麟光", "lat": 25.0184950, "lon": 121.5588335},
    {"name": "龍山寺", "lat": 25.0352800, "lon": 121.5003250},
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    origin_lat = math.radians(lat1)
    destination_lat = math.radians(lat2)
    a = math.sin(dlat / 2) ** 2 + math.cos(origin_lat) * math.cos(destination_lat) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_walk_minutes(distance_km: float) -> int:
    # 12.5 min/km ~= 80 m/min, plus a small station access buffer.
    return max(1, math.ceil(distance_km * 12.5 + 2))


def find_nearest_station(lat: float | None, lon: float | None) -> dict[str, float | str] | None:
    if lat is None or lon is None:
        return None

    nearest = min(
        TAIPEI_METRO_STATIONS,
        key=lambda station: haversine_km(lat, lon, station["lat"], station["lon"]),
    )
    distance_km = haversine_km(lat, lon, nearest["lat"], nearest["lon"])
    return {
        "name": nearest["name"],
        "distance_km": round(distance_km, 3),
        "walk_minutes": estimate_walk_minutes(distance_km),
    }
