# 本机同步配置（密钥不进 Git）

| 文件 | 说明 | 是否提交 |
|------|------|----------|
| `competition_sync_task.bat` | 真实 bat（含 `DEEPSEEK_API_KEY`） | **否**（gitignore） |
| `competition_sync_task.bat.example` | 无密钥模板 | 是 |

Windows 任务 `CompetitionSearchSync` 当前使用：

`C:\Users\Lenovo\competition_sync_task.bat`

也可改为本目录 bat；任务「起始位置」必须是仓库根目录。

```bat
rem 从 example 复制后填 key
copy competition_sync_task.bat.example competition_sync_task.bat
```
