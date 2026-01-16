import React, { useState, useEffect, useCallback } from 'react';

/**
 * CodeQuestion - компонент для создания/редактирования задания на программирование
 * Используется учителем в конструкторе ДЗ
 */
const CodeQuestion = ({ question, onChange }) => {
  const { config = {} } = question;
  
  const [testCases, setTestCases] = useState(config.testCases || [
    { id: 'tc-1', input: '', expectedOutput: '' }
  ]);
  
  useEffect(() => {
    if (config.testCases && config.testCases.length > 0) {
      setTestCases(config.testCases);
    }
  }, [config.testCases]);

  const updateConfig = useCallback((patch) => {
    const nextConfig = { ...config, ...patch };
    onChange({ ...question, config: nextConfig });
  }, [config, question, onChange]);

  const handleLanguageChange = (language) => {
    updateConfig({ language });
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

  return (
    <div className="hc-question-editor">
      {/* Язык программирования */}
      <div className="form-group">
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
      <div className="form-group">
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

      {/* Решение учителя (опционально, для проверки тестов) */}
      <div className="form-group">
        <label className="form-label">Эталонное решение (для проверки тестов)</label>
        <textarea
          className="form-textarea code-textarea"
          rows={6}
          value={config.solutionCode || ''}
          onChange={handleSolutionCodeChange}
          placeholder={language === 'python'
            ? 'def solution():\n    return "Hello"'
            : 'function solution() {\n  return "Hello";\n}'}
          style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}
        />
        <small className="gm-hint">
          Опционально: для проверки корректности тестов
        </small>
      </div>

      {/* Тест-кейсы */}
      <div className="form-group">
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
