"""CLI 命令。"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import pandas as pd
from rich import print as rprint
from rich.table import Table

from taric_match.api import TaricAPIError, TaricClient


def _format_validity(start: Optional[str], end: Optional[str]) -> str:
    if start and end:
        return f"{start} - {end}"
    if start:
        return f"{start}+"
    if end:
        return f"截止 {end}"
    return "-"


def _api_error(exc: TaricAPIError) -> click.ClickException:
    message = (
        f"{exc.message}\n" "如果你只是想先本地演示，可设置环境变量 TARIC_USE_MOCK=true 后重试。"
    )
    return click.ClickException(message)


@click.group()
@click.option("--api-url", default=None, help="TARIC API URL")
@click.option("--timeout", default=30, show_default=True, type=int, help="请求超时时间（秒）")
@click.option(
    "--mock/--no-mock",
    default=False,
    show_default=True,
    help="显式启用内置 mock 数据，不访问真实 TARIC 接口",
)
@click.pass_context
def main(ctx: click.Context, api_url: Optional[str], timeout: int, mock: bool) -> None:
    """taric-match: 欧盟海关关税查询工具。"""
    ctx.ensure_object(dict)
    ctx.obj["client"] = TaricClient(api_url=api_url, timeout=timeout, use_mock=mock)


@main.command("query")
@click.argument("goods_code")
@click.option(
    "--country",
    default="EU",
    show_default=True,
    help="国家代码 (ISO 2位, 如 CN, US, 默认 EU)",
)
@click.option(
    "--movement",
    default="I",
    show_default=True,
    type=click.Choice(["I", "E", "IE"]),
    help="贸易方向 (I=进口, E=出口, IE=两者)",
)
@click.option(
    "--date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="参考日期 (YYYY-MM-DD)",
)
@click.option(
    "--lang",
    default="EN",
    show_default=True,
    help="描述语言 (EN, ZH, FR, DE...)",
)
@click.pass_context
def query(
    ctx: click.Context,
    goods_code: str,
    country: str,
    movement: str,
    date: Optional[datetime],
    lang: str,
) -> None:
    """查询商品编码对应的关税措施。"""
    client: TaricClient = ctx.obj["client"]
    ref_date = date.date() if date else None

    try:
        desc = client.get_goods_description(
            goods_code=goods_code,
            language_code=lang.upper(),
            reference_date=ref_date,
        )
        measures = client.get_goods_measures(
            goods_code=goods_code,
            country_code=country.upper(),
            trade_movement=movement,
            reference_date=ref_date,
        )
    except TaricAPIError as exc:
        raise _api_error(exc) from exc

    table = Table(title=f"商品信息: {goods_code}")
    table.add_column("字段", style="cyan")
    table.add_column("值")
    table.add_row("商品编码", measures.goods_code)
    table.add_row("描述", desc.description or measures.description or "-")
    table.add_row("国家", measures.country_code)
    table.add_row("贸易方向", {"I": "进口", "E": "出口", "IE": "两者"}[movement])
    rprint(table)

    if not measures.measures:
        rprint("[yellow]未找到适用的关税措施[/yellow]")
        return

    measures_table = Table(title=f"关税措施 ({len(measures.measures)}项)")
    measures_table.add_column("措施类型", style="yellow")
    measures_table.add_column("措施描述")
    measures_table.add_column("税率/金额")
    measures_table.add_column("附加代码")
    measures_table.add_column("有效期")
    measures_table.add_column("法规编号")

    for measure in measures.measures:
        measures_table.add_row(
            measure.measure_type,
            measure.measure_type_description or "-",
            measure.duty_rate or "-",
            measure.additional_code.code if measure.additional_code else "-",
            _format_validity(measure.validity_start_date, measure.validity_end_date),
            measure.regulation_id or "-",
        )

    rprint(measures_table)


@main.command("batch")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", default="result.xlsx", show_default=True, help="输出文件路径")
@click.option("--column", default="商品编码", show_default=True, help="商品编码所在的列名")
@click.option("--country", default="EU", show_default=True, help="国家代码")
@click.pass_context
def batch(
    ctx: click.Context,
    input_file: str,
    output: str,
    column: str,
    country: str,
) -> None:
    """批量查询 Excel 中的商品编码。"""
    client: TaricClient = ctx.obj["client"]

    try:
        df = pd.read_excel(input_file)
    except Exception as exc:  # pragma: no cover - pandas/openpyxl details are noisy
        raise click.ClickException(f"读取 Excel 失败: {exc}") from exc

    if column not in df.columns:
        raise click.ClickException(f"未找到列 '{column}'，可用列: {list(df.columns)}")

    output_path = Path(output)
    codes = [str(code).strip() for code in df[column].dropna().tolist() if str(code).strip()]
    if not codes:
        raise click.ClickException(f"列 '{column}' 中没有可用的商品编码")

    rprint(f"📦 共有 {len(codes)} 个商品编码待查询")

    results = []
    for index, code in enumerate(codes, start=1):
        rprint(f"🔍 查询 [{index}/{len(codes)}]: {code}")

        try:
            description = client.get_goods_description(code, language_code="ZH").description
            measures = client.get_goods_measures(
                goods_code=code,
                country_code=country.upper(),
                trade_movement="I",
            )
        except TaricAPIError as exc:
            raise _api_error(exc) from exc

        if not measures.measures:
            results.append(
                {
                    "商品编码": code,
                    "描述": description or measures.description or "-",
                    "措施类型": "无措施",
                    "措施描述": "-",
                    "税率": "-",
                    "附加代码": "-",
                    "有效期": "-",
                    "法规编号": "-",
                }
            )
            continue

        for measure in measures.measures:
            results.append(
                {
                    "商品编码": code,
                    "描述": description or measures.description or "-",
                    "措施类型": measure.measure_type,
                    "措施描述": measure.measure_type_description or "-",
                    "税率": measure.duty_rate or "-",
                    "附加代码": measure.additional_code.code if measure.additional_code else "-",
                    "有效期": _format_validity(
                        measure.validity_start_date,
                        measure.validity_end_date,
                    ),
                    "法规编号": measure.regulation_id or "-",
                }
            )

    result_df = pd.DataFrame(results)
    result_df.to_excel(output_path, index=False)
    rprint(f"✅ 结果已保存到: {output_path}")


@main.command("version")
def version() -> None:
    """显示版本。"""
    from taric_match import __version__

    click.echo(f"taric-match v{__version__}")
