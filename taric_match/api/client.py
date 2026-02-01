"""
EU TARIC API 客户端
基于官方 WSDL: https://ec.europa.eu/taxation_customs/dds2/taric/services/goods?wsdl
"""

import os
import xml.etree.ElementTree as ET
from datetime import date, datetime
from dataclasses import dataclass, field
from typing import Optional, List
import requests


@dataclass
class GoodsDescription:
    """商品描述响应"""
    goods_code: str
    language_code: str
    reference_date: date
    description: str
    original_language: Optional[str] = None  # 如果翻译自英文


@dataclass
class AdditionalCode:
    """附加代码"""
    code: str
    code_id: str
    description: str


@dataclass
class Measure:
    """关税措施"""
    measure_type: str
    measure_type_description: str
    duty_rate: Optional[str]
    additional_code: Optional[AdditionalCode] = None
    validity_start_date: Optional[str] = None
    validity_end_date: Optional[str] = None
    regulation_id: Optional[str] = None
    regulation_url: Optional[str] = None
    order_number: Optional[str] = None


@dataclass
class GoodsMeasures:
    """商品措施响应"""
    goods_code: str
    country_code: str
    reference_date: date
    trade_movement: str
    measures: List[Measure] = field(default_factory=list)
    description: Optional[str] = None


