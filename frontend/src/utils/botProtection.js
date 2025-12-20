/**
 * Device Fingerprinting + Behavioral Analysis для защиты от ботов
 * 
 * Собирает:
 * 1. Hardware fingerprint (экран, CPU, память, WebGL)
 * 2. Browser fingerprint (plugins, fonts, canvas)
 * 3. Behavioral data (движения мыши, нажатия клавиш, время заполнения)
 * 
 * Используется для:
 * - Бан по железу (fingerprint) вместо IP
 * - Определение ботов по поведению
 * - Rate limiting на уровне устройства
 */

// ============================================================================
// FINGERPRINT COLLECTION
// ============================================================================

/**
 * Собирает полный fingerprint устройства
 */
export async function collectDeviceFingerprint() {
  const fp = {};
  
  try {
    // Screen
    fp.screenWidth = window.screen.width;
    fp.screenHeight = window.screen.height;
    fp.screenAvailWidth = window.screen.availWidth;
    fp.screenAvailHeight = window.screen.availHeight;
    fp.colorDepth = window.screen.colorDepth;
    fp.pixelRatio = window.devicePixelRatio || 1;
    
    // Platform & Language
    fp.platform = navigator.platform;
    fp.language = navigator.language;
    fp.languages = navigator.languages ? navigator.languages.join(',') : '';
    fp.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    fp.timezoneOffset = new Date().getTimezoneOffset();
    
    // Hardware
    fp.hardwareConcurrency = navigator.hardwareConcurrency || 0;
    fp.deviceMemory = navigator.deviceMemory || 0;
    
    // Touch support
    fp.touchSupport = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    fp.maxTouchPoints = navigator.maxTouchPoints || 0;
    
    // WebGL
    const webglInfo = getWebGLInfo();
    fp.webglVendor = webglInfo.vendor;
    fp.webglRenderer = webglInfo.renderer;
    
    // Canvas fingerprint
    fp.canvasHash = getCanvasFingerprint();
    
    // Audio fingerprint
    fp.audioHash = await getAudioFingerprint();
    
    // Fonts fingerprint (simplified)
    fp.fontsHash = getFontsFingerprint();
    
    // Plugins
    fp.pluginsHash = getPluginsFingerprint();
    
    // Session info
    fp.sessionStorage = !!window.sessionStorage;
    fp.localStorage = !!window.localStorage;
    fp.indexedDB = !!window.indexedDB;
    fp.cookiesEnabled = navigator.cookieEnabled;
    
    // Do Not Track
    fp.doNotTrack = navigator.doNotTrack || '';
    
    // Connection info
    if (navigator.connection) {
      fp.connectionType = navigator.connection.effectiveType || '';
      fp.connectionDownlink = navigator.connection.downlink || 0;
    }
    
  } catch (e) {
    console.warn('Error collecting fingerprint:', e);
  }
  
  return fp;
}

/**
 * Получает информацию о WebGL
 */
function getWebGLInfo() {
  const info = { vendor: '', renderer: '' };
  
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    
    if (gl) {
      const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
      if (debugInfo) {
        info.vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) || '';
        info.renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) || '';
      }
    }
  } catch (e) {
    // WebGL not available
  }
  
  return info;
}

/**
 * Создаёт canvas fingerprint
 */
function getCanvasFingerprint() {
  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    canvas.width = 200;
    canvas.height = 50;
    
    // Text with custom font
    ctx.textBaseline = 'top';
    ctx.font = "14px 'Arial'";
    ctx.fillStyle = '#f60';
    ctx.fillRect(125, 1, 62, 20);
    ctx.fillStyle = '#069';
    ctx.fillText('Lectio.space 🎓', 2, 15);
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
    ctx.fillText('Lectio.space 🎓', 4, 17);
    
    // Emoji and unicode
    ctx.font = "11px 'Times New Roman'";
    ctx.fillText('абвгд αβγδ 你好', 2, 37);
    
    return simpleHash(canvas.toDataURL());
  } catch (e) {
    return '';
  }
}

