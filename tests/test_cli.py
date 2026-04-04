"""CLI 测试。"""

from datetime import date
from pathlib import Path

import pandas as pd
from click.testing import CliRunner

from taric_match.api import GoodsDescription, GoodsMeasures, Measure, TaricAPIError
from taric_match.cli import main


class FakeClient:
    def __init__(self, api_url=None, timeout=30, use_mock=False):  # noqa: ANN001, D401
        self.api_url = api_url
        self.timeout = timeout
        self.use_mock = use_mock

    def get_goods_description(
        self, goods_code, language_code="EN", reference_date=None
    ):  # noqa: ANN001
        return GoodsDescription(
            goods_code=goods_code,
            language_code=language_code,
            reference_date=reference_date or date.today(),
            description="测试商品",
        )

    def get_goods_measures(  # noqa: ANN001
        self,
        goods_code,
        country_code="CN",
        trade_movement="I",
        reference_date=None,
    ):
        return GoodsMeasures(
            goods_code=goods_code,
            country_code=country_code,
            reference_date=reference_date or date.today(),
            trade_movement=trade_movement,
            description="测试商品",
            measures=[
                Measure(
                    measure_type="103",
                    measure_type_description="Import duty",
                    duty_rate="10%",
                    validity_start_date="2024-01-01",
                    regulation_id="R1234",
                )
            ],
        )


class ErrorClient(FakeClient):
    def get_goods_description(
        self, goods_code, language_code="EN", reference_date=None
    ):  # noqa: ANN001
        raise TaricAPIError("真实 API 暂时不可用")


def test_help_command() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "query" in result.output
    assert "batch" in result.output


def test_query_command(monkeypatch) -> None:  # noqa: ANN001
    runner = CliRunner()
    monkeypatch.setattr("taric_match.cli.commands.TaricClient", FakeClient)
    result = runner.invoke(main, ["query", "87032319", "--country", "CN", "--lang", "ZH"])
    assert result.exit_code == 0
    assert "商品信息: 87032319" in result.output
    assert "测试商品" in result.output
    assert "Import duty" in result.output


def test_query_command_surfaces_api_error(monkeypatch) -> None:  # noqa: ANN001
    runner = CliRunner()
    monkeypatch.setattr("taric_match.cli.commands.TaricClient", ErrorClient)
    result = runner.invoke(main, ["query", "87032319"])
    assert result.exit_code != 0
    assert "真实 API 暂时不可用" in result.output
    assert "TARIC_USE_MOCK=true" in result.output


def test_batch_command_requires_existing_column(
    monkeypatch, tmp_path: Path
) -> None:  # noqa: ANN001
    runner = CliRunner()
    monkeypatch.setattr("taric_match.cli.commands.TaricClient", FakeClient)
    input_file = tmp_path / "products.xlsx"
    pd.DataFrame({"错误列": ["87032319"]}).to_excel(input_file, index=False)

    result = runner.invoke(main, ["batch", str(input_file), "--column", "商品编码"])
    assert result.exit_code != 0
    assert "未找到列 '商品编码'" in result.output


def test_batch_command_writes_results(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    runner = CliRunner()
    monkeypatch.setattr("taric_match.cli.commands.TaricClient", FakeClient)
    input_file = tmp_path / "products.xlsx"
    output_file = tmp_path / "result.xlsx"
    pd.DataFrame({"商品编码": ["87032319"]}).to_excel(input_file, index=False)

    result = runner.invoke(main, ["batch", str(input_file), "-o", str(output_file)])
    assert result.exit_code == 0
    assert output_file.exists()
    output_df = pd.read_excel(output_file)
    assert output_df.loc[0, "商品编码"] == 87032319 or output_df.loc[0, "商品编码"] == "87032319"
    assert output_df.loc[0, "描述"] == "测试商品"
