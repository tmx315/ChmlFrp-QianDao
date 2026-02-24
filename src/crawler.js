const { chromium } = require('playwright');
const fs = require('fs-extra');

const BASE_URL = 'https://nocfond.us.ci/';
const OUTPUT_DIR = './crawl-results';
const VISITED_LINKS = new Set();
const PAGE_LOAD_TIMEOUT = 120000;
const SCROLL_DELAY = 1000;
const MAX_RETRY = 3;

async function initDir() {
  await fs.emptyDir(OUTPUT_DIR);
  await fs.ensureDir(`${OUTPUT_DIR}/screenshots`);
  await fs.ensureDir(`${OUTPUT_DIR}/videos`);
  await fs.ensureDir(`${OUTPUT_DIR}/html`);
}

async function preparePage(page, url) {
  await page.goto(url, {
    waitUntil: 'networkidle',
    timeout: PAGE_LOAD_TIMEOUT
  });

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

async function crawlPage(browser, url) {
  console.log(`爬取中: ${url}`);
  VISITED_LINKS.add(url);

  const page = await browser.newPage();
  await page.setViewportSize({ width: 1920, height: 1080 });

  try {
    const videoName = encodeURIComponent(url).replace(/[^a-zA-Z0-9]/g, '_');
    await page.video.start({ path: `${OUTPUT_DIR}/videos/${videoName}.webm` });

    await preparePage(page, url);

    await page.screenshot({ path: `${OUTPUT_DIR}/screenshots/${videoName}.png`, fullPage: true });

    const html = await page.content();
    await fs.writeFile(`${OUTPUT_DIR}/html/${videoName}.html`, html, 'utf8');

    await page.video.stop();

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

async function main() {
  try {
    await initDir();

    const browser = await chromium.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage'
      ]
    });

    await crawlPageWithRetry(browser, BASE_URL);

    await browser.close();
    console.log('✅ 爬取完成！');

  } catch (error) {
    console.error('❌ 爬取出错:', error);
    process.exit(1);
  }
}

main();