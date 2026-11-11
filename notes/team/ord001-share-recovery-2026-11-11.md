# ORD001 共享入口恢复记录（2026-11-11 上午）

## 现象

2026-11-11 早上发现前一晚的临时通道 `studios-diamonds-qualifying-affects.trycloudflare.com` 已被 Cloudflare 服务端删除（日志反复 `Unauthorized: Tunnel not found`，主机名从 DNS 消失），Surge 固定入口虽然还能打开，但跳转后的后端打不开。

随后两次重建快速通道（`fitting-thompson-typing-flow`、`behaviour-scheduled-prices-wearing`）都在注册后约 17 分钟被服务端删除，且主机名从未出现在 Cloudflare 的公共 DNS 里（NXDOMAIN）。判断为 Cloudflare 对本机出口的快速通道做了限流或策略收紧。

## 恢复过程

| 时间（UTC） | 操作 | 结果 |
|---|---|---|
| 02:02Z | 第四次创建快速通道 | 分配 `clips-son-enough-samba.trycloudflare.com`，DNS 正常解析（104.16.x） |
| 02:0xZ | 8028 网关以新主机名重启（`--open`） | 公网 `/api/health` 返回 200，`model_mode: live` |
| 02:11Z | 用 `share/entry.html` 重新生成 `index.html` / `200.html` | 入口指向新地址 |
| 02:12Z | 用本地已安装的 Surge CLI 0.56.0 发布 | `Success! Published to ord001-group24.surge.sh`（上次失败是因为包装脚本走 `npx` 挂住） |
| 02:16Z | 公网浏览器复验 `share.cjs` | 4 项通过、0 失败，errors=[]；真实 DeepSeek 问候、商家读取原 1 张工单、公网重置 403、手机无溢出 |

证据：`examples/ord001/evidence/2026-11-11-share/public-browser.json` 与三张截图。

## 当前状态与已知不稳定

- 固定入口不变：顾客 <https://ord001-group24.surge.sh/>，商家 <https://ord001-group24.surge.sh/review>。
- 临时后端：`https://clips-son-enough-samba.trycloudflare.com`（重启即换）。
- 本机 8024 原服务、8028 网关、隧道进程需持续运行；数据库仍为 1 张工单、1 条事件。
- 观察到 Cloudflare 边缘连接约每 7 分钟被断开一次，cloudflared 会在几秒到百余秒内自动重连。空窗期公网可能短暂返回 530，刷新即可。
- 5 分钟可用性采样（20 次、每 15 秒一次）：15 次成功、5 次失败，失败全部集中在重连后的空窗期（前 65 秒），之后连续 4 分钟稳定。结论：链接可用，短暂 530 时刷新即可。
- 若之后再次出现 `Unauthorized: Tunnel not found`，说明本出口的快速通道再次被限流，需要重建通道并重新发布 Surge 入口；频繁重建可能加重限流。

## 复跑命令

```bash
# 网关（主机名随通道变化）
env UV_PYTHON_INSTALL_DIR="$HOME/.uv/python" \
  uv run --no-project --python 3.12 examples/ord001/ord001_share.py \
  --public-host clips-son-enough-samba.trycloudflare.com \
  --open --upstream http://127.0.0.1:8024 --port 8028

# 隧道
~/is5542-dev/share-runtime/cloudflared tunnel --url http://127.0.0.1:8028 \
  --protocol http2 --no-autoupdate

# 生成入口并发布（Surge CLI 在 share-tools 里，勿用 npx）
python3 - <<'PY'
from pathlib import Path
origin = 'https://clips-son-enough-samba.trycloudflare.com'
site = Path.home()/'is5542-dev/share-runtime/surge-site'
tpl = (Path.home()/'is5542-dev/is5542-food-delivery-agent/examples/ord001/share/entry.html').read_text()
for name in ('index.html','200.html'):
    (site/name).write_text(tpl.replace('__LIVE_ORIGIN__', origin))
PY
SURGE_TOKEN=... node ~/is5542-dev/share-tools/node_modules/surge/bin/surge \
  publish ~/is5542-dev/share-runtime/surge-site ord001-group24.surge.sh

# 公网复验
NODE_PATH="$HOME/is5542-dev/browser-tools/node_modules" \
  node examples/ord001/ui-check/share.cjs \
  https://ord001-group24.surge.sh - /tmp/ord001-public-browser \
  https://clips-son-enough-samba.trycloudflare.com
```
