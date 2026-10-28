"""Build Chinese PDF and Markdown reports from validated measured results."""
import argparse
import hashlib
import html
import json
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, KeepTogether


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('results', type=Path)
    parser.add_argument('--font', default='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
    args = parser.parse_args()
    root = args.results.resolve()
    repo = Path(__file__).resolve().parents[1]
    metrics = json.loads((root / 'summary.json').read_text())
    validation = json.loads((root / 'validation.json').read_text())
    assert len(validation['files']) == 13 and metrics['rows'] == 2152
    assert sum(item['rows'] for item in validation['files']) == metrics['rows']
    # Refuse to publish a report if raw data changed after analysis.
    for item in validation['files']:
        raw = root / 'raw' / item['file']
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == item['sha256'], raw
        summary = pd.read_csv(root / 'tables' / item['file'])
        assert (summary.n == 4).all() and summary.n.sum() == item['rows'], item['file']
    timing = pd.read_csv(root / 'timing.tsv', sep='\t')
    assert len(timing) == 13 and (timing.exit_code == 0).all()
    assert not timing.duplicated(['dataset', 'task', 'group']).any()
    assert (pd.to_datetime(timing.finished_utc) >= pd.to_datetime(timing.started_utc)).all()
    elapsed = (pd.to_datetime(timing.finished_utc).max() - pd.to_datetime(timing.started_utc).min()).total_seconds()/60
    pdfmetrics.registerFont(TTFont('ReportCJK', args.font))
    body = ParagraphStyle('ChineseBody', fontName='ReportCJK', fontSize=9.5, leading=16,
                          wordWrap='CJK', spaceAfter=9, textColor=colors.HexColor('#263544'))
    heading = ParagraphStyle('ChineseHeading', parent=body, fontSize=18, leading=26,
                             textColor=colors.HexColor('#176B87'), spaceAfter=16, keepWithNext=True)
    small = ParagraphStyle('ChineseSmall', parent=body, fontSize=8, leading=12)
    caption = ParagraphStyle('ChineseCaption', parent=small, alignment=TA_CENTER, spaceAfter=12)
    story, markdown = [], []

    def title(text):
        story.append(Paragraph(html.escape(text), heading))
        markdown.append('## ' + text + '\n')

    def para(text):
        story.append(Paragraph(html.escape(text), body))
        markdown.append(text + '\n')

    def table(headers, rows, widths=None):
        data = [[Paragraph(html.escape(str(v)), small) for v in row] for row in [headers] + rows]
        t = Table(data, colWidths=widths or [499/len(headers)]*len(headers), repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E7F0F4')),
            ('VALIGN',(0,0),(-1,-1),'TOP'), ('TOPPADDING',(0,0),(-1,-1),6),
            ('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#9DB9C5')),
            ('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#D8E0E5'))]))
        story.extend([t, Spacer(1,12)])
        markdown.extend(['| '+' | '.join(map(str, headers))+' |',
                         '| '+' | '.join(['---']*len(headers))+' |'])
        markdown.extend('| '+' | '.join(str(v).replace('|','/') for v in row)+' |' for row in rows)
        markdown.append('')

    def figure(name, text, width=495):
        p=root/'figures'/name
        im=Image(str(p))
        im.drawHeight=im.imageHeight*width/im.imageWidth
        im.drawWidth=width
        story.append(KeepTogether([im, Paragraph(html.escape(text), caption)]))
        markdown.append(f'![{text}](results/{root.name}/figures/{name})\n')

    def page():
        story.append(PageBreak())

    def value(x, digits=2):
        if x is None or pd.isna(x):
            return '未定义'
        return f'{x:,.{digits}f}'

    title('DProvDB 论文复现实验报告')
    para('DProvDB: Differentially Private Query Processing with Multi-Analyst Provenance')
    para('论文：Shufan Zhang、Xi He；SIGMOD 2024。实验日期：2026 年 10 月 28 日。')
    para('本报告基于作者开源实现，在独立的 ARM64 Linux 容器与 PostgreSQL 16.1 上运行。采用 Adult 完整记录数据和 TPC-H SF=1，完成端到端、缓存、分析者约束、预算扩展、隐私组合与 delta 参数实验。')
    para(f'共完成 13 个实验批次、{metrics["rows"]:,} 条配置重复记录；每种配置重复 4 次。批次总墙钟时间约 {elapsed:.1f} 分钟。全部数字来自本次实际执行，作者原文数值仅在明确标注的对照中出现。')
    for d in ('adult','tpch'):
        m=metrics['datasets'][d]
        para(f'{d.upper()}：DProvDB 在 {m["e2e_settings"]} 个“隐私预算 × 调度方式”设置中，有 {m["e2e_agm_at_least_vanilla"]} 个设置的平均可回答查询数不低于 Vanilla。6 个分析者时，DProvDB 与 Vanilla 的可回答查询数之比为 {value(m["six_analysts_ratio"])}。')
    para('复现性质：作者实现的可运行复现与主要实验趋势核验，不是原论文每个图点的严格数值重现。数据行数、硬件、仓库参数与论文存在差异，详见本报告的有效性限制。误差线表示样本标准差，不是置信区间；效用使用四轮记录，公平性仅使用分数有定义的运行。')
    para('仓库：https://github.com/hobbescalvin414-tech/DProvDB；结果目录：reproduction/results/' + root.name)
    page()

    title('1. 研究问题与核心方法')
    para('差分隐私查询系统通过给统计结果加入随机噪声，限制某个个体的加入或删除对输出分布的影响。epsilon 越小通常意味着更强的隐私保护；delta 用于近似差分隐私的额外容许项。多个分析者反复访问同一数据库时，系统需要同时管理总预算、个人预算与结果复用。')
    para('将所有分析者视为一个主体，会让先提问的人耗尽公共预算；完全独立地回答每个人的问题，又可能为相同信息重复消耗预算。论文试图在满足查询精度要求的条件下，增加有限预算下的可回答查询数，并使资源分配体现分析者的权限等级。')
    table(['组成','作用'],[
        ['隐私溯源表','以分析者与视图为维度跟踪隐私损失，并施加个人、视图和系统总量约束。'],
        ['缓存的加噪摘要','保存数据直方图的差分隐私版本，后续查询可从摘要计算答案，减少重复访问与重复预算支出。'],
        ['追加高斯机制','从全局加噪摘要派生分析者本地摘要，通过追加噪声控制各自精度；利用噪声相关性减少跨分析者及跨时间的冗余预算。'],
        ['权限约束','按权限设置个人预算。追加高斯配置采用最大权限归一化，Vanilla 配置采用权限之和归一化。']], [115,384])
    para('理论与实验的边界：论文的隐私证明与公平性定理依赖其数学模型及约束条件；本次实验验证程序运行行为与效用趋势，不构成对差分隐私证明的独立形式化验证。')
    para('“公平”在这里不是每个人回答数量相等。论文按权限衡量资源分配，并以 nDCFG 作为经验指标；较高权限分析者的已回答查询在该分数中权重更大。')
    page()

    title('2. 实验环境与数据准备')
    table(['项目','实际设置'],[
        ['系统','macOS 主机上的 Docker；Linux aarch64；计算容器 2 CPU / 4 GiB，数据库容器 1 CPU / 1 GiB。'],
        ['语言与构建','Temurin Java 11.0.32.1；Scala 2.12.2；sbt 1.10.7；Maven 3.6.3。'],
        ['数据库','PostgreSQL 16.1；独立 dprovdb-repro-db 容器，无主机端口映射。'],
        ['分析与绘图','Python 3.10.12；NumPy 1.26.4；pandas 2.2.3；Matplotlib 3.9.2；Seaborn 0.13.2。'],
        ['源码基准','DProvDB c7a4cba240f89a8fb696e40557fe1c44fb4785b4；Chorus 35b9c06a9d0bf00d0b1eef1231f0b5ea0b237f1c。'],
        ['Adult','UCI 训练集与测试集合并，删除含 ? 的缺失记录，统一收入标签结尾句点；30,162 + 15,060 = 45,222 行。'],
        ['TPC-H','作者推荐 tpch-kit 生成 SF=1 全部八张表。实验使用 orders：1,500,000 行；lineitem 校验为 6,001,215 行。']], [95,404])
    para('论文写 Adult 45,224 行，而标准 UCI 完整记录合并得到 45,222 行，差 2 行；仓库原始 adult.data 只有 32,561 行。本次不补造记录，并保留原始文件不变。原仓库数据另存为 adult_upstream 数据库，仅用于准备核验，没有混入正式统计。')
    para('与论文的计时环境不同：原文使用 AMD Ryzen 5 3600、64 GB DDR4 的 Linux 服务器。本次结果只能用于当前环境内比较，不能将绝对耗时差直接归因于算法。')
    page()

    title('3. 实验设计与统计口径')
    table(['批次类型','参数及比较对象','记录数'],[
        ['RRQ 端到端 × 2 数据集','每分析者 4,000 条范围查询；epsilon 为 0.4/0.8/1.6/3.2/6.4；轮询与随机调度；5 种方法。','400'],
        ['BFS 探索 × 2','权限 1:4；总体预算 200；DProvDB、Vanilla、Chorus、ChorusP。','32'],
        ['分析者约束 × 2','2 至 6 个分析者；比较追加高斯的两种预算约束与 Vanilla。','216'],
        ['缓存 × 2','总查询数 100/800/2,000/4,000/8,000/14,000；5 个预算值；4 种方法。','960'],
        ['预算扩展 × 2','扩展系数 1/1.3/1.6/1.9；5 个预算值；两种调度。','320'],
        ['隐私组合 × 2','basic/advanced/renyi；每分析者 15,000 条查询。','24'],
        ['delta 敏感性：Adult','每查询 delta 从 1e-13 至 1e-9；epsilon=6.4；两种调度；5 种方法。','200']], [108,337,54])
    para('权限比例：端到端与 delta 使用 1:4；分析者约束实验沿用仓库的等权限 5。四轮工作负载种子分别为 1025、2050、3075、4100。相同参数结果按四轮计算均值和样本标准差，绝不把四次记录当作四种独立配置。')
    para('DProvDB 对应代码 aGM；Vanilla 对应 baseline；sPrivateSQL 是作者对 PrivateSQL 的模拟，不是完整外部系统。ChorusP 是带溯源、无缓存的对照。Brownian 是仓库后来加入的方法，本次不纳入论文对照。')
    para('原始 CSV 的 DCFG 未归一化，本次分析以 DCFG / utility 计算 nDCFG。utility=0 时记为未定义，不补成 0；其均值和标准差只使用有定义的轮次，有效样本数见汇总表 ndcfg_n，单个有效样本不估计标准差。BFS 使用所记录累计预算序列的末值，不补造未记录的中间或末尾点。原始 avgAccuracy 实际累计的是请求精度要求，不能当作实际答案误差。')
    page()

    title('4. 端到端查询效用')
    figure('adult_utility.png','图 1：Adult 在固定预算下的可回答查询数，均值 ± 样本标准差。')
    figure('tpch_utility.png','图 2：TPC-H orders 的端到端效用，统计口径同图 1。')
    table(['epsilon=6.4，轮询','DProvDB','Vanilla','sPrivateSQL','Chorus','ChorusP'],
          [[d.upper()]+[value(metrics['datasets'][d]['epsilon_6_4_round_robin'][m],1)
                        for m in ('DProvDB','Vanilla','sPrivateSQL','Chorus','ChorusP')]
           for d in ('adult','tpch')], [124,75,75,75,75,75])
    examples = []
    for dataset in ('adult', 'tpch'):
        comparison = metrics['datasets'][dataset]['epsilon_6_4_round_robin']
        leader = max(comparison, key=comparison.get)
        if leader != 'DProvDB':
            examples.append(f"{dataset.upper()} 中 {leader} 平均回答 {value(comparison[leader], 1)} 条，DProvDB 为 {value(comparison['DProvDB'], 1)} 条")
    if examples:
        para('在 epsilon=6.4、轮询设置下，' + '；'.join(examples) + '。因此本次结果不支持 DProvDB 在所有设置下都领先的表述。这里比较的是样本均值，未进行显著性检验。')
    para('这些结果比较的是满足实现中查询精度要求的回答数量，不是所有已回答查询具有相同的实际相对误差。缓存命中率、预算分配和查询需求共同影响曲线。与原文的趋势比较应同时考虑第 11 节中的实现差异。')
    para('Chorus 类基线的极低回答数还受到实现口径影响：预算换算接收视图覆盖桶数作为敏感度，而实际 COUNT 加噪使用单条记录敏感度。与高斯/Laplace 差异一起，这使得巨大效用比不能直接解释为公平控制条件下的纯算法提升。')
    page()

    title('5. 多分析者的公平性')
    figure('adult_fairness.png','图 3：Adult 的 nDCFG；无查询被回答时该分数未定义，图中不绘制。')
    figure('tpch_fairness.png','图 4：TPC-H 的 nDCFG。')
    para('nDCFG = [各分析者已回答查询数 / log2(1 + 1/权限) 的总和] / 总已回答查询数。对于权限 1 和 4，该指标介于 1 与约 3.106 之间；上界对应全部回答分配给高权限分析者。因此它应结合效用和各分析者回答数解释，而不能单独作为普适公平性的证明。')
    para('原文自身也存在需要澄清的口径：第 11 页正文写默认权限 1:4，但图 3 的 nDCFG 出现约 4-6 的数值，超过按同页公式计算的 3.106 上界。仓库 1:9 设置的理论上界约 6.579，与图的量级相近，但不足以确定原图实际参数。本次采用正文 1:4 和明确公式，不追求机械匹配该图纵轴。')
    para('轮询与随机调度的对比考察提问顺序对资源分配的影响。完整的个人回答数保留在原始 CSV 的 utility_breakdown 中，汇总统计保留在 tables/ 目录。')
    page()

    title('6. 缓存摘要的作用')
    figure('adult_cache.png','图 5：Adult 缓存组件比较；横轴为所有分析者提交的总查询数。')
    para('TPC-H 的同类完整图另存为 figures/tpch_cache.png；两数据集的每个参数点都保留在汇总表和原始 CSV 中。')
    para('本组使用 DProvDB、Vanilla、Chorus、ChorusP，对多个查询规模和预算进行比较。DProvDB 与 Vanilla 都有可复用摘要；Chorus 与 ChorusP 不使用这些缓存。随着提交查询变多，含缓存的方法有机会通过复用提高总回答数，而不必为每个新请求独立访问原始数据库。')
    para('这是一组组件证据，而非完全隔离单一代码开关的实验：不同方法同时具有机制和预算管理差异。本次忠实保留作者实验设计，不把所有差异都归因于缓存一项。四次重复的具体结果与标准差可在 increasing_workload 汇总表中检查。')
    page()

    title('7. 追加高斯机制与分析者数量')
    figure('adult_analysts.png','图 6：Adult 的分析者数量与预算约束比较。')
    figure('tpch_analysts.png','图 7：TPC-H 的同类比较。')
    table(['6 个分析者，epsilon=3.2','DProvDB 均值','Vanilla 均值','比值'],
          [[d.upper(),value(metrics['datasets'][d]['six_analysts_agm'],1),
            value(metrics['datasets'][d]['six_analysts_vanilla'],1),
            value(metrics['datasets'][d]['six_analysts_ratio'])] for d in ('adult','tpch')], [190,110,110,89])
    para('原文在这组设置中报告约 2-4 倍的效用提升。本表给出本次独立运行的比值；它同时包含追加高斯机制和个人预算配置的影响。图中 max 对应 fixed-aGM，按最大权限归一化；sum 对应 fixed-normalized，按权限总和归一化，不能将两者混作同一种约束。')
    page()

    title('8. 预算扩展与 delta 敏感性')
    figure('adult_expansion.png','图 8：Adult 轮询下，扩展个人预算约束的效用与公平性变化。')
    figure('adult_delta.png','图 9：Adult RRQ 的每查询 delta 参数比较，epsilon 固定为 6.4。')
    para('预算扩展实验允许个人预算上限增大，但仍由实现的全局约束限制总支出。增加可使用预算可能改善利用率，同时改变低权限和高权限分析者的分配。TPC-H 的扩展图另存于 figures/tpch_expansion.png。')
    para('重要差异：论文图 8 的文字标为 BFS，而作者提供的 delta 实验入口实际生成 RRQ。本次执行并如实标注为 RRQ，不将其命名为对论文 BFS 图的精确重现。当前完整代码没有独立产生论文图 9 所需的逐查询实际误差记录，本报告不伪造该图。')
    page()

    title('9. 隐私组合方法对照')
    para('本组固定 DProvDB、轮询调度、权限 1:4 和总体 epsilon=6.4，每个分析者提交 15,000 条查询；比较上游实现中的 basic、advanced 和 renyi 三种隐私组合方式。每个设置重复四次。')
    composition_rows = []
    for dataset in ('adult', 'tpch'):
        f = pd.read_csv(root/'tables'/f'RRQ_{dataset}_compositions.csv')
        for name in ('basic', 'advanced', 'renyi'):
            row = f[f.composition == name].iloc[0]
            composition_rows.append([dataset.upper(), name,
                value(row.utility_mean, 1) + ' ± ' + value(row.utility_sd, 1),
                value(row.budget_mean, 4), value(row.execution_ms, 1)])
    table(['数据', '组合方式', '可答量均值 ± 标准差', '账本 epsilon', '执行 ms'],
          composition_rows, [66, 85, 160, 94, 94])
    para('原 CSV 没有单独写出 composition 字段。本次分析依据已固定的源码循环顺序，为每个 runIndex 内的三条记录标注 basic、advanced、renyi，并检查每种组合均有四个不同运行编号。这个映射规则明确写在分析脚本中。')
    para('该表比较的是现有实现的账本与查询效用。本次没有重新推导或证明不同组合方式之间的隐私参数换算，不能只凭一个较小的账本数值声称实际隐私更强。完整配置、运行时间和分组统计保存在 compositions 汇总 CSV 中。')
    page()

    title('10. 探索查询与运行开销')
    figure('bfs_budget.png','图 10：BFS 账本末次记录的累计 epsilon；均值 ± 样本标准差。')
    bfs=pd.read_csv(root/'tables/bfs_summary.csv')
    table(['数据','方法','查询数','累计预算','执行 ms','建视图 ms'],
        [[r.dataset.upper(),r.method,value(r.queries,1),value(r.budget_mean,4),value(r.execution_ms,1),value(r.setup_ms,1)]
         for r in bfs.itertuples()], [57,90,75,85,96,96])
    para('BFS 根据带噪回答决定是否继续探索，不同方法和随机噪声可能产生不同实际路径。因此，“末次记录预算更低”并不自动意味着它们完成完全相同的查询序列；必须结合回答数量一起阅读。另因上游 BFS 的 totalNoOfQueries 字段重复乘入分析者数量，本报告不使用该字段计算完成率。')
    para('执行时间取作者 System.execute() 的计时区间；建视图时间单独列出。RRQ 会复用 State 中的视图，记录的 setup_time 可能沿用之前的视图构建值，因此不能简单逐行相加。此外，原实验框架对 Chorus 类方法也统一预建视图；这部分是框架准备开销，不能理解为 Chorus 算法必须建视图。方法内仍存在直接输出日志，记录的执行时间包含相应开销。')
    para('按用户加速要求，后段 TPC-H 预算扩展/组合和 Adult delta 与 TPC-H 组件批次并行运行，使用相同源码和独立输出文件。共享 CPU、数据库与磁盘会影响运行时间；这些计时仅作为本次执行记录，不用于严格性能基准结论。实际批次起止时间见 timing.tsv。')
    page()

    title('11. 与原文的差异及有效性限制')
    table(['方面','处理与限制'],[
        ['数据','Adult 使用标准完整记录 45,222 行，原文写 45,224；不会补造数据。TPC-H SF=1，实验访问 orders。'],
        ['参数适配','可选 paper 配置将 1:9 改为 1:4、排除 Brownian，并删除扩展机制列表和 delta 列表里的重复项；默认配置仍保留上游行为。'],
        ['总体 delta','保留原实现 deltaConstraint=1e-5。对 1,500,000 行 orders，这大于原文建议的 1/N≈6.67e-7。因此 TPC-H 的数值结果不能直接宣称满足该原文建议设置。'],
        ['随机性','四轮工作负载种子有记录，但代码并未把所有噪声来源统一到这些种子。重跑可能得到不同输出，四轮也不足以支持强统计推断。'],
        ['基线实现','原文描述 Chorus 使用高斯机制，但当前 Chorus/ChorusP 源码实际调用 laplaceSample。本次保留实现，不把它说成严格一致的高斯基线复现。'],
        ['支持范围','完成作者脚本中的主要比较和补充组合实验；没有从零重写算法、重证理论，也没有独立验证所有答案的真实误差或复现论文全部图。'],
        ['运行平台','ARM64 容器和资源限制与论文硬件不同。为避免短寿命 ThreadLocal RNG 累积导致长批次变慢，单线程实验直接使用相同的 MersenneTwister，省略 ThreadLocal 包装。随机算法、参数与机制公式不改；所有正式结果统一采用此适配。']], [84,415])
    para(f'结构校验：{len(validation["files"])} 份 CSV 均达到预期行数；每组配置均有四次记录；工作负载种子、回答数求和、主要数值有限性均通过检查。累计 epsilon 超限检查发现 {sum(v["epsilon_exceeded_rows"] for v in validation["files"])} 条超限记录。该检查仅核验日志中的账本，不等同于数学隐私证明。')
    para('报告保留不一致与局限，避免把“运行成功”写成“完整精确复现”。若要进一步追求逐图数值对齐，需要作者确认 Adult 清洗版本、原始参数、delta 工作负载定义和完整噪声种子。')
    page()

    title('12. 复现步骤、产物与参考资料')
    para('在仓库根目录准备环境：docker build -t dprovdb-repro:java11 reproduction；然后 bash reproduction/build.sh。已有独立数据库时，可运行 bash reproduction/run-suite.sh reproduction/results/新的目录。脚本拒绝覆盖已有结果，并在结束或失败时停止专用数据库。')
    para('数据库首次创建、数据下载与导入步骤见 reproduction/README.md。绘图：bash reproduction/container.sh python3 reproduction/analyze.py reproduction/results/结果目录。中文报告生成使用 reproduction/report.py，需 reportlab、pandas 和一个支持中文的字体。')
    table(['产物','位置'],[
        ['本报告可修改源稿','reproduction/REPORT.md'],
        ['PDF','output/pdf/DProvDB-reproduction-report.pdf'],
        ['原始结果与日志','reproduction/results/'+root.name+'/raw/ 与 logs/'],
        ['图表及分组统计','同目录 figures/ 与 tables/'],
        ['完整性与来源','validation.json、summary.json、source-check.txt、manifest.json、timing.tsv'],
        ['运行脚本与改动','reproduction/ 下脚本；实验入口中的 opt-in paper 配置；保留上游默认行为。']], [115,384])
    para('[1] Zhang, Shufan; He, Xi. DProvDB: Differentially Private Query Processing with Multi-Analyst Provenance. SIGMOD 2024；用户提供的全文为 arXiv:2309.10240v1，主要参照第 1、5、6 节及附录 C。https://arxiv.org/abs/2309.10240')
    para('[2] DProvDB 作者开源实现。https://github.com/DProvDB/DProvDB。本次基准提交与压缩包中的 Experiment.scala 完全一致，SHA-256 记录在 source-check.txt。')
    para('[3] UCI Adult 数据集。https://archive.ics.uci.edu/dataset/2/adult。原始文件来源与校验值见 adult-manifest.json。')
    para('[4] TPC-H 数据生成器。https://github.com/gregrahn/tpch-kit；本次固定提交 852ad0a5ee31ebefeed884cea4188781dd9613a3。')

    output = repo/'output/pdf'
    output.mkdir(parents=True, exist_ok=True)
    pdf=output/'DProvDB-reproduction-report.pdf'
    def footer(canvas, doc):
        canvas.setFont('ReportCJK',8)
        canvas.setFillColor(colors.HexColor('#657784'))
        canvas.drawString(48,25,'DProvDB | 实测复现报告 | 2026-10-28')
        canvas.drawRightString(A4[0]-48,25,str(doc.page))
    SimpleDocTemplate(str(pdf), pagesize=A4, leftMargin=48, rightMargin=48,
                      topMargin=43, bottomMargin=43, title='DProvDB 论文复现实验报告',
                      author='hobbescalvin414-tech').build(story, onFirstPage=footer, onLaterPages=footer)
    (repo/'reproduction/REPORT.md').write_text('\n'.join(markdown))
    print(pdf)


if __name__ == '__main__':
    main()
