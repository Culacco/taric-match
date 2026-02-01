"""CLI 命令"""

from datetime import datetime
from typing import Optional
import click
from rich import print as rprint
from rich.table import Table

from taric_match.api import TaricClient


@click.group()
@click.option(
    "--api-url",
    default=None,
    help="TARIC API URL",
)
@click.pass_context
def main(ctx: click.Context, api_url: str):
    """EU TARIC 海关关税查询工具"""
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url
    ctx.obj["client"] = TaricClient(api_url=api_url)


@main.command("describe")
@click.argument("goods_code")
@click.option(
    "--lang",
    default="EN",
    help="语言代码 (EN, ZH, FR, DE, etc.)",
)
@click.option(
    "--date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="参考日期 (YYYY-MM-DD)",
)
@click.pass_context
def describe(
    ctx: click.Context,
    goods_code: str,
    lang: str,
    date: Optional[datetime]
):
    """查询商品描述"""
    client: TaricClient = ctx.obj["client"]
    ref_date = date.date() if date else None

    try:
        result = client.get_goods_description(
            goods_code=goods_code,
            language_code=lang.upper(),
            reference_date=ref_date
        )

        table = Table(title="商品描述")
        table.add_column("字段", style="cyan")
        table.add_column("值")

        table.add_row("商品编码", result.goods_code)
        table.add_row("语言", result.language_code)
        table.add_row("参考日期", str(result.reference_date))
        table.add_row("描述", result.description)

        rprint(table)

    except Exception as e:
        rprint(f"[red]错误: {e}[/red]")


@main.command("measure")
@click.argument("goods_code")
@click.option(
    "--country",
    required=True,
    help="国家代码 (ISO 2位, 如 CN, US)",
)
@click.option(
    "--movement",
    default="I",
    type=click.Choice(["I", "E", "IE"]),
    help="贸易方向 (I=进口, E=出口, IE=两者)",
)
@click.option(
    "--date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="参考日期 (YYYY-MM-DD)",
)
@click.pass_context
def measure(
    ctx: click.Context,
    goods_code: str,
    country: str,
    movement: str,
    date: Optional[datetime]
):
    """查询关税措施"""
    client: TaricClient = ctx.obj["client"]
    ref_date = date.date() if date else None

    try:
        result = client.get_goods_measures(
            goods_code=goods_code,
            country_code=country.upper(),
            trade_movement=movement,
            reference_date=ref_date
        )

        # 基本信息
        table = Table(title="查询信息")
        table.add_column("字段", style="cyan")
        table.add_column("值")
        table.add_row("商品编码", result.goods_code)
        table.add_row("国家", result.country_code)
        table.add_row("贸易方向", {"I": "进口", "E": "出口", "IE": "两者"}[movement])
        table.add_row("参考日期", str(result.reference_date))
        rprint(table)

        # 措施列表
        if result.measures:
            measures_table = Table(title=f"适用措施 ({len(result.measures)}项)")
            measures_table.add_column("类型")
            measures_table.add_column("税率/金额")
            measures_table.add_column("有效期")
            measures_table.add_column("法规")

            for m in result.measures:
                measures_table.add_row(
                    m.measure_type,
                    m.duty_rate or "-",
                    f"{m.validity_start or ''} - {m.validity_end or ''}",
                    m.regulation_id or "-"
                )
            rprint(measures_table)
        else:
            rprint("[yellow]未找到适用的关税措施[/yellow]")

    except Exception as e:
        rprint(f"[red]错误: {e}[/red]")


@main.command("version")
def version():
    """显示版本"""
    from taric_match import __version__
    click.echo(f"taric-match v{__version__}")