/**
 * Создаёт audio fingerprint
 */
async function getAudioFingerprint() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return '';
    
    const context = new AudioContext();
    const oscillator = context.createOscillator();
    const analyser = context.createAnalyser();
    const gain = context.createGain();
    const scriptProcessor = context.createScriptProcessor(4096, 1, 1);
    
    oscillator.type = 'triangle';
    oscillator.frequency.setValueAtTime(10000, context.currentTime);
    
    gain.gain.setValueAtTime(0, context.currentTime);
    
    oscillator.connect(analyser);
    analyser.connect(scriptProcessor);
    scriptProcessor.connect(gain);
    gain.connect(context.destination);
    
    oscillator.start(0);
    
    return new Promise((resolve) => {
      scriptProcessor.onaudioprocess = (event) => {
        const output = event.inputBuffer.getChannelData(0);
        let sum = 0;
        for (let i = 0; i < output.length; i++) {
          sum += Math.abs(output[i]);
        }
        
        oscillator.stop();
        scriptProcessor.disconnect();
        context.close();
        
        resolve(simpleHash(sum.toString()));
      };
      
      // Fallback timeout
      setTimeout(() => {
        try { oscillator.stop(); } catch (e) {}
        try { context.close(); } catch (e) {}
        resolve('');
      }, 500);
    });
  } catch (e) {
    return '';
  }
}

/**
 * Проверяет наличие шрифтов
 */
function getFontsFingerprint() {
  const testFonts = [
    'Arial', 'Arial Black', 'Calibri', 'Cambria', 'Comic Sans MS',
    'Courier New', 'Georgia', 'Helvetica', 'Impact', 'Lucida Console',
    'Palatino', 'Tahoma', 'Times New Roman', 'Trebuchet MS', 'Verdana',
    // Russian fonts
    'Arial CYR', 'Times New Roman CYR',
  ];
  
  const baseFonts = ['monospace', 'sans-serif', 'serif'];
  const testString = 'mmmmmmmmmmlli';
  const testSize = '72px';
  
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  
  const getWidth = (fontFamily) => {
    ctx.font = `${testSize} ${fontFamily}`;
    return ctx.measureText(testString).width;
  };
  
  const baseWidths = baseFonts.map(getWidth);
  
  const detectedFonts = testFonts.filter((font) => {
    return baseFonts.some((baseFont, i) => {
      const width = getWidth(`'${font}',${baseFont}`);
      return width !== baseWidths[i];
    });
  });
  
  return simpleHash(detectedFonts.join(','));
}

/**
 * Получает информацию о плагинах
 */
function getPluginsFingerprint() {
  const plugins = Array.from(navigator.plugins || [])
    .map(p => p.name)
    .sort()
    .join(',');
  
  return simpleHash(plugins);
}

/**
 * Простая хэш-функция
 */
function simpleHash(str) {
  let hash = 0;
  if (str.length === 0) return hash.toString(16);
  
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  
  return Math.abs(hash).toString(16);
}


// ============================================================================
// BEHAVIORAL ANALYSIS
// ============================================================================

/**
 * Класс для отслеживания поведенческих паттернов
 */
export class BehavioralTracker {
  constructor() {
    this.startTime = Date.now();
    this.mouseMovements = [];
    this.keyPresses = 0;
    this.clicks = 0;
    this.scrollEvents = 0;
    this.focusChanges = 0;
    this.touchEvents = 0;
    
    this.setupListeners();
  }
  
