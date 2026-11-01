#!/usr/bin/env python3
"""Render five independent Chinese Markdown reports from validated local measurements."""
import json, pathlib, sys
import pandas as pd
BASE=pathlib.Path(__file__).resolve().parents[1]
LABEL={'aGM':'DProvDB/aGM','baseline':'Vanilla','PrivateSQL':'sPrivateSQL','Chorus':'Chorus','ChorusP':'ChorusP'}
INFO={
'bank':dict(title='银行营销：多分析者共享统计的预算与缓存',intro='Bank Marketing 来自葡萄牙银行的电话营销记录，适合模拟营销分析人员重复询问年龄、余额和联系行为的范围计数。这里研究统计查询处理，不训练存款订阅预测模型。',choice='明确选用官方压缩包内 bank.zip → bank-full.csv 的 45,211 行版本；没有使用 41,188 行 bank-additional-full.csv。年龄、余额、通话时长、当轮联系次数和历史联系次数都是可解释的数量字段。',boundary='记录关联客户营销行为，实验单位是一行营销记录；没有证明每位自然人只出现一次，不外推为人员级保护。职业、婚姻、月份等类别不参与范围查询；未选用包含 -1 哨兵的 pdays。',bfs='age',meaning='年龄',course='银行不同部门可能反复询问相近客群。缓存状态显示共享统计有复用机会，但权限 1:4 并不能自动保证个人隐私额度落实；必须把查询授权、缓存访问和隐私账本放在同一套检查中。余额长尾还提醒我们：统一桶宽能简化系统，却可能牺牲低余额区域的分辨率。'),
'credit':dict(title='信用卡客户：额度分布、权限与查询资源分配',intro='Default of Credit Card Clients 是台湾信用卡客户公开基准，包含额度、年龄、账单与还款信息。风险分析人员常对额度或金额区间求人数，因此适合测试多分析者范围查询。',choice='使用 UCI 官方 data.csv 的 30,000 行版本。根据 metadata 映射 X5→AGE、X1→LIMIT_BAL、X12→BILL_AMT1、X18→PAY_AMT1、X19→PAY_AMT2；不把 ID、SEX、EDUCATION、MARRIAGE 或 PAY_* 状态编码作为连续属性。',boundary='一行客户记录是本实验的数据贡献单位。金额字段保留负值原始含义，再用明确的线性变换映射到非负域；没有将负账单裁剪为零。',bfs='limit_bal',meaning='信用额度',course='同一额度区间可被授信、风险和运营分析复用，但回答数量多不等于风险模型更准。额度和金额的长尾使固定宽度直方图损失细节，展示了大数据近似结构的存储与分辨率取舍。资源分配还必须审计缓存路径，否则个人预算约束可能被复用逻辑绕过。'),
'shoppers':dict(title='网购行为：小数域适配与会话统计复用',intro='Online Shoppers Purchasing Intention 包含电商网站访问会话，适合研究页面访问数量、停留时间和转化相关指标的范围统计。数据混合计数、大跨度时长与 0 到 1 附近的小数。',choice='使用 UCI 官方 data.csv 的 12,330 个会话，选产品页面数、产品页面访问时长、BounceRates、ExitRates、PageValues。月份、浏览器、操作系统、访客类型等类别不当作连续范围。',boundary='实验单位是访问会话，不是去重后的访客。缩放保留原来的小数信息；避免原生成器把小值域转为整数后得到零尺度高斯分布。它不等于把 BounceRates 转成整数类别。',bfs='productrelated',meaning='产品页面数量',course='Web 指标常同时出现比例、时长和次数，类型正确只是第一步，查询生成器也要理解单位和数值尺度。统一尺度便于比较系统行为，却可能让不同业务的接受率完全一致。因此大数据评估既要报告系统指标，也要检查原始分布与业务语义。'),
'diabetes':dict(title='糖尿病住院记录：就诊级隐私与医疗数据分布',intro='Diabetes 130-US Hospitals 汇集 1999–2008 年 130 家美国医院的糖尿病相关住院记录。住院时长、检查和用药数量具有清晰计数语义，适合模拟不同医疗分析人员共享统计。',choice='使用官方 diabetic_data.csv 的全部 101,766 次就诊。选住院天数、化验次数、用药数量、既往门诊次数和既往住院次数。encounter_id、patient_nbr 不进入查询；年龄是区间类别，不把它转换成连续年龄。',boundary='这是就诊记录级实验，明确不是患者级差分隐私。同一患者可能多次入院；如果需要患者级保护，必须限制每位患者的贡献次数并重新计算敏感度。',bfs='num_lab_procedures',meaning='化验次数',course='医疗数据中的“一个人”和“一条记录”并不等价。分布式汇总、缓存和预算会计都依赖一致的贡献单位；仅把 ID 删除并不能得到患者级保护。未使用字段的缺失不应导致无理由删除完整就诊记录，预处理策略必须与分析任务相匹配。'),
'covertype':dict(title='森林植被：全量规模与地形分布验证',intro='Covertype 记录森林地形与覆盖类型，共 581,012 个 30×30 米地理单元。它比其余四组更大，用于验证全量扫描、直方图构建和地形分布下的系统表现。',choice='使用官方 covtype.data.gz 的 581,012 行、55 列原始文件；选海拔、坡度、到水源水平距离、到水源垂直距离、到道路水平距离。不把土壤和荒野区的二元编码全部纳入范围查询，也不使用覆盖类型标签作连续属性。',boundary='这是地理单元的规模和分布实验，不是个人隐私应用案例。它能检验软件路径，不能据此主张保护个人信息的实际效果。',bfs='elevation',meaning='海拔',course='输入从万级增长到近六十万行后，缓存视图将重复处理转为固定大小的统计结构，数据扫描与后续预算决策应分别计时。相同回答数不能说明扫描成本相同；相反，规模、分布、查询形状和并发资源要分开控制。本实验规模仍不足以证明分布式或十亿行可扩展性。')}
def fmt(v):return '未定义' if pd.isna(v) else f'{v:,.2f}'
def mdtable(df,columns):
 head='| '+' | '.join(columns.values())+' |\n| '+' | '.join(['---']*len(columns))+' |\n'
 return head+'\n'.join('| '+' | '.join(str(row[k]) for k in columns)+' |' for _,row in df.iterrows())
