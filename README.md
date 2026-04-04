# taric-match

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![GitHub](https://img.shields.io/badge/GitHub-Culacco%2Ftaric-match-black)

欧盟海关关税查询工具。通过 EU TARIC 官方 Web Services API 查询商品编码对应的关税措施和管制信息。

## 功能

- 🔍 **单条查询**: 输入商品编码 → 查询关税措施
- 📦 **批量查询**: 导入 Excel → 批量匹配 → 导出结果
- 🌐 **多语言支持**: 支持多种语言描述
- 📅 **历史日期**: 可查询特定日期的有效数据

## 安装

```bash
# 从源码安装
git clone https://github.com/Culacco/taric-match.git
cd taric-match
pip install -e .
```

开发环境也可以使用 Poetry:

```bash
poetry install --with dev
```

## 使用方法

### 单条查询

```bash
taric-match query 87032319 --country CN
```

如果 TARIC 官方接口暂时不可用，但你想先本地演示 CLI：

```bash
TARIC_USE_MOCK=true taric-match query 87032319 --country CN
```

输出示例:
```
┌─────────────────────────────────────┐
│ 商品编码: 87032319                   │
│ 描述: 仅需驾驶员乘坐的车辆            │
├─────────────────────────────────────┤
│ 措施类型        │ 税率    │ 有效期   │
├────────────────┼─────────┼──────────┤
│ 进口关税        │ 10%     │ 2024-01+ │
│ 进口管制(710)   │ -       │ 2024-01+ │
│ 增值税(VAT)     │ 21%     │ 2024-01+ │
└────────────────┴─────────┴──────────┘
```

### 批量查询

```bash
taric-match batch products.xlsx -o results.xlsx --column 商品编码
```

## 命令

| 命令 | 描述 |
|------|------|
| `taric-match query <编码>` | 查询单个商品编码 |
| `taric-match batch <文件>` | 批量查询 Excel 文件 |
| `taric-match --help` | 显示帮助信息 |

## 选项

### query 命令

| 选项 | 默认值 | 描述 |
|------|--------|------|
| `--country` | EU | 国家代码 (ISO 2位) |
| `--movement` | I | 贸易方向: I=进口, E=出口, IE=两者 |
| `--date` | 当前日期 | 参考日期 (YYYY-MM-DD) |
| `--lang` | EN | 描述语言 |

### batch 命令

| 选项 | 默认值 | 描述 |
|------|--------|------|
| `--output, -o` | result.xlsx | 输出文件路径 |
| `--column` | 商品编码 | 商品编码所在列名 |
| `--country` | EU | 国家代码 |

## API

本工具使用 EU TARIC 官方 Web Services:
- `goodsDescrForWs`: 获取商品描述
- `goodsMeasForWs`: 获取关税措施

## 开发

```bash
# 安装开发依赖
poetry install --with dev

# 运行测试
poetry run pytest

# 代码检查
poetry run black --check taric_match tests
poetry run isort --check taric_match tests
poetry run mypy taric_match
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License - 详见 LICENSE 文件

## 参考

- [EU TARIC 官方](https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp?Lang=en)
- [TARIC Help](https://ec.europa.eu/taxation_customs/dds2/taric/help/index.jsp?Lang=en)
