const { chromium } = require('playwright');
const fs = require('fs-extra');
const { parseHTML } = require('linkedom');

// 配置项
const BASE_URL = 'https://nocfond.us.ci/';
const OUTPUT_DIR = './crawl-results';
const VISITED_LINKS = new Set();
const PAGE_LOAD_TIMEOUT = 120000; // 页面加载超时：2分钟
const SCROLL_DELAY = 1000; // 滚动间隔：1秒
const PAGE_STABLE_DELAY = 5000; // 页面稳定等待：5秒
const MAX_RETRY = 3; // 单个页面重试次数

// 初始化目录
async function initDir() {
  await fs.emptyDir(OUTPUT_DIR);
  await fs.ensureDir(`${OUTPUT_DIR}/screenshots`);
  await fs.ensureDir(`${OUTPUT_DIR}/videos`);
  await fs.ensureDir(`${OUTPUT_DIR}/html`);
}

// 加载已爬取链接（断点续爬）
async function loadVisitedLinks() {
  const linkFile = `${OUTPUT_DIR}/visited-links.json`;
  if (await fs.exists(linkFile)) {
    const links = await fs.readJSON(linkFile);
    links.forEach(link => VISITED_LINKS.add(link));
    console.log(`从本地加载已爬取链接：${VISITED_LINKS.size} 个`);
  }
}

// 保存已爬取链接（断点续爬）
async function saveVisitedLinks() {
  const linkFile = `${OUTPUT_DIR}/visited-links.json`;
  await fs.writeJSON(linkFile, Array.from(VISITED_LINKS));
}

// 准备页面（加载+滚动）
async function preparePage(page, url) {
  await page.goto(url, {
    waitUntil: 'networkidle',
    timeout: PAGE_LOAD_TIMEOUT
  });

  // 模拟滚动到底部
  await page.evaluate(async (scrollStep, scrollDelay) => {
    let currentScroll = 0;
    const maxScroll = document.body.scrollHeight;
    while (currentScroll < maxScroll) {
      window.scrollTo(0, currentScroll);
      currentScroll += scrollStep;
      await new Promise(resolve => setTimeout(resolve, scrollDelay));
    }
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(resolve => setTimeout(resolve, 5000));
  }, 300, SCROLL_DELAY);

  await page.waitForTimeout(PAGE_STABLE_DELAY);
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
    console.warn(`爬取 ${url} 失败（第${retryCount+1}次）:`, error.message);
    await new Promise(resolve => setTimeout(resolve, 10000));
    await crawlPageWithRetry(browser, url, retryCount + 1);
  }
}

// 核心爬取函数
async function crawlPage(browser, url) {
  console.log(`开始爬取: ${url}`);
  VISITED_LINKS.add(url);

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  try {
    // 启动录屏
    const videoPath = `${OUTPUT_DIR}/videos/${encodeURIComponent(url).replace(/[^a-zA-Z0-9]/g, '_')}.webm`;
    await page.video.start({ path: videoPath });

    // 准备页面
    await preparePage(page, url);

    // 截图
    const screenshotPath = `${OUTPUT_DIR}/screenshots/${encodeURIComponent(url).replace(/[^a-zA-Z0-9]/g, '_')}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: true });

    // 保存HTML
    const htmlContent = await page.content();
    const htmlPath = `${OUTPUT_DIR}/html/${encodeURIComponent(url).replace(/[^a-zA-Z0-9]/g, '_')}.html`;
    await fs.writeFile(htmlPath, htmlContent, 'utf8');

    // 停止录屏
    await page.video.stop();

    // 保存已访问链接（断点续爬）
    await saveVisitedLinks();

    // 提取链接并递归爬取
    const links = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('a[href]')).map(a => new URL(a.href, window.location.href).href);
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
    await loadVisitedLinks(); // 加载断点

    const browser = await chromium.launch({
      headless: false,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--display=:99' // 适配GitHub Actions虚拟显示
      ]
    });

    await crawlPageWithRetry(browser, BASE_URL);

    await browser.close();
    console.log('爬取完成！所有内容已保存到 crawl-results 目录');

  } catch (error) {
    console.error('爬取过程出错:', error);
    process.exit(1);
  }
}

// 执行主函数
main();