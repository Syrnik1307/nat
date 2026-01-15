/**
 * Image Compressor Utility
 * Сжимает изображения перед загрузкой на сервер для ускорения upload
 * Максимальный размер: 1920px, качество: 80%
 */

const MAX_WIDTH = 1920;
const MAX_HEIGHT = 1920;
const QUALITY = 0.80;
const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2MB - если больше, сжимаем

/**
 * Сжимает изображение, если оно слишком большое
 * @param {File} file - Исходный файл изображения
 * @returns {Promise<File>} - Сжатый файл или оригинал если сжатие не нужно
 */
export const compressImage = async (file) => {
  // Пропускаем не-изображения
  if (!file.type.startsWith('image/')) {
    return file;
  }

  // Пропускаем GIF (анимации теряются при сжатии)
  if (file.type === 'image/gif') {
    return file;
  }

  // Если файл маленький, не сжимаем
  if (file.size <= MAX_FILE_SIZE) {
    // Но всё равно проверим размеры
    const needsResize = await checkNeedsResize(file);
    if (!needsResize) {
      return file;
    }
  }

  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        // Вычисляем новые размеры
        let { width, height } = img;
        
        if (width > MAX_WIDTH) {
          height = Math.round(height * (MAX_WIDTH / width));
          width = MAX_WIDTH;
        }
        if (height > MAX_HEIGHT) {
          width = Math.round(width * (MAX_HEIGHT / height));
          height = MAX_HEIGHT;
        }

        // Создаём canvas для сжатия
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        // Улучшаем качество рендеринга
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(img, 0, 0, width, height);

        // Конвертируем в blob
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              resolve(file); // Fallback to original
              return;
            }
            
            // Создаём новый File с тем же именем
            const compressedFile = new File(
              [blob],
              file.name.replace(/\.[^.]+$/, '.jpg'), // Меняем расширение на .jpg
              { type: 'image/jpeg', lastModified: Date.now() }
            );

            // Если сжатый файл больше оригинала, возвращаем оригинал
            if (compressedFile.size >= file.size) {
              resolve(file);
            } else {
              console.log(
                `[ImageCompressor] Compressed ${file.name}: ${formatBytes(file.size)} → ${formatBytes(compressedFile.size)} (${Math.round((1 - compressedFile.size / file.size) * 100)}% reduction)`
              );
              resolve(compressedFile);
            }
          },
          'image/jpeg',
          QUALITY
        );
      };
      img.onerror = () => resolve(file); // Fallback on error
      img.src = event.target.result;
    };
    reader.onerror = () => resolve(file); // Fallback on error
    reader.readAsDataURL(file);
  });
};

/**
 * Проверяет, нужно ли ресайзить изображение
 */
const checkNeedsResize = (file) => {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        resolve(img.width > MAX_WIDTH || img.height > MAX_HEIGHT);
      };
      img.onerror = () => resolve(false);
      img.src = event.target.result;
    };
    reader.onerror = () => resolve(false);
    reader.readAsDataURL(file);
  });
};

/**
 * Форматирует размер файла для логов
 */
const formatBytes = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
};

export default compressImage;
