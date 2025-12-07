#!/usr/bin/env node

/**
 * Winter Magic GIF Generator
 * Генерирует анимированный GIF зимней сказки в стиле модальных окон
 */

const puppeteer = require('puppeteer');
const GifEncoder = require('gif-encoder');
const path = require('path');
const fs = require('fs');

const FRAME_COUNT = 120; // 5 секунд при 24 fps
const FRAME_DELAY = 1000 / 24;
const OUTPUT_PATH = path.join(__dirname, '../public/winter-magic.gif');
const HTML_PATH = path.join(__dirname, '../public/winter-magic.html');

async function generateGif() {
    console.log('🎄 Генерируем зимнюю сказку GIF...');
    
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();
    
    // Устанавливаем размер viewport
    await page.setViewport({
        width: 1200,
        height: 600,
        deviceScaleFactor: 1
    });

    // Загружаем HTML
    const htmlUrl = `file://${HTML_PATH}`;
    await page.goto(htmlUrl, { waitUntil: 'networkidle0' });

    // Даём время на загрузку анимаций
    await page.waitForTimeout(500);

    // Создаём GIF энкодер
    const encoder = new GifEncoder(1200, 600);
    encoder.setDelay(Math.round(FRAME_DELAY));
    encoder.setRepeat(0); // Бесконечнаяループа
    encoder.setQuality(10);

    const writeStream = fs.createWriteStream(OUTPUT_PATH);
    encoder.pipe(writeStream);
    encoder.render();

    // Захватываем фреймы
    console.log(`📹 Захватываем ${FRAME_COUNT} фреймов...`);
    
    for (let i = 0; i < FRAME_COUNT; i++) {
        // Обновляем время для анимации
        await page.evaluate((frameIndex) => {
            document.documentElement.style.setProperty('--animation-time', `${frameIndex * 0.08}s`);
        }, i);

        // Захватываем скриншот
        const screenshot = await page.screenshot({ 
            type: 'png',
            omitBackground: false
        });

        // Добавляем в GIF
        encoder.addFrame(screenshot);

        // Прогресс
        if ((i + 1) % 10 === 0) {
            console.log(`  ${i + 1}/${FRAME_COUNT} фреймов ✓`);
        }
    }

    encoder.finish();

    // Ждём завершения записи
    await new Promise((resolve) => {
        writeStream.on('finish', resolve);
    });

    console.log(`\n✅ GIF успешно создан!`);
    console.log(`📦 Файл: ${OUTPUT_PATH}`);
    console.log(`📊 Размер: ${(fs.statSync(OUTPUT_PATH).size / 1024 / 1024).toFixed(2)} MB`);

    await browser.close();
}

generateGif().catch(error => {
    console.error('❌ Ошибка:', error);
    process.exit(1);
});
