/**
 * ExamPage.js — главная страница модуля экзаменов.
 *
 * Учитель: управление шаблонами, банком заданий, вариантами.
 * Ученик: список назначенных экзаменов, результаты.
 */

import React, { useState, useCallback } from 'react';
import { useAuth } from '../../../auth';
import { Badge } from '../../../shared/components';
import BlueprintList from './BlueprintList';
import BlueprintEditor from './BlueprintEditor';
import TaskBank from './TaskBank';
import VariantBuilder from './VariantBuilder';
import ExamResults from './ExamResults';
import './ExamPage.css';

const TABS = {
  teacher: [
    { id: 'blueprints', label: 'Шаблоны экзаменов' },
    { id: 'bank', label: 'Банк заданий' },
    { id: 'variants', label: 'Варианты' },
    { id: 'results', label: 'Результаты' },
  ],
  student: [
    { id: 'my-exams', label: 'Мои экзамены' },
    { id: 'results', label: 'Результаты' },
  ],
};

export default function ExamPage() {
  const { user } = useAuth();
  const isTeacher = user?.role === 'teacher' || user?.role === 'admin';
  const tabs = isTeacher ? TABS.teacher : TABS.student;

  const [activeTab, setActiveTab] = useState(tabs[0].id);
  const [selectedBlueprintId, setSelectedBlueprintId] = useState(null);
  const [editingBlueprintId, setEditingBlueprintId] = useState(null);

  const handleSelectBlueprint = useCallback((id) => {
    setSelectedBlueprintId(id);
  }, []);

  const handleEditBlueprint = useCallback((id) => {
    setEditingBlueprintId(id);
  }, []);

  const handleCloseEditor = useCallback(() => {
    setEditingBlueprintId(null);
  }, []);

  const handleCreateBlueprint = useCallback(() => {
    setEditingBlueprintId('new');
  }, []);

  const renderContent = () => {
    if (editingBlueprintId !== null) {
      return (
        <BlueprintEditor
          blueprintId={editingBlueprintId === 'new' ? null : editingBlueprintId}
          onClose={handleCloseEditor}
          onSaved={(bp) => {
            setSelectedBlueprintId(bp.id);
            setEditingBlueprintId(null);
          }}
        />
      );
    }

    switch (activeTab) {
      case 'blueprints':
        return (
          <BlueprintList
            selectedId={selectedBlueprintId}
            onSelect={handleSelectBlueprint}
            onEdit={handleEditBlueprint}
            onCreate={handleCreateBlueprint}
          />
        );
      case 'bank':
        return (
          <TaskBank
            blueprintId={selectedBlueprintId}
            onSelectBlueprint={handleSelectBlueprint}
          />
        );
      case 'variants':
        return (
          <VariantBuilder
            blueprintId={selectedBlueprintId}
            onSelectBlueprint={handleSelectBlueprint}
          />
        );
      case 'results':
        return <ExamResults blueprintId={selectedBlueprintId} isTeacher={isTeacher} />;
      case 'my-exams':
        return <ExamResults blueprintId={null} isTeacher={false} />;
      default:
        return null;
    }
  };

  return (
    <div className="exam-page animate-page-enter">
      <div className="exam-header">
        <h1 className="exam-title">Симуляция экзаменов</h1>
        {isTeacher && selectedBlueprintId && (
          <Badge variant="primary">Шаблон #{selectedBlueprintId}</Badge>
        )}
      </div>

      <div className="exam-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`exam-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="exam-content animate-content">{renderContent()}</div>
    </div>
  );
}
