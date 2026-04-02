# 🎬 動画ダウンローダー / Video Downloader / 视频下载器

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-green.svg)](https://flask.palletsprojects.com/)

---

## ⚠️ 重要な法的免責事項 / Legal Disclaimer / 法律免责声明

**🇯🇵 日本語**

本ツールは**個人の学習・研究目的のみ**を対象としています。

- 著作権で保護されたコンテンツを許可なくダウンロードすることは、**著作権法およびYouTubeの利用規約に違反する可能性があります**
- **特に日本においては**、2020年の著作権法改正により、著作権を侵害するコンテンツのダウンロードは**個人利用目的であっても違法**となる場合があります
- 本ツールを使用した結果生じるいかなる法的責任も、**作者は一切負いません**
- 使用者は自国の法律および規制を遵守する責任を**単独で負います**
- **在留資格をお持ちの方は特にご注意ください** — 著作権法違反は在留資格に影響する可能性があります

**🌐 English**

This tool is intended for **personal learning and research purposes only**.

- Downloading copyrighted content without permission may **violate copyright law and YouTube's Terms of Service**
- **In Japan**, the 2020 amendment to the Copyright Act makes it **illegal to download copyright-infringing content even for personal use**
- The author assumes **absolutely no legal responsibility** for any consequences arising from the use of this tool
- Users are **solely responsible** for complying with the laws and regulations of their country or region
- **Non-Japanese residents in Japan should be especially cautious** — copyright violations may affect visa/residence status

**🇨🇳 中文**

本工具**仅供个人学习和研究使用**。

- 未经授权下载受版权保护的内容可能**违反版权法及 YouTube 服务条款**
- **在日本**，根据2020年修订的著作权法，即使出于个人目的下载侵权内容也**可能构成违法**
- 作者对本工具的任何使用后果**不承担任何法律责任**
- 用户需**自行承担**遵守所在国家/地区法律法规的责任
- **持有在留资格的外国人请特别注意** — 违反著作权法可能影响在留资格

---

## 📖 概要 / Overview / 概述

自己ホスト型のYouTube動画ダウンローダーWebアプリです。VPSにデプロイして、ブラウザからアクセスするだけで動画をダウンロードできます。

A self-hosted YouTube video downloader web application. Deploy on your VPS and download videos directly from your browser.

自托管的 YouTube 视频下载 Web 应用，部署在 VPS 上，通过浏览器即可下载视频。

---

## ✨ 機能 / Features / 功能

| 機能 / Feature / 功能 | 説明 / Description / 说明 |
|---|---|
| 🎬 画質選択 / Quality Selection / 画质选择 | 解像度・フォーマット選択対応 / Select resolution and format / 支持选择分辨率和格式 |
| ⚡ 直接ダウンロード / Direct Download / 直接下载 | サーバーを経由せずブラウザへ直接転送 / Stream directly to browser / 直接推送到浏览器 |
| 💾 サーバーキャッシュ / Server Cache / 服务器缓存 | サーバーに保存後ダウンロード / Save to server then download / 先保存到服务器再下载 |
| 🔗 共有リンク / Share Link / 分享链接 | 24時間有効なトークンリンク / 24-hour token links / 24小时有效的 token 链接 |
| 👥 マルチユーザー / Multi-User / 多用户 | 有効期限付きアカウント管理 / Account management with expiry / 支持有效期的账户管理 |
| 🍪 Cookies対応 / Cookies Support / Cookie 支持 | 年齢制限コンテンツ対応 / Age-restricted content support / 支持受限内容下载 |
| 🌐 多言語対応 / Multilingual / 多语言 | 日本語・English・中文切替 / Switch between JA/EN/ZH / 支持日英中三语切换 |
| 📱 レスポンシブ / Responsive / 响应式 | スマートフォン・タブレット対応 / Mobile & tablet friendly / 支持手机和平板 |

---

## 🛠️ 必要環境 / Requirements / 环境要求

| 項目 / Item / 项目 | バージョン / Version / 版本 |
|---|---|
| OS | Debian 12 / Ubuntu 24.04 |
| Python | 3.10+ |
| Node.js | 20+ |
| ffmpeg | Latest |
| Nginx | Latest |

---

## 🚀 インストール / Installation / 安装

### 1. 依存関係のインストール / Install Dependencies / 安装依赖

```bash
# yt-dlp
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
chmod a+rx /usr/local/bin/yt-dlp

# Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install nodejs ffmpeg python3 python3-pip -y

# Flask
pip3 install flask --break-system-packages

# yt-dlp に Node.js を設定 / Configure yt-dlp to use Node.js / 配置 yt-dlp 使用 Node.js
mkdir -p ~/.config/yt-dlp
echo '--js-runtimes node:/usr/bin/node' > ~/.config/yt-dlp/config
```

### 2. ファイルの配置 / File Setup / 文件部署

```bash
git clone https://github.com/teikenn/video-downloader.git
cd video-downloader
mkdir -p static downloads
cp static/main.js /root/ytdl/static/main.js
cp app.py /root/ytdl/app.py
```

### 3. systemd サービスの設定 / Configure systemd / 配置 systemd

```bash
cp ytdl.service /etc/systemd/system/ytdl.service

# パスワードを設定 / Set passwords / 设置密码
nano /etc/systemd/system/ytdl.service
# YTDL_ADMIN_PASSWORD と YTDL_SECRET_KEY を変更してください
# Change YTDL_ADMIN_PASSWORD and YTDL_SECRET_KEY
# 修改 YTDL_ADMIN_PASSWORD 和 YTDL_SECRET_KEY

systemctl daemon-reload
systemctl enable ytdl
systemctl start ytdl
```

### 4. Nginx + SSL の設定 / Configure Nginx + SSL / 配置 Nginx 和 SSL

```bash
apt install nginx certbot python3-certbot-nginx -y

# Nginx設定を作成 / Create Nginx config / 创建 Nginx 配置
cat > /etc/nginx/sites-available/ytdl << 'EOF'
server {
    listen 80;
    server_name your-domain.com;
    location / {
        proxy_pass http://127.0.0.1:5005;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        add_header X-Accel-Buffering no;
    }
}
EOF

ln -s /etc/nginx/sites-available/ytdl /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

# SSL証明書の取得 / Get SSL certificate / 申请 SSL 证书
certbot --nginx -d your-domain.com
```

---

## 📖 使い方 / Usage / 使用方法

### 動画のダウンロード / Download Video / 下载视频

1. ブラウザで `https://your-domain.com` を開く / Open in browser / 在浏览器打开
2. 管理者アカウントでログイン / Login with admin account / 使用管理员账号登录
3. URLを貼り付け → 画質取得 → ダウンロード方法を選択 / Paste URL → Get Quality → Choose download method / 粘贴链接 → 获取清晰度 → 选择下载方式

### ダウンロード方法 / Download Methods / 下载方式

| 方法 / Method / 方式 | 説明 / Description / 说明 |
|---|---|
| 💾 サーバーに保存 / Save to Server / 存到服务器 | サーバーに保存後、リストからダウンロード / Save first, then download from list / 先保存再下载 |
| ⚡ 直接ダウンロード / Direct Download / 直接下载 | ブラウザに直接転送（最佳単一ファイル・音声のみ対応）/ Stream to browser (best single file & audio only) / 直接推送到浏览器（仅支持最佳单文件和音频）|

### Cookies の設定 / Configure Cookies / 配置 Cookies

年齢制限などのコンテンツをダウンロードするには Cookies が必要です。
Cookies are required for age-restricted or member-only content.
下载受限内容需要配置 Cookies。

1. Chrome に「Get cookies.txt LOCALLY」拡張機能をインストール / Install extension / 安装扩展
2. YouTubeにログインして拡張機能でエクスポート / Login and export / 登录后导出
3. 管理パネル →「Cookies を更新」に貼り付け / Paste in Admin Panel / 粘贴到管理后台

> ⚠️ Cookies は数ヶ月で期限切れになります。期限切れの場合は再エクスポートしてください。
> Cookies expire after a few months. Re-export when expired.
> Cookie 几个月后会过期，过期后需要重新导出。

---

## ⚙️ 環境変数 / Environment Variables / 环境变量

| 変数 / Variable / 变量 | デフォルト / Default / 默认 | 説明 / Description / 说明 |
|---|---|---|
| `YTDL_ADMIN_PASSWORD` | `admin123` | 管理者パスワード / Admin password / 管理员密码 |
| `YTDL_SECRET_KEY` | `yt_secret_2026` | セッションキー / Session key / Session 密钥 |

> ⚠️ 本番環境では必ず変更してください / Always change in production / 生产环境必须修改

---

## 🔧 トラブルシューティング / Troubleshooting / 常见问题

| 問題 / Problem / 问题 | 解決方法 / Solution / 解决方法 |
|---|---|
| 502 Bad Gateway | `systemctl restart ytdl` |
| Cookie期限切れ / Cookie expired / Cookie过期 | 管理パネルでCookiesを更新 / Update in Admin Panel / 在管理后台更新 |
| ダウンロード失敗 / Download failed / 下载失败 | 著作権制限の可能性 / Possible copyright restriction / 可能有版权限制 |
| 進捗バーが表示されない / No progress bar / 进度条不显示 | Nginx設定に `proxy_buffering off` を追加 / Add to Nginx config / 在 Nginx 配置中添加 |

---

## 📄 ライセンス / License / 许可证

MIT License — 詳細は [LICENSE](LICENSE) を参照 / See LICENSE for details / 详见 LICENSE 文件

---

## 👨‍💻 作者 / Author / 作者

**teikenn** — [GitHub](https://github.com/teikenn)

---

*本プロジェクトはyt-dlpを利用しています / This project uses yt-dlp / 本项目使用 yt-dlp*
