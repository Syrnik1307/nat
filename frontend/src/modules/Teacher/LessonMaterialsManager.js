import React, { useState, useEffect } from 'react';
import './LessonMaterialsManager.css';

/**
 * Компонент для управления учебными материалами урока (для учителя)
 * - Загрузка теории (перед уроком) и конспектов (после урока)
 * - Статистика просмотров по каждому материалу
 * - Отслеживание какие ученики просмотрели материалы
 */
function LessonMaterialsManager({ lessonId, lessonTitle, onClose }) {
    const [materials, setMaterials] = useState([]);
    const [statistics, setStatistics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    
    // Форма загрузки нового материала
    const [showUploadForm, setShowUploadForm] = useState(false);
    const [uploadForm, setUploadForm] = useState({
        material_type: 'theory',
        title: '',
        description: '',
        file_url: '',
        file_name: '',
        file_size_bytes: 0
    });
    const [uploading, setUploading] = useState(false);
    
    // Просмотр статистики конкретного материала
    const [selectedMaterial, setSelectedMaterial] = useState(null);
    const [materialViews, setMaterialViews] = useState(null);
    const [loadingViews, setLoadingViews] = useState(false);

    useEffect(() => {
        loadData();
    }, [lessonId]);

    const loadData = async () => {
        setLoading(true);
        setError(null);
        
        try {
            // Загрузить список материалов
            const materialsResponse = await fetch(`/schedule/api/lessons/${lessonId}/materials/`);
            if (!materialsResponse.ok) throw new Error('Ошибка загрузки материалов');
            const materialsData = await materialsResponse.json();
            setMaterials(materialsData.materials || []);
            
            // Загрузить общую статистику
            const statsResponse = await fetch(`/schedule/api/lessons/${lessonId}/materials/statistics/`);
            if (!statsResponse.ok) throw new Error('Ошибка загрузки статистики');
            const statsData = await statsResponse.json();
            setStatistics(statsData);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleUploadSubmit = async (e) => {
        e.preventDefault();
        
        if (!uploadForm.title || !uploadForm.file_url) {
            alert('Заполните обязательные поля: название и ссылка на файл');
            return;
        }
        
        setUploading(true);
        
        try {
            const response = await fetch(`/schedule/api/lessons/${lessonId}/materials/upload/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(uploadForm)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Ошибка загрузки материала');
            }
            
            // Сбросить форму
            setUploadForm({
                material_type: 'theory',
                title: '',
                description: '',
                file_url: '',
                file_name: '',
                file_size_bytes: 0
            });
            setShowUploadForm(false);
            
            // Перезагрузить данные
            await loadData();
            
            alert('Материал успешно загружен!');
        } catch (err) {
            alert(`Ошибка: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    const handleDeleteMaterial = async (materialId, materialTitle) => {
        if (!window.confirm(`Удалить материал "${materialTitle}"?`)) return;
        
        try {
            const response = await fetch(`/schedule/api/materials/${materialId}/delete/`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Ошибка удаления');
            }
            
            // Перезагрузить данные
            await loadData();
            
            alert('Материал удален');
        } catch (err) {
            alert(`Ошибка: ${err.message}`);
        }
    };

    const handleViewStatistics = async (material) => {
        setSelectedMaterial(material);
        setLoadingViews(true);
        
        try {
            const response = await fetch(`/schedule/api/materials/${material.id}/views/`);
            if (!response.ok) throw new Error('Ошибка загрузки статистики');
            
            const data = await response.json();
            setMaterialViews(data);
        } catch (err) {
            alert(`Ошибка: ${err.message}`);
        } finally {
            setLoadingViews(false);
        }
    };

    const closeViewsModal = () => {
        setSelectedMaterial(null);
        setMaterialViews(null);
    };

    if (loading) {
        return (
            <div className="materials-manager-overlay">
                <div className="materials-manager-modal">
                    <div className="loading">Загрузка...</div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="materials-manager-overlay">
                <div className="materials-manager-modal">
                    <div className="error-message">Ошибка: {error}</div>
                    <button onClick={onClose} className="btn-close">Закрыть</button>
                </div>
            </div>
        );
    }

    const theoryMaterials = materials.filter(m => m.material_type === 'theory');
    const notesMaterials = materials.filter(m => m.material_type === 'notes');

    return (
        <div className="materials-manager-overlay" onClick={onClose}>
            <div className="materials-manager-modal" onClick={(e) => e.stopPropagation()}>
                {/* Заголовок */}
                <div className="materials-manager-header">
                    <h2>📚 Учебные материалы</h2>
                    <p className="lesson-title">{lessonTitle}</p>
                    <button className="btn-close-icon" onClick={onClose}>×</button>
                </div>

                {/* Общая статистика */}
                {statistics && (
                    <div className="materials-statistics">
                        <div className="stat-card">
                            <div className="stat-value">{statistics.summary.total_materials}</div>
                            <div className="stat-label">Всего материалов</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{statistics.summary.theory_materials_count}</div>
                            <div className="stat-label">Теория</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{statistics.summary.notes_materials_count}</div>
                            <div className="stat-label">Конспекты</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{statistics.summary.total_views}</div>
                            <div className="stat-label">Просмотров</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{statistics.summary.total_students}</div>
                            <div className="stat-label">Учеников</div>
                        </div>
                    </div>
                )}

                {/* Кнопка добавления материала */}
                <div className="materials-actions">
                    <button 
                        className="btn-add-material"
                        onClick={() => setShowUploadForm(!showUploadForm)}
                    >
                        {showUploadForm ? '✖ Отмена' : '➕ Добавить материал'}
                    </button>
                </div>

                {/* Форма загрузки */}
                {showUploadForm && (
                    <div className="upload-form">
                        <h3>Загрузить новый материал</h3>
                        <form onSubmit={handleUploadSubmit}>
                            <div className="form-group">
                                <label>Тип материала:</label>
                                <select
                                    value={uploadForm.material_type}
                                    onChange={(e) => setUploadForm({...uploadForm, material_type: e.target.value})}
                                    required
                                >
                                    <option value="theory">📖 Теория (перед уроком)</option>
                                    <option value="notes">📝 Конспект (после урока)</option>
                                </select>
                            </div>
                            
                            <div className="form-group">
                                <label>Название:</label>
                                <input
                                    type="text"
                                    value={uploadForm.title}
                                    onChange={(e) => setUploadForm({...uploadForm, title: e.target.value})}
                                    placeholder="Например: Введение в алгебру"
                                    required
                                />
                            </div>
                            
                            <div className="form-group">
                                <label>Описание (опционально):</label>
                                <textarea
                                    value={uploadForm.description}
                                    onChange={(e) => setUploadForm({...uploadForm, description: e.target.value})}
                                    placeholder="Краткое описание содержания"
                                    rows={3}
                                />
                            </div>
                            
                            <div className="form-group">
                                <label>Ссылка на файл (Google Drive/Dropbox):</label>
                                <input
                                    type="url"
                                    value={uploadForm.file_url}
                                    onChange={(e) => setUploadForm({...uploadForm, file_url: e.target.value})}
                                    placeholder="https://drive.google.com/..."
                                    required
                                />
                                <small>Убедитесь, что файл доступен по ссылке</small>
                            </div>
                            
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Имя файла:</label>
                                    <input
                                        type="text"
                                        value={uploadForm.file_name}
                                        onChange={(e) => setUploadForm({...uploadForm, file_name: e.target.value})}
                                        placeholder="document.pdf"
                                    />
                                </div>
                                
                                <div className="form-group">
                                    <label>Размер (в байтах):</label>
                                    <input
                                        type="number"
                                        value={uploadForm.file_size_bytes}
                                        onChange={(e) => setUploadForm({...uploadForm, file_size_bytes: parseInt(e.target.value) || 0})}
                                        placeholder="1024000"
                                    />
                                </div>
                            </div>
                            
                            <div className="form-actions">
                                <button type="submit" className="btn-submit" disabled={uploading}>
                                    {uploading ? 'Загрузка...' : '✓ Загрузить'}
                                </button>
                            </div>
                        </form>
                    </div>
                )}

                {/* Список материалов */}
                <div className="materials-content">
                    {/* Теория */}
                    <div className="materials-section">
                        <h3>📖 Теория (перед уроком)</h3>
                        {theoryMaterials.length === 0 ? (
                            <p className="no-materials">Материалов нет</p>
                        ) : (
                            <div className="materials-list">
                                {theoryMaterials.map(material => (
                                    <div key={material.id} className="material-card">
                                        <div className="material-info">
                                            <h4>{material.title}</h4>
                                            {material.description && <p className="material-description">{material.description}</p>}
                                            <div className="material-meta">
                                                <span>📁 {material.file_name || 'Файл'}</span>
                                                <span>💾 {material.file_size_mb} MB</span>
                                                <span>👁️ {material.views_count} просмотров</span>
                                            </div>
                                        </div>
                                        <div className="material-actions">
                                            <button 
                                                className="btn-statistics"
                                                onClick={() => handleViewStatistics(material)}
                                            >
                                                📊 Статистика
                                            </button>
                                            <a 
                                                href={material.file_url} 
                                                target="_blank" 
                                                rel="noopener noreferrer"
                                                className="btn-view"
                                            >
                                                👁️ Открыть
                                            </a>
                                            <button
                                                className="btn-delete"
                                                onClick={() => handleDeleteMaterial(material.id, material.title)}
                                            >
                                                🗑️ Удалить
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Конспекты */}
                    <div className="materials-section">
                        <h3>📝 Конспекты (после урока)</h3>
                        {notesMaterials.length === 0 ? (
                            <p className="no-materials">Материалов нет</p>
                        ) : (
                            <div className="materials-list">
                                {notesMaterials.map(material => (
                                    <div key={material.id} className="material-card">
                                        <div className="material-info">
                                            <h4>{material.title}</h4>
                                            {material.description && <p className="material-description">{material.description}</p>}
                                            <div className="material-meta">
                                                <span>📁 {material.file_name || 'Файл'}</span>
                                                <span>💾 {material.file_size_mb} MB</span>
                                                <span>👁️ {material.views_count} просмотров</span>
                                            </div>
                                        </div>
                                        <div className="material-actions">
                                            <button 
                                                className="btn-statistics"
                                                onClick={() => handleViewStatistics(material)}
                                            >
                                                📊 Статистика
                                            </button>
                                            <a 
                                                href={material.file_url} 
                                                target="_blank" 
                                                rel="noopener noreferrer"
                                                className="btn-view"
                                            >
                                                👁️ Открыть
                                            </a>
                                            <button
                                                className="btn-delete"
                                                onClick={() => handleDeleteMaterial(material.id, material.title)}
                                            >
                                                🗑️ Удалить
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Модальное окно статистики просмотров */}
                {selectedMaterial && (
                    <div className="views-modal-overlay" onClick={closeViewsModal}>
                        <div className="views-modal" onClick={(e) => e.stopPropagation()}>
                            <div className="views-modal-header">
                                <h3>📊 Статистика просмотров</h3>
                                <p>{selectedMaterial.title}</p>
                                <button className="btn-close-icon" onClick={closeViewsModal}>×</button>
                            </div>
                            
                            {loadingViews ? (
                                <div className="loading">Загрузка...</div>
                            ) : materialViews && (
                                <div className="views-content">
                                    {/* Сводка */}
                                    <div className="views-summary">
                                        <div className="summary-item">
                                            <span className="summary-label">Всего учеников:</span>
                                            <span className="summary-value">{materialViews.statistics.total_students}</span>
                                        </div>
                                        <div className="summary-item">
                                            <span className="summary-label">Просмотрели:</span>
                                            <span className="summary-value success">{materialViews.statistics.viewed_count}</span>
                                        </div>
                                        <div className="summary-item">
                                            <span className="summary-label">Не просмотрели:</span>
                                            <span className="summary-value danger">{materialViews.statistics.not_viewed_count}</span>
                                        </div>
                                        <div className="summary-item">
                                            <span className="summary-label">% просмотра:</span>
                                            <span className="summary-value">{materialViews.statistics.view_rate}%</span>
                                        </div>
                                    </div>
                                    
                                    {/* Таблица учеников */}
                                    <div className="students-table-container">
                                        <table className="students-table">
                                            <thead>
                                                <tr>
                                                    <th>Ученик</th>
                                                    <th>Email</th>
                                                    <th>Статус</th>
                                                    <th>Дата просмотра</th>
                                                    <th>Завершен</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {materialViews.students.map(student => (
                                                    <tr key={student.student_id} className={student.has_viewed ? 'viewed' : 'not-viewed'}>
                                                        <td>{student.student_name}</td>
                                                        <td>{student.student_email}</td>
                                                        <td>
                                                            {student.has_viewed ? (
                                                                <span className="badge badge-success">✓ Просмотрел</span>
                                                            ) : (
                                                                <span className="badge badge-danger">✗ Не просмотрел</span>
                                                            )}
                                                        </td>
                                                        <td>
                                                            {student.viewed_at ? new Date(student.viewed_at).toLocaleString('ru-RU') : '-'}
                                                        </td>
                                                        <td>
                                                            {student.completed ? '✓' : '-'}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default LessonMaterialsManager;
