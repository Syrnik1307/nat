import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getSubmissions } from '../../apiService';
import Button from '../../shared/components/Button';
import '../GroupDetailModal.css';

const HomeworkTab = ({ groupId }) => {
  const navigate = useNavigate();
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadSubmissions();
  }, [groupId]);

  const loadSubmissions = async () => {
    if (!groupId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await getSubmissions({ 
        homework__lesson__group: groupId,
        status: 'submitted' // только непроверенные
      });
      const data = Array.isArray(response.data) ? response.data : response.data.results || [];
      setSubmissions(data);
    } catch (err) {
      console.error('Ошибка загрузки ДЗ:', err);
      setError('Не удалось загрузить домашние задания');
    } finally {
      setLoading(false);
    }
  };

  const handleViewAll = () => {
    navigate(`/homework/graded?group=${groupId}`);
  };

  const handleReview = (submissionId) => {
    navigate(`/submissions/${submissionId}/review`);
  };

  if (loading) {
    return (
      <div className="tab-content">
        <div className="placeholder">Загрузка домашних заданий...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="tab-content">
        <div className="placeholder" style={{ color: '#ef4444' }}>{error}</div>
      </div>
    );
  }

  if (submissions.length === 0) {
    return (
      <div className="tab-content">
        <div className="placeholder">
          ✅ Нет непроверенных домашних заданий
        </div>
        <div style={{ marginTop: '1rem', textAlign: 'center' }}>
          <Button variant="secondary" onClick={handleViewAll}>
            Посмотреть все ДЗ группы
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="tab-content">
      <div className="homework-header" style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1rem',
        paddingBottom: '0.75rem',
        borderBottom: '2px solid #e2e8f0'
      }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>
          Непроверенные ДЗ ({submissions.length})
        </h3>
        <Button variant="secondary" onClick={handleViewAll} style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
          Посмотреть все
        </Button>
      </div>

      <div className="submissions-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {submissions.map(submission => (
          <div
            key={submission.id}
            className="submission-card"
            style={{
              padding: '1rem',
              backgroundColor: '#f8fafc',
              borderRadius: '12px',
              border: '1px solid #e2e8f0',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#f1f5f9';
              e.currentTarget.style.borderColor = '#cbd5e1';
              e.currentTarget.style.transform = 'translateY(-2px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#f8fafc';
              e.currentTarget.style.borderColor = '#e2e8f0';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
            onClick={() => handleReview(submission.id)}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
              <div style={{ flex: 1 }}>
                <div style={{ 
                  fontSize: '0.95rem', 
                  fontWeight: 600, 
                  color: '#1e293b',
                  marginBottom: '0.25rem' 
                }}>
                  {submission.homework_title || 'ДЗ без названия'}
                </div>
                <div style={{ 
                  fontSize: '0.875rem', 
                  color: '#64748b',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  <span>{submission.student_name || 'Ученик'}</span>
                  {submission.submitted_at && (
                    <span>- {new Date(submission.submitted_at).toLocaleDateString('ru-RU')}</span>
                  )}
                </div>
              </div>
              <div style={{
                padding: '0.35rem 0.75rem',
                backgroundColor: '#fef3c7',
                color: '#92400e',
                borderRadius: '999px',
                fontSize: '0.75rem',
                fontWeight: 700,
                whiteSpace: 'nowrap'
              }}>
                На проверке
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HomeworkTab;
