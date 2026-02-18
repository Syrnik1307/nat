import React, { useState, useEffect } from 'react';
import { getLessonAnalytics } from '../../apiService';
import LessonAnalytics from '../../components/LessonAnalytics';
import { Modal } from '../../shared/components'; // Assuming you have a Modal component

const LessonAnalyticsModal = ({ lessonId, isOpen, onClose }) => {
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen && lessonId) {
            setLoading(true);
            setError(null);
            getLessonAnalytics(lessonId)
                .then(response => {
                    setAnalytics(response.data);
                    setLoading(false);
                })
                .catch(err => {
                    console.error("Failed to load analytics", err);
                    if (err.response && err.response.status === 404) {
                         setError("Аналитика еще не готова или транскрипт отсутствует.");
                    } else {
                        setError("Ошибка загрузки данных.");
                    }
                    setLoading(false);
                });
        }
    }, [isOpen, lessonId]);

    if (!isOpen) return null;

    return (
        <Modal 
            isOpen={isOpen} 
            onClose={onClose} 
            title="Аналитика урока"
            size="lg" // Adjust size if your modal supports it
        >
            <div className="p-4">
                {loading && <div className="text-center py-8">Загрузка аналитики...</div>}
                
                {error && <div className="bg-yellow-100 p-4 rounded text-yellow-800 text-center">{error}</div>}
                
                {!loading && !error && analytics && (
                    <LessonAnalytics analytics={analytics} />
                )}
            </div>
            <div className="flex justify-end p-4 border-t">
                <button 
                    onClick={onClose}
                    className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
                >
                    Закрыть
                </button>
            </div>
        </Modal>
    );
};

export default LessonAnalyticsModal;
