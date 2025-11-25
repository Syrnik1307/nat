import React, { useMemo, useState } from 'react';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import useHomeworkConstructor from '../../hooks/useHomeworkConstructor';
import {
  QUESTION_TYPES,
  createQuestionTemplate,
  getQuestionLabel,
} from '../../utils/questionTemplates';
import TextQuestion from '../questions/TextQuestion';
import SingleChoiceQuestion from '../questions/SingleChoiceQuestion';
import MultipleChoiceQuestion from '../questions/MultipleChoiceQuestion';
import ListeningQuestion from '../questions/ListeningQuestion';
import MatchingQuestion from '../questions/MatchingQuestion';
import DragDropQuestion from '../questions/DragDropQuestion';
import FillBlanksQuestion from '../questions/FillBlanksQuestion';
import HotspotQuestion from '../questions/HotspotQuestion';
import './HomeworkConstructor.css';

const initialMeta = {
  title: '',
  description: '',
  groupId: '',
  deadline: '',
  maxScore: 100,
  gamificationEnabled: true,
};

const QUESTION_COMPONENTS = {
  TEXT: TextQuestion,
  SINGLE_CHOICE: SingleChoiceQuestion,
  MULTIPLE_CHOICE: MultipleChoiceQuestion,
  LISTENING: ListeningQuestion,
  MATCHING: MatchingQuestion,
  DRAG_DROP: DragDropQuestion,
  FILL_BLANKS: FillBlanksQuestion,
  HOTSPOT: HotspotQuestion,
};

