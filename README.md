# taric-match

EU TARIC 海关关税查询工具。

## 安装

```bash
# 方式1: pip 安装
pip install taric-match

# 方式2: 从源码安装
git clone https://github.com/yourusername/taric-match.git
cd taric-match
pip install -e .
```

## 使用方法

### 查询商品描述

```bash
taric-match describe 87032319 --lang zh
```

### 查询关税措施

```bash
taric-match measure 87032319 --country CN --movement I
```

### 查询历史数据

```bash
taric-match describe 87032319 --date 2024-01-15
```

## 配置

可以通过环境变量配置:

```bash
export TARIc_API_URL="https://ec.europa.eu/.../dds2/taric/webservices"
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
black taric_match tests
mypy taric_match
```

## License

MIT
