/**
 * Клиентское сжатие изображений перед загрузкой на сервер.
 * Уменьшает размер изображений для ускорения загрузки.
 */

const MAX_WIDTH = 1920;
const MAX_HEIGHT = 1920;
const QUALITY = 0.8;

/**
 * Сжимает изображение до указанных максимальных размеров.
 * @param {File} file - Файл изображения
 * @param {Object} options - Опции сжатия
 * @param {number} options.maxWidth - Максимальная ширина (по умолчанию 1920)
 * @param {number} options.maxHeight - Максимальная высота (по умолчанию 1920)
 * @param {number} options.quality - Качество сжатия 0-1 (по умолчанию 0.8)
 * @returns {Promise<File>} Сжатый файл
 */
export const compressImage = async (file, options = {}) => {
  const { maxWidth = MAX_WIDTH, maxHeight = MAX_HEIGHT, quality = QUALITY } = options;

  // Только изображения
  if (!file.type.startsWith('image/')) {
    return file;
  }

  // Не сжимаем GIF (анимация) и SVG (вектор)
  if (file.type === 'image/gif' || file.type === 'image/svg+xml') {
    return file;
  }

  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(url);

      let { width, height } = img;

      // Пропускаем если и так маленькое
      if (width <= maxWidth && height <= maxHeight && file.size < 2 * 1024 * 1024) {
        resolve(file);
        return;
      }

      // Рассчитываем новый размер сохраняя пропорции
      if (width > maxWidth) {
        height = Math.round((height * maxWidth) / width);
        width = maxWidth;
      }
      if (height > maxHeight) {
        width = Math.round((width * maxHeight) / height);
        height = maxHeight;
      }

      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          if (!blob) {
            resolve(file); // Fallback
            return;
          }
          const compressedFile = new File([blob], file.name, {
            type: 'image/jpeg',
            lastModified: Date.now(),
          });

          // Если сжатый файл больше оригинала — вернём оригинал
          if (compressedFile.size >= file.size) {
            resolve(file);
          } else {
            resolve(compressedFile);
          }
        },
        'image/jpeg',
        quality
      );
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(file); // Fallback при ошибке
    };

    img.src = url;
  });
};

export default compressImage;
