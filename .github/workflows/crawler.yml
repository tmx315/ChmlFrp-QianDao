name: 网站爬取器
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'

jobs:
  crawl-website:
    runs-on: ubuntu-latest
    timeout-minutes: 360
    steps:
      - name: 检出仓库代码
        uses: actions/checkout@v4

      - name: 配置Node.js环境
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: './package-lock.json' 

      - name: 安装系统依赖（Playwright 运行依赖）
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            libnss3 \
            libatk-bridge2.0-0 \
            libdrm-dev \
            libxkbcommon-dev \
            libgbm-dev \
            libasound-dev \
            libatspi2.0-0 \
            libxshmfence-dev \
            ffmpeg \
            xvfb # 新增：虚拟显示服务，支持非无头模式

      - name: 安装项目依赖
        run: npm install --force
        env:
          NODE_OPTIONS: "--max-old-space-size=4096"

      - name: 安装Playwright浏览器（关键修复步骤）
        run: |
          # 下载Chromium浏览器二进制文件
          npx playwright install chromium
          # 安装Playwright系统依赖（自动补全缺失的库）
          npx playwright install-deps

      - name: 启动虚拟显示（支持非无头模式录屏）
        run: |
          export DISPLAY=:99
          Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
          sleep 3 # 等待虚拟显示启动

      - name: 执行网站爬取
        run: node src/crawler.js
        env:
          DISPLAY: :99 # 告诉Playwright使用虚拟显示

      - name: 上传爬取结果到Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: 网站爬取结果
          path: crawl-results/
          retention-days: 30
          if-no-files-found: warn