import React, { useState, useEffect, useCallback, useRef } from 'react';
import './StudentMaterialsPage.css';
import api, { withScheduleApiBase } from '../../apiService';
import { ToastContainer, Modal } from '../../shared/components';
import { getCached } from '../../utils/dataCache';
import DOMPurify from 'dompurify';

/**
 * StudentMaterialsPage - Страница материалов для ученика
 * Miro доски и конспекты от учителя
 */
function StudentMaterialsPage() {
  const [activeTab, setActiveTab] = useState('miro');
  
  // Данные
  const [materials, setMaterials] = useState({ miro: [], notes: [] });

  // Notes preview
  const [selectedNote, setSelectedNote] = useState(null);
  
  // UI State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const initialLoadDone = useRef(false);

  // Toasts
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, ...toast }]);
    setTimeout(() => removeToast(id), 5000);
    return id;
  }, [removeToast]);

  useEffect(() => {
    loadMaterials(!initialLoadDone.current);
    initialLoadDone.current = true;
  }, []);

  const loadMaterials = async (useCache = true) => {
    const cacheTTL = 30000; // 30 секунд
    
    if (useCache) {
      try {
        const cachedMaterials = await getCached('student:materials', async () => {
          const response = await api.get('lesson-materials/student_materials/', withScheduleApiBase());
          if (response.data.materials) {
            const m = response.data.materials;
            return {
              miro: m.miro || [],
              notes: m.notes || [],
            };
          }
          return { miro: [], notes: [] };
        }, cacheTTL);
        
        setMaterials(cachedMaterials);
        setLoading(false);
        return;
      } catch (err) {
        console.error('Error loading cached materials:', err);
      }
    }
    
    setLoading(true);
    try {
      const response = await api.get('lesson-materials/student_materials/', withScheduleApiBase());
      if (response.data.materials) {
        const m = response.data.materials;
        setMaterials({
          miro: m.miro || [],
          notes: m.notes || [],
        });
      }
    } catch (err) {
      console.error('Error loading materials:', err);
      setError('Не удалось загрузить материалы');
      addToast({ type: 'error', title: 'Ошибка', message: 'Не удалось загрузить материалы' });
    } finally {
      setLoading(false);
    }
  };

  const handleViewMaterial = async (material) => {
    const isMiro = material.material_type === 'miro';
    if (isMiro) {
      const url = material.miro_board_url || material.miro_embed_url;
      if (url) window.open(url, '_blank');
      try {
        await api.post(`lesson-materials/${material.id}/view/`, {}, withScheduleApiBase());
      } catch (err) {
        console.error('Error tracking view:', err);
      }
      return;
    }

    // Notes: открываем внутри модалки
    setSelectedNote(material);
    try {
      await api.post(`lesson-materials/${material.id}/view/`, {}, withScheduleApiBase());
    } catch (err) {
      console.error('Error tracking view:', err);
    }
  };

  const stripHtml = (html) => {
    if (!html) return '';
    const div = document.createElement('div');
    div.innerHTML = html;
    return (div.textContent || div.innerText || '').trim();
  };

  const getFilteredMaterials = (list) => {
    if (!searchTerm) return list;
    const term = searchTerm.toLowerCase();
    return list.filter(m => 
      m.title?.toLowerCase().includes(term) ||
      m.description?.toLowerCase().includes(term) ||
      m.teacher_name?.toLowerCase().includes(term) ||
      m.group_name?.toLowerCase().includes(term)
    );
  };

  const tabItems = [
    { key: 'miro', label: 'Miro', count: materials.miro?.length || 0 },
    { key: 'notes', label: 'Конспекты', count: materials.notes?.length || 0 },
  ];

  const renderMaterialCard = (material) => {
    const isMiro = material.material_type === 'miro';
    const url = material.miro_board_url || material.miro_embed_url;
    
    return (
      <div key={material.id} className="sm-material-card">
        {isMiro && material.miro_thumbnail_url && (
          <div className="sm-card-thumbnail">
            <img src={material.miro_thumbnail_url} alt="" />
          </div>
        )}
        
        <div className="sm-card-content">
          <h3 className="sm-card-title">{material.title}</h3>
          
          {material.description && (
            <p className="sm-card-description">{material.description}</p>
          )}
          
          <div className="sm-card-meta">
            {material.teacher_name && (
              <span className="sm-meta-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
                {material.teacher_name}
              </span>
            )}
            {material.group_name && (
              <span className="sm-meta-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
                {material.group_name}
              </span>
            )}
            {material.uploaded_at && (
              <span className="sm-meta-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                  <line x1="16" y1="2" x2="16" y2="6"/>
                  <line x1="8" y1="2" x2="8" y2="6"/>
                  <line x1="3" y1="10" x2="21" y2="10"/>
                </svg>
                {new Date(material.uploaded_at).toLocaleDateString('ru-RU')}
              </span>
            )}
          </div>

          {!isMiro && material.content && (
            <div className="sm-note-excerpt">
              {stripHtml(material.content).substring(0, 220)}
              {stripHtml(material.content).length > 220 ? '…' : ''}
            </div>
          )}
          
          <button 
            className="sm-open-btn"
            onClick={() => handleViewMaterial(material)}
            disabled={isMiro && !url}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
              <polyline points="15 3 21 3 21 9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
            Открыть
          </button>
        </div>
      </div>
    );
  };

  const renderEmptyState = () => (
    <div className="sm-empty-state">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="12" y1="18" x2="12" y2="12"/>
        <line x1="9" y1="15" x2="15" y2="15"/>
      </svg>
      <h3>Материалов пока нет</h3>
      <p>Здесь будут появляться материалы, которые вам выгружают преподаватели</p>
    </div>
  );

  const currentMaterials = getFilteredMaterials(materials[activeTab] || []);

  if (loading) {
    return (
      <div className="sm-page">
        <div className="sm-container">
          <div className="sm-loading">
            <div className="sm-spinner" />
            <span>Загрузка материалов...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="sm-page">
        <div className="sm-container">
          <div className="sm-error">
            <p>{error}</p>
            <button onClick={loadMaterials} className="sm-retry-btn">Попробовать снова</button>
          </div>
        </div>
      </div>
    );
  }

  const totalCount = (materials.miro?.length || 0) + 
                     (materials.notes?.length || 0);

  return (
    <div className="sm-page">
      <div className="sm-container">
        {/* Header */}
        <div className="sm-header">
          <div className="sm-header-left">
            <h1 className="sm-title">Учебные материалы</h1>
            <p className="sm-subtitle">
              {totalCount > 0 
                ? `${totalCount} материал${totalCount === 1 ? '' : totalCount < 5 ? 'а' : 'ов'} от преподавателей`
                : 'Материалы от преподавателей'}
            </p>
          </div>
          
          <div className="sm-header-right">
            <div className="sm-search">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.35-4.35"/>
              </svg>
              <input
                type="text"
                placeholder="Поиск материалов..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="sm-tabs">
          {tabItems.map(tab => (
            <button
              key={tab.key}
              className={`sm-tab ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
              {tab.count > 0 && <span className="sm-tab-count">{tab.count}</span>}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="sm-content">
          {currentMaterials.length === 0 ? (
            renderEmptyState()
          ) : (
            <div className="sm-materials-grid">
              {currentMaterials.map(material => renderMaterialCard(material))}
            </div>
          )}
        </div>
      </div>

      <ToastContainer toasts={toasts} onRemove={removeToast} />

      {selectedNote && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedNote(null)}
          title={selectedNote.title}
          size="large"
        >
          {selectedNote.description && (
            <div className="sm-note-description">{selectedNote.description}</div>
          )}
          <div
            className="sm-note-content"
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(selectedNote.content || '') }}
          />
        </Modal>
      )}
    </div>
  );
}

export default StudentMaterialsPage;
