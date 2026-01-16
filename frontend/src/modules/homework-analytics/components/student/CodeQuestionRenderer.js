import React, { useState, useCallback, useEffect } from 'react';
import { runCode, runTests, preloadPyodide } from '../../services/codeRunner';
import '../questions/CodeQuestion.css';

/**
 * CodeQuestionRenderer - компонент для студента
 * Позволяет писать код, запускать его и видеть результаты тестов
 */
const CodeQuestionRenderer = ({ question, answer, onChange, disabled = false }) => {
  const { config = {} } = question;
  const language = config.language || 'python';
  const testCases = config.testCases || [];
  const hint = config.hint || '';
  
  // Парсим answer (JSON с code и testResults)
  const parseAnswer = useCallback((ans) => {
    if (!ans) return { code: config.starterCode || '', testResults: [] };
    if (typeof ans === 'string') {
      try {
        return JSON.parse(ans);
      } catch {
        return { code: ans, testResults: [] };
      }
    }
    return ans;
  }, [config.starterCode]);
  
  const [code, setCode] = useState(() => parseAnswer(answer).code);
  const [testResults, setTestResults] = useState(() => parseAnswer(answer).testResults);
  const [output, setOutput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [isLoadingPyodide, setIsLoadingPyodide] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [activeTab, setActiveTab] = useState('output'); // 'output' | 'tests'

  // Предзагрузка Pyodide для Python
  useEffect(() => {
    if (language === 'python') {
      preloadPyodide();
    }
  }, [language]);

  // Синхронизация с answer из props
  useEffect(() => {
    const parsed = parseAnswer(answer);
    if (parsed.code !== code) {
      setCode(parsed.code);
    }
    if (JSON.stringify(parsed.testResults) !== JSON.stringify(testResults)) {
      setTestResults(parsed.testResults);
    }
  }, [answer]); // eslint-disable-line react-hooks/exhaustive-deps

  // Сохранение ответа в parent
  const saveAnswer = useCallback((newCode, newTestResults) => {
    const answerData = {
      code: newCode,
      testResults: newTestResults,
    };
    onChange(answerData);
  }, [onChange]);

  // Обработка изменения кода
  const handleCodeChange = (e) => {
    const newCode = e.target.value;
    setCode(newCode);
    // Автосохранение при изменении (debounced в parent)
    saveAnswer(newCode, testResults);
  };

  // Запуск кода (просто выполнение без тестов)
  const handleRun = async () => {
    if (isRunning || disabled) return;
    
    setIsRunning(true);
    setActiveTab('output');
    
    if (language === 'python') {
      setIsLoadingPyodide(true);
    }
    
    try {
      const result = await runCode(language, code, '');
      
      if (result.error) {
        setOutput(`Ошибка: ${result.error}`);
      } else {
        const outputText = result.stdout || '(нет вывода)';
        const timeInfo = `\n\n--- Выполнено за ${result.duration}ms ---`;
        setOutput(outputText + timeInfo);
      }
    } catch (error) {
      setOutput(`Ошибка: ${error.message}`);
    } finally {
      setIsRunning(false);
      setIsLoadingPyodide(false);
    }
  };

  // Запуск тестов
  const handleRunTests = async () => {
    if (isRunning || disabled || testCases.length === 0) return;
    
    setIsRunning(true);
    setActiveTab('tests');
    
    if (language === 'python') {
      setIsLoadingPyodide(true);
    }
    
    try {
      const results = await runTests(language, code, testCases);
      setTestResults(results);
      saveAnswer(code, results);
      
      const passed = results.filter(r => r.passed).length;
      const total = results.length;
      setOutput(`Тесты: ${passed}/${total} пройдено`);
    } catch (error) {
      setOutput(`Ошибка: ${error.message}`);
    } finally {
      setIsRunning(false);
      setIsLoadingPyodide(false);
    }
  };

  // Подсчёт результатов
  const passedCount = testResults.filter(r => r.passed).length;
  const totalTests = testCases.length;

  return (
    <div className="code-editor-container">
      {/* Заголовок с языком и кнопками */}
      <div className="code-editor-header">
        <span className="code-language-badge">
          {language === 'python' ? '🐍 Python' : '📜 JavaScript'}
        </span>
        <div className="code-editor-actions">
          <button
            type="button"
            className={`code-run-btn ${isRunning ? 'running' : ''}`}
            onClick={handleRun}
            disabled={isRunning || disabled}
          >
            {isRunning ? 'Выполняется...' : '▶ Запустить'}
          </button>
          {testCases.length > 0 && (
            <button
              type="button"
              className="code-run-btn"
              onClick={handleRunTests}
              disabled={isRunning || disabled}
              style={{ background: 'var(--color-primary)' }}
            >
              {isRunning ? '...' : '🧪 Тесты'}
            </button>
          )}
        </div>
      </div>

      {/* Загрузка Pyodide */}
      {isLoadingPyodide && (
        <div className="code-loading-pyodide">
          <div className="code-loading-spinner" />
          <span>Загрузка Python...</span>
        </div>
      )}

      {/* Редактор кода */}
      <textarea
        className="code-editor-textarea"
        value={code}
        onChange={handleCodeChange}
        disabled={disabled}
        placeholder={`Напишите ${language === 'python' ? 'Python' : 'JavaScript'} код здесь...`}
        spellCheck={false}
        autoCapitalize="off"
        autoCorrect="off"
      />

      {/* Вывод / Результаты тестов */}
      <div className="code-output-container">
        <div className="code-output-header">
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              type="button"
              className={`gm-tab-button ${activeTab === 'output' ? 'active' : ''}`}
              onClick={() => setActiveTab('output')}
              style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
            >
              Вывод
            </button>
            {testCases.length > 0 && (
              <button
                type="button"
                className={`gm-tab-button ${activeTab === 'tests' ? 'active' : ''}`}
                onClick={() => setActiveTab('tests')}
                style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
              >
                Тесты ({passedCount}/{totalTests})
              </button>
            )}
          </div>
        </div>

        {activeTab === 'output' && (
          <div className={`code-output-content ${output.startsWith('Ошибка') ? 'code-output-error' : ''}`}>
            {output || 'Нажмите "Запустить" чтобы выполнить код'}
          </div>
        )}

        {activeTab === 'tests' && testCases.length > 0 && (
          <div className="code-tests-results">
            <div className="code-tests-summary">
              <span className={`code-tests-passed ${
                passedCount === totalTests ? 'all-passed' : 
                passedCount === 0 ? 'all-failed' : 'some-failed'
              }`}>
                {passedCount}/{totalTests} тестов пройдено
              </span>
            </div>
            <div className="code-tests-list">
              {testCases.map((tc, index) => {
                const result = testResults[index];
                const passed = result?.passed || false;
                
                return (
                  <div key={tc.id || index} className={`code-test-result ${passed ? 'passed' : 'failed'}`}>
                    <span className="code-test-icon">
                      {passed ? '✓' : '✗'}
                    </span>
                    <div className="code-test-details">
                      <div className="code-test-label">
                        Тест {index + 1}: {passed ? 'Пройден' : 'Не пройден'}
                      </div>
                      {!passed && result && (
                        <div className="code-test-io">
                          <div className="code-test-io-item">
                            <div className="code-test-io-label">Ожидалось:</div>
                            <div className="code-test-io-value">{result.expected || '(пусто)'}</div>
                          </div>
                          <div className="code-test-io-item">
                            <div className="code-test-io-label">Получено:</div>
                            <div className="code-test-io-value">{result.actual || '(пусто)'}</div>
                          </div>
                        </div>
                      )}
                      {result?.error && (
                        <div className="code-test-io-item" style={{ marginTop: '0.25rem' }}>
                          <div className="code-test-io-value code-output-error">{result.error}</div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Подсказка */}
      {hint && (
        <div style={{ padding: '0.75rem 1rem', borderTop: '1px solid var(--border-light)' }}>
          <button
            type="button"
            className="code-hint-toggle"
            onClick={() => setShowHint(!showHint)}
          >
            {showHint ? '🔼 Скрыть подсказку' : '💡 Показать подсказку'}
          </button>
          {showHint && (
            <div className="code-hint-content">{hint}</div>
          )}
        </div>
      )}
    </div>
  );
};

export default CodeQuestionRenderer;