def report(name):
 p=BASE/name;i=INFO[name];m=json.loads((p/'manifest.json').read_text());v=json.loads((p/'validation.json').read_text());assert v['passed']
 d=pd.read_csv(p/'raw/results.csv');h=pd.read_csv(p/'raw/histograms.csv');s=pd.read_csv(p/'summary.csv')
 rr=s[(s.phase=='RRQ')&(s.scheduler=='round-robin')];bfs=s[s.phase=='BFS']
 table=[]
 for method in LABEL:
  row={'method':LABEL[method]}
  for budget in [.4,.8,1.6,3.2,6.4]:
   r=rr[(rr.mechanism==method)&(rr.budget==budget)].iloc[0];row[str(budget)]=f"{r.utility_mean:.2f} ± {r.utility_std:.2f}"
  table.append(row)
 rrtable=mdtable(pd.DataFrame(table),{'method':'方法',**{str(k):f'ε={k}' for k in [.4,.8,1.6,3.2,6.4]}})
 rows=[]
 for _,r in bfs.iterrows():rows.append({'method':LABEL[r.mechanism],'answers':f'{r.utility_mean:.2f} ± {r.utility_std:.2f}','cache':fmt(r.cache_hits_mean),'epsilon':fmt(r.epsilon_mean),'ndcfg':fmt(r.ndcfg_mean)})
 btable=mdtable(pd.DataFrame(rows),{'method':'方法','answers':'已回答数，均值 ± SD','cache':'缓存命中均值','epsilon':'最终 ε 账本均值','ndcfg':'nDCFG 均值'})
 fields='| 原始字段 | 实验字段 | 原始最小值 | 原始最大值 |\n| --- | --- | ---: | ---: |\n'+'\n'.join(f'| {f["source"]} | {f["name"]} | {f["min"]:.12g} | {f["max"]:.12g} |' for f in m['fields'])
 hist=h[h.attribute==i['bfs']].sort_values('bin');peak=hist.loc[hist['count'].idxmax()];share=peak['count']/m['raw_rows']*100
 f=next(f for f in m['fields'] if f['name']==i['bfs']);blo=f['min']+(f['max']-f['min'])*peak['bin']/50;bhi=f['min']+(f['max']-f['min'])*(peak['bin']+1)/50
 r=rr[(rr.mechanism=='aGM')&(rr.budget==6.4)].iloc[0];baseline=rr[(rr.mechanism=='baseline')&(rr.budget==6.4)].iloc[0]
 private=rr[(rr.mechanism=='PrivateSQL')&(rr.budget==6.4)].iloc[0]
 cachepct=100*r.cache_hits_mean/r.utility_mean if r.utility_mean else 0
 zeros=int((d.utility==0).sum());b=d[d.phase=='BFS'];delta_note='本组 1e-5 大于 1/N，应视为保留实现默认值的限制。' if 1e-5>1/m['raw_rows'] else '本组 1e-5 小于 1/N；这不替代整个实现的隐私证明。'
 missing='选定的五列均无缺失值，不做填补，不删除任何行。未选中字段的缺失或类别标记不影响本任务。'
 if name=='diabetes':missing+=f" 原始文件有 {m['distinct_patient_ids']:,} 个不同 patient_nbr，保留其全部 {m['raw_rows']:,} 次就诊；`?` 等缺失计数详见 manifest 的 raw_missing_counts。"
 tailfield=m['fields'][-1]['name'];tailhist=h[h.attribute==tailfield];tailpeak=100*tailhist['count'].max()/m['raw_rows']
 time_ms=d.view_setup_ms.iloc[0]
 random_high=s[(s.phase=='RRQ')&(s.scheduler=='random')&(s.mechanism=='aGM')&(s.budget==6.4)].iloc[0]
 # Individual bookkeeping is observational: do not label an implementation ledger a proof.
 personal_over=int(((d.mechanism=='aGM')&(d.epsilon_low>d.budget/4+1e-6)).sum())
 text=f'''# {i['title']}

本组实际完成 **{m['raw_rows']:,} 条全量记录、216 条正式配置记录**：范围查询 200 条（5 方法 × 5 预算 × 2 调度 × 4 轮），探索查询 16 条（4 方法 × 4 轮）。每条 RRQ 配置向两个分析者各提供 4,000 个请求；配置记录数不等于回答数。所有四轮和唯一键检查通过，详见 [validation.json](validation.json)。这是 SIGMOD 2024 论文 *DProvDB: Differentially Private Query Processing with Multi-Analyst Provenance* 的额外数据集扩展验证。

## 1. 数据与选择理由

{i['intro']}

{i['choice']} 官方说明：[UCI 数据集页面]({m['repository_url']})；本次具体下载：[官方数据文件]({m['download_url']})。版本由文件成员名、完整行列数和 SHA-256 共同标识，详见 [manifest.json](manifest.json)。

{i['boundary']}

## 2. 预处理与全量分布

原始文件 **{m['raw_rows']:,} 行、{m['raw_columns']} 列**；处理后仍为 **{m['processed_rows']:,} 行、5 列**。{missing}

{fields}

原始文件保留在本地 `.runtime/five-datasets/{name}/`，处理文件另存为 `processed.csv`，不将大体积公开原始数据提交 GitHub。每列按 `z = 1000 × (x − min) / (max − min)` 缩放至 `[0,1000]`，保留 12 位有效数字，不取整、不抽样、不截断。边界来自公开基准，若换成私人数据，边界估计也需要隐私设计。原生成器会对值域做整数转换，统一非退化值域保证小数比例等字段可运行。

![本组全量数据分布](figures/distribution.png)

分布图来自数据库实际生成的 5×50 桶计数，逐列求和均为 {m['raw_rows']:,}。以 BFS 字段“{i['meaning']}”为例，最密集的 20 单位缩放区间对应原始约 **{blo:.3g}–{bhi:.3g}**，占全部记录 **{share:.2f}%**。第五字段 `{tailfield}` 的最大单桶占比为 **{tailpeak:.2f}%**，提示等宽分桶下部分区间聚集、其他区间稀疏。缩放只改变坐标，没有把长尾或集中分布变均匀。

## 3. 方法、参数和运行

两位分析者权限为 1:4；机制为 DProvDB/aGM、Vanilla（baseline）、sPrivateSQL（PrivateSQL）、Chorus、ChorusP。aGM 使用 dynamic/fixed-aGM（个人额度 ε/4、ε），Vanilla 使用 dynamic/fixed-normalized；RRQ 其余三种使用 static/fixed-normalized。BFS 不运行 sPrivateSQL，其余三种基线使用 dynamic/fixed-normalized，沿用原探索配置。

- **RRQ**：ε∈{{0.4,0.8,1.6,3.2,6.4}}；round-robin 与 random；每人 4,000 条；请求方差上限 `max(3000−查询索引,1)`。这是沿用原端到端实验的绝对 COUNT 方差要求，不是相对误差保证。五字段抽样权重为 1:10:1:1:1，第二字段更频繁。
- **BFS**：字段 `{i['bfs']}`，ε=200，5 叉树，粒度 2，最多每人 156、两人 312 个候选；以带噪回答大于 **{m['raw_rows']*.01:g}（N 的 1%）** 决定继续探索。粒度与阈值是针对新值域和规模的明确适配，没有减少配置数。请求方差在 DFS 赋值顺序下为 24,900 至 9,400，执行顺序是 BFS。
- 两项均为 basic composition；每次 delta=1e-9，总 delta=1e-5。{delta_note}
- 四轮工作负载种子为 1025、2050、3075、4100；每方法每轮新建机制。噪声沿用上游未统一固定种子的发生器，不能保证重跑逐位相同；BFS 的树 ID 使用原固定生成流程，四轮不代表四棵随机几何树。

从仓库根目录运行（先按顶层 README 准备一次镜像、数据库和编译产物）：

```bash
python3 extensions/five-datasets/shared/prepare_data.py --dataset {name}
python3 extensions/five-datasets/shared/load_data.py {name} # 只用于尚不存在的新数据库
bash extensions/five-datasets/shared/run_one.sh {name} .runtime/five-datasets/{name}-new-smoke smoke
bash extensions/five-datasets/shared/run_one.sh {name} .runtime/five-datasets/{name}-new-formal formal
```

输出目录必须不存在，载入脚本拒绝替换已有数据库。正式批次使用冻结代码，最多两进程并行，每进程 2 CPU / 2 GiB、Java 堆 1200 MiB；共享专用 PostgreSQL。此并发计时不可当成严格硬件性能对比。源码版本、参数与 SHA-256 见 [experiment.json](../shared/experiment.json)，实际运行时间见 [日志](logs/)。

## 4. 实测统计

以下为四轮均值和样本标准差（SD，非置信区间）。nDCFG 仅聚合非零效用的轮次，其有效 count 见 summary.csv；全为零回答则保持未定义。重复一致时 SD=0；不会为了制造差异加入扰动。

### 范围查询

{rrtable}

![范围查询回答数](figures/utility.png)

在 round-robin、ε=6.4 下，aGM 平均回答 **{r.utility_mean:.2f}** 条，Vanilla 为 **{baseline.utility_mean:.2f}** 条；aGM 的缓存状态命中平均 **{r.cache_hits_mean:.2f}** 条，占其回答的 **{cachepct:.2f}%**。切换到 random 后，aGM 平均回答 **{random_high.utility_mean:.2f}** 条。这里的“缓存命中”来自执行状态计数，不保证零计算成本，aGM 缓存路径仍可能进行额外计算。

![正确归一化的公平性指标](figures/ndcfg.png)

`nDCFG = (u_low / log2(2) + u_high / log2(1.25)) / (u_low + u_high)`。它除以总回答数，**不是 0–1 分数**，本配置非零效用时约落在 [1,3.1063]。本组有 **{zeros}** 条配置零回答，其 nDCFG 和已回答请求方差均为空值，未当成 0 或正常公平性分数。该指标更偏重高权限分析者，不能直接解释为平等程度。

### 探索查询

{btable}

![探索查询回答数、缓存和账本](figures/bfs.png)

BFS 候选总数最多 312，实际回答范围为 **{int(b.utility.min())}–{int(b.utility.max())}**。提前停止会受分布、阈值、噪声及既有实现行为共同影响。预建本组五视图实际耗时 **{time_ms/1000:.3f} 秒**，每进程只初始化一次；CSV 中重复记录该值，不能把它按 216 行相加。完整分调度、分预算统计见 [summary.csv](summary.csv)。

## 5. 本组观察与不符合预期的结果

aGM 并非在所有设置都领先：round-robin、ε=6.4 时，sPrivateSQL 平均回答 **{private.utility_mean:.2f}** 条，对比 aGM 的 **{r.utility_mean:.2f}** 条。调度切换也会改变排名，说明静态视图预分配在本次统一查询结构下并非必然劣势；不能只挑出 aGM 最好的设置写结论。

本组数据的集中度可由分布图直接检查，但统一的五字段、值域、桶数、精度和种子使五组 RRQ 的接收数与账本呈相同结果。这反映原程序的接收决策主要取决于查询结构和预算，而不是数据值。我们保存每组各自运行的结果与日志，没有把其他组数字复制过来。

BFS 对带噪回答作分支决策，比 RRQ 更容易体现分布差异。不过原直方图桶顺序、查询范围与敏感度问题会影响这类解释，不能将方法间回答差异直接归因为更好的真实区间发现。预算为 200 时账本远低于上限并不奇怪：缓存复用和阈值剪枝都可能提前减少新发布。

另一个与直觉不符的结果是：aGM 本组有 **{personal_over}** 条配置的低权限分析者最终账本超过其实际个人额度 ε/4。aGM 按最高权限归一化，个人额度分别为 ε/4 和 ε；其缓存状态可早于个人约束检查返回。全局账本在上限内不能证明个人约束全部满足。

## 6. 对“大数据”课程的启发

{i['course']}

查询处理的吞吐、近似结构的分辨率、请求精度、实际答案误差和隐私预算是不同维度。本次同时保留原始结果、分布、账本和缓存计数，体现了大数据实验应如何区分这些维度；单看“回答更多”容易遗漏正确性与公平性问题。

## 7. 限制、验证和复现材料

本实验沿用原实现，没有重写机制公式，也不声称修复原 [source-audit.md](../../../reproduction/source-audit.md) 中的问题。Chorus/ChorusP 实际使用 Laplace 噪声但以 Gaussian 校准预算；范围桶数可能让基线预算换算过于保守。请求方差均值来自 `_accuracyRequirement`，**没有测量实际答案 MSE**；最终 epsilon 是程序账本，不是独立隐私证明。

新增审查还发现：原视图以 Map.values 顺序存入列表、回答却用数字桶索引，存在错桶风险；BFS 没给 `_rlb/_rub` 赋值，敏感度路径返回 1，无法据此保证跨桶答案满足请求方差；BFS 严格开区间 SQL 与整桶近似不等价。缓存路径个人额度检查及 BFS 拒答空指针问题也未修复。这些限制使 BFS 结果只能代表现有程序执行行为。详见 [扩展审查](../shared/implementation-notes.md)。

验证覆盖全部 216 条唯一配置、四轮种子、200/16 配置分组、计数守恒、零效用空值、nDCFG 公式、全局账本范围、原始直方图总数及进程成功结束。它不验证真实误差、患者级贡献约束或完整 DP 证明。

- [原始正式结果](raw/results.csv)、[真实直方图计数](raw/histograms.csv)、[统计汇总](summary.csv)
- [数据处理清单与校验值](manifest.json)、[验证结果](validation.json)、[运行日志与时间](logs/)
- [独立公共脚本和冻结参数](../shared/)、[本扩展导航](../README.md)

本组没有未完成的正式配置；未增加组件消融，未重跑 Adult/TPC-H。原始公开数据按官方来源重新下载，处理后 SHA-256 可与清单核对。
'''
 (p/'REPORT.md').write_text(text)
 print(name,'report written')
if __name__=='__main__':
 for name in sys.argv[1:] or INFO:report(name)
