"""API 客户端测试。"""

from datetime import date

import pytest

from taric_match.api import AdditionalCode, GoodsDescription, Measure, TaricAPIError, TaricClient

DESCRIPTION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <ns2:goodsDescrForWsResponse xmlns:ns2="http://goodsNomenclatureForWS.ws.taric.dds.s/">
      <return>
        <goodsCode>87032319</goodsCode>
        <languageCode>ZH</languageCode>
        <referenceDate>2024-01-15</referenceDate>
        <description>[EN] Motor vehicles</description>
      </return>
    </ns2:goodsDescrForWsResponse>
  </soapenv:Body>
</soapenv:Envelope>
"""


MEASURES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>
    <ns2:goodsMeasForWsResponse xmlns:ns2="http://goodsNomenclatureForWS.ws.taric.dds.s/">
      <return>
        <goodsCode>87032319</goodsCode>
        <countryCode>CN</countryCode>
        <referenceDate>2024-01-15</referenceDate>
        <tradeMovement>I</tradeMovement>
        <goodsDescription>Motor vehicles</goodsDescription>
        <measureList>
          <measure>
            <measureType>103</measureType>
            <measureTypeDescription>Import duty</measureTypeDescription>
            <dutyRate>10%</dutyRate>
            <validityStartDate>2024-01-01</validityStartDate>
            <validityEndDate>2024-12-31</validityEndDate>
            <regulationId>R1234</regulationId>
            <additionalCode>
              <code>A123</code>
              <codeId>AC</codeId>
              <additionalCodeDescription>Anti-dumping</additionalCodeDescription>
            </additionalCode>
          </measure>
        </measureList>
      </return>
    </ns2:goodsMeasForWsResponse>
  </soapenv:Body>
</soapenv:Envelope>
"""


def test_create_goods_description() -> None:
    desc = GoodsDescription(
        goods_code="87032319",
        language_code="ZH",
        reference_date=date(2024, 1, 15),
        description="仅需驾驶员乘坐的车辆",
    )
    assert desc.goods_code == "87032319"
    assert desc.language_code == "ZH"
    assert desc.reference_date == date(2024, 1, 15)


def test_measure_validity_alias_properties() -> None:
    measure = Measure(
        measure_type="Import duty",
        measure_type_description="Import duty",
        duty_rate="10%",
        additional_code=AdditionalCode("A", "AC", "Anti-dumping"),
        validity_start_date="2024-01-01",
        validity_end_date="2024-12-31",
        regulation_id="R1234",
    )
    assert measure.validity_start == "2024-01-01"
    assert measure.validity_end == "2024-12-31"


def test_client_init_defaults() -> None:
    client = TaricClient()
    assert client.api_url == TaricClient.BASE_URL
    assert client.service_url == TaricClient.SERVICE_URL
    assert client.timeout == 30
    assert client.use_mock is False
    assert client.fallback_to_mock is False


def test_client_custom_url() -> None:
    custom_url = "https://custom.api/taric"
    client = TaricClient(api_url=custom_url)
    assert client.api_url == custom_url
    assert client.service_url == custom_url


def test_parse_description_response() -> None:
    client = TaricClient(use_mock=False)
    result = client._parse_description_response(DESCRIPTION_XML)
    assert result is not None
    assert result.goods_code == "87032319"
    assert result.language_code == "ZH"
    assert result.reference_date == date(2024, 1, 15)
    assert result.description == "Motor vehicles"
    assert result.original_language == "EN"


def test_parse_measures_response() -> None:
    client = TaricClient(use_mock=False)
    result = client._parse_measures_response(MEASURES_XML)
    assert result is not None
    assert result.goods_code == "87032319"
    assert result.country_code == "CN"
    assert len(result.measures) == 1
    measure = result.measures[0]
    assert measure.measure_type == "103"
    assert measure.measure_type_description == "Import duty"
    assert measure.validity_start_date == "2024-01-01"
    assert measure.additional_code is not None
    assert measure.additional_code.code == "A123"


def test_get_goods_description_raises_when_api_fails() -> None:
    client = TaricClient(use_mock=False, fallback_to_mock=False)

    def boom(_: str) -> str:
        raise TaricAPIError("boom")

    client._make_soap_request = boom  # type: ignore[method-assign]

    with pytest.raises(TaricAPIError, match="boom"):
        client.get_goods_description("87032319")


def test_get_goods_description_falls_back_when_enabled() -> None:
    client = TaricClient(use_mock=False, fallback_to_mock=True)

    def boom(_: str) -> str:
        raise TaricAPIError("boom")

    client._make_soap_request = boom  # type: ignore[method-assign]

    result = client.get_goods_description("87032319", language_code="ZH")
    assert (
        result.description == "装有点燃式活塞内燃发动机，气缸容量超过1500cc但不超过3000cc的机动车辆"
    )


def test_get_goods_measures_uses_mock_when_requested() -> None:
    client = TaricClient(use_mock=True)
    result = client.get_goods_measures("87032319", country_code="CN")
    assert result.country_code == "CN"
    assert len(result.measures) == 2