const HomeworkConstructor = () => {
  const {
    groupOptions,
    loadingGroups,
    groupError,
    reloadGroups,
    computeSuggestedMaxScore,
    saveDraft,
  } = useHomeworkConstructor();

  const [assignmentMeta, setAssignmentMeta] = useState(initialMeta);
  const [questions, setQuestions] = useState([]);
  const [showTypeMenu, setShowTypeMenu] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [validationIssues, setValidationIssues] = useState(null);

  const handleMetaChange = (field, value) => {
    setAssignmentMeta((previous) => ({
      ...previous,
      [field]: value,
    }));
  };

  const handleMaxScoreChange = (value) => {
    const numeric = Number(value);
    handleMetaChange('maxScore', Number.isFinite(numeric) ? numeric : value);
  };

  const handleAutoMaxScore = () => {
    const suggested = computeSuggestedMaxScore(questions);
    if (!suggested) return;
    handleMetaChange('maxScore', suggested);
  };

  const handleAddQuestion = (type) => {
    const template = createQuestionTemplate(type);
    template.order = questions.length;
    setQuestions((previous) => [...previous, template]);
    setShowTypeMenu(false);
  };

  const handleUpdateQuestion = (index, nextQuestion) => {
    setQuestions((previous) =>
      previous.map((question, questionIndex) =>
        questionIndex === index
          ? { ...nextQuestion, order: questionIndex }
          : { ...question, order: questionIndex }
      )
    );
  };

  const handleQuestionTextChange = (index, text) => {
    setQuestions((previous) =>
      previous.map((question, questionIndex) =>
        questionIndex === index
          ? { ...question, question_text: text }
          : question
      )
    );
  };

  const handleQuestionPointsChange = (index, value) => {
    const numeric = Number(value);
    setQuestions((previous) =>
      previous.map((question, questionIndex) =>
        questionIndex === index
          ? {
              ...question,
              points: Number.isFinite(numeric) ? numeric : question.points,
            }
          : question
      )
    );
  };

  const handleRemoveQuestion = (index) => {
    if (!window.confirm('Удалить вопрос из задания?')) return;
    setQuestions((previous) =>
      previous
        .filter((_, questionIndex) => questionIndex !== index)
        .map((question, order) => ({ ...question, order }))
    );
  };

  const handleDuplicateQuestion = (index) => {
    const source = questions[index];
    if (!source) return;
    const duplicate = {
      ...createQuestionTemplate(source.question_type),
      question_text: source.question_text,
      points: source.points,
      config: JSON.parse(JSON.stringify(source.config || {})),
      correct_answer: Array.isArray(source.correct_answer)
        ? [...source.correct_answer]
        : source.correct_answer,
    };
    setQuestions((previous) => {
      const next = [...previous];
      next.splice(index + 1, 0, duplicate);
      return next.map((question, order) => ({ ...question, order }));
    });
  };

  const handleDragEnd = (result) => {
    if (!result.destination) return;
    const reordered = Array.from(questions);
    const [moved] = reordered.splice(result.source.index, 1);
    reordered.splice(result.destination.index, 0, moved);
    setQuestions(reordered.map((question, order) => ({ ...question, order })));
  };

  const questionCount = questions.length;

  const previewTitle = useMemo(() => assignmentMeta.title || 'Новое домашнее задание', [assignmentMeta.title]);

  const QuestionEditor = ({ question, index }) => {
    const TypeComponent = QUESTION_COMPONENTS[question.question_type];

    if (!TypeComponent) {
      return (
        <div className="hc-preview-placeholder">
          Тип вопроса в разработке. Он появится в следующей итерации.
        </div>
      );
    }

    return <TypeComponent question={question} onChange={(next) => handleUpdateQuestion(index, next)} />;
  };

  const handleSaveDraft = async () => {
    setSaving(true);
    setFeedback(null);
    setValidationIssues(null);
    try {
      const result = await saveDraft(assignmentMeta, questions, null);
      if (!result.saved) {
        setValidationIssues(result.validation);
        setFeedback({
          status: 'warning',
          message: 'Проверьте настройки — найдено несколько моментов, требующих внимания.',
        });
        return;
      }

      setFeedback({ status: 'success', message: 'Черновик успешно сохранен.' });
      setValidationIssues(result.validation);
    } catch (error) {
      console.error('[HomeworkConstructor] Save draft failed:', error);
      const backendMessage = error.response?.data?.detail || error.message;
      setFeedback({ status: 'error', message: backendMessage || 'Не удалось сохранить задание.' });
    } finally {
      setSaving(false);
    }
  };

  const renderValidationDetails = () => {
    if (!validationIssues || validationIssues.ok) {
      return null;
    }

    const { metaIssues = [], questionIssues = [] } = validationIssues;
    if (!metaIssues.length && !questionIssues.length) {
      return null;
    }

    return (
      <ul className="hc-validation-list">
        {metaIssues.map((issue) => (
          <li key={`meta-${issue}`}>{issue}</li>
        ))}
        {questionIssues.map(({ index, issues }) => (
          <li key={`question-${index}`}>
            Вопрос {index + 1}: {issues.join('; ')}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="homework-constructor-page">
      <div className="hc-header">
        <h1 className="hc-header-title">🏗️ Конструктор домашних заданий</h1>
        <p className="hc-header-subtitle">
          Соберите идеальное ДЗ с разными типами вопросов, настройте дедлайны и включите геймификацию.
        </p>
      </div>

      {feedback && (
        <div
          className={`hc-feedback ${
            feedback.status === 'success'
              ? 'hc-feedback-success'
              : feedback.status === 'error'
              ? 'hc-feedback-error'
              : 'hc-feedback-warning'
          }`}
        >
          {feedback.message}
        </div>
      )}

      {renderValidationDetails()}

      <div className="hc-grid">
        <div className="hc-card">
          <div className="hc-section-title">
            <span>Параметры задания</span>
            <div className="hc-inline-fields" style={{ maxWidth: '240px' }}>
              <label className="form-label" style={{ fontSize: '0.75rem' }}>Вопросов: {questionCount}</label>
            </div>
          </div>

          <form className="gm-form" onSubmit={(event) => event.preventDefault()}>
            <div className="form-group">
              <label className="form-label">Название</label>
              <input
                className="form-input"
                value={assignmentMeta.title}
                onChange={(event) => handleMetaChange('title', event.target.value)}
                placeholder="Например: Past Simple revision"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Описание</label>
              <textarea
                className="form-textarea"
                rows={3}
                value={assignmentMeta.description}
                onChange={(event) => handleMetaChange('description', event.target.value)}
                placeholder="Дайте ученикам контекст и пояснение к заданию"
              />
            </div>

            <div className="hc-inline-fields">
              <div className="form-group">
                <label className="form-label">Группа</label>
                <select
                  className="form-input"
                  value={assignmentMeta.groupId}
                  onChange={(event) => handleMetaChange('groupId', event.target.value)}
                  disabled={loadingGroups}
                >
                  <option value="">Выберите группу</option>
                  {groupOptions.map((group) => (
                    <option key={group.value} value={group.value}>
                      {group.label}
                    </option>
                  ))}
                </select>
                {groupError && (
                  <button type="button" className="gm-btn-surface" onClick={reloadGroups}>
                    Повторить загрузку групп
                  </button>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">Дедлайн</label>
                <input
                  className="form-input"
                  type="datetime-local"
                  value={assignmentMeta.deadline}
                  onChange={(event) => handleMetaChange('deadline', event.target.value)}
                />
              </div>
            </div>

            <div className="hc-inline-fields">
              <div className="form-group">
                <label className="form-label">Максимальный балл</label>
                <input
                  className="form-input"
                  type="number"
                  min={1}
                  value={assignmentMeta.maxScore}
                  onChange={(event) => handleMaxScoreChange(event.target.value)}
                />
                <button type="button" className="gm-btn-surface" onClick={handleAutoMaxScore}>
                  Рассчитать по сумме вопросов
                </button>
              </div>

              <div className="form-group">
                <label className="form-label">Геймификация</label>
                <div className="gm-tab-switch">
                  <button
                    type="button"
                    className={`gm-tab-button ${assignmentMeta.gamificationEnabled ? 'active' : ''}`}
                    onClick={() => handleMetaChange('gamificationEnabled', true)}
                  >
                    Включено
                  </button>
                  <button
                    type="button"
                    className={`gm-tab-button ${!assignmentMeta.gamificationEnabled ? 'active' : ''}`}
                    onClick={() => handleMetaChange('gamificationEnabled', false)}
                  >
                    Выключено
                  </button>
                </div>
              </div>
            </div>

            <div className="gm-actions">
              <button
                type="button"
                className="gm-btn-primary"
                onClick={handleSaveDraft}
                disabled={saving}
              >
                {saving ? 'Сохранение...' : '💾 Сохранить черновик'}
              </button>
              <button
                type="button"
                className="gm-btn-surface"
                onClick={() => {
                  setAssignmentMeta({ ...initialMeta });
                  setQuestions([]);
                }}
                disabled={saving}
              >
                Очистить форму
              </button>
            </div>
          </form>
        </div>

        <div className="hc-card hc-preview-card">
          <div className="hc-section-title">Превью для студентов</div>
          <div className="hc-preview-placeholder">
            <strong>{previewTitle}</strong>
            <p>
              Здесь будет интерактивный предпросмотр, как только мы подключим рендерер вопросов и экран
              прохождения.
            </p>
          </div>
        </div>
      </div>

      <div className="hc-card">
        <div className="hc-section-title">
          <span>Вопросы ({questionCount})</span>
          <button
            type="button"
            className="hc-add-button"
            onClick={() => setShowTypeMenu((value) => !value)}
          >
            {showTypeMenu ? 'Закрыть меню типов' : '+ Добавить вопрос'}
          </button>
        </div>

        {showTypeMenu && (
          <div className="hc-type-menu">
            {QUESTION_TYPES.map((type) => (
              <button key={type.value} type="button" onClick={() => handleAddQuestion(type.value)}>
                <span>{type.label}</span>
                <span>{type.description}</span>
              </button>
            ))}
          </div>
        )}

        {questionCount === 0 ? (
          <div className="hc-empty-state">
            <strong>Пока вопросов нет.</strong>
            <span>Добавьте первый вопрос, чтобы начать собирать задание.</span>
          </div>
        ) : (
          <DragDropContext onDragEnd={handleDragEnd}>
            <Droppable droppableId="homework-questions">
              {(droppableProvided) => (
                <div
                  className="hc-question-list"
                  ref={droppableProvided.innerRef}
                  {...droppableProvided.droppableProps}
                >
                  {questions.map((question, index) => (
                    <Draggable key={question.id} draggableId={question.id} index={index}>
                      {(draggableProvided, snapshot) => (
                        <div
                          className={`hc-question-card ${snapshot.isDragging ? 'is-dragging' : ''}`}
                          ref={draggableProvided.innerRef}
                          {...draggableProvided.draggableProps}
                        >
                          <div className="hc-question-toolbar">
                            <div className="hc-question-toolbar-left">
                              <span className="hc-question-index">{index + 1}</span>
                              <span className="hc-question-type">{getQuestionLabel(question.question_type)}</span>
                            </div>
                            <div className="hc-question-actions">
                              <button
                                type="button"
                                className="gm-btn-icon"
                                {...draggableProvided.dragHandleProps}
                                aria-label="Переместить вопрос"
                              >
                                ☰
                              </button>
                              <button
                                type="button"
                                className="gm-btn-surface"
                                onClick={() => handleDuplicateQuestion(index)}
                              >
                                Дублировать
                              </button>
                              <button
                                type="button"
                                className="gm-btn-danger"
                                onClick={() => handleRemoveQuestion(index)}
                              >
                                Удалить
                              </button>
                            </div>
                          </div>

                          <div className="form-group">
                            <label className="form-label">Формулировка вопроса</label>
                            <textarea
                              className="form-textarea"
                              rows={3}
                              value={question.question_text}
                              onChange={(event) => handleQuestionTextChange(index, event.target.value)}
                              placeholder="Опишите задание для ученика"
                            />
                          </div>

                          <div className="form-group" style={{ maxWidth: '160px' }}>
                            <label className="form-label">Баллы</label>
                            <input
                              className="form-input"
                              type="number"
                              min={1}
                              value={question.points}
                              onChange={(event) => handleQuestionPointsChange(index, event.target.value)}
                            />
                          </div>

                          <QuestionEditor question={question} index={index} />
                        </div>
                      )}
                    </Draggable>
                  ))}
                  {droppableProvided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>
        )}
      </div>
    </div>
  );
};

export default HomeworkConstructor;
