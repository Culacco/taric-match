"""
EU TARIC API 客户端。

基于官方 WSDL:
https://ec.europa.eu/taxation_customs/dds2/taric/services/goods?wsdl
"""

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional

import requests


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_date(value: str) -> date:
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _find_text(element: ET.Element, tag: str) -> str:
    direct = element.findtext(f"{{*}}{tag}")
    if direct:
        return direct
    fallback = element.findtext(tag)
    return fallback or ""


def _find_child(element: ET.Element, tag: str) -> Optional[ET.Element]:
    return element.find(f".//{{*}}{tag}") or element.find(f".//{tag}")


def _normalize_goods_code(goods_code: str) -> str:
    value = "".join(ch for ch in goods_code.strip() if ch.isdigit())
    if not value:
        raise TaricAPIError("商品编码不能为空，且必须包含数字。")
    if len(value) > 10:
        raise TaricAPIError("商品编码长度不能超过 10 位。")
    return value.ljust(10, "0")


def _normalize_language_code(language_code: str) -> str:
    value = language_code.strip().lower()
    if len(value) != 2 or not value.isalpha():
        raise TaricAPIError("语言代码必须是 2 位字母，例如 en、zh、fr。")
    return value


@dataclass
class GoodsDescription:
    """商品描述响应。"""

    goods_code: str
    language_code: str
    reference_date: date
    description: str
    original_language: Optional[str] = None


@dataclass
class AdditionalCode:
    """附加代码。"""

    code: str
    code_id: str
    description: str


@dataclass
class Measure:
    """关税措施。"""

    measure_type: str
    measure_type_description: str
    duty_rate: Optional[str]
    additional_code: Optional[AdditionalCode] = None
    validity_start_date: Optional[str] = None
    validity_end_date: Optional[str] = None
    regulation_id: Optional[str] = None
    regulation_url: Optional[str] = None
    order_number: Optional[str] = None

    @property
    def validity_start(self) -> Optional[str]:
        return self.validity_start_date

    @property
    def validity_end(self) -> Optional[str]:
        return self.validity_end_date


@dataclass
class GoodsMeasures:
    """商品措施响应。"""

    goods_code: str
    country_code: str
    reference_date: date
    trade_movement: str
    measures: List[Measure] = field(default_factory=list)
    description: Optional[str] = None


