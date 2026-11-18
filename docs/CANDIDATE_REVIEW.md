# 候选版验收入口

最新架构阶段请从 [ARCHITECTURE_ACCEPTANCE.md](ARCHITECTURE_ACCEPTANCE.md) 验收：
模块化、统一数据、知识库、修改影响和两个真实专业案例已执行，当前全量回归已通过，
限制及跳过项保留。以下保留早期候选版的历史记录，不代表后续源码版本。

下列历史实现固定为 `7632371a6e1288af4f150357586e2116704e7da7`。
当时后续提交仅补充验证记录和说明。该版本完整回归和凭证核验已完成。
本次没有发布正式 release/tag，也没有代替用户作出验收结论。

## 实际完成的改进

| 项目 | 优化前 | 优化后 | 测量范围 |
|---|---:|---:|---|
| HVAC 依赖文件 | 239,198,010 bytes | 213,639,960 bytes | 两个新环境的 site-packages，排除字节码缓存、源码和原生引擎；减少 10.68% |
| 泵恢复模块导入峰值 | 101.23 MiB | 28.56 MiB | Windows 三个新进程的中位值，非整个求解过程 |
| 泵恢复模块导入时间 | 0.513 s | 0.042 s | 同一导入基准的中位值，非整个项目执行时间 |
| 32 MiB 日志压力下 MCP 父进程峰值 | 156.31 MiB | 60.18 MiB | 进程通信压力测试，非整机或原生求解器内存 |

进程通信拆到 `worker_transport`；日志通过临时文件和分块解码转发。
恢复流程按实际任务加载可选几何依赖。运行时方法凭证集中校验，外部安装的
Fluids 方法和 EPANET 二进制采用明确路径及哈希，不扩大项目文件访问范围。
HVAC 使用较小的 `spatial` 依赖组合，其他专业依赖仍按需保留。
现有上游算法、固定版本、许可证和归属记录均保留。

## 已执行的使用验证

- 当前实现的五个核心/配置、六个专业和完整回归 CI 均通过。
  [12 个任务的最终状态](evidence/current-candidate-ci.json) 已分别核对。
- 完整回归运行 1,840 项测试，零失败、零错误，记录 258 个跳过结果；
  `all_tests_pass=false` 保留。跳过项不计为执行通过，子测试结果不能简单相加。
  凭证文件哈希已核验，814 个受检源码文件与同提交源码包逐字节一致。
- 外部运行环境的八项恢复/边界回归全部执行通过，零跳过，源码及凭证独立核验。
- 全新 Git checkout、新环境、约束安装通过 `pip check` 和选定配置的 doctor。
- 真实 SDK 会话列出 40 个 MCP 工具并完成六次原生项目调用；接口契约另对全部
  40 个工具执行未知字段拒绝检查。这不等于穷举每个工具的有效输入组合。
- 隔离的真实历史项目变更工况完成计算、图纸、表格、报告联动：47 段中 44 段
  尺寸改变，235 个图纸单元更新，风量和 20 组 VAV 表保持一致。
- AutoCAD 保存并重开 DWG，对应 718 个生成实体；100 mm 基准实测约 99.991 mm。
- 23 页报告核对 388 项数值；总图和报告第 17 页详细查看，另查看全部报告页的
  排版总览，未观察到明显裁切、空白页或表格溢出。

上述工况是 agent 的隔离验收场景，**没有替换 BSE3227 已有提交方案**。
它证明数据变更及交付联动，不能单独证明 ADPI、厂家设备选型或完整设计合规。

## 如何使用

完整功能推荐使用固定提交的 Git checkout，并为选定配置建立专用环境。
Windows/Python 3.12 的原生 HVAC/MCP 安装命令为：

```powershell
python -m pip install -c locks/hvac-mcp-windows-py312.txt -e ".[drawing,mcp,codex-setup,reports,network,spatial]"
python -m pip check
bsa doctor --extra drawing --extra mcp --extra codex-setup --extra reports --extra network --extra spatial
```

请在该专用环境中执行。其他专业需要其自身 extras 和原生引擎；doctor 只检查
直接依赖和指定路径，不能替代原生执行验证。

按照 [MCP 本地设置](CODEX_LOCAL_SETUP.md) 设置真实主机程序路径，
再按照 [统一使用指南](START_USING.md) 选择项目、解释来源、执行并独立检查结果。
已有桌面对话不会自动采用新配置。软件安装、许可、字体和出图配置属于主机准备。
这些已验证的 MCP 执行路径不需要 computer use。

可以给宿主 agent 这样的验收任务：

> 在主机明确选定的项目目录中，读取现有 brief 和结果，不从头重跑。
> 对一项有来源的设计输入作隔离修改，保留原方案。执行对应计算及图纸/表格/报告
> 联动，独立检查保存结果，重开 DWG 并查看实际 PDF。说明改了什么、数值如何变化，
> 保留未解决的输入和人工审查项，不自动认定设计已获验收。

## 分发与限制

已核验的源码 ZIP 为 28,259,139 bytes、3,687 个条目，其提交及哈希见
[源码凭证](evidence/current-candidate-source.json)。它不含环境、原生程序、私有
项目输入或 Git 对象数据库。不可把 ZIP 或当前 wheel 宣称为完整独立安装包；
不可变引用库功能要求真实 Git checkout。

已验证 Python 3.12 的 Windows/Ubuntu 核心配置；原生 DWG 为 Windows AutoCAD 2027。
Python 元数据允许的其他版本不等于已实测支持。部分引擎及适配器仍有自己的平台、
数据和人工准备边界，见 [支持范围](CANDIDATE_SUPPORT.md)。任意缺资料的工程任务
不能自动变成获批设计；数值执行、证据完整性、工程判断和用户验收分别保留。

完整回归全部跳过记录及核验范围见
[完整回归凭证](evidence/current-candidate-full-regression.json)。
跳过原因涉及未选择的原生主机、隔离环境、上游 checkout 和资料缓存；
部分原生路径由专门 CI 或本机验证另行覆盖，不能据此宣称所有跳过集成都已验证。
详情见 [逐项验收审计](CANDIDATE_GATE_AUDIT.md)、
[当前原生 MCP 凭证](evidence/current-candidate-native-mcp.json) 和
[恢复凭证](evidence/external-runtime-recovery.json)。
