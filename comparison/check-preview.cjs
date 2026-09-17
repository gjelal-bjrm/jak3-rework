const {chromium} = require('C:/Users/Gjelal/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({headless:true, executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  try {
    const page = await browser.newPage({viewport:{width:780,height:700}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(path.join(__dirname,'preview.html')).href);
    const frame = page.frameLocator('iframe');
    await frame.locator('#spargus-position').waitFor();
    const images = await frame.locator('img').evaluateAll(imgs => imgs.map(i=>({loaded:i.complete&&i.naturalWidth>0,width:i.naturalWidth})));
    if (images.some(i=>!i.loaded)) throw Error('Image not loaded');
    await frame.locator('#spargus-position').fill('25');
    const style = await frame.locator('.spargus-before').getAttribute('style');
    if (!style.includes('75%')) throw Error('Slider failed: '+style);
    await frame.locator('#spargus-position').fill('50');
    await page.screenshot({path:path.join(__dirname,'preview-check.png')});
    await page.setViewportSize({width:320,height:700});
    const overflow = await frame.locator('html').evaluate(e=>e.scrollWidth>e.clientWidth);
    if (overflow || errors.length) throw Error(JSON.stringify({overflow,errors}));
    console.log(JSON.stringify({images,slider:'passed',narrow_layout:'passed',errors}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