class TaricAPIError(Exception):
    """TARIC API 错误。"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TaricClient:
    """EU TARIC API 客户端。"""

    WSDL_URL = "https://ec.europa.eu/taxation_customs/dds2/taric/services/goods?wsdl"
    SERVICE_URL = "https://ec.europa.eu/taxation_customs/dds2/taric/services/goods"
    BASE_URL = SERVICE_URL
    DEFAULT_HEADERS = {
        "User-Agent": "curl/8.7.1",
        "Accept": "text/xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(
        self,
        api_url: Optional[str] = None,
        service_url: Optional[str] = None,
        timeout: int = 30,
        use_mock: Optional[bool] = None,
        fallback_to_mock: Optional[bool] = None,
    ):
        resolved_url = api_url or service_url or self.SERVICE_URL
        self.api_url = resolved_url
        self.service_url = resolved_url
        self.timeout = timeout
        self.use_mock = _env_flag("TARIC_USE_MOCK") if use_mock is None else use_mock
        self.fallback_to_mock = (
            _env_flag("TARIC_FALLBACK_TO_MOCK") if fallback_to_mock is None else fallback_to_mock
        )

    def _make_soap_request(self, soap_body: str) -> str:
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "",
        }
        headers.update(self.DEFAULT_HEADERS)

        try:
            response = requests.post(
                self.service_url,
                data=soap_body.encode("utf-8"),
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TaricAPIError(f"请求 TARIC API 失败: {exc}") from exc

        if response.status_code == 502:
            raise TaricAPIError(
                "EU TARIC API 返回 502，可能是服务端 Web Filter 或临时限制，请稍后重试。",
                status_code=502,
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise TaricAPIError(
                f"TARIC API 返回 HTTP {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            ) from exc

        return str(response.text)

    def _parse_description_response(self, xml_response: str) -> Optional[GoodsDescription]:
        root = ET.fromstring(xml_response)
        return_elem = root.find(".//{*}return") or root.find(".//return")
        if return_elem is None:
            return None

        result_elem = _find_child(return_elem, "result")
        if result_elem is not None:
            request_elem = _find_child(result_elem, "request")
            data_elem = _find_child(result_elem, "data")
            goods_code = _find_text(request_elem, "goods_code") if request_elem is not None else ""
            language_code = (
                _find_text(request_elem, "language_code") if request_elem is not None else ""
            )
            reference_date = (
                _parse_date(_find_text(request_elem, "reference_date"))
                if request_elem is not None
                else date.today()
            )
            description = _find_text(data_elem, "description") if data_elem is not None else ""
        else:
            goods_code = _find_text(return_elem, "goodsCode")
            language_code = _find_text(return_elem, "languageCode")
            reference_date = _parse_date(_find_text(return_elem, "referenceDate"))
            description = _find_text(return_elem, "description")

        original_language = None
        if description.startswith("[EN] "):
            original_language = "EN"
            description = description[5:]

        return GoodsDescription(
            goods_code=goods_code,
            language_code=language_code,
            reference_date=reference_date,
            description=description,
            original_language=original_language,
        )

    def _parse_measures_response(self, xml_response: str) -> Optional[GoodsMeasures]:
        root = ET.fromstring(xml_response)
        return_elem = root.find(".//{*}return") or root.find(".//return")
        if return_elem is None:
            return None

        result_elem = _find_child(return_elem, "result")
        if result_elem is not None:
            request_elem = _find_child(result_elem, "request")
            measures_container = _find_child(result_elem, "measures")
            goods_code = _find_text(request_elem, "goods_code") if request_elem is not None else ""
            country_code = (
                _find_text(request_elem, "country_code") if request_elem is not None else ""
            )
            reference_date = (
                _parse_date(_find_text(request_elem, "reference_date"))
                if request_elem is not None
                else date.today()
            )
            trade_movement = (
                _find_text(request_elem, "trade_movement") if request_elem is not None else ""
            )
            description = None
        else:
            measures_container = _find_child(return_elem, "measureList")
            goods_code = _find_text(return_elem, "goodsCode")
            country_code = _find_text(return_elem, "countryCode")
            reference_date = _parse_date(_find_text(return_elem, "referenceDate"))
            trade_movement = _find_text(return_elem, "tradeMovement")
            description = _find_text(return_elem, "goodsDescription") or None

        measures: List[Measure] = []
        if measures_container is not None:
            for measure_elem in measures_container.findall(
                ".//{*}measure"
            ) or measures_container.findall(".//measure"):
                parsed = self._parse_measure_element(measure_elem)
                if parsed is not None:
                    measures.append(parsed)

        return GoodsMeasures(
            goods_code=goods_code,
            country_code=country_code,
            reference_date=reference_date,
            trade_movement=trade_movement,
            measures=measures,
            description=description,
        )

    def _parse_measure_element(self, element: ET.Element) -> Optional[Measure]:
        measure_type_elem = _find_child(element, "measure_type")
        if measure_type_elem is not None:
            measure_type = _find_text(measure_type_elem, "measure_type")
            measure_type_description = _find_text(measure_type_elem, "description")
        else:
            measure_type = _find_text(element, "measureType")
            measure_type_description = _find_text(element, "measureTypeDescription")

        if not measure_type:
            return None

        additional_code = None
        additional_code_elem = element.find(".//{*}additionalCode") or element.find(
            ".//additionalCode"
        )
        if additional_code_elem is not None and _find_text(additional_code_elem, "code"):
            additional_code = AdditionalCode(
                code=_find_text(additional_code_elem, "code"),
                code_id=_find_text(additional_code_elem, "codeId"),
                description=_find_text(additional_code_elem, "additionalCodeDescription"),
            )

        return Measure(
            measure_type=measure_type,
            measure_type_description=measure_type_description,
            duty_rate=_find_text(element, "dutyRate") or None,
            additional_code=additional_code,
            validity_start_date=_find_text(element, "validityStartDate")
            or _find_text(element, "validity_start_date")
            or None,
            validity_end_date=_find_text(element, "validityEndDate")
            or _find_text(element, "validity_end_date")
            or None,
            regulation_id=_find_text(element, "regulationId")
            or _find_text(element, "regulation_id")
            or None,
            regulation_url=_find_text(element, "regulationUrl")
            or _find_text(element, "regulation_url")
            or None,
            order_number=_find_text(element, "orderNumber")
            or _find_text(element, "order_number")
            or None,
        )

    def _maybe_fallback_description(
        self,
        exc: TaricAPIError,
        goods_code: str,
        language_code: str,
    ) -> GoodsDescription:
        if self.fallback_to_mock:
            return self._mock_description(goods_code, language_code)
        raise exc

    def _maybe_fallback_measures(
        self,
        exc: TaricAPIError,
        goods_code: str,
        country_code: str,
        trade_movement: str,
    ) -> GoodsMeasures:
        if self.fallback_to_mock:
            return self._mock_measures(goods_code, country_code, trade_movement)
        raise exc

    def get_goods_description(
        self,
        goods_code: str,
        language_code: str = "EN",
        reference_date: Optional[date] = None,
    ) -> GoodsDescription:
        if self.use_mock:
            return self._mock_description(goods_code, language_code)

        normalized_goods_code = _normalize_goods_code(goods_code)
        normalized_language_code = _normalize_language_code(language_code)
        ref_date = reference_date or date.today()
        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://goodsNomenclatureForWS.ws.taric.dds.s/">
  <soapenv:Body>
    <ns:goodsDescrForWs>
      <ns:goodsCode>{normalized_goods_code}</ns:goodsCode>
      <ns:languageCode>{normalized_language_code}</ns:languageCode>
      <ns:referenceDate>{ref_date.strftime('%Y-%m-%d')}</ns:referenceDate>
    </ns:goodsDescrForWs>
  </soapenv:Body>
</soapenv:Envelope>"""

        try:
            response = self._make_soap_request(soap_body)
            result = self._parse_description_response(response)
            if result is None:
                raise TaricAPIError(f"TARIC 未返回商品编码 {normalized_goods_code} 的描述数据。")
            return result
        except TaricAPIError as exc:
            return self._maybe_fallback_description(exc, goods_code, language_code)

    def get_goods_measures(
        self,
        goods_code: str,
        country_code: str = "CN",
        trade_movement: str = "I",
        reference_date: Optional[date] = None,
    ) -> GoodsMeasures:
        if self.use_mock:
            return self._mock_measures(goods_code, country_code, trade_movement)

        normalized_goods_code = _normalize_goods_code(goods_code)
        ref_date = reference_date or date.today()
        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://goodsNomenclatureForWS.ws.taric.dds.s/">
  <soapenv:Body>
    <ns:goodsMeasForWs>
      <ns:goodsCode>{normalized_goods_code}</ns:goodsCode>
      <ns:countryCode>{country_code.upper()}</ns:countryCode>
      <ns:referenceDate>{ref_date.strftime('%Y-%m-%d')}</ns:referenceDate>
      <ns:tradeMovement>{trade_movement.upper()}</ns:tradeMovement>
    </ns:goodsMeasForWs>
  </soapenv:Body>
