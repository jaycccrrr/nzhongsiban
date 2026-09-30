# 廿中四班

十二个人的班级纪念网站：聊天数据统计、人物录、关系图谱、大事记、照片墙、梗百科。

## 目录结构

```
content/     所有内容（人物档案、大事记、梗、照片、聊天统计）——你只需维护这里
pipeline/    数据管道（微信解密导出 → 统计 JSON），见 pipeline/README.md
site/        网站代码（Astro 静态站点），一般不用动
tools/       构建工具（照片同步、整站加密门禁）
```

## 日常更新

1. 改 `content/` 里的内容（或按 `pipeline/README.md` 更新聊天统计）
2. `git add . && git commit -m "更新" && git push`
3. GitHub Actions 自动构建、加密、部署，几分钟后生效

## 本地预览

```
cd site
npm install
npm run dev        # 开发预览（明文）
npm run build      # 构建到 site/dist
```

## 访问控制

网站发布时是**整站加密**的，访客需要输入密码才能看到内容：

- 线上密码存在 GitHub 仓库 `Settings → Secrets and variables → Actions → SITE_PASSWORD`
- 本地测试加密：`node tools/encrypt.mjs`（读取 `tools/password.txt`，该文件不上传）
- 换密码：改 Secret 后重新 push 一次即可

## 部署（首次设置）

1. GitHub 上新建仓库 `nzhongsiban`（Private 即可，Pages 照样能公开访问；如想 Pages 也私有需付费，所以靠加密门禁控制访问）
2. 仓库 Settings → Pages → Source 选 **GitHub Actions**
3. 添加 Secret `SITE_PASSWORD`
4. 本地：`git remote add origin git@github.com:jaycccrrr/nzhongsiban.git` 后 push
5. 网站地址：`https://jaycccrrr.github.io/nzhongsiban/`

> 若改仓库名，同步修改 `site/astro.config.mjs` 里的 `base`。
