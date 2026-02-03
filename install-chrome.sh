#!/bin/bash
# install-chrome.sh - 从仓库缓存安装 Chrome

set -e

CHROME_DIR="$GITHUB_WORKSPACE/chrome-linux"
CHROMEDRIVER_DIR="$GITHUB_WORKSPACE/chromedriver-linux"

echo "=== 检查仓库缓存的 Chrome ==="

if [ -f "$CHROME_DIR/chrome" ] && [ -f "$CHROMEDRIVER_DIR/chromedriver" ]; then
    echo "找到缓存的 Chrome，直接安装..."
    
    # 安装到系统
    sudo mkdir -p /opt/google/chrome
    sudo cp -r $CHROME_DIR/* /opt/google/chrome/
    sudo chmod +x /opt/google/chrome/chrome
    
    sudo cp $CHROMEDRIVER_DIR/chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver
    
    # 创建软链接
    sudo ln -sf /opt/google/chrome/chrome /usr/bin/google-chrome || true
    sudo ln -sf /opt/google/chrome/chrome /usr/bin/chromium-browser || true
    
    echo "Chrome 版本:"
    google-chrome --version || /opt/google/chrome/chrome --version
    echo "ChromeDriver 版本:"
    chromedriver --version
    
else
    echo "未找到缓存，从网络安装（首次）..."
    
    # 安装依赖
    sudo apt-get update
    sudo apt-get install -y wget unzip libnss3 libgconf-2-4 libfontconfig1
    
    # 下载并安装 Chrome
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo dpkg -i google-chrome-stable_current_amd64.deb || sudo apt-get install -f -y
    
    # 获取 Chrome 版本并下载对应 ChromeDriver
    CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1-3)
    echo "Chrome 版本: $CHROME_VERSION"
    
    # 下载 ChromeDriver
    wget -q "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION" -O driver_version
    DRIVER_VERSION=$(cat driver_version)
    echo "ChromeDriver 版本: $DRIVER_VERSION"
    
    wget -q "https://chromedriver.storage.googleapis.com/$DRIVER_VERSION/chromedriver_linux64.zip"
    unzip -q chromedriver_linux64.zip
    sudo mv chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver
    
    # 保存到仓库（供下次使用）- 可选，需要配置权限
    # mkdir -p $CHROME_DIR $CHROMEDRIVER_DIR
    # cp -r /opt/google/chrome/* $CHROME_DIR/
    # cp /usr/local/bin/chromedriver $CHROMEDRIVER_DIR/
fi

echo "=== 安装完成 ==="