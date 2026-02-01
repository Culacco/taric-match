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
    """taric-match: 欧盟海关关税查询工具"""
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url
    ctx.obj["client"] = TaricClient(api_url=api_url)


@main.command("query")
@click.argument("goods_code")
@click.option(
    "--country",
    default="EU",
    help="国家代码 (ISO 2位, 如 CN, US, 默认 EU)",
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
@click.option(
    "--lang",
    default="EN",
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
):
    """查询商品编码对应的关税措施"""
    client: TaricClient = ctx.obj["client"]
    ref_date = date.date() if date else None

    try:
        # 1. 获取商品描述
        desc = client.get_goods_description(
            goods_code=goods_code,
            language_code=lang.upper(),
            reference_date=ref_date
        )

        # 2. 获取关税措施
        measures = client.get_goods_measures(
            goods_code=goods_code,
            country_code=country.upper(),
            trade_movement=movement,
            reference_date=ref_date
        )

        # 显示基本信息
        table = Table(title=f"商品信息: {goods_code}")
        table.add_column("字段", style="cyan")
        table.add_column("值")
        table.add_row("商品编码", measures.goods_code)
        table.add_row("描述", desc.description)
        table.add_row("国家", measures.country_code)
        table.add_row("贸易方向", {"I": "进口", "E": "出口", "IE": "两者"}[movement])
        rprint(table)

        # 显示措施列表
        if measures.measures:
            measures_table = Table(title=f"关税措施 ({len(measures.measures)}项)")
            measures_table.add_column("措施类型", style="yellow")
            measures_table.add_column("税率/金额")
            measures_table.add_column("有效期")
            measures_table.add_column("法规编号")

            for m in measures.measures:
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


@main.command("batch")
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output", "-o",
    default="result.xlsx",
    help="输出文件路径",
)
@click.option(
    "--column",
    default="商品编码",
    help="商品编码所在的列名",
)
@click.option(
    "--country",
    default="EU",
    help="国家代码",
)
@click.pass_context
def batch(
    ctx: click.Context,
    input_file: str,
    output: str,
    column: str,
    country: str,
):
    """批量查询 Excel 中的商品编码"""
    import pandas as pd
    from pathlib import Path

    client: TaricClient = ctx.obj["client"]

    try:
        # 读取 Excel
        rprint(f"📖 读取文件: {input_file}")
        df = pd.read_excel(input_file)

        if column not in df.columns:
            rprint(f"[red]错误: 未找到列 '{column}'[/red]")
            rprint(f"可用列: {list(df.columns)}")
            return

        # 获取商品编码列表
        codes = df[column].dropna().unique().tolist()
        rprint(f"📦 共有 {len(codes)} 个商品编码待查询")

        # 批量查询
        results = []
        for i, code in enumerate(codes, 1):
            rprint(f"🔍 查询 [{i}/{len(codes)}]: {code}")

            try:
                measures = client.get_goods_measures(
                    goods_code=str(code),
                    country_code=country.upper(),
                    trade_movement="I",
                    reference_date=None
                )

                if measures.measures:
                    for m in measures.measures:
                        results.append({
                            "商品编码": code,
                            "措施类型": m.measure_type,
                            "税率": m.duty_rate or "-",
                            "附加代码": m.additional_code or "-",
                            "有效期起": m.validity_start or "-",
                            "有效期止": m.validity_end or "-",
                            "法规编号": m.regulation_id or "-",
                        })
                else:
                    results.append({
                        "商品编码": code,
                        "措施类型": "无措施",
                        "税率": "-",
                        "附加代码": "-",
                        "有效期起": "-",
                        "有效期止": "-",
                        "法规编号": "-",
                    })

            except Exception as e:
                results.append({
                    "商品编码": code,
                    "措施类型": f"查询失败: {e}",
                    "税率": "-",
                    "附加代码": "-",
                    "有效期起": "-",
                    "有效期止": "-",
                    "法规编号": "-",
                })

        # 保存结果
        result_df = pd.DataFrame(results)
        result_df.to_excel(output, index=False)
        rprint(f"✅ 结果已保存到: {output}")

    except Exception as e:
        rprint(f"[red]错误: {e}[/red]")


@main.command("version")
def version():
    """显示版本"""
    from taric_match import __version__
    click.echo(f"taric-match v{__version__}")
