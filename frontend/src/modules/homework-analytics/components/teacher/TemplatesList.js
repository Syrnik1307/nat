import React, { useState, useEffect, useCallback } from 'react';
import { getHomeworkTemplates, deleteHomework } from '../../../../apiService';
import { Button, Modal } from '../../../../shared/components';
import { useNotifications } from '../../../../shared/context/NotificationContext';
import InstantiateTemplateModal from './InstantiateTemplateModal';
import './TemplatesList.css';

/**
 * Список шаблонов домашних заданий учителя.
 * Позволяет просматривать, удалять и создавать ДЗ из шаблона.
 */
const TemplatesList = () => {
  const { toast, showConfirm } = useNotifications();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [showInstantiateModal, setShowInstantiateModal] = useState(false);

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getHomeworkTemplates();
      const data = response.data?.results || response.data || [];
      setTemplates(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load templates:', err);
      setError('Не удалось загрузить шаблоны');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const handleDelete = async (template) => {
    const confirmed = await showConfirm({
      title: 'Удалить шаблон?',
      message: `Шаблон "${template.title}" будет удалён. Уже созданные из него ДЗ останутся без изменений.`,
      variant: 'danger',
      confirmText: 'Удалить',
      cancelText: 'Отмена'
    });
    if (!confirmed) return;

    try {
      await deleteHomework(template.id);
      toast.success('Шаблон удалён');
      loadTemplates();
    } catch (err) {
      toast.error('Ошибка удаления шаблона');
    }
  };

  const handleInstantiate = (template) => {
    setSelectedTemplate(template);
    setShowInstantiateModal(true);
  };

  const handleInstantiateSuccess = () => {
    setShowInstantiateModal(false);
    setSelectedTemplate(null);
    toast.success('Домашнее задание создано из шаблона');
  };

  if (loading) {
    return (
      <div className="templates-list-loading">
        <div className="templates-spinner" />
        <span>Загрузка шаблонов...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="templates-list-error">
        <p>{error}</p>
        <Button variant="secondary" onClick={loadTemplates}>Повторить</Button>
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <div className="templates-list-empty">
        <h3>Нет сохранённых шаблонов</h3>
        <p>Создайте домашнее задание и сохраните его как шаблон для повторного использования</p>
      </div>
    );
  }

  return (
    <div className="templates-list">
      <div className="templates-grid">
        {templates.map((template) => (
          <div key={template.id} className="template-card">
            <div className="template-card-header">
              <h3 className="template-title">{template.title}</h3>
              <span className="template-badge">Шаблон</span>
            </div>
            
            <p className="template-description">
              {template.description || 'Без описания'}
            </p>
            
            <div className="template-meta">
              <span className="template-questions">
                📝 {template.questions_count || 0} вопросов
              </span>
              <span className="template-score">
                🎯 {template.max_score || 100} баллов
              </span>
            </div>
            
            <div className="template-actions">
              <Button 
                variant="primary" 
                onClick={() => handleInstantiate(template)}
              >
                Назначить
              </Button>
              <Button 
                variant="danger-outline" 
                onClick={() => handleDelete(template)}
              >
                Удалить
              </Button>
            </div>
          </div>
        ))}
      </div>

      {showInstantiateModal && selectedTemplate && (
        <InstantiateTemplateModal
          template={selectedTemplate}
          onClose={() => {
            setShowInstantiateModal(false);
            setSelectedTemplate(null);
          }}
          onSuccess={handleInstantiateSuccess}
        />
      )}
    </div>
  );
};

export default TemplatesList;
