const puppeteer = require('puppeteer');
const fs = require('fs-extra');
const { parseHTML } = require('linkedom');
const { PuppeteerScreenRecorder } = require('puppeteer-screen-recorder');

// 核心配置
const BASE_URL = 'https://nocfond.us.ci/';
const OUTPUT_DIR = './crawl-results';
const VISITED_LINKS = new Set();
// 适配慢网站的超时配置
const PAGE_LOAD_TIMEOUT = 120000; // 2分钟
const SCROLL_DELAY = 1000;
const MAX_RETRY = 3;

// 初始化目录
async function initDir() {
  await fs.emptyDir(OUTPUT_DIR);
  await fs.ensureDir(`${OUTPUT_DIR}/screenshots`);
  await fs.ensureDir(`${OUTPUT_DIR}/videos`);
  await fs.ensureDir(`${OUTPUT_DIR}/html`);
}

// 等待页面加载+滚动到底部（确保内容加载完整）
async function preparePage(page, url) {
  await page.goto(url, {
    waitUntil: ['networkidle2', 'domcontentloaded'],
    timeout: PAGE_LOAD_TIMEOUT
  });

  // 模拟滚动（放慢速度，适配慢网站）
  await page.evaluate(async (scrollStep, scrollDelay) => {
    let currentScroll = 0;
    const maxScroll = document.body.scrollHeight;
    while (currentScroll < maxScroll) {
      window.scrollTo(0, currentScroll);
      currentScroll += 300;
      await new Promise(resolve => setTimeout(resolve, scrollDelay));
    }
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(resolve => setTimeout(resolve, 5000));
  }, 300, SCROLL_DELAY);

  await page.waitForTimeout(5000);
}

// 带重试的爬取函数
async function crawlPageWithRetry(browser, url, retryCount = 0) {
  if (VISITED_LINKS.has(url) || !url.startsWith(BASE_URL)) return;
  if (retryCount >= MAX_RETRY) {
    console.error(`爬取 ${url} 失败，已重试${MAX_RETRY}次，跳过`);
    return;
  }

  try {
    await crawlPage(browser, url);
  } catch (error) {
    console.warn(`重试 ${url} (第${retryCount+1}次):`, error.message);
    await new Promise(resolve => setTimeout(resolve, 10000));
    await crawlPageWithRetry(browser, url, retryCount + 1);
  }
}

// 核心爬取逻辑（截图+录屏+保存HTML）
async function crawlPage(browser, url) {
  console.log(`爬取中: ${url}`);
  VISITED_LINKS.add(url);

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  try {
    // 启动录屏
    const recorder = new PuppeteerScreenRecorder(page, {
      followNewTab: false,
      fps: 15 // 降低帧率，减少文件大小
    });
    const videoName = encodeURIComponent(url).replace(/[^a-zA-Z0-9]/g, '_');
    await recorder.start(`${OUTPUT_DIR}/videos/${videoName}.mp4`);

    // 加载并滚动页面
    await preparePage(page, url);

    // 全屏截图
    await page.screenshot({
      path: `${OUTPUT_DIR}/screenshots/${videoName}.png`,
      fullPage: true
    });

    // 保存完整HTML
    const html = await page.content();
    await fs.writeFile(`${OUTPUT_DIR}/html/${videoName}.html`, html, 'utf8');

    // 停止录屏
    await recorder.stop();

    // 提取所有内部链接，递归爬取
    const links = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('a[href]')).map(a => 
        new URL(a.href, window.location.href).href
      );
    });
    for (const link of links) {
      await crawlPageWithRetry(browser, link);
    }

  } catch (error) {
    throw error;
  } finally {
    await page.close();
  }
}

// 主函数
async function main() {
  try {
    await initDir();

    // 启动浏览器（适配GitHub Actions环境）
    const browser = await puppeteer.launch({
      headless: "new", // 新无头模式，无需虚拟桌面
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-software-rasterizer'
      ],
      timeout: 120000
    });

    // 开始爬取主页面
    await crawlPageWithRetry(browser, BASE_URL);

    await browser.close();
    console.log('✅ 爬取完成！结果已保存到 crawl-results 目录');

  } catch (error) {
    console.error('❌ 爬取出错:', error);
    process.exit(1);
  }
}

main();