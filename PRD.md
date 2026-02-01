# taric-match 功能需求书 (PRD)

## 1. 项目概述

### 1.1 项目简介
`taric-match` 是一个基于 Python 的欧盟海关关税查询工具，通过调用 EU TARIC 官方 Web Services API，帮助用户快速查询商品编码（HS Code/TARIC Code）对应的关税税率、贸易措施和政策信息。

### 1.2 目标用户
- 进出口贸易企业
- 报关代理公司
- 跨境电商从业者
- 海关事务从业人员

### 1.3 核心价值
- 快速查询欧盟关税信息
- 替代手动查询 EU TARIC 网站
- 支持命令行和未来 Web UI 双模式

---

## 2. 功能列表

### 2.1 MVP 功能 (Phase 1) - 核心查询

| 功能 | 描述 | 输入 | 输出 |
|------|------|------|------|
| **商品描述查询** | 查询 TARIC 编码的商品描述 | TARIC Code (4-10位), 语言 | 商品名称/描述 |
| **关税措施查询** | 查询某商品针对某国的关税措施 | TARIC Code, 国家代码, 贸易方向 | 关税税率、管制措施 |
| **多语言支持** | 支持多种语言描述 | 语言代码 (en, zh, fr, de...) | 对应语言描述 |
| **历史日期查询** | 查询特定日期的有效信息 | 参考日期 | 当日有效的数据 |

### 2.2 扩展功能 (Phase 2)

| 功能 | 描述 |
|------|------|
| **批量查询** | 批量导入 HS Code 列表，一次性查询 |
| **结果导出** | 导出 CSV/Excel 格式 |
| **查询历史** | 本地保存查询记录 |
| **商品编码搜索** | 通过描述文字搜索对应编码 |
| **国家查询** | 查询国家代码和地理区域信息 |

### 2.3 未来功能 (Phase 3)

| 功能 | 描述 |
|------|------|
| **Web UI** | 浏览器界面 |
| **多 API 来源** | 支持其他关税 API (ViaEurope, Taric Support 等) |
| **智能推荐** | 基于查询历史推荐相关编码 |
| **API 服务** | 提供 REST API 给其他程序调用 |

---

## 3. API 对接方案

### 3.1 EU TARIC Web Services

根据 EU 官方文档，使用两个 SOAP Web Services：

#### API 1: goodsDescrForWs (商品描述)

```
Endpoint: /dds2/taric/webservices (待确认具体URL)

输入参数:
- Goods code: 商品编码 (4-10位)
- Language Code: 语言代码 (en, zh, fr, de, es, it, nl, pl, pt, ro)
- Reference Date: 参考日期 (可选，默认当前日期)

输出:
- Goods_code: 商品编码
- Language_code: 语言代码
- Reference_date: 参考日期
- Description: 商品描述
```

#### API 2: goodsMeasForWs (关税措施)

```
输入参数:
- Goods code: 商品编码 (4-10位)
- Country Code: 国家代码 (ISO 2位，如 CN, US, JP)
- Reference Date: 参考日期 (可选)
- Trade Movement: 贸易方向 (I=进口, E=出口, IE=两者)

输出:
- Goods_code: 商品编码
- Country_code: 国家代码
- Reference_date: 参考日期
- Trade_movement: 贸易方向
- List of measures: 措施列表
  - Measure type: 措施类型
  - Duty rate: 关税税率
  - Additional code: 附加代码
  - Validity period: 有效期
```

### 3.2 技术实现

```python
# 核心依赖
requests          # HTTP 请求
zeep / suds-lite # SOAP 客户端 (或直接用 requests 构建 XML)
pandas           # 数据处理
rich             # CLI 美化输出
click            # CLI 框架
```

---

## 4. 用户故事

### Story 1: 查询商品描述
```
作为: 报关员
我想: 通过 TARIC 编码查询商品的中文描述
以便: 确认商品归类是否正确

场景:
- 输入: taric-match describe 87032319 --lang zh
- 输出: "仅需驾驶员乘坐的车辆" (中文描述)
```

