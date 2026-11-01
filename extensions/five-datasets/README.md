# DProvDB：五个额外数据集

本目录用于“大数据”课程五人分组分享，每组正文独立。核心实验为每组 200 条范围查询配置和 16 条探索查询配置，共 1,080 条正式记录；不包含新的组件消融。Adult/TPC-H 的既有复现不重跑、不覆盖。

| 小组 | 独立报告 | 全量记录数 | 正式配置 |
| --- | --- | ---: | ---: |
| 银行营销 | [bank/REPORT.md](bank/REPORT.md) | 45,211 | 200 RRQ + 16 BFS |
| 信用卡客户 | [credit/REPORT.md](credit/REPORT.md) | 30,000 | 200 RRQ + 16 BFS |
| 网购行为 | [shoppers/REPORT.md](shoppers/REPORT.md) | 12,330 | 200 RRQ + 16 BFS |
| 糖尿病就诊 | [diabetes/REPORT.md](diabetes/REPORT.md) | 101,766 | 200 RRQ + 16 BFS |
| 森林植被 | [covertype/REPORT.md](covertype/REPORT.md) | 581,012 | 200 RRQ + 16 BFS |

## 公共环境与运行

需要已有 `dprovdb-repro:java11` 镜像、Chorus 构建依赖和专用 `dprovdb-repro-db` 数据库容器。首次准备见 [原环境说明](../../reproduction/README.md)。不要对已有数据库运行会重新初始化资源的准备流程。本次只启动并复用专用容器，在原卷中新增五个数据库，不改变 Adult/TPC-H，也不操作其他项目容器。

在仓库根目录执行：

```bash
# 元数据、原文件、处理后 CSV 均置于 .runtime/five-datasets，默认不上传
python3 extensions/five-datasets/shared/prepare_data.py
python3 extensions/five-datasets/shared/check_data.py

docker start dprovdb-repro-db
# 等 pg_isready 成功后再导入；已有数据库会被明确拒绝，不会覆盖
docker exec dprovdb-repro-db pg_isready -U link
python3 extensions/five-datasets/shared/load_data.py bank credit shoppers diabetes covertype

# 只编译一次；后续调用 Java 产物，不能并行启动多个 sbt
bash extensions/five-datasets/shared/compile.sh

# 每组先检查完整链路，输出目录必须为新的仓库相对路径
bash extensions/five-datasets/shared/run_one.sh bank .runtime/five-datasets/bank-smoke-new smoke
bash extensions/five-datasets/shared/run_one.sh bank .runtime/five-datasets/bank-formal-new formal
```

把 `bank` 替换为其他组名即可。`smoke` 每组 14 条：RRQ 每人 40 查询、预算 0.4，覆盖两调度和全部五方法；BFS 使用完整树和四方法各一轮。`formal` 固定每组 216 条，不通过环境变量暗中缩减。输出目录必须不存在；已有正式产物不可覆盖。

最多同时运行两组，每组独立容器和目录，2 CPU、2 GiB 内存，Java 堆 1200 MiB。数据库使用原 1 GiB 限制。所有组完成后才可按需停止 `dprovdb-repro-db`，不要让单组脚本停止共享数据库。

本次正式结果在各组 `raw/`，运行日志压缩保存于 `logs/`；原始公开数据在本地保留，仓库提供来源、下载脚本和哈希。`manifest.json` 记录具体成员、版本、行列数、字段、缺失、缩放和校验值。下载程序会验证完整行列数，ZIP 校验 CRC，拒绝已有截断文件。

## 验证与重新生成图表

```bash
# 使用运行镜像中已有 pandas/NumPy/Matplotlib
bash reproduction/container.sh python3 extensions/five-datasets/shared/analyze.py
bash reproduction/container.sh python3 extensions/five-datasets/shared/report.py
```

脚本从五组既定 `raw/` 路径读取。要分析自己的新结果，应使用独立克隆/副本安排同样布局，不能覆盖本次归档。分析检查完整配置集合、四轮种子、无重复计数、正确 nDCFG、零效用空值、账本和直方图总数，再生成每组统计与图表。全套 [验证](shared/validation.json) 包含冻结源码哈希检查；每组另有 `validation.json`。

[冻结参数与源码哈希](shared/experiment.json) 基于提交 `a9d051a7d2a75f3e60035ea28693be5c3b43b937`，只新增独立 Scala 入口与本目录材料。运行机制源码与该基准一致，继续启用通过固定种子一致性测试的 paper 随机数包装。构建环境和验证证据见 [environment.json](shared/environment.json) 与 [smoke-validation.json](shared/smoke-validation.json)。

## 阅读口径

统一五个连续字段、`[0,1000]` 值域和 50 桶是明确的接入选择；BFS 阈值为 N 的 1%，5 叉树粒度 2、最多 312 个候选。RRQ 的相同几何结构会导致跨数据集相同的接收与账本结果，各组均实际独立执行并留有日志。

nDCFG 是 DCFG 除以回答总数，权限 1:4 下上界约 3.1063，并非 0–1；零回答时为空值。请求方差不等于实际误差，程序账本不等于新的 DP 证明。BFS 原实现的错桶风险、范围敏感度、缓存个人额度检查等问题均未修复，详见 [扩展实现审查](shared/implementation-notes.md) 和每份独立报告。Diabetes 明确是就诊记录级；Covertype 是地理规模验证，不能作为个人隐私案例。
