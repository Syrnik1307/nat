import { useEffect } from 'react';

/**
 * React Hook для работы с Google reCAPTCHA v3
 * 
 * Использование:
 * const { executeRecaptcha } = useRecaptcha();
 * 
 * const handleSubmit = async () => {
 *   try {
 *     const token = await executeRecaptcha('register');
 *     // Отправляем token в API
 *   } catch (error) {
 *     console.error('reCAPTCHA error:', error);
 *   }
 * };
 */
export const useRecaptcha = () => {
  // Site Key из переменных окружения или тестовый ключ
  const siteKey = process.env.REACT_APP_RECAPTCHA_SITE_KEY || '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI';
  
  useEffect(() => {
    // Проверяем, не загружен ли уже скрипт
    const existingScript = document.querySelector('script[src*="recaptcha"]');
    if (existingScript) {
      return;
    }
    
    // Загружаем reCAPTCHA скрипт
    const script = document.createElement('script');
    script.src = `https://www.google.com/recaptcha/api.js?render=${siteKey}`;
    script.async = true;
    script.defer = true;
    
    script.onerror = () => {
      console.error('Ошибка загрузки reCAPTCHA скрипта');
    };
    
    document.head.appendChild(script);
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);
    
    // Очистка при размонтировании
    return () => {
      // Не удаляем скрипт, так как он может использоваться другими компонентами
      // document.head.removeChild(script);
    };
  }, [siteKey]);
  
  /**
   * Выполнить reCAPTCHA и получить токен
   * 
   * @param {string} action - Название действия (например 'register', 'login', 'send_verification')
   * @returns {Promise<string>} reCAPTCHA токен
   */
  const executeRecaptcha = async (action) => {
    return new Promise((resolve, reject) => {
      if (!window.grecaptcha) {
        reject(new Error('reCAPTCHA не загружена'));
        return;
      }
      
      window.grecaptcha.ready(() => {
        window.grecaptcha.execute(siteKey, { action })
          .then(token => {
            resolve(token);
          })
          .catch(error => {
            console.error('Ошибка reCAPTCHA:', error);
            reject(error);
          });
      });
    });
  };
  
  return { executeRecaptcha };
};