  setupListeners() {
    // Mouse movements (throttled)
    let lastMouseMove = 0;
    this.mouseMoveHandler = (e) => {
      const now = Date.now();
      if (now - lastMouseMove > 50) { // Throttle to 20 events/sec
        this.mouseMovements.push({
          x: e.clientX,
          y: e.clientY,
          t: now - this.startTime
        });
        // Keep only last 100 movements
        if (this.mouseMovements.length > 100) {
          this.mouseMovements.shift();
        }
        lastMouseMove = now;
      }
    };
    
    // Key presses
    this.keyPressHandler = () => {
      this.keyPresses++;
    };
    
    // Clicks
    this.clickHandler = () => {
      this.clicks++;
    };
    
    // Scroll
    this.scrollHandler = () => {
      this.scrollEvents++;
    };
    
    // Focus changes
    this.focusHandler = () => {
      this.focusChanges++;
    };
    
    // Touch events
    this.touchHandler = () => {
      this.touchEvents++;
    };
    
    document.addEventListener('mousemove', this.mouseMoveHandler);
    document.addEventListener('keydown', this.keyPressHandler);
    document.addEventListener('click', this.clickHandler);
    document.addEventListener('scroll', this.scrollHandler);
    document.addEventListener('focusin', this.focusHandler);
    document.addEventListener('touchstart', this.touchHandler);
  }
  
  cleanup() {
    document.removeEventListener('mousemove', this.mouseMoveHandler);
    document.removeEventListener('keydown', this.keyPressHandler);
    document.removeEventListener('click', this.clickHandler);
    document.removeEventListener('scroll', this.scrollHandler);
    document.removeEventListener('focusin', this.focusHandler);
    document.removeEventListener('touchstart', this.touchHandler);
  }
  
  /**
   * Анализирует, насколько движения мыши похожи на линейные (бот)
   */
  isLinearMousePath() {
    if (this.mouseMovements.length < 10) return false;
    
    const movements = this.mouseMovements.slice(-20);
    let linearCount = 0;
    
    for (let i = 2; i < movements.length; i++) {
      const p1 = movements[i - 2];
      const p2 = movements[i - 1];
      const p3 = movements[i];
      
      // Calculate cross product to determine linearity
      const cross = (p2.x - p1.x) * (p3.y - p1.y) - (p2.y - p1.y) * (p3.x - p1.x);
      
      // If points are collinear (cross product near 0)
      if (Math.abs(cross) < 100) {
        linearCount++;
      }
    }
    
    // If more than 80% of movements are linear, suspicious
    return linearCount / (movements.length - 2) > 0.8;
  }
  
  /**
   * Собирает данные для отправки на сервер
   */
  getData() {
    const now = Date.now();
    const formFillTime = (now - this.startTime) / 1000; // в секундах
    
    return {
      formFillTime,
      mouseMovements: this.mouseMovements.length,
      keyPresses: this.keyPresses,
      clicks: this.clicks,
      scrollEvents: this.scrollEvents,
      focusChanges: this.focusChanges,
      touchEvents: this.touchEvents,
      linearMousePath: this.isLinearMousePath(),
      // Дополнительные метрики
      avgMouseSpeed: this.calculateAvgMouseSpeed(),
      hasNaturalPauses: this.hasNaturalPauses(),
    };
  }
  
  calculateAvgMouseSpeed() {
    if (this.mouseMovements.length < 2) return 0;
    
    let totalDistance = 0;
    let totalTime = 0;
    
    for (let i = 1; i < this.mouseMovements.length; i++) {
      const p1 = this.mouseMovements[i - 1];
      const p2 = this.mouseMovements[i];
      
      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const dt = p2.t - p1.t;
      
      if (dt > 0) {
        totalDistance += Math.sqrt(dx * dx + dy * dy);
        totalTime += dt;
      }
    }
    
    return totalTime > 0 ? (totalDistance / totalTime) * 1000 : 0; // pixels/sec
  }
  
  hasNaturalPauses() {
    // Люди делают паузы при заполнении формы
    // Боты обычно заполняют всё сразу
    if (this.mouseMovements.length < 5) return false;
    
    let pauseCount = 0;
    for (let i = 1; i < this.mouseMovements.length; i++) {
      const dt = this.mouseMovements[i].t - this.mouseMovements[i - 1].t;
      if (dt > 500) { // Пауза больше 500мс
        pauseCount++;
      }
    }
    
    return pauseCount >= 2;
  }
}