</soapenv:Envelope>"""

        try:
            response = self._make_soap_request(soap_body)
            result = self._parse_measures_response(response)
            if result is None:
                raise TaricAPIError(
                    f"TARIC 未返回商品编码 {normalized_goods_code} 的关税措施数据。"
                )
            return result
        except TaricAPIError as exc:
            return self._maybe_fallback_measures(exc, goods_code, country_code, trade_movement)

    def _mock_description(self, goods_code: str, language_code: str) -> GoodsDescription:
        sample_descriptions = {
            "87032319": "Motor vehicles with spark-ignition internal combustion engine, of a cylinder capacity exceeding 1,500 cc but not exceeding 3,000 cc",
            "85171300": "Telephones for cellular networks or for other wireless networks",
            "84713000": "Portable automatic data processing machines, weighing not more than 10 kg",
        }

        description_en = sample_descriptions.get(goods_code, f"Goods code {goods_code}")
        if language_code.upper() == "ZH":
            zh_descriptions = {
                "87032319": "装有点燃式活塞内燃发动机，气缸容量超过1500cc但不超过3000cc的机动车辆",
                "85171300": "蜂窝网络或其他无线网络电话机",
                "84713000": "重量不超过10公斤的便携式自动数据处理机器",
            }
            description = zh_descriptions.get(goods_code, description_en)
        else:
            description = description_en

        return GoodsDescription(
            goods_code=goods_code,
            language_code=language_code.upper(),
            reference_date=date.today(),
            description=description,
        )

    def _mock_measures(
        self,
        goods_code: str,
        country_code: str,
        trade_movement: str,
    ) -> GoodsMeasures:
        sample_measures = {
            "87032319": [
                Measure(
                    measure_type="103",
                    measure_type_description="Import duty",
                    duty_rate="10%",
                    validity_start_date="2024-01-01",
                    regulation_id="R(2024)1234",
                ),
                Measure(
                    measure_type="710",
                    measure_type_description="Import control",
                    duty_rate=None,
                    validity_start_date="2024-01-01",
                    regulation_id="R(2024)5678",
                ),
            ],
            "85171300": [
                Measure(
                    measure_type="103",
                    measure_type_description="Import duty",
                    duty_rate="0%",
                    validity_start_date="2024-01-01",
                    regulation_id="R(2024)2345",
                ),
            ],
        }

        description = self._mock_description(goods_code, "ZH").description
        return GoodsMeasures(
            goods_code=goods_code,
            country_code=country_code.upper(),
            reference_date=date.today(),
            trade_movement=trade_movement.upper(),
            measures=sample_measures.get(goods_code, []),
            description=description,
        )
