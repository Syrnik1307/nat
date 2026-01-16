/**
 * Браузерный сервис для выполнения кода (Python через Pyodide, JS нативно)
 * Безопасное выполнение в песочнице без доступа к серверу
 */

let pyodideInstance = null;
let pyodideLoading = false;
let pyodideLoadPromise = null;

/**
 * Загрузка Pyodide (ленивая, один раз)
 */
const loadPyodide = async () => {
  if (pyodideInstance) return pyodideInstance;
  if (pyodideLoading) return pyodideLoadPromise;

  pyodideLoading = true;
  pyodideLoadPromise = (async () => {
    try {
      // Динамически загружаем Pyodide из CDN
      if (!window.loadPyodide) {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js';
        document.head.appendChild(script);
        await new Promise((resolve, reject) => {
          script.onload = resolve;
          script.onerror = reject;
        });
      }
      pyodideInstance = await window.loadPyodide();
      return pyodideInstance;
    } catch (error) {
      pyodideLoading = false;
      throw new Error('Не удалось загрузить Python: ' + error.message);
    }
  })();
  
  return pyodideLoadPromise;
};

/**
 * Выполнение Python кода
 */
const runPython = async (code, stdin = '') => {
  const startTime = performance.now();
  const timeout = 5000; // 5 секунд
  
  try {
    const pyodide = await loadPyodide();
    
    // Подготовка окружения с перехватом stdout/stderr и mock stdin
    await pyodide.runPythonAsync(`
import sys
from io import StringIO

# Mock stdin
class MockStdin:
    def __init__(self, data):
        self.data = StringIO(data)
    def readline(self):
        return self.data.readline()
    def read(self, n=-1):
        return self.data.read(n)

sys.stdin = MockStdin(${JSON.stringify(stdin)})
sys.stdout = StringIO()
sys.stderr = StringIO()
    `);

    // Выполняем код пользователя с таймаутом
    const runPromise = pyodide.runPythonAsync(code);
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Превышено время выполнения (5 сек)')), timeout)
    );
    
    await Promise.race([runPromise, timeoutPromise]);
    
    // Получаем вывод
    const stdout = await pyodide.runPythonAsync('sys.stdout.getvalue()');
    const stderr = await pyodide.runPythonAsync('sys.stderr.getvalue()');
    
    const duration = Math.round(performance.now() - startTime);
    
    return {
      success: true,
      stdout: stdout || '',
      stderr: stderr || '',
      duration,
      error: null,
    };
  } catch (error) {
    const duration = Math.round(performance.now() - startTime);
    return {
      success: false,
      stdout: '',
      stderr: '',
      duration,
      error: error.message || 'Ошибка выполнения',
    };
  }
};

/**
 * Выполнение JavaScript кода
 */
const runJavaScript = async (code, stdin = '') => {
  const startTime = performance.now();
  const timeout = 5000;
  
  return new Promise((resolve) => {
    const output = [];
    const errors = [];
    
    // Создаём sandbox iframe
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.sandbox = 'allow-scripts';
    document.body.appendChild(iframe);
    
    const cleanup = () => {
      document.body.removeChild(iframe);
    };
    
    // Таймаут
    const timeoutId = setTimeout(() => {
      cleanup();
      resolve({
        success: false,
        stdout: output.join('\n'),
        stderr: '',
        duration: Math.round(performance.now() - startTime),
        error: 'Превышено время выполнения (5 сек)',
      });
    }, timeout);
    
    // Слушаем сообщения из iframe
    const handler = (event) => {
      if (event.source !== iframe.contentWindow) return;
      
      const { type, data } = event.data || {};
      if (type === 'log') {
        output.push(data);
      } else if (type === 'error') {
        errors.push(data);
      } else if (type === 'done') {
        clearTimeout(timeoutId);
        window.removeEventListener('message', handler);
        cleanup();
        
        const duration = Math.round(performance.now() - startTime);
        resolve({
          success: errors.length === 0,
          stdout: output.join('\n'),
          stderr: errors.join('\n'),
          duration,
          error: errors.length > 0 ? errors[0] : null,
        });
      }
    };
    
    window.addEventListener('message', handler);
    
    // Код для iframe с перехватом console.log и обработкой readline
    const iframeCode = `
      <script>
        const output = [];
        const inputLines = ${JSON.stringify(stdin.split('\n'))};
        let inputIndex = 0;
        
        // Перехват console.log
        const originalLog = console.log;
        console.log = (...args) => {
          const line = args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' ');
          parent.postMessage({ type: 'log', data: line }, '*');
        };
        
        // Mock readline (для совместимости)
        const readline = () => inputLines[inputIndex++] || '';
        const input = readline;
        const prompt = (msg) => { console.log(msg); return readline(); };
        
        try {
          ${code}
          parent.postMessage({ type: 'done' }, '*');
        } catch (e) {
          parent.postMessage({ type: 'error', data: e.message }, '*');
          parent.postMessage({ type: 'done' }, '*');
        }
      <\/script>
    `;
    
    iframe.srcdoc = iframeCode;
  });
};

/**
 * Универсальный запуск кода
 */
export const runCode = async (language, code, stdin = '') => {
  if (!code || !code.trim()) {
    return {
      success: false,
      stdout: '',
      stderr: '',
      duration: 0,
      error: 'Пустой код',
    };
  }
  
  switch (language) {
    case 'python':
      return runPython(code, stdin);
    case 'javascript':
      return runJavaScript(code, stdin);
    default:
      return {
        success: false,
        stdout: '',
        stderr: '',
        duration: 0,
        error: `Язык ${language} не поддерживается`,
      };
  }
};

/**
 * Запуск тестов для кода
 * @param {string} language - 'python' | 'javascript'
 * @param {string} code - код пользователя
 * @param {Array} testCases - [{input: string, expectedOutput: string}]
 * @returns {Array} - [{passed: boolean, input, expected, actual, duration, error}]
 */
export const runTests = async (language, code, testCases) => {
  const results = [];
  
  for (const testCase of testCases) {
    const { input = '', expectedOutput = '' } = testCase;
    
    const result = await runCode(language, code, input);
    
    // Нормализуем вывод (убираем trailing whitespace)
    const actualOutput = (result.stdout || '').trim();
    const expected = expectedOutput.trim();
    
    const passed = result.success && actualOutput === expected;
    
    results.push({
      passed,
      input,
      expected,
      actual: actualOutput,
      duration: result.duration,
      error: result.error,
    });
  }
  
  return results;
};

/**
 * Проверка доступности Pyodide
 */
export const isPyodideLoaded = () => pyodideInstance !== null;

/**
 * Предзагрузка Pyodide (опционально, для UX)
 */
export const preloadPyodide = () => {
  loadPyodide().catch(() => {}); // Молча игнорируем ошибки
};

const codeRunnerService = {
  runCode,
  runTests,
  isPyodideLoaded,
  preloadPyodide,
};

export default codeRunnerService;
