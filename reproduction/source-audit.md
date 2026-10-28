# 论文与实现核对记录

本记录区分论文描述、上游实现和本次修改。其结论不替代隐私证明。

| 核对点 | 证据 | 本次处理 |
|---|---|---|
| 压缩包代码版本 | 压缩包内 Experiment.scala 与基准提交对应文件 SHA-256 相同 | 保存 source-check.txt |
| 权限默认值 | 原文 6.1.2 使用 1:4；上游 RRQ 端到端和 delta 使用 1:9 | opt-in paper 配置改为 1:4 |
| 新增基线 | 上游含 Brownian；原文列出的基线无此项 | paper 配置排除 Brownian，保留上游默认 |
| 扩展配置重复 | 上游机制列表四个相同 aGM，外层已遍历四个预算扩展配置 | paper 配置每种配置只执行一次，保留四个 runIndex |
| delta 重复 | 上游 1e-11 出现两次 | paper 配置去重 |
| Adult 数据 | 原文 45,224 行；UCI complete cases 为 45,222 行；仓库文件 32,561 行 | 保留原文件，正式实验采用 45,222 行并披露差异 |
| delta 工作负载 | 原文图 8 标为 BFS；上游 delta 入口位于 RRQExperiments | 标注本次为 RRQ，不能声称精确复现图 8 |
| 总体 delta | Experiment.setupState 默认 deltaConstraint=1e-5；TPC-H orders 行数 1,500,000 | 沿用实现并披露大于原文建议的 1/N |
| 真实误差 | CSV 的 avgAccuracy 累计的是 query._accuracyRequirement | 不把 avgAccuracy 当成答案误差；不伪造论文图 9 |
| 基线噪声 | 原文 6.1.1 描述 Chorus 使用 Gaussian mechanism；Chorus.scala 与 ChorusWithProvenance.scala 调用 laplaceSample | 不静默替换算法；报告限制中披露 |
| 计数查询敏感度 | System.execute 将视图覆盖桶数作为 querySens 传入 Chorus 预算换算；实际 COUNT 加噪使用单条记录敏感度 1 | 可能导致较保守的基线预算分配；不将巨大效用比解释为纯算法差距 |
| 噪声种子 | AdditiveGM 创建不带固定种子的 MersenneTwister；工作负载另有种子 | 四轮工作负载可追溯，噪声不承诺位级重现 |
| 计时 | System.execute 内仍有直接日志输出；State 重用视图及 viewSetupTime，且对 Chorus 也统一预建视图 | 不将所有 setup_time 相加、不跨硬件宣称加速比 |
| BFS 候选查询总数 | setupEQW 已将单分析者树大小乘以分析者数，CSV 写出时再次乘分析者数 | BFS 的 totalNoOfQueries 不用于完成率或归一化指标；仅报告真实 answered 计数 |
| 原文公平性刻度 | PDF 第 11 页正文写权限 1:4；按同页 nDCFG 公式其上界约 3.106，但图 3 出现约 4-6 的分数 | 正文参数与图存在不一致；代码的 1:9 设置上界约 6.579，但不能据此确定原图真实设置，需作者确认 |
| 公平性 | MetricUtils.DCFG 只产生未归一化的总和 | 分析阶段除以 utility，零效用时为未定义 |

本次保留机制公式、噪声算法、精度换算和预算规则。修改包括实验参数、输出/重复控制，以及单线程随机数包装适配：paper 配置直接把同一个 MersenneTwister 传给 RandBasis，省略 ThreadLocalRandomGenerator。默认配置继续使用原包装方式。

线程诊断捕捉到工作线程处于 ThreadLocalMap.getEntryAfterMiss → ThreadLocalRandomGenerator.nextGaussian → AdditiveGM.run。每个噪声样本/工作负载样本都新建 ThreadLocal 包装会在长批次内产生明显开销。没有重写高斯采样器，也没有改变 seed 或高斯均值/尺度。

验证分两层：RandomBasisTest 对 100 个固定种子各生成 20 个高斯样本，直接与 ThreadLocal 包装的输出逐项零容差比较；完整 Adult 预算扩展配置再比较 utility、utility_breakdown、DCFG、accountant 和工作负载 seed。正式结果统一采用最终适配，早期运行不混入统计。