### Story 2: 查询进口关税
```
作为: 贸易经理
我想: 查询某商品从中国进口到欧盟的关税税率
以便: 核算产品成本

场景:
- 输入: taric-match measure 87032319 --country CN --movement I
- 输出: 关税税率 10%, 增值税 21%, 特殊措施...
```

### Story 3: 历史数据查询
```
作为: 审计人员
我想: 查询某商品在特定历史日期的关税政策
以便: 核对历史进出口申报

场景:
- 输入: taric-match describe 87032319 --date 2024-01-15
- 输出: 当日有效的商品描述和措施
```

---

## 5. 目录结构

```
taric-match/
├── taric_match/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py          # SOAP API 客户端
│   │   ├── exceptions.py      # 自定义异常
│   │   └── models.py         # 数据模型
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py           # CLI 入口
│   │   ├── commands.py       # 命令实现
│   │   └── formatters.py     # 输出格式化
│   └── utils/
│       ├── __init__.py
│       ├── config.py         # 配置管理
│       └── logger.py         # 日志
├── tests/
│   ├── __init__.py
│   ├── test_api/
│   └── test_cli/
├── scripts/
│   ├── search.mjs           # Tavily 搜索脚本(复用)
│   └── extract.mjs          # Tavily 提取脚本(复用)
├── docs/
│   ├── API.md
│   └── USER_GUIDE.md
├── .github/
│   └── workflows/
│       └── ci.yml           # CI/CD 配置
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml           # Poetry 配置
├── requirements.txt         # Pip 依赖
└── setup.py
```

---

## 6. 开发里程碑

### Phase 1: MVP (Week 1-2)
- [ ] 项目初始化，配置开发环境
- [ ] 实现 API 客户端，连接 EU TARIC Web Services
- [ ] 实现 `describe` 命令 - 商品描述查询
- [ ] 实现 `measure` 命令 - 关税措施查询
- [ ] 基础单元测试 (覆盖率 > 80%)
- [ ] 首次提交 GitHub，发布 v0.1.0

### Phase 2: 完善功能 (Week 3-4)
- [ ] 实现 `search` 命令 - 通过描述搜索编码
- [ ] 实现 `country` 命令 - 国家代码查询
- [ ] 结果导出功能 (CSV)
- [ ] 查询历史记录
- [ ] 完善文档，发布 v0.5.0

### Phase 3: 优化与扩展 (Week 5-6)
- [ ] 批量查询功能
- [ ] 性能优化和缓存
- [ ] 错误处理和用户提示优化
- [ ] 发布 v1.0.0

---

## 7. 质量标准

### 7.1 代码质量
- 类型注解 (Type Hints) 全覆盖
- 单元测试覆盖率 > 80%
- 遵循 PEP 8 规范
- 使用 Poetry 管理依赖

### 7.2 用户体验
- 清晰的错误信息
- 进度提示
- 输出格式美观易读

### 7.3 运维
- CI/CD 自动测试
- 发布到 PyPI
- 版本语义化 (Semantic Versioning)

---

## 8. 风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| EU TARIC API 不可用 | 低 | 高 | 考虑备选 API (ViaEurope, Taric Support) |
| SOAP 接口变更 | 低 | 中 | 抽象 API 层，易于适配 |
| 语言支持不完整 | 中 | 低 | 默认为英文，逐步完善 |

---

## 9. 附录

### 9.1 参考资料
- EU TARIC 官方: https://ec.europa.eu/taxation_customs/dds2/taric/help/index.jsp
- API 文档: Web Services 章节

### 9.2 缩写说明
- TARIC: Integrated Tariff of the Community
- HS Code: Harmonized System Code
- API: Application Programming Interface
- SOAP: Simple Object Access Protocol

---

**文档版本**: v1.0
**创建日期**: 2026-02-01
**作者**: Cula (AI Assistant)
