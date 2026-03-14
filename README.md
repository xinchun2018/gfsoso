# bbs.91bdqu.com 自动签到（GitHub Actions）

> 参考项目：`daitcl/ablesciSign` 的运行方式（Secrets + 定时任务 + Python 脚本）

## 1. 关键说明
- 按你最新要求：脚本运行在 GitHub 官方 runner（`ubuntu-latest`），不在你本机运行。
- 脚本默认不使用代理环境变量（`BBS_FORCE_DIRECT=1`）。
- 注意：若网站严格要求“你的本机公网 IP”，GitHub runner 的 IP 不同，签到会失败。

## 2. 功能
- 自动登录 `https://bbs.91bdqu.com`
- 自动执行签到（默认适配 Discuz 常见 `dsu_paulsign` 插件）
- 已签到场景自动识别并退出

## 3. 环境变量（GitHub Secrets）
在仓库 `Settings -> Secrets and variables -> Actions -> New repository secret` 添加：

- `BBS_USERNAME`：论坛用户名
- `BBS_PASSWORD`：论坛密码
- `BBS_BASE_URL`：`https://bbs.91bdqu.com`
- `BBS_LOGIN_URL`：登录页 URL（可选）
  - 默认：`https://bbs.91bdqu.com/member.php?mod=logging&action=login`
- `BBS_LOGIN_POST_URL`：登录提交 URL（可选）
  - 默认：`https://bbs.91bdqu.com/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes&inajax=1`
- `BBS_SIGN_PAGE_URL`：签到页 URL（可选）
  - 默认：`https://bbs.91bdqu.com/plugin.php?id=dsu_paulsign:sign`
- `BBS_SIGN_POST_URL`：签到提交 URL（可选）
  - 默认：`https://bbs.91bdqu.com/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1`
- `BBS_TODAYSAY`：签到留言（可选）
- `BBS_QDXQ`：签到心情（可选，默认 `kx`）
- `BBS_QDMODE`：签到模式（可选，默认 `1`）
- `BBS_QUESTIONID`：安全提问 ID（可选，默认 `0`）
- `BBS_ANSWER`：安全提问答案（可选）

## 4. 使用
1. 把本项目推送到 GitHub 仓库。
2. 配置上述 Secrets。
3. 在 `Actions` 页面手动 `Run workflow` 测试。
4. 成功后等待定时任务自动运行。

## 5. 本地调试（可选）
```bash
pip install -r requirements.txt
set BBS_USERNAME=你的用户名
set BBS_PASSWORD=你的密码
set BBS_FORCE_DIRECT=1
python sign.py
```

## 6. 常见问题
- 如果登录失败：
  - 论坛可能有验证码/额外字段，请抓包后调整提交字段。
- 如果签到失败：
  - 插件可能不是 `dsu_paulsign`，把签到页面与提交 URL 改成实际接口。
- 如果任务未触发：
  - 检查仓库 Actions 是否启用、cron 配置是否正确。
