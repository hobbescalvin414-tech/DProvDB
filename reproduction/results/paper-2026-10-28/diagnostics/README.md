# 诊断与适配验证（不属于正式统计）

- `original-partial-fairness.csv`：原线程局部随机数包装下运行变慢时保留的部分结果。
- `thread-isolated-validation.csv`：用短生命周期工作线程验证的 40 个配置；该策略未作为最终运行方式。
- `direct-rng-validation.csv`：省略单线程下 ThreadLocal 包装后的 40 个配置。
- `original-adult-end-to-end.csv`：原包装下完成的 Adult 端到端 200 条记录。
- `rng-validation.json`：上述对照关键效用/预算字段一致性，以及 100 个种子 × 20 个高斯样本零容差测试结果。
- `rng-test.xml`：JUnit 测试结果。
- `threadlocal-stack.txt`：性能退化期间捕获的相关线程栈。

本目录记录不得加入 raw/ 的正式均值和标准差计算。最终正式运行统一使用 `RandomBasis` 的直接 MersenneTwister 分支；环境标志只在 helper 初始化时读取一次。
