"""API 客户端测试"""

import pytest
from datetime import date
from taric_match.api import (
    TaricClient,
    GoodsDescription,
    GoodsMeasures,
    Measure
)


class TestGoodsDescription:
    """商品描述测试"""

    def test_create_goods_description(self):
        """测试创建商品描述对象"""
        desc = GoodsDescription(
            goods_code="87032319",
            language_code="ZH",
            reference_date=date(2024, 1, 15),
            description="仅需驾驶员乘坐的车辆"
        )
        assert desc.goods_code == "87032319"
        assert desc.language_code == "ZH"
        assert desc.reference_date == date(2024, 1, 15)


class TestGoodsMeasures:
    """商品措施测试"""

    def test_create_goods_measures(self):
        """测试创建商品措施对象"""
        measure1 = Measure(
            measure_type="Import duty",
            duty_rate="10%",
            additional_code=None,
            validity_start="2024-01-01",
            validity_end=None,
            regulation_id="R1234"
        )
        measures = GoodsMeasures(
            goods_code="87032319",
            country_code="CN",
            reference_date=date.today(),
            trade_movement="I",
            measures=[measure1]
        )
        assert measures.goods_code == "87032319"
        assert len(measures.measures) == 1


class TestTaricClient:
    """TARIC 客户端测试"""

    def test_client_init(self):
        """测试客户端初始化"""
        client = TaricClient()
        assert client.api_url == TaricClient.BASE_URL
        assert client.timeout == 30

    def test_client_custom_url(self):
        """测试自定义 URL"""
        custom_url = "https://custom.api/taric"
        client = TaricClient(api_url=custom_url)
        assert client.api_url == custom_url
