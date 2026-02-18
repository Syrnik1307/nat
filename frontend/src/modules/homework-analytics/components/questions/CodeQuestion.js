import React, { useState, useEffect, useCallback } from 'react';
import { runCode, runTests, preloadPyodide } from '../../services/codeRunner';
import './CodeQuestion.css';

/**
 * CodeQuestion - компонент для создания/редактирования задания на программирование
 * Используется учителем в конструкторе ДЗ
 * Включает встроенный терминал для тестирования эталонного решения
 */
const CodeQuestion = ({ question, onChange }) => {
  const { config = {} } = question;
  
  const [testCases, setTestCases] = useState(config.testCases || [
    { id: 'tc-1', input: '', expectedOutput: '' }
  ]);
  
  // Состояние терминала
  const [terminalOutput, setTerminalOutput] = useState('');
  const [testResults, setTestResults] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isLoadingPyodide, setIsLoadingPyodide] = useState(false);
  const [activeTab, setActiveTab] = useState('output'); // 'output' | 'tests'
  
  useEffect(() => {
    if (config.testCases && config.testCases.length > 0) {
      setTestCases(config.testCases);
    }
  }, [config.testCases]);

  // Предзагрузка Pyodide для Python
  useEffect(() => {
    const language = config.language || 'python';
    if (language === 'python') {
      preloadPyodide();
    }
  }, [config.language]);

  const updateConfig = useCallback((patch) => {
    const nextConfig = { ...config, ...patch };
    onChange({ ...question, config: nextConfig });
  }, [config, question, onChange]);

  const handleLanguageChange = (language) => {
    updateConfig({ language });
    // Сброс результатов при смене языка
    setTerminalOutput('');
    setTestResults([]);
  };

  const handleStarterCodeChange = (e) => {
    updateConfig({ starterCode: e.target.value });
  };

  const handleSolutionCodeChange = (e) => {
    updateConfig({ solutionCode: e.target.value });
  };

  const addTestCase = () => {
    const newId = `tc-${Date.now()}`;
    const next = [...testCases, { id: newId, input: '', expectedOutput: '' }];
    setTestCases(next);
    updateConfig({ testCases: next });
  };

  const removeTestCase = (id) => {
    if (testCases.length <= 1) return;
    const next = testCases.filter(tc => tc.id !== id);
    setTestCases(next);
    updateConfig({ testCases: next });
  };

  const updateTestCase = (id, field, value) => {
    const next = testCases.map(tc => 
      tc.id === id ? { ...tc, [field]: value } : tc
    );
    setTestCases(next);
    updateConfig({ testCases: next });
  };

  const language = config.language || 'python';
  const solutionCode = config.solutionCode || '';

  // Запуск эталонного решения
  const handleRunSolution = async () => {
    if (isRunning || !solutionCode.trim()) return;
    
    setIsRunning(true);
    setActiveTab('output');
    
    if (language === 'python') {
      setIsLoadingPyodide(true);
    }
    
    try {
      const result = await runCode(language, solutionCode, '');
      
      if (result.error) {
        setTerminalOutput(`Ошибка: ${result.error}`);
      } else {
        const outputText = result.stdout || '(нет вывода)';
        const timeInfo = `\n\n--- Выполнено за ${result.duration}ms ---`;
        setTerminalOutput(outputText + timeInfo);
      }
    } catch (error) {
      setTerminalOutput(`Ошибка: ${error.message}`);
    } finally {
      setIsRunning(false);
      setIsLoadingPyodide(false);
    }
  };

  // Запуск тестов на эталонном решении
  const handleRunTests = async () => {
    if (isRunning || !solutionCode.trim() || testCases.length === 0) return;
    
    // Проверяем что есть хотя бы один тест с ожидаемым выводом
    const hasValidTests = testCases.some(tc => tc.expectedOutput.trim());
    if (!hasValidTests) {
      setTerminalOutput('Добавьте хотя бы один тест с ожидаемым выводом');
      return;
    }
    
    setIsRunning(true);
    setActiveTab('tests');
    
    if (language === 'python') {
      setIsLoadingPyodide(true);
    }
    
    try {
      const results = await runTests(language, solutionCode, testCases);
      setTestResults(results);
      
      const passed = results.filter(r => r.passed).length;
      const total = results.length;
      setTerminalOutput(`Тесты: ${passed}/${total} пройдено`);
    } catch (error) {
      setTerminalOutput(`Ошибка: ${error.message}`);
    } finally {
      setIsRunning(false);
      setIsLoadingPyodide(false);
    }
  };

  const passedCount = testResults.filter(r => r.passed).length;
  const totalTests = testCases.length;

  return (
    <div className="hc-question-editor">
      {/* Язык программирования */}
      <div className="form-group" data-tour="q-code-language">
        <label className="form-label">Язык программирования</label>
        <div className="gm-tab-switch">
          <button
            type="button"
            className={`gm-tab-button ${language === 'python' ? 'active' : ''}`}
            onClick={() => handleLanguageChange('python')}
          >
            Python
          </button>
          <button
            type="button"
            className={`gm-tab-button ${language === 'javascript' ? 'active' : ''}`}
            onClick={() => handleLanguageChange('javascript')}
          >
            JavaScript
          </button>
        </div>
      </div>

      {/* Начальный код (шаблон для ученика) */}
      <div className="form-group" data-tour="q-code-starter">
        <label className="form-label">Начальный код (шаблон для ученика)</label>
        <textarea
          className="form-textarea code-textarea"
          rows={6}
          value={config.starterCode || ''}
          onChange={handleStarterCodeChange}
          placeholder={language === 'python' 
            ? '# Напишите функцию solution()\ndef solution():\n    pass'
            : '// Напишите функцию solution()\nfunction solution() {\n  \n}'}
          style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}
        />
        <small className="gm-hint">
          Этот код будет показан ученику как стартовая точка
        </small>
      </div>

      {/* Эталонное решение с терминалом */}
      <div className="form-group" data-tour="q-code-solution">
        <label className="form-label">Эталонное решение (для проверки тестов)</label>
        <div className="code-editor-container" data-tour="q-code-terminal">
          {/* Заголовок с языком и кнопками */}
          <div className="code-editor-header">
            <span className="code-language-badge">
              {language === 'python' ? 'Python' : 'JavaScript'}
            </span>
            <div className="code-editor-actions">
              <button
                type="button"
                className={`code-run-btn ${isRunning ? 'running' : ''}`}
                onClick={handleRunSolution}
                disabled={isRunning || !solutionCode.trim()}
                title="Запустить эталонное решение"
                data-tour="q-code-run"
              >
                {isRunning ? 'Выполняется...' : 'Запустить'}
              </button>
              {testCases.length > 0 && (
                <button
                  type="button"
                  className="code-run-btn code-run-btn-tests"
                  onClick={handleRunTests}
                  disabled={isRunning || !solutionCode.trim()}
                  title="Проверить эталонное решение на тестах"
                    data-tour="q-code-run-tests"
                >
                  {isRunning ? '...' : 'Тесты'}
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
            value={solutionCode}
            onChange={handleSolutionCodeChange}
            placeholder={language === 'python'
              ? 'def solution():\n    return "Hello"'
              : 'function solution() {\n  return "Hello";\n}'}
            spellCheck={false}
            autoCapitalize="off"
            autoCorrect="off"
          />

          {/* Терминал вывода */}
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
              <div className={`code-output-content ${terminalOutput.startsWith('Ошибка') ? 'code-output-error' : ''}`}>
                {terminalOutput || 'Нажмите "Запустить" для выполнения эталонного решения'}
              </div>
            )}

            {activeTab === 'tests' && testCases.length > 0 && (
              <div className="code-tests-results">
                <div className="code-tests-summary">
                  <span className={`code-tests-passed ${
                    passedCount === totalTests ? 'all-passed' : 
                    passedCount === 0 ? 'all-failed' : 'some-failed'
                  }`}>
                    {testResults.length > 0 ? `${passedCount}/${totalTests} тестов пройдено` : 'Нажмите "Тесты" для проверки'}
                  </span>
                </div>
                {testResults.length > 0 && (
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
                )}
              </div>
            )}
          </div>
        </div>
        <small className="gm-hint">
          Напишите эталонное решение и нажмите "Тесты" для проверки корректности тест-кейсов
        </small>
      </div>

      {/* Тест-кейсы */}
      <div className="form-group" data-tour="q-code-tests">
        <label className="form-label">Тест-кейсы для автопроверки</label>
        <div className="code-test-cases">
          {testCases.map((tc, index) => (
            <div key={tc.id} className="code-test-case">
              <div className="code-test-case-header">
                <span className="code-test-case-number">Тест {index + 1}</span>
                {testCases.length > 1 && (
                  <button
                    type="button"
                    className="gm-btn-danger-text"
                    onClick={() => removeTestCase(tc.id)}
                  >
                    Удалить
                  </button>
                )}
              </div>
              <div className="code-test-case-fields">
                <div className="code-test-field">
                  <label className="form-label-small">Входные данные (stdin)</label>
                  <textarea
                    className="form-textarea"
                    rows={2}
                    value={tc.input}
                    onChange={(e) => updateTestCase(tc.id, 'input', e.target.value)}
                    placeholder="Входные данные (каждая строка = input())"
                    style={{ fontFamily: 'monospace', fontSize: '0.8125rem' }}
                  />
                </div>
                <div className="code-test-field">
                  <label className="form-label-small">Ожидаемый вывод (stdout)</label>
                  <textarea
                    className="form-textarea"
                    rows={2}
                    value={tc.expectedOutput}
                    onChange={(e) => updateTestCase(tc.id, 'expectedOutput', e.target.value)}
                    placeholder="Ожидаемый вывод программы"
                    style={{ fontFamily: 'monospace', fontSize: '0.8125rem' }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
        <button
          type="button"
          className="gm-btn-surface"
          onClick={addTestCase}
          style={{ marginTop: '0.75rem' }}
          data-tour="q-code-add-test"
        >
          + Добавить тест
        </button>
      </div>

      {/* Подсказки для ученика */}
      <div className="form-group">
        <label className="form-label">Подсказка для ученика (опционально)</label>
        <textarea
          className="form-textarea"
          rows={2}
          value={config.hint || ''}
          onChange={(e) => updateConfig({ hint: e.target.value })}
          placeholder="Подсказка, которую ученик может открыть"
        />
      </div>
    </div>
  );
};

export default CodeQuestion;