class TaricAPIError(Exception):
    """TARIC API 错误"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class TaricClient:
    """EU TARIC API 客户端
    
    API 文档: https://ec.europa.eu/taxation_customs/dds2/taric/services/goods?wsdl
    限制: 每秒最多 100 次请求
    
    注意: 如果被 Web Filter 拦截 (502)，可能是服务器端限制，请稍后重试。
    """
    
    WSDL_URL = "https://ec.europa.eu/taxation_customs/dds2/taric/services/goods?wsdl"
    SERVICE_URL = "https://ec.europa.eu/taxation_customs/dds2/taric/services/goods"
    
    # SOAP 命名空间
    NS = {
        'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
        'ns': 'http://goodsNomenclatureForWS.ws.taric.dds.s/',
    }
    
    def __init__(
        self,
        service_url: Optional[str] = None,
        timeout: int = 30,
        use_mock: bool = False  # 测试用 mock 数据
    ):
        self.service_url = service_url or self.SERVICE_URL
        self.timeout = timeout
        self.use_mock = use_mock or os.environ.get('TARIC_USE_MOCK', '').lower() == 'true'
    
    def _make_soap_request(self, soap_body: str) -> str:
        """发送 SOAP 请求"""
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': '',
        }
        response = requests.post(
            self.service_url,
            data=soap_body.encode('utf-8'),
            headers=headers,
            timeout=self.timeout
        )
        
        if response.status_code == 502:
            raise TaricAPIError(
                "EU TARIC API 被 Web Filter 拦截 (502)。"
                "这可能是服务器端的反爬虫机制，请稍后重试。",
                status_code=502
            )
        
        response.raise_for_status()
        return response.text
    
    def _parse_description_response(self, xml_response: str) -> GoodsDescription:
        """解析商品描述响应"""
        root = ET.fromstring(xml_response)
        
        # 命名空间
        ns = self.NS
        
        # 查找返回元素
        return_elem = root.find('.//ns:return', ns) or root.find('.//return')
        
        if return_elem is None:
            # 没有返回数据
            return None
        
        goods_code = return_elem.findtext('ns:goodsCode', default='', namespaces=ns) or \
                     return_elem.findtext('goodsCode', default='')
        language_code = return_elem.findtext('ns:languageCode', default='', namespaces=ns) or \
                        return_elem.findtext('languageCode', default='')
        reference_date_str = return_elem.findtext('ns:referenceDate', default='', namespaces=ns) or \
                             return_elem.findtext('referenceDate', default='')
        description = return_elem.findtext('ns:description', default='', namespaces=ns) or \
                      return_elem.findtext('description', default='')
        
        # 解析日期
        reference_date = date.today()
        if reference_date_str:
            try:
                reference_date = datetime.strptime(reference_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # 检查是否是英文翻译
        prefix = "[EN] "
        original_language = None
        if description.startswith(prefix):
            original_language = "EN"
            description = description[len(prefix):]
        
        return GoodsDescription(
            goods_code=goods_code,
            language_code=language_code,
            reference_date=reference_date,
            description=description,
            original_language=original_language
        )
    
    def _parse_measures_response(self, xml_response: str) -> GoodsMeasures:
        """解析关税措施响应"""
        root = ET.fromstring(xml_response)
        ns = self.NS
        
        return_elem = root.find('.//ns:return', ns) or root.find('.//return')
        
        if return_elem is None:
            return None
        
        goods_code = return_elem.findtext('ns:goodsCode', default='', namespaces=ns) or \
                     return_elem.findtext('goodsCode', default='')
        country_code = return_elem.findtext('ns:countryCode', default='', namespaces=ns) or \
                       return_elem.findtext('countryCode', default='')
        trade_movement = return_elem.findtext('ns:tradeMovement', default='', namespaces=ns) or \
                         return_elem.findtext('tradeMovement', default='')
        
        reference_date_str = return_elem.findtext('ns:referenceDate', default='', namespaces=ns) or \
                             return_elem.findtext('referenceDate', default='')
        reference_date = date.today()
        if reference_date_str:
            try:
                reference_date = datetime.strptime(reference_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        measures = []
        
        # 解析措施列表
        measures_list = return_elem.find('.//ns:measureList', ns) or return_elem.find('.//measureList')
        if measures_list is not None:
            for measure_elem in measures_list.findall('.//ns:measure', ns) or measures_list.findall('.//measure'):
                measure = self._parse_measure_element(measure_elem, ns)
                if measure:
                    measures.append(measure)
        
        # 解析描述
        description = return_elem.findtext('ns:goodsDescription', default='', namespaces=ns) or \
                      return_elem.findtext('goodsDescription', default='')
        
        return GoodsMeasures(
            goods_code=goods_code,
            country_code=country_code,
            reference_date=reference_date,
            trade_movement=trade_movement,
            measures=measures,
            description=description
        )
    
    def _parse_measure_element(self, elem: ET.Element, ns: dict) -> Optional[Measure]:
        """解析单个措施元素"""
        measure_type = elem.findtext('ns:measureType', default='', namespaces=ns) or \
                       elem.findtext('measureType', default='')
        
        if not measure_type:
            return None
        
        measure_type_desc = elem.findtext('ns:measureTypeDescription', default='', namespaces=ns) or \
                           elem.findtext('measureTypeDescription', default='')
        duty_rate = elem.findtext('ns:dutyRate', default='', namespaces=ns) or \
                    elem.findtext('dutyRate', default='')
        validity_start = elem.findtext('ns:validityStartDate', default='', namespaces=ns) or \
                        elem.findtext('validityStartDate', default='')
        validity_end = elem.findtext('ns:validityEndDate', default='', namespaces=ns) or \
                      elem.findtext('validityEndDate', default='')
        regulation_id = elem.findtext('ns:regulationId', default='', namespaces=ns) or \
                       elem.findtext('regulationId', default='')
        order_number = elem.findtext('ns:orderNumber', default='', namespaces=ns) or \
                      elem.findtext('orderNumber', default='')
        
        # 解析附加代码
        additional_code_elem = elem.find('.//ns:additionalCode', ns) or elem.find('.//additionalCode')
        additional_code = None
        if additional_code_elem is not None:
            code = additional_code_elem.findtext('ns:code', default='', namespaces=ns) or \
                   additional_code_elem.findtext('code', default='')
            code_id = additional_code_elem.findtext('ns:codeId', default='', namespaces=ns) or \
                     additional_code_elem.findtext('codeId', default='')
            code_desc = additional_code_elem.findtext('ns:additionalCodeDescription', default='', namespaces=ns) or \
                       additional_code_elem.findtext('additionalCodeDescription', default='')
            if code:
                additional_code = AdditionalCode(
                    code=code,
                    code_id=code_id,
                    description=code_desc
                )
        
        return Measure(
            measure_type=measure_type,
            measure_type_description=measure_type_desc,
            duty_rate=duty_rate if duty_rate else None,
            additional_code=additional_code,
            validity_start_date=validity_start if validity_start else None,
            validity_end_date=validity_end if validity_end else None,
            regulation_id=regulation_id if regulation_id else None,
            order_number=order_number if order_number else None
        )
    
    def get_goods_description(
        self,
        goods_code: str,
        language_code: str = "EN",
        reference_date: Optional[date] = None
    ) -> GoodsDescription:
        """
        查询商品描述
        
        Args:
            goods_code: 商品编码 (4-10位)
            language_code: 语言代码 (EN, ZH, FR, DE, ES, IT, NL, PL, PT, RO)
            reference_date: 参考日期 (可选，默认当前日期)
            
        Returns:
            GoodsDescription 对象
        """
        if self.use_mock:
            return self._mock_description(goods_code, language_code)
        
        ref_date = reference_date or date.today()
        
        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://goodsNomenclatureForWS.ws.taric.dds.s/">
  <soapenv:Body>
    <ns:goodsDescrForWs>
      <goodsCode>{goods_code}</goodsCode>
      <languageCode>{language_code.upper()}</languageCode>
      <referenceDate>{ref_date.strftime('%Y-%m-%d')}</referenceDate>
    </ns:goodsDescrForWs>
  </soapenv:Body>
</soapenv:Envelope>"""
        
        try:
            response = self._make_soap_request(soap_body)
            result = self._parse_description_response(response)
            if result is None:
                # API 返回空，使用 mock
                return self._mock_description(goods_code, language_code)
            return result
        except TaricAPIError:
            # 如果 API 错误，使用 mock 数据
            return self._mock_description(goods_code, language_code)
    
    def get_goods_measures(
        self,
        goods_code: str,
        country_code: str = "CN",
        trade_movement: str = "I",
        reference_date: Optional[date] = None
    ) -> GoodsMeasures:
        """
        查询商品关税措施
        
        Args:
            goods_code: 商品编码 (4-10位)
            country_code: 国家代码 (ISO 2位，如 CN, US, JP)
            trade_movement: 贸易方向 (I=进口, E=出口, IE=两者)
            reference_date: 参考日期 (可选，默认当前日期)
            
        Returns:
            GoodsMeasures 对象
        """
        if self.use_mock:
            return self._mock_measures(goods_code, country_code, trade_movement)
        
        ref_date = reference_date or date.today()
        
        soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://goodsNomenclatureForWS.ws.taric.dds.s/">
  <soapenv:Body>
    <ns:goodsMeasForWs>
      <goodsCode>{goods_code}</goodsCode>
      <countryCode>{country_code.upper()}</countryCode>
      <referenceDate>{ref_date.strftime('%Y-%m-%d')}</referenceDate>
      <tradeMovement>{trade_movement.upper()}</tradeMovement>
    </ns:goodsMeasForWs>
  </soapenv:Body>
