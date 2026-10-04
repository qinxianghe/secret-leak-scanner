# 密钥泄露防护平台（前后端一体说明）

> Git Hooks + FastAPI + SQLite + SQLAlchemy + Angular 21（Zoneless 独立组件）  
> 目标：在提交/推送环节发现密钥/凭据，阻断/预警，并提供可视化面板。

## 技术架构
- **后端**：FastAPI + SQLAlchemy + SQLite（可换 PostgreSQL）；PyYAML 热更规则/白名单。
- **扫描引擎**：正则规则库 + 校验器（JWT/Base64/PEM/长度/Luhn）+ 高熵兜底；脱敏存储（hash/掩码）。
- **API**：`/api/scan`、`/api/findings`（过滤分页/状态流转）、`/api/rules`（查询/启停/热更）、`/api/allowlist/reload`、`/api/stats`、`/health`。
- **前端**：Angular 21 独立组件 + Signals + Tailwind（CDN 开发模式），HttpClient 全局提供。
- **CLI & Hooks**：通用 CLI（跳过二进制/大文件）；预置 pre-commit/pre-receive 样例。
- **安全**：可选 API_TOKEN 鉴权；CORS 允许本地 3000/4200；不落盘原始密钥。

### 模块关系
- **main.py**：API 入口，CORS、中间件、路由、鉴权、规则/白名单热更、发现/统计接口。
- **scanner.py**：规则定义、校验器、高熵检测、白名单判定、掩码工具。
- **models.py**：ORM 表定义（findings/scan_records/secret_incidents/rules/alerts），SessionLocal。
- **cli.py**：文件扫描 CLI，供 Hook/手动调用。
- **rules.yml / allowlist.yml**：规则/白名单配置，支持热更。
- **前端 src/**：独立组件（仪表盘、发现、手动扫描、规则、设置），ApiService 对接后端。

## 功能清单
- 实时扫描：`POST /api/scan`，命中返回规则/严重性/掩码，入库 findings + secret_incidents。
- 发现管理：`GET /api/findings?limit&offset&repo&branch&status_filter&severity`，`PATCH /api/findings/{id}` 状态更新。
- 规则管理：`GET /api/rules`，`PATCH /api/rules/{id}` 启停规则，`POST /api/rules/reload` 热更 rules.yml。
- 白名单：`allowlist.yml`（片段/路径/仓库），`POST /api/allowlist/reload`。
- 统计：`GET /api/stats`（总数/24h/扫描次数），`/health`。
- 前端面板：仪表盘（趋势/计数）、发现列表（展开详情）、手动扫描、规则管理、设置占位。
- Hooks/CLI：本地 pre-commit 扫暂存区；服务端 pre-receive 扫推送；CLI 可独立扫描文件。

## API 详情与示例
- `POST /api/scan`  
  Body: `{"content": "...", "repo": "...", "branch": "...", "file_path": "...", "mode": "pre-commit|pre-receive|manual", "commit": "...", "author": "...", "line": 123}`  
  命中返回：`{"message":"检测到密钥泄露","found":[{rule_id,severity,description,masked,match}], "duration_ms": 12}`  
  未命中返回：`{"message":"未发现敏感信息","duration_ms":8}`
- `GET /api/findings?limit&offset&repo&branch&status_filter&severity`  
  返回：`[{id,repo,branch,file_path,line,masked_snippet,commit,author,created_at,status,rule:{id,severity,description}}]`
- `PATCH /api/findings/{id}` Body: `{"status":"Resolved"|"Ignored"|"New"}`
- `GET /api/rules` / `PATCH /api/rules/{id}` / `POST /api/rules/reload`
- `POST /api/allowlist/reload`
- `GET /api/stats` -> `{total_findings, findings_24h, scans}`
- `GET /health` -> `{status:"ok", rules:<count>, allowlist_patterns:<count>}`

## 规则与白名单格式示例
### rules.yml
```yaml
- id: GITHUB_TOKEN
  pattern: "ghp_[0-9A-Za-z]{36}"
  severity: High
  description: "GitHub personal access token"
  enabled: true
  validators: ["length>=39"]
```
### allowlist.yml
```yaml
patterns:
  - "ghp_EXAMPLE"
paths:
  - "tests/"
repos:
  - "demo-repo"
```

## 数据流（扫描）
1) 前端/CLI/Hook 调用 `/api/scan` 发送文本及上下文信息。
2) 扫描引擎加载规则 + 白名单，执行正则匹配、校验器、熵检测。
3) 命中后：返回 found 列表；写入 `findings`（脱敏）、`secret_incidents`（hash 前缀）；记录 `scan_records`。
4) 前端仪表盘/列表通过 `/api/stats`、`/api/findings` 展示。

## 前端结构
- `src/app.component.*`：壳组件，侧边导航，页面切换（Signals）。
- 组件：
  - `dashboard`：统计卡片、近7天趋势、最近发现。
  - `findings`：分页列表、展开详情。
  - `scan`：手动扫描输入、结果展示。
  - `rules`：规则列表、热更按钮、启停开关（前端优化占位）。
  - `settings`：白名单/通知占位 UI。
- `services/api.service.ts`：所有 API 调用入口。
- `types.ts`：前后端共享类型定义。

## 本地数据填充（如需演示）
在项目根目录（已激活 venv）运行：
```powershell
@"
from datetime import datetime, timedelta
from random import randint
import models

samples = [
    {"repo":"frontend-app","branch":"main","file_path":"src/app/config.ts","line":42,"masked_snippet":"ghp_...A1B2","commit":"a1b2c3d4","author":"alice","rule_id":"GITHUB_TOKEN","rule_severity":"High","rule_description":"GitHub personal access token"},
    {"repo":"backend-service","branch":"develop","file_path":"config/settings.py","line":88,"masked_snippet":"AKIA...PQRS","commit":"e5f6a7b8","author":"bob","rule_id":"AWS_ACCESS_KEY","rule_severity":"High","rule_description":"AWS Access Key ID"},
    {"repo":"infra","branch":"main","file_path":"terraform/vars.tf","line":17,"masked_snippet":"-----BEGIN...","commit":"deadbeef","author":"carol","rule_id":"RSA_PRIVATE_KEY","rule_severity":"High","rule_description":"RSA private key header"},
    {"repo":"mobile-app","branch":"release","file_path":"lib/auth.dart","line":23,"masked_snippet":"eyJ...jwt","commit":"c0ffee01","author":"dave","rule_id":"JWT","rule_severity":"Medium","rule_description":"Likely JWT token"},
]

with models.SessionLocal() as db:
    for s in samples:
        db.add(models.Finding(
            repo=s["repo"], branch=s["branch"], file_path=s["file_path"], line=s["line"],
            masked_snippet=s["masked_snippet"], commit=s["commit"], author=s["author"],
            status="New", rule_id=s["rule_id"], rule_severity=s["rule_severity"],
            rule_description=s["rule_description"],
            created_at=datetime.utcnow() - timedelta(hours=randint(1,72)),
        ))
    db.commit()
print("seeded", len(samples), "findings")
"@ | .\.venv\Scripts\python -
```

## 测试与验证清单
- API：`/api/scan` 命中/未命中返回；`/api/findings` 分页/过滤；`/api/stats` 数字递增；规则热更；白名单热更；状态更新 PATCH。
- 前端：仪表盘统计/趋势/最近发现；发现列表展开；手动扫描命中提示；规则列表/热更；设置页占位。
- CLI：扫描包含 ghp_/AKIA/BEGIN RSA 的文件，命中退出码 1。
- Hook：复制样例到 `.git/hooks/pre-commit` 或 server hooks，含密钥提交应被阻断。

## 部署建议（生产）
- 数据库：使用 PostgreSQL，配置备份；迁移工具可选 Alembic。
- 安全：开启 API_TOKEN，前后端统一加 `X-API-Key`；全站 HTTPS。
- 构建：前端改用本地 Tailwind/PostCSS 构建，`npm run build` 产物部署到静态服务器或反向代理。
- 日志/监控：开启 Uvicorn 访问日志、错误日志；接入简单 metrics（请求量/耗时/命中数）。
- 大文件：避免提交 `node-portable` 等大文件，使用 `.gitignore` / Git LFS。

## 性能与限制
- 默认跳过二进制/大文件（CLI 参数可设定 max-bytes）。
- 规则越多/内容越大，扫描耗时增加；高熵检测对长串敏感，阈值可调。
- 目前上下文裁判/模型未实现，仅正则+校验+熵；可后续扩展。

## TODO / Backlog
- 规则管理：后端持久化编辑、前端开关真实生效。
- 白名单管理：API + 前端 CRUD，作用域（片段/路径/仓库）。
- 告警：邮件/企业微信/Slack Webhook 发送，重复抑制。
- 鉴权：UI 统一加 `X-API-Key`；可选 JWT 登录。
- 部署：Docker/Compose 模板（api+db+frontend）。
- 监控：简单 Prometheus 指标或日志查询。

## 常见问题扩展
- 跨域：确保后端在 8000 跑，CORS 已允许 3000/4200；如有 API_TOKEN，前端需带 `X-API-Key`。
- 热重载抖动：后端 `--reload-exclude "**/node_modules/**"` 或关闭 reload；前端正常 `npm run dev`。
- PowerShell UTF-8：`[Console]::OutputEncoding=[System.Text.Encoding]::UTF8`。
- MIME 报错：已移除 index.css 引用，使用 Tailwind CDN（开发）。

## 目录结构（关键文件）
```
git-guardian_-secret-leak-scanner-dashboard/
├─ README.md                # 本说明
├─ package.json             # 前端依赖与脚本
├─ angular.json / tsconfig.json
├─ index.html               # Tailwind CDN + importmap
├─ index.css                # 基础样式占位
├─ src/
│  ├─ app.component.(ts|html)   # 壳组件，侧边导航 + 页面切换
│  ├─ types.ts                  # 前后端共享类型
│  ├─ services/
│  │   └─ api.service.ts        # 所有后端 API 调用入口
│  └─ components/
│      ├─ dashboard/            # 仪表盘（统计卡片、近7天趋势、最近发现）
│      ├─ findings/             # 发现列表（分页/展开详情）
│      ├─ scan/                 # 手动扫描页面
│      ├─ rules/                # 规则列表、热更按钮、开关占位
│      └─ settings/             # 设置占位（白名单/通知）
├─ dist/                        # 构建产物（npm run build 后生成）
└─ node_modules/                # 依赖（已在 .gitignore）

后端（同级目录 C:\Users\29466\Desktop\hqx_1）关键文件
├─ main.py          # FastAPI 入口、路由、CORS、鉴权、热更
├─ models.py        # ORM 表定义（findings/scan_records/secret_incidents/rules/alerts）
├─ scanner.py       # 规则/校验器/熵检测/白名单/掩码
├─ cli.py           # CLI 扫描工具（给 Hook/手动用）
├─ rules.yml        # 规则配置（可热更）
├─ allowlist.yml    # 白名单配置
├─ hooks/           # pre-commit.sample / pre-receive.sample
└─ secrets.db       # SQLite 数据文件（可切换 Postgres）
```

## 快速运行
### 后端
```powershell
cd C:\Users\29466\Desktop\hqx_1
.\.venv\Scripts\Activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
- 环境变量：`API_TOKEN`（可选鉴权），`ENTROPY_THRESHOLD`（默认 4.0），`ENTROPY_MIN_LENGTH`（默认 24）
- CORS 已默认允许 3000/4200。

### 前端
```powershell
cd C:\Users\29466\Desktop\hqx_1\git-guardian_-secret-leak-scanner-dashboard
$env:Path="C:\Users\29466\Desktop\hqx_1\node-portable\node-v22.17.1-win-x64;"+$env:Path
npm run dev   # 默认 3000/4200
```
- `ApiService.apiUrl` 已指向 `http://localhost:8000/api`。
- 如设置了 `API_TOKEN`，需在前端统一加 `X-API-Key` 请求头或关闭该变量。

### API 示例（PowerShell）
```powershell
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$h=@{"Content-Type"="application/json"}
$b='{"content":"token ghp_123456789012345678901234567890123456","repo":"demo","branch":"main","file_path":"src/app.py","commit":"abc123","author":"me","line":12}'
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/scan -Method Post -Headers $h -Body $b
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/findings?limit=10&offset=0" -Headers $h
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/stats -Headers $h
```

### CLI / Hooks
- CLI 扫描文件：
```powershell
.\.venv\Scripts\python cli.py --mode pre-commit --repo demo --branch main --files path\to\file1 path\to\file2
```
- 本地 Hook：`hooks/pre-commit.sample` 复制到目标仓库 `.git/hooks/pre-commit`（Linux/macOS `chmod +x`）。
- 服务端 Hook：`hooks/pre-receive.sample` 复制到远端裸仓库 hooks 目录，修正 `python/cli.py` 路径。

## 数据模型（models.py）
- `findings`：repo/branch/file_path/line/commit/author/status/rule_id/rule_severity/rule_description/masked_snippet/created_at
- `scan_records`：mode/repo/branch/file_path/findings_count/duration_ms/created_at
- `secret_incidents`：file_path/secret_content(hash前缀)/created_at
- `rules`：id/pattern/severity/description/enabled/updated_at
- `alerts`：finding_id/channel/status/sent_at/created_at

## 扫描引擎（scanner.py）
- 默认规则：AWS_ACCESS_KEY、GITHUB_TOKEN、RSA_PRIVATE_KEY、JWT + 高熵检测。
- 校验器：jwt/base64/pem/length/luhn。
- 白名单：patterns/paths/repos（allowlist.yml）。
- 返回脱敏字段：`masked` + hash 片段入库。

## 配置文件
- `rules.yml`：可编辑/热更规则（pattern、severity、description、enabled、validators）。
- `allowlist.yml`：白名单占位。
- `.gitignore`：忽略 venv/node_modules/node-portable/临时文件等。

## 生产注意
- Tailwind CDN 仅开发提示，生产可改用 `npm install tailwindcss postcss autoprefixer` + 本地构建。
- 考虑用 Postgres/外部存储替代 SQLite，并配置备份。
- 可启用 API_TOKEN，前端添加统一鉴权头；启用 HTTPS。
- 若仓库体积过大，可清理 `node-portable` 等大文件历史。

## 常见问题
- 前端跨域：确保后端运行、CORS 允许当前端口，或关闭 API_TOKEN。
- UTF-8 中文乱码（PowerShell）：`[Console]::OutputEncoding=[System.Text.Encoding]::UTF8`。
- 热重载乱跳：后端 `--reload-exclude "**/node_modules/**"`，或关闭 `--reload`。
- 404/MIME（index.css）：已移除无用引用，直接用 Tailwind CDN。

## 当前状态
- 后端/前端可运行；规则、白名单热更；发现列表、趋势、手动扫描可用。
- 填充了示例数据（近7天），仪表盘趋势、统计卡片有展示。
