import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import SubjectTab from './components/SubjectTab';
import TelegramConnect from './components/TelegramConnect';
import './ParentDashboard.css';

const ParentDashboard = () => {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });

  const fetchDashboard = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get(`/api/parents/dashboard/${token}/`, {
        params: { month: selectedMonth },
      });
      setData(res.data);
      setError(null);
    } catch (err) {
      if (err.response?.status === 404) {
        setError('not_found');
      } else if (err.response?.status === 429) {
        setError('rate_limit');
      } else {
        setError('unknown');
      }
    } finally {
      setLoading(false);
    }
  }, [token, selectedMonth]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  if (loading) {
    return (
      <div className="pd-root">
        <div className="pd-container">
          <div className="pd-skeleton">
            <div className="pd-skeleton-header" />
            <div className="pd-skeleton-tabs" />
            <div className="pd-skeleton-cards" />
            <div className="pd-skeleton-list" />
          </div>
        </div>
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="pd-root">
        <div className="pd-container">
          <div className="pd-error">
            <h2>Ссылка недействительна</h2>
            <p>Доступ к дашборду отозван или ссылка неверна. Обратитесь к преподавателю.</p>
          </div>
        </div>
      </div>
    );
  }

  if (error === 'rate_limit') {
    return (
      <div className="pd-root">
        <div className="pd-container">
          <div className="pd-error">
            <h2>Слишком много запросов</h2>
            <p>Пожалуйста, подождите минуту и обновите страницу.</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="pd-root">
        <div className="pd-container">
          <div className="pd-error">
            <h2>Ошибка загрузки</h2>
            <p>Попробуйте обновить страницу.</p>
          </div>
        </div>
      </div>
    );
  }

  const subjects = data.subjects || [];

  return (
    <div className="pd-root">
      <div className="pd-container">
        {/* Header */}
        <header className="pd-header">
          <div className="pd-header-info">
            <h1 className="pd-student-name">{data.student_name}</h1>
            <span className="pd-brand">Lectio Space</span>
          </div>
        </header>

        {/* Subject Tabs */}
        {subjects.length > 0 ? (
          <>
            <div className="pd-tabs">
              {subjects.map((subj, idx) => (
                <button
                  key={subj.grant_id}
                  className={`pd-tab ${idx === activeTab ? 'pd-tab--active' : ''}`}
                  onClick={() => setActiveTab(idx)}
                >
                  {subj.subject_label}
                </button>
              ))}
            </div>

            <SubjectTab
              subject={subjects[activeTab]}
              selectedMonth={selectedMonth}
              onMonthChange={setSelectedMonth}
            />
          </>
        ) : (
          <div className="pd-empty">
            <p>Пока нет предметов. Преподаватель ещё не открыл доступ к данным.</p>
          </div>
        )}

        {/* Telegram */}
        <TelegramConnect
          connected={data.telegram_connected}
          botLink={data.telegram_bot_link}
        />

        {/* Footer */}
        <footer className="pd-footer">
          <span>Lectio Space</span>
        </footer>
      </div>
    </div>
  );
};

export default ParentDashboard;
