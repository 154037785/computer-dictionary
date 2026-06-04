# 计算机词典

一个手机优先的计算机系统学习版词典网站，覆盖计算机基础、硬件、操作系统、网络、前端、后端、数据库、安全、云原生、数据科学、大模型、AI 工程、图形、多媒体、嵌入式、隐私合规等方向。

## 本地运行

直接打开 `index.html` 可以浏览静态词典。

如果要让手机在同一局域网访问，可以启动本地服务：

```powershell
python -m http.server 8765 --bind 0.0.0.0
```

然后访问：

```text
http://电脑局域网IP:8765
```

## 固定公网网址

`trycloudflare.com` quick tunnel 是临时网址，电脑关机、睡眠、网络变化或隧道进程退出后都可能失效。

推荐按“摸鱼早报”的方式部署到 Cloudflare Pages：GitHub Actions 每 12 小时更新新闻 JSON，Cloudflare Pages 固定托管 `public` 目录。

### Cloudflare Pages 免费固定网址

部署后会得到类似这样的固定网址：

```text
https://computer-dictionary.pages.dev
```

部署步骤：

1. 把本项目上传到 GitHub 仓库。
2. 打开 GitHub 仓库 Settings -> Secrets and variables -> Actions。
3. 新增 Repository secret：

```text
DEEPSEEK_API_KEY=你的 DeepSeek key
```

4. 打开 Actions -> Update dictionary static data -> Run workflow，先手动生成一次静态数据。
5. 打开 Cloudflare Dashboard -> Workers & Pages -> Create application -> Pages。
6. 选择这个 GitHub 仓库。
7. 构建设置：

```text
Framework preset: None
Build command: 留空
Build output directory: public
```

8. 部署完成后使用 Cloudflare 给出的 `pages.dev` 固定网址。

新闻会由 GitHub Actions 每 12 小时自动更新一次。也可以手动点 Run workflow 立即更新。

## 构建静态发布目录

```powershell
npm run build
```

该命令会把 `index.html`、`app.js`、`styles.css`、`assets`、`data` 复制到 `public`，供 Cloudflare Pages 托管。

## Wrangler 直接部署

如果你有 Cloudflare API Token，也可以不经过网页手动点击，直接部署：

```powershell
$env:CLOUDFLARE_API_TOKEN="你的 Cloudflare API Token"
$env:CLOUDFLARE_PAGES_PROJECT="computer-dictionary"
powershell -ExecutionPolicy Bypass -File scripts\deploy_cloudflare_pages.ps1
```

部署成功后，Cloudflare Pages 会给出固定网址，例如：

```text
https://computer-dictionary.pages.dev
```

## 注意

不要把 `DEEPSEEK_API_KEY` 写进代码、README 或提交到 GitHub。只放到 GitHub Actions Secrets。
同样不要把 `CLOUDFLARE_API_TOKEN` 写进仓库，只放在本机环境变量或 Cloudflare/GitHub 的 Secrets 中。