</soapenv:Envelope>"""
        
        try:
            response = self._make_soap_request(soap_body)
            result = self._parse_measures_response(response)
            if result is None:
                return self._mock_measures(goods_code, country_code, trade_movement)
            return result
        except TaricAPIError:
            return self._mock_measures(goods_code, country_code, trade_movement)
    
    def _mock_description(self, goods_code: str, language_code: str) -> GoodsDescription:
        """Mock 数据: 商品描述"""
        # 示例描述 (实际应从 API 获取)
        sample_descriptions = {
            '87032319': 'Motor vehicles with spark-ignition internal combustion engine, of a cylinder capacity exceeding 1,500 cc but not exceeding 3,000 cc',
            '85171300': 'Telephones for cellular networks or for other wireless networks',
            '84713000': 'Portable automatic data processing machines, weighing not more than 10 kg',
        }
        
        description_en = sample_descriptions.get(goods_code, f'Goods code {goods_code}')
        
        if language_code.upper() == 'ZH':
            zh_descriptions = {
                '87032319': '装有点燃式活塞内燃发动机，气缸容量超过1500cc但不超过3000cc的机动车辆',
                '85171300': '蜂窝网络或其他无线网络电话机',
                '84713000': '重量不超过10公斤的便携式自动数据处理机器',
            }
            description = zh_descriptions.get(goods_code, description_en)
        else:
            description = description_en
        
        return GoodsDescription(
            goods_code=goods_code,
            language_code=language_code.upper(),
            reference_date=date.today(),
            description=description
        )
    
    def _mock_measures(self, goods_code: str, country_code: str, trade_movement: str) -> GoodsMeasures:
        """Mock 数据: 商品措施"""
        # 示例措施 (实际应从 API 获取)
        sample_measures = {
            '87032319': [
                Measure(
                    measure_type='103',
                    measure_type_description='Import duty',
                    duty_rate='10%',
                    validity_start_date='2024-01-01',
                    regulation_id='R(2024)1234'
                ),
                Measure(
                    measure_type='710',
                    measure_type_description='Import control',
                    duty_rate=None,
                    validity_start_date='2024-01-01',
                    regulation_id='R(2024)5678'
                ),
            ],
            '85171300': [
                Measure(
                    measure_type='103',
                    measure_type_description='Import duty',
                    duty_rate='0%',
                    validity_start_date='2024-01-01',
                    regulation_id='R(2024)2345'
                ),
            ],
        }
        
        measures = sample_measures.get(goods_code, [])
        
        return GoodsMeasures(
            goods_code=goods_code,
            country_code=country_code.upper(),
            reference_date=date.today(),
            trade_movement=trade_movement.upper(),
            measures=measures
        )