// ============================================================================
// INTEGRATION HOOKS
// ============================================================================

/**
 * React Hook для использования fingerprint защиты
 */
export function useBotProtection() {
  const [fingerprint, setFingerprint] = React.useState(null);
  const [behavioralTracker, setBehavioralTracker] = React.useState(null);
  const [isReady, setIsReady] = React.useState(false);
  
  React.useEffect(() => {
    let tracker = null;
    
    const init = async () => {
      // Собираем fingerprint
      const fp = await collectDeviceFingerprint();
      setFingerprint(fp);
      
      // Запускаем отслеживание поведения
      tracker = new BehavioralTracker();
      setBehavioralTracker(tracker);
      
      setIsReady(true);
    };
    
    init();
    
    return () => {
      if (tracker) {
        tracker.cleanup();
      }
    };
  }, []);
  
  /**
   * Получить данные для отправки на сервер
   */
  const getProtectionData = React.useCallback(() => {
    return {
      deviceFingerprint: fingerprint,
      behavioralData: behavioralTracker ? behavioralTracker.getData() : null,
    };
  }, [fingerprint, behavioralTracker]);
  
  /**
   * Добавить данные в API запрос
   */
  const enhanceRequest = React.useCallback((data) => {
    return {
      ...data,
      ...getProtectionData(),
    };
  }, [getProtectionData]);
  
  return {
    fingerprint,
    isReady,
    getProtectionData,
    enhanceRequest,
  };
}


// ============================================================================
// HONEYPOT COMPONENT
// ============================================================================

/**
 * Скрытое поле-ловушка для ботов
 * Люди не видят и не заполняют, боты заполняют
 */
export function HoneypotField({ name = 'website', onChange }) {
  return (
    <div
      style={{
        position: 'absolute',
        left: '-9999px',
        top: '-9999px',
        width: '1px',
        height: '1px',
        overflow: 'hidden',
        opacity: 0,
        pointerEvents: 'none',
      }}
      aria-hidden="true"
    >
      <label htmlFor={name}>
        Leave this field empty
        <input
          type="text"
          id={name}
          name={name}
          tabIndex={-1}
          autoComplete="off"
          onChange={(e) => {
            if (onChange) {
              onChange(e.target.value);
            }
          }}
        />
      </label>
    </div>
  );
}


// ============================================================================
// FINGERPRINT HEADER
// ============================================================================

/**
 * Добавляет fingerprint в заголовки запроса
 */
export function getFingerprintHeaders(fingerprint) {
  if (!fingerprint) return {};
  
  return {
    'X-Device-Fingerprint': JSON.stringify(fingerprint),
  };
}


// ============================================================================
// STORAGE
// ============================================================================

const FP_STORAGE_KEY = 'lectio_device_fp';

/**
 * Кэширует fingerprint в localStorage
 */
export function cacheFingerprint(fp) {
  try {
    localStorage.setItem(FP_STORAGE_KEY, JSON.stringify({
      fp,
      ts: Date.now(),
    }));
  } catch (e) {
    // localStorage may be unavailable
  }
}

/**
 * Получает кэшированный fingerprint
 */
export function getCachedFingerprint() {
  try {
    const data = localStorage.getItem(FP_STORAGE_KEY);
    if (!data) return null;
    
    const parsed = JSON.parse(data);
    // Fingerprint valid for 24 hours
    if (Date.now() - parsed.ts > 24 * 60 * 60 * 1000) {
      localStorage.removeItem(FP_STORAGE_KEY);
      return null;
    }
    
    return parsed.fp;
  } catch (e) {
    return null;
  }
}


// Need React for hooks
import React from 'react';

export default {
  collectDeviceFingerprint,
  BehavioralTracker,
  useBotProtection,
  HoneypotField,
  getFingerprintHeaders,
  cacheFingerprint,
  getCachedFingerprint,
};
