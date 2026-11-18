# Current agent status

The architecture candidate is ready for user review. The source-layout beta adds
project-local setup; see [installation](INSTALL.md). User acceptance is pending;
software publication and checks do not approve engineering designs.

| Item | Verified state |
| --- | --- |
| Interfaces |43 MCP tools and 42 fixed worker operations |
| Common data | Project/scenario identities, source pointers, units and air/electrical/lighting views; other typed domain contracts retained |
| Knowledge | SQLite/FTS5 source indexes with selected pages, editions, conditions and bounded retrieval; not a complete professional library |
| Changes | Source/method/runtime impact and checkpoints; numerical reuse whitelist restricted to air/electrical |
| Real cases | Actual HVAC native chain and recorded lighting calculation/report/knowledge propagation checked |
| Regression | Tested productiona524418:1949cases, zero failures/errors,258skip outcomes explicitly retained |
| Native delivery | Actual AutoCAD save/reopen and plotted-page review; engineering applicability remains separate |
| Resource evidence | Lazy optional engines, bounded verification memo and reproducible Windows probes; no universal memory guarantee |

Use [START_USING.md](START_USING.md) to operate and
[ARCHITECTURE_ACCEPTANCE.md](ARCHITECTURE_ACCEPTANCE.md) to inspect results,
source versions, skipped cases and limitations. The
[roadmap](ROADMAP.md) retains the full multi-service goal and remaining work.

BSE3227's existing submission is unchanged by this architecture stage. BSE3124
remains read-only. Historical runs and private sources are not public snapshots.

Older status narrative is available through
[Git history](https://github.com/LYUml/building-services-agent/blob/19e29fb41a7c3dd80e59813d28c6a79310075a24/docs/AGENT_STATUS.md),
not repeated in this operational status page.
