# taric-match 功能需求书 (PRD)

## 1. 项目概述

### 1.1 项目简介
`taric-match` 是一个基于 Python 的欧盟海关关税查询工具，通过调用 EU TARIC 官方 Web Services API，查询商品编码对应的关税措施和管制信息。

### 1.2 核心需求
1. **单条查询**: 输入商品编码 → 输出所有关税措施
2. **批量查询**: 导入 Excel → 批量匹配 → 导出结果

---

## 2. API 对接

### 2.1 EU TARIC Web Services

| 接口 | 功能 |
|------|------|
| `goodsDescrForWs` | 获取商品描述 |
| `goodsMeasForWs` | 获取关税措施列表 |

### 2.2 goodsMeasForWs 返回字段

```
输入:
- Goods code: 商品编码 (4-10位)
- Country Code: 国家代码 (可选，默认 EU)
- Reference Date: 参考日期 (可选，默认当前)
- Trade Movement: 贸易方向 I/E/IE (可选)

输出:
- Goods_code: 商品编码
- Country_code: 国家代码
- Reference_date: 参考日期
- Trade_movement: 贸易方向
- List of measures:
  ├─ Measure type: 措施类型 (关税/管制/限制等)
  ├─ Duty rate: 税率/金额
  ├─ Additional code: 附加代码
  ├─ Validity period: 有效期
  └─ Regulation id: 法规编号
```

---

## 3. 功能规格

### Phase 1: MVP - 单条查询

```bash
# 命令
taric-match query <商品编码> [--country CN] [--date 2024-01-15]

# 输出
┌─────────────────────────────────────┐
│ 商品编码: 87032319                   │
│ 描述: 仅需驾驶员乘坐的车辆            │
├─────────────────────────────────────┤
│ 措施类型        │ 税率    │ 有效期   │
├────────────────┼─────────┼──────────┤
│ 进口关税        │ 10%     │ 2024-01+ │
│ 进口管制(710)   │ -       │ 2024-01+ │
│ 增值税( VAT)   │ 21%     │ 2024-01+ │
└────────────────┴─────────┴──────────┘
```

### Phase 2: 批量查询

```bash
# 命令
taric-match batch input.xlsx --output result.xlsx

# 输入 Excel 格式
| 商品编码    |
| 87032319   |
| 85171300   |

# 输出 Excel 格式
| 商品编码  | 描述                | 措施类型      | 税率  | 法规编号 |
| 87032319 | 仅需驾驶员乘坐的车辆 | 进口关税      | 10%   | R12345   |
| 87032319 | 仅需驾驶员乘坐的车辆 | 进口管制(710) | -     | R12346   |
| 85171300 | 无线耳机            | 进口关税      | 0%    | R12347   |
```

---

## 4. 目录结构

```
taric-match/
├── taric_match/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── client.py          # SOAP API 客户端
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py            # CLI 入口
│   │   └── commands.py        # query / batch 命令
│   └── utils/
│       ├── __init__.py
│       └── excel.py           # Excel 读写
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── .github/workflows/ci.yml
├── .gitignore
├── README.md
├── pyproject.toml
└── setup.py
```

---

## 5. 依赖

```toml
[tool.poetry.dependencies]
python = "^3.9"
click = "^8.1.7"              # CLI 框架
rich = "^13.7.0"              # 终端美化
pandas = "^2.1.0"             # Excel 处理
openpyxl = "^3.1.0"           # Excel 读写
requests = "^2.31.0"          # HTTP
python-dotenv = "^1.0.0"      # 环境变量
```

---

**文档版本**: v2.0 (精简版)
**创建日期**: 2026-02-01
