const { chromium } = require('playwright-core'); // 只装core，不用下载浏览器
const fs = require('fs-extra');

// 核心配置
const BASE_URL = 'https://nocfond.us.ci/';
const OUTPUT_DIR = './crawl-results';
const VISITED_LINKS = new Set();
// Chrome 安装路径（固定）
const CHROME_PATH = '/usr/bin/google-chrome';

// 初始化目录
async function initDir() {
  await fs.emptyDir(OUTPUT_DIR);
  await fs.ensureDir(`${OUTPUT_DIR}/screenshots`);
  await fs.ensureDir(`${OUTPUT_DIR}/html`);
}

// 爬取单个页面
async function crawlPage(browser, url) {
  if (VISITED_LINKS.has(url) || !url.startsWith(BASE_URL)) return;
  console.log(`爬取: ${url}`);
  VISITED_LINKS.add(url);

  const page = await browser.newPage();
  await page.setViewportSize({ width: 1920, height: 1080 });

  try {
    // 加载页面
    await page.goto(url, { waitUntil: 'networkidle', timeout: 120000 });
    // 滚动到底部
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(3000);

    // 截图
    const fileName = encodeURIComponent(url).replace(/[^a-zA-Z0-9]/g, '_');
    await page.screenshot({ path: `${OUTPUT_DIR}/screenshots/${fileName}.png`, fullPage: true });
    // 保存HTML
    await fs.writeFile(`${OUTPUT_DIR}/html/${fileName}.html`, await page.content(), 'utf8');

    // 提取链接递归爬取
    const links = await page.evaluate(() => 
      Array.from(document.querySelectorAll('a[href]')).map(a => new URL(a.href, window.location.href).href)
    );
    for (const link of links) await crawlPage(browser, link);

  } catch (e) {
    console.warn(`爬取${url}失败:`, e.message);
  } finally {
    await page.close();
  }
}

// 主函数（指定Chrome路径启动）
async function main() {
  try {
    await initDir();
    // 用已安装的Chrome启动，绝对不会找不到浏览器！
    const browser = await chromium.launch({
      executablePath: CHROME_PATH,
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    });

    await crawlPage(browser, BASE_URL);
    await browser.close();
    console.log('✅ 爬取完成！结果在 crawl-results 目录');

  } catch (error) {
    console.error('❌ 爬取出错:', error);
    process.exit(1);
  }
}

main();