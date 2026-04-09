# 🚀 GitHub Pages 部署指南

> **项目**：五大游戏账号数据分析仪表板  
> **文件**：`douyin-analytics.html`（单文件，无需构建）

---

## 第一步：安装 Git

### 方法 A：官方下载（推荐）
访问 **https://git-scm.com/download/win** 下载 Windows 安装包

如果 GitHub 下载慢，使用以下**国内镜像源**：

| 镜像站 | 地址 |
|--------|------|
| 腾讯软件中心 | 搜索 "git for windows" |
| 华为云镜像 | https://mirrors.huaweicloud.com/home |
| npmmirror | https://npmmirror.com/mirrors/git-for-windows/ |

> 💡 **提示**：搜索 `Git-2.xx.x-64-bit.exe`，双击安装即可，一路默认下一步。

### 方法 B： winget 命令（需管理员权限）
```powershell
# 以管理员身份运行 PowerShell
winget install Git.Git
```

---

## 第二步：创建 GitHub 仓库

1. 打开 **https://github.com/new**
2. Repository name 填：`douyin-analytics`
3. 选择 **Public**（公开仓库才能用免费 GitHub Pages）
4. **不要勾选** "Add a README file"
5. 点击 **Create repository**

---

## 第三步：推送代码到 GitHub

打开 PowerShell 或 Git Bash，依次执行以下命令：

```bash
# 1. 进入项目目录
cd "d:\xy\Desktop\网页动态表"

# 2. 初始化 Git 仓库
git init

# 3. 只添加网页文件（不上传截图和脚本等无关文件）
git add douyin-analytics.html

# 4. 提交
git commit -m "🎮 五大游戏账号数据分析仪表板 v1.0"

# 5. 设置主分支名称
git branch -M main

# 6. 添加远程仓库地址（替换为你的GitHub用户名）
git remote add origin https://github.com/你的用户名/douyin-analytics.git

# 7. 推送到 GitHub
git push -u origin main
```

---

## 第四步：开启 GitHub Pages

1. 进入刚创建的 GitHub 仓库页面
2. 点击 **Settings**（设置）→ 左侧找到 **Pages**
3. Source 选 **Deploy from a branch**
4. Branch 选 **main** / root，点击 Save
5. 等待约 1-2 分钟，页面顶部会显示你的网站链接

✅ **最终访问地址**：`https://你的用户名.github.io/douyin-analytics.html`

---

## 第五步：更新数据后如何同步？

每次修改了 `douyin-analytics.html` 后，只需在项目目录执行：

```bash
git add douyin-analytics.html
git commit -m "更新数据 (日期)"
git push
```

GitHub Pages 会在 1-2 分钟内自动更新。

---

## ⚠️ 注意事项

- **公开仓库**：所有文件对互联网可见，确保没有敏感信息
- **头像URL**：当前使用的是抖音CDN直链，如果失效需重新采集
- **数据更新**：如需定期更新数据，重新采集后替换 HTML 中的 `accountsData` 即可

---

*生成时间：2026-04-10*
