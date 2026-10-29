import { defineConfig } from '@playwright/test';
export default defineConfig({
 testDir: '.', testMatch: '*.spec.js', timeout: 45000, workers: 1,
 retries: 0, reporter: [['list'], ['html', {outputFolder:'results/html',open:'never'}], ['junit',{outputFile:'results/browser.xml'}]],
 use: { browserName:'chromium', launchOptions: process.env.QA_CHROMIUM ? {executablePath:process.env.QA_CHROMIUM} : {}, screenshot:'only-on-failure', trace:'off', video:'off' },
 projects:[{name:'desktop',use:{viewport:{width:1440,height:1000}}},{name:'mobile',use:{viewport:{width:390,height:844}}}]
});
