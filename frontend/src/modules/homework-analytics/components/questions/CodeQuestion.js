import React from 'react';
import './CodeQuestion.css';

/**
 * CodeQuestion — редактор вопроса типа «Код» для HomeworkConstructor.
 * config: { language, starterCode, solutionCode, testCases[], hint }
 */
const CodeQuestion = ({ question, onChange }) => {
  const { config = {} } = question;

  const updateConfig = (patch) => {
    const nextConfig = { ...config, ...patch };
    onChange({ ...question, config: nextConfig });
  };

  /* ---------- test-cases ---------- */
  const testCases = config.testCases || [];

  const addTestCase = () => {
    const id = `tc-${Date.now()}`;
    updateConfig({ testCases: [...testCases, { id, input: '', expectedOutput: '' }] });
  };

  const removeTestCase = (id) => {
    updateConfig({ testCases: testCases.filter((tc) => tc.id !== id) });
  };

  const updateTestCase = (id, field, value) => {
    updateConfig({
      testCases: testCases.map((tc) => (tc.id === id ? { ...tc, [field]: value } : tc)),
    });
  };

  return (
    <div className="hc-question-editor code-question">
      {/* Язык */}
      <div className="form-group">
        <label className="form-label">Язык программирования</label>
        <select
          className="form-select"
          value={config.language || 'python'}
          onChange={(e) => updateConfig({ language: e.target.value })}
        >
          <option value="python">Python</option>
          <option value="javascript">JavaScript</option>
          <option value="java">Java</option>
          <option value="cpp">C++</option>
          <option value="csharp">C#</option>
        </select>
      </div>

      {/* Стартовый код */}
      <div className="form-group">
        <label className="form-label">Стартовый код (видит ученик)</label>
        <textarea
          className="form-textarea code-textarea"
          rows={6}
          value={config.starterCode || ''}
          onChange={(e) => updateConfig({ starterCode: e.target.value })}
          placeholder="# Напишите стартовый код..."
        />
      </div>

      {/* Решение */}
      <div className="form-group">
        <label className="form-label">Эталонное решение</label>
        <textarea
          className="form-textarea code-textarea"
          rows={6}
          value={config.solutionCode || ''}
          onChange={(e) => updateConfig({ solutionCode: e.target.value })}
          placeholder="# Эталонное решение для автопроверки..."
        />
      </div>

      {/* Тест-кейсы */}
      <div className="form-group">
        <label className="form-label">Тест-кейсы</label>
        {testCases.map((tc, idx) => (
          <div key={tc.id} className="code-test-case">
            <span className="code-tc-num">#{idx + 1}</span>
            <input
              className="form-input"
              placeholder="Входные данные"
              value={tc.input}
              onChange={(e) => updateTestCase(tc.id, 'input', e.target.value)}
            />
            <input
              className="form-input"
              placeholder="Ожидаемый вывод"
              value={tc.expectedOutput}
              onChange={(e) => updateTestCase(tc.id, 'expectedOutput', e.target.value)}
            />
            <button type="button" className="btn-icon danger" onClick={() => removeTestCase(tc.id)}>
              ✕
            </button>
          </div>
        ))}
        <button type="button" className="btn-secondary btn-sm" onClick={addTestCase}>
          + Добавить тест-кейс
        </button>
      </div>

      {/* Подсказка */}
      <div className="form-group">
        <label className="form-label">Подсказка (опционально)</label>
        <input
          className="form-input"
          value={config.hint || ''}
          onChange={(e) => updateConfig({ hint: e.target.value })}
          placeholder="Подсказка для ученика"
        />
      </div>
    </div>
  );
};

export default CodeQuestion;
