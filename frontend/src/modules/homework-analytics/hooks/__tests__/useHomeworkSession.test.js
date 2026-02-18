// Minimal tests for useHomeworkSession with injected mock service
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!doctype html><html><body></body></html>');
global.window = dom.window;
global.document = dom.window.document;
global.navigator = { userAgent: 'node.js' };

const { renderHook, act, waitFor } = require('@testing-library/react');

const mockHomework = {
  id: 1,
  questions: [
    { id: 'q1', question_type: 'TEXT', question_text: 'Текст?', config: {} },
    { id: 'q2', question_type: 'SINGLE_CHOICE', question_text: 'Выбери?', config: { options: [{ id: 'a', text: 'A' }, { id: 'b', text: 'B' }] } },
    { id: 'q3', question_type: 'LISTENING', question_text: 'Аудио?', config: { subQuestions: [{ id: 'sq1', text: 'Что услышал?' }], audioUrl: 'audio.mp3' } },
  ],
};

const mockService = {
  fetchHomework: jest.fn(),
  fetchSubmissions: jest.fn(),
  startSubmission: jest.fn(),
  saveProgress: jest.fn(),
  submit: jest.fn(),
};

const hookModule = require('../useHomeworkSession');
const useHomeworkSession = hookModule.default || hookModule;

describe('useHomeworkSession hook', () => {
  beforeEach(() => {
    mockService.fetchHomework.mockResolvedValue({ data: mockHomework });
    mockService.fetchSubmissions.mockResolvedValue({ data: { results: [] } });
    mockService.startSubmission.mockResolvedValue({ data: { id: 123, status: 'in_progress' } });
    mockService.saveProgress.mockResolvedValue(true);
    mockService.submit.mockResolvedValue({ data: { id: 123, status: 'submitted', score: 100, percent: 100 } });
  });

  it('loads homework and initializes answers', async () => {
    const { result } = renderHook(() => useHomeworkSession(1, mockService));
    await waitFor(() => expect(mockService.fetchHomework).toHaveBeenCalled());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await waitFor(() => expect(result.current.answers).toHaveProperty('q1'));
    expect(result.current.answers.q1).toBeDefined();
  });

  it('records answers and saves progress', async () => {
    const { result } = renderHook(() => useHomeworkSession(1, mockService));
    await waitFor(() => expect(result.current.loading).toBe(false));
    await waitFor(() => expect(result.current.answers).toHaveProperty('q1'));
    act(() => result.current.recordAnswer('q1', 'Ответ'));
    await waitFor(() => expect(result.current.answers.q1).toBe('Ответ'));
    await act(async () => { await result.current.saveProgress(); });
    expect(mockService.saveProgress).toHaveBeenCalled();
  });

  it('submits homework and returns result', async () => {
    const { result } = renderHook(() => useHomeworkSession(1, mockService));
    await waitFor(() => expect(result.current.loading).toBe(false));
    await waitFor(() => expect(result.current.submission).toBeTruthy());
    await act(async () => { await result.current.submitHomework(); });
    expect(mockService.submit).toHaveBeenCalled();
  });
});
