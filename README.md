# 谷粉学术文献互助自动签到(bbs.91bdqu.com)自动签到（GitHub Actions）

参考：`daitcl/ablesciSign`（Secrets + 定时任务 + Python 脚本）

## 功能
- GitHub Actions 定时自动执行
- 自动登录 `https://bbs.91bdqu.com`
- 自动识别签到插件：优先 `are_sign`，失败时回退 `dsu_paulsign`
- 支持单账号和多账号批量签到

## 运行环境
- 运行在 GitHub 官方 Runner（`ubuntu-latest`）
- 不依赖你本地电脑,长期在线

## Secrets 配置
在仓库 `Settings -> Secrets and variables -> Actions` 添加。

### 必填（单账号模式）
- `BBS_USERNAME`
- `BBS_PASSWORD`

### 可选（多账号模式，优先级高于单账号）
- `BBS_ACCOUNTS_JSON`

示例：
```json
[
  {"username":"account1@example.com","password":"pass1","loginfield":"email"},
  {"username":"account2@example.com","password":"pass2","loginfield":"email"}
]
```

### 其他常用可选
- `BBS_BASE_URL`：默认 `https://bbs.91bdqu.com`
- `BBS_LOGIN_FIELD`：默认 `email`（可改 `username`）
- `BBS_SIGN_MODE`：默认 `auto`（可选 `are_sign` / `auto`）
- `BBS_ARE_SIGN_TYPEID`：默认 `1`
- `BBS_USE_CURL_CFFI`：默认 `1`
- `BBS_IMPERSONATE`：默认 `chrome124`
- `BBS_TODAYSAY` / `BBS_QDXQ` / `BBS_QDMODE`（仅 dsu_paulsign 回退流程会用到）

## 使用步骤
1. 推送代码到 GitHub 仓库。
2. 配置 Secrets。
3. 打开 `Actions`，手动运行一次 `bbs-91bdqu-auto-sign` 验证。
4. 验证通过后等待定时任务自动执行。

## 本地调试
```bash
pip install -r requirements.txt
set BBS_USERNAME=你的账号
set BBS_PASSWORD=你的密码
python sign.py
```

## 常见问题
- 日志出现 Cloudflare challenge / 403：
  - 确认 `BBS_USE_CURL_CFFI=1`（默认就是 1）。
- 登录失败（密码明明正确）：
  - 尝试把 `BBS_LOGIN_FIELD` 改成 `username` 或 `email`。
- 多账号有部分失败：
  - 脚本会继续执行其他账号，最后统一报失败列表。

