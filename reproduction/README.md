# DProvDB 论文复现

本目录提供独立 Docker 环境、论文参数适配、实际运行记录与中文实验报告。所有准备与运行只针对本仓库和 `dprovdb-repro-db` / `dprovdb-repro-pgdata` 专用资源，不使用主机数据库，不修改其他项目。

## 实验状态与报告

正式实验已于 2026-10-28 完成，13 批次共 2,152 条记录通过完整性校验。报告位于 [REPORT.md](REPORT.md)，PDF 位于 [output/pdf](../output/pdf/)。完整原始结果与日志位于 [results/paper-2026-10-28](results/paper-2026-10-28/)。不注册定时或自动启动任务。

## 从新克隆准备环境

需要 Docker、Git、curl、Bash。主机不需要 Java、Scala、PostgreSQL 或 Conda。

```bash
git clone --recurse-submodules https://github.com/hobbescalvin414-tech/DProvDB.git
cd DProvDB
bash reproduction/prepare.sh
```

`prepare.sh` 会创建 Docker 镜像、下载公开数据、初始化专用 PostgreSQL 16.1、导入数据并编译项目，结束后停止数据库。若同名容器或数据卷已存在，脚本拒绝重建，以免覆盖数据。首次准备脚本根据本次逐步执行并验证的命令整理；未通过删除现有数据库做第二次破坏性重建测试。

只需重编译已有环境时：

```bash
bash reproduction/build.sh
```

Chorus 构建使用固定子模块提交并跳过其独立测试；首次发现 Maven 仅下载 `slf4j-api:1.7.13` 的 POM，脚本会补齐 Maven Central 的对应 JAR，不改变依赖版本。

## 运行正式实验

```bash
bash reproduction/run-suite.sh reproduction/results/my-run
```

输出目录必须不存在；脚本拒绝覆盖。总共 13 批、每种配置 4 次重复，预计 2,152 条记录。中途失败保留已有结果与日志，停止数据库；不要直接重复到同一个输出目录。单组调试请指定新的输出目录，例如：

```bash
docker start dprovdb-repro-db
DPROVDB_WITH_DB=1 DPROVDB_PROFILE=paper DPROVDB_RUNS=1 \
DPROVDB_LOG_LEVEL=info DPROVDB_OUTPUT_DIR=.runtime/debug \
bash reproduction/sbt.sh 'runMain edu.Experiments.Experiment adult EQW adult TFFFFF'
docker stop dprovdb-repro-db
```

使用显式 `runMain`，避免上游同时存在 CLI 与 Experiment 入口时弹出选择。`run-suite.sh` 使用 4 次重复，单次调试不混入正式结果。

## 数据和可追溯性

- 上游基准：`c7a4cba240f89a8fb696e40557fe1c44fb4785b4`；压缩包的 Experiment.scala 与之相同。
- Chorus：`35b9c06a9d0bf00d0b1eef1231f0b5ea0b237f1c`。
- TPC-H kit：`852ad0a5ee31ebefeed884cea4188781dd9613a3`，SF=1，全八张表；orders=1,500,000 行，lineitem=6,001,215 行。
- 正式 Adult：UCI 训练+测试集完整记录，45,222 行。原文写 45,224，差异如实披露。原始 `data/adult.data` 的 32,561 行未修改，另存为 `adult_upstream` 数据库，但不参加本次正式统计。
- 下载文件、数据库输入和构建缓存放在 `.runtime/`，不上传数据库文件。原始 CSV、压缩日志、校验和及版本清单随结果保存。
- 四轮工作负载种子为 1025 / 2050 / 3075 / 4100；噪声并未统一设种子，不能保证重跑位级一致。

## 参数与论文差异

`DPROVDB_PROFILE=paper` 为可选配置，改变实验参数及随机数包装方式，不改机制公式：端到端/参数实验权限 1:9 → 1:4；排除后来新增的 Brownian；去除重复的扩展机制和 delta 组合；单线程实验直接使用相同的 MersenneTwister，省略短寿命 ThreadLocal 包装，以避免线程局部表累积导致后续配置变慢。固定种子随机输出一致性由 RandomBasisTest 验证，默认配置仍保留原包装方式。`DPROVDB_OUTPUT_DIR`、`DPROVDB_RUNS`、`DPROVDB_LOG_LEVEL` 用于控制输出、重复次数和可控日志。未设置时保持上游默认行为。

[详细源码核对](source-audit.md)记录了数据、delta、噪声机制和误差统计等差异。所谓 paper 配置只是参数适配，不代表原论文全部图点的精确重现。原 `run.sh` 会删除 CSV，因此不直接使用。

## 分析和报告生成

```bash
bash reproduction/container.sh python3 reproduction/analyze.py reproduction/results/my-run
python3 reproduction/report.py reproduction/results/my-run --font /path/to/Chinese-font.ttf
```

分析脚本使用容器内固定版本 NumPy/pandas/Matplotlib；报告脚本需要 pandas、reportlab 和中文 TTF 字体。本次 PDF 使用 macOS 系统 Arial Unicode，字体不随仓库分发。四次结果按均值和样本标准差汇总；先检查记录数量、配置唯一性、种子、计数和累计 epsilon，再生成图表。

## 资源与身份

- Java 11 / Scala 2.12.2 / sbt 1.10.7 / Maven 3.6.3 / PostgreSQL 16.1。
- 计算容器限制 2 CPU、4 GiB；数据库限制 1 CPU、1 GiB；不发布主机端口、不自动重启。
- 本次提交采用 `hobbescalvin414-tech` 的 GitHub 隐私邮箱，只配置本仓库。提交及推送时显式忽略全局与系统 Git 配置，避免使用公司身份。

## 本次并行尾部批次

应用户加速要求，最后阶段的 TPC-H 预算扩展/组合和 Adult delta 与主序列并行。它们使用同一编译产物、配置及数据库，只读查询数据库、写入各自不同结果文件。直接 Java 调用避免多个 sbt 同时改写构建输出。`.claim/.status` 协调机制让主脚本等待对应批次而不重复运行。最终时间表使用实际开始/结束时间。并行批次共享 CPU、数据库和磁盘，其计时可能受竞争影响，不用于精确性能基准结论。全量重新复现仍可使用默认串行 `run-suite.sh`；`run-external-batch.sh` 是本次加速调度记录。
