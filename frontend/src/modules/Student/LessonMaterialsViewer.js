import React, { useState, useEffect } from 'react';
import './LessonMaterialsViewer.css';

/**
 * Компонент для просмотра учебных материалов урока (для ученика)
 * - Красивое отображение теории (перед уроком) и конспектов (после урока)
 * - Автоматическое отслеживание просмотров
 * - Индикаторы прочитанных/непрочитанных материалов
 */
function LessonMaterialsViewer({ lessonId, lessonTitle, onClose }) {
    const [materials, setMaterials] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadMaterials();
    }, [lessonId]);

    const loadMaterials = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const response = await fetch(`/schedule/api/lessons/${lessonId}/materials/`);
            if (!response.ok) throw new Error('Ошибка загрузки материалов');
            
            const data = await response.json();
            setMaterials(data.materials || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleViewMaterial = async (material) => {
        // Открыть материал в новой вкладке
        window.open(material.file_url, '_blank');
        
        // Отследить просмотр
        try {
            await fetch(`/schedule/api/materials/${material.id}/view/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    duration_seconds: 0,
                    completed: false
                })
            });
            
            // Перезагрузить материалы для обновления статуса
            await loadMaterials();
        } catch (err) {
            console.error('Ошибка отслеживания просмотра:', err);
        }
    };

    if (loading) {
        return (
            <div className="materials-viewer-overlay">
                <div className="materials-viewer-modal">
                    <div className="loading">Загрузка материалов...</div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="materials-viewer-overlay">
                <div className="materials-viewer-modal">
                    <div className="error-message">Ошибка: {error}</div>
                    <button onClick={onClose} className="btn-close">Закрыть</button>
                </div>
            </div>
        );
    }

    const theoryMaterials = materials.filter(m => m.material_type === 'theory');
    const notesMaterials = materials.filter(m => m.material_type === 'notes');

    return (
        <div className="materials-viewer-overlay" onClick={onClose}>
            <div className="materials-viewer-modal" onClick={(e) => e.stopPropagation()}>
                {/* Заголовок */}
                <div className="materials-viewer-header">
                    <h2>📚 Учебные материалы</h2>
                    <p className="lesson-title">{lessonTitle}</p>
                    <button className="btn-close-icon" onClick={onClose}>×</button>
                </div>

                {/* Контент */}
                <div className="materials-viewer-content">
                    {materials.length === 0 ? (
                        <div className="no-materials-message">
                            <div className="icon">📭</div>
                            <h3>Материалов пока нет</h3>
                            <p>Преподаватель ещё не загрузил материалы к этому уроку</p>
                        </div>
                    ) : (
                        <>
                            {/* Теория (перед уроком) */}
                            {theoryMaterials.length > 0 && (
                                <div className="materials-section theory-section">
                                    <div className="section-header">
                                        <div className="section-icon">📖</div>
                                        <div className="section-info">
                                            <h3>Теория для подготовки</h3>
                                            <p>Прочитайте эти материалы перед уроком</p>
                                        </div>
                                    </div>
                                    
                                    <div className="materials-grid">
                                        {theoryMaterials.map(material => (
                                            <div 
                                                key={material.id} 
                                                className={`material-card ${material.is_viewed ? 'viewed' : 'not-viewed'}`}
                                            >
                                                {material.is_viewed && (
                                                    <div className="viewed-badge">✓ Прочитано</div>
                                                )}
                                                {!material.is_viewed && (
                                                    <div className="new-badge">Новое</div>
                                                )}
                                                
                                                <div className="material-card-content">
                                                    <h4>{material.title}</h4>
                                                    
                                                    {material.description && (
                                                        <p className="material-description">{material.description}</p>
                                                    )}
                                                    
                                                    <div className="material-meta">
                                                        <span className="meta-item">
                                                            📁 {material.file_name || 'Документ'}
                                                        </span>
                                                        <span className="meta-item">
                                                            💾 {material.file_size_mb} MB
                                                        </span>
                                                        <span className="meta-item">
                                                            👁️ {material.views_count} просмотров
                                                        </span>
                                                    </div>
                                                    
                                                    <button 
                                                        className="btn-open-material"
                                                        onClick={() => handleViewMaterial(material)}
                                                    >
                                                        {material.is_viewed ? '📖 Открыть снова' : '📖 Читать'}
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Конспекты (после урока) */}
                            {notesMaterials.length > 0 && (
                                <div className="materials-section notes-section">
                                    <div className="section-header">
                                        <div className="section-icon">📝</div>
                                        <div className="section-info">
                                            <h3>Конспекты урока</h3>
                                            <p>Материалы для повторения пройденного</p>
                                        </div>
                                    </div>
                                    
                                    <div className="materials-grid">
                                        {notesMaterials.map(material => (
                                            <div 
                                                key={material.id} 
                                                className={`material-card ${material.is_viewed ? 'viewed' : 'not-viewed'}`}
                                            >
                                                {material.is_viewed && (
                                                    <div className="viewed-badge">✓ Прочитано</div>
                                                )}
                                                {!material.is_viewed && (
                                                    <div className="new-badge">Новое</div>
                                                )}
                                                
                                                <div className="material-card-content">
                                                    <h4>{material.title}</h4>
                                                    
                                                    {material.description && (
                                                        <p className="material-description">{material.description}</p>
                                                    )}
                                                    
                                                    <div className="material-meta">
                                                        <span className="meta-item">
                                                            📁 {material.file_name || 'Документ'}
                                                        </span>
                                                        <span className="meta-item">
                                                            💾 {material.file_size_mb} MB
                                                        </span>
                                                        <span className="meta-item">
                                                            👁️ {material.views_count} просмотров
                                                        </span>
                                                    </div>
                                                    
                                                    <button 
                                                        className="btn-open-material"
                                                        onClick={() => handleViewMaterial(material)}
                                                    >
                                                        {material.is_viewed ? '📝 Открыть снова' : '📝 Читать'}
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

export default LessonMaterialsViewer;
