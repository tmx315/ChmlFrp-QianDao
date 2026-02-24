const puppeteer = require('puppeteer');
const fs = require('fs-extra');
const { parseHTML } = require('linkedom');
const { PuppeteerScreenRecorder } = require('puppeteer-screen-recorder');

// 配置项（针对慢网站优化）
const BASE_URL = 'https://nocfond.us.ci/';
const OUTPUT_DIR = './crawl-results';
const VISITED_LINKS = new Set();
// 核心优化：延长各类超时时间
const PAGE_LOAD_TIMEOUT = 120000; // 页面加载超时：2分钟（原60秒）
const SCROLL_DELAY = 1000; // 滚动间隔：1秒（原500毫秒，给慢网站更多加载时间）
const PAGE_STABLE_DELAY = 5000; // 页面稳定等待：5秒（原3秒）
const MAX_RETRY = 3; // 单个页面爬取失败后重试次数

// 初始化目录（不变）
async function initDir() {
  await fs.emptyDir(OUTPUT_DIR);
  await fs.ensureDir(`${OUTPUT_DIR}/screenshots`);
  await fs.ensureDir(`${OUTPUT_DIR}/videos`);
  await fs.ensureDir(`${OUTPUT_DIR}/html`);
}

// 优化：智能等待页面加载（适配慢网站）
async function preparePage(page, url) {
  // 1. 开启请求拦截，记录加载状态
  let resourceLoaded = false;
  await page.setRequestInterception(true);
  page.on('requestfinished', () => {
    resourceLoaded = true;
  });
  page.on('requestfailed', (req) => {
    console.warn(`资源加载失败: ${req.url()}`);
  });

  // 2. 超宽松的页面加载配置
  await page.goto(url, {
    waitUntil: ['networkidle2'], // 放宽：网络请求≤2个时认为加载完成（原networkidle0）
    timeout: PAGE_LOAD_TIMEOUT
  });

  // 3. 额外等待动态内容加载（针对慢网站）
  await page.waitForFunction(
    () => document.readyState === 'complete',
    { timeout: PAGE_LOAD_TIMEOUT }
  );

  // 4. 模拟滚动（放慢速度）
  await page.evaluate(async (scrollStep, scrollDelay) => {
    let currentScroll = 0;
    const maxScroll = document.body.scrollHeight;
    while (currentScroll < maxScroll) {
      window.scrollTo(0, currentScroll);
      currentScroll += scrollStep;
      // 每滚动一次，等待更长时间
      await new Promise(resolve => setTimeout(resolve, scrollDelay));
    }
    window.scrollTo(0, document.body.scrollHeight);
    // 滚动后再等5秒，确保动态内容加载
    await new Promise(resolve => setTimeout(resolve, 5000));
  }, 300, SCROLL_DELAY); // 滚动步长减小（300px），间隔延长

  // 5. 最终等待页面稳定
  await page.waitForTimeout(PAGE_STABLE_DELAY);
}

// 优化：添加重试逻辑的爬取函数
async function crawlPageWithRetry(browser, url, retryCount = 0) {
  if (VISITED_LINKS.has(url) || !url.startsWith(BASE_URL)) return;
  
  // 超过重试次数则跳过
  if (retryCount >= MAX_RETRY) {
    console.error(`爬取 ${url} 失败，已重试${MAX_RETRY}次，跳过`);
    return;
  }

  try {
    await crawlPage(browser, url);
  } catch (error) {
    console.warn(`爬取 ${url} 失败（第${retryCount+1}次）:`, error.message);
    // 重试前等待10秒，避免频繁请求
    await new Promise(resolve => setTimeout(resolve, 10000));
    await crawlPageWithRetry(browser, url, retryCount + 1);
  }
}

// 原爬取函数（仅修改调用的preparePage）
async function crawlPage(browser, url) {
  console.log(`开始爬取: ${url}`);
  VISITED_LINKS.add(url);

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  try {
    const videoPath = `${OUTPUT_DIR}/videos/${encodeURIComponent(url).replace(/[^a-zA-Z0-9]/g, '_')}.mp4`;
    const recorder = new PuppeteerScreenRecorder(page);
    await recorder.start(videoPath);

    await preparePage(page, url); // 调用优化后的preparePage

    // 截图+保存HTML（不变）
    const screenshotPath = `${OUTPUT_DIR}/screenshots/${encodeURIComponent(url).replace(/[^a-zA-Z0-9]/g, '_')}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: true });
    const htmlContent = await page.content();
    const htmlPath = `${OUTPUT_DIR}/html/${encodeURIComponent(url).replace(/[^a-zA-Z0-9]/g, '_')}.html`;
    await fs.writeFile(htmlPath, htmlContent, 'utf8');

    await recorder.stop();

    // 提取链接并递归爬取（调用带重试的函数）
    const links = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('a[href]')).map(a => new URL(a.href, window.location.href).href);
    });
    for (const link of links) {
      await crawlPageWithRetry(browser, link);
    }

  } catch (error) {
    throw error; // 抛出错误供重试逻辑处理
  } finally {
    await page.close();
  }
}

// 主函数（修改调用入口）
async function main() {
  try {
    await initDir();
    const browser = await puppeteer.launch({
      headless: false,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--start-maximized',
        '--disable-timeout-detection' // 禁用浏览器超时检测
      ],
      defaultViewport: null,
      slowMo: 100 // 放慢浏览器操作速度（100毫秒），适配慢网站
    });

    await crawlPageWithRetry(browser, BASE_URL); // 从主页面开始重试爬取

    await browser.close();
    console.log('爬取完成！所有内容已保存到 crawl-results 目录');

  } catch (error) {
    console.error('爬取过程出错:', error);
    process.exit(1);
  }
}

main();