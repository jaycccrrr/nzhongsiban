# 数据更新管道

更新网站聊天统计的完整流程（全程在本机进行，原始数据不会上传）：

## 首次 / 微信大版本更新后：抓密钥

```
python capture_keys.py
```

按提示操作（需要微信已登录，依赖 frida）。密钥会保存到 `dbkeys_found.txt`。
**密钥与微信账号绑定，不换号、不卸载重装就一直有效。**

## 常规更新（每学期/每月一次）

```
# 1. 解密微信数据库（需要微信先退出）
python decrypt_db.py

# 2. 导出群聊消息为 jsonl（输出 group_msgs.jsonl 到当前目录）
python export_wechat.py

# 3. 重新生成网站统计数据（自动写到 ../content/stats.json）
python gen_stats.py

# 4. 提交发布（GitHub Actions 自动构建部署）
git add ../content/stats.json
git commit -m "更新聊天统计"
git push
```

## 依赖

```
pip install pycryptodome zstandard jieba frida
```

`group_msgs.jsonl`、`dbkeys_found.txt`、解密出的 db 文件都是**隐私数据**，
已被 `.gitignore` 排除，永远不会进入仓库。
