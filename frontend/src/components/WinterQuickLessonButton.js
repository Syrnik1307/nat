import React, { useState, useEffect } from 'react';
import { startQuickLesson } from '../apiService';

// CSS для зимней анимации
const winterStyles = `
  @keyframes snowfall {
    0% { 
      transform: translateY(-10px) translateX(0) rotate(0deg);
      opacity: 0;
    }
    10% {
      opacity: 1;
    }
    100% { 
      transform: translateY(600px) translateX(100px) rotate(360deg);
      opacity: 0.8;
    }
  }

  @keyframes glow {
    0% {
      box-shadow: 0 25px 70px rgba(0, 0, 0, 0.5), 
                 inset 0 2px 0 rgba(255, 255, 255, 0.3), 
                 0 0 80px rgba(96, 165, 250, 0.2);
    }
    100% {
      box-shadow: 0 25px 70px rgba(0, 0, 0, 0.5), 
                 inset 0 2px 0 rgba(255, 255, 255, 0.3), 
                 0 0 120px rgba(96, 165, 250, 0.4);
    }
  }

  @keyframes winterBackground {
    0% {
      background-position: 0% 0%;
    }
    100% {
      background-position: 100% 100%;
    }
  }

  @keyframes iconFloat {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
  }

  @keyframes modalSlideIn {
    from {
      opacity: 0;
      transform: translate(-50%, -50%) scale(0.8);
    }
    to {
      opacity: 1;
      transform: translate(-50%, -50%) scale(1);
    }
  }
`;

const Snowflake = ({ delay, duration, left }) => (
  <div
    style={{
      position: 'absolute',
      top: '-10px',
      left: `${left}%`,
      width: '8px',
      height: '8px',
      background: 'white',
      borderRadius: '50%',
      opacity: 0.8,
      animation: `snowfall ${duration}s linear infinite`,
      animationDelay: `${delay}s`,
      boxShadow: '0 0 10px rgba(255, 255, 255, 0.8)',
    }}
  />
);

const PRIMARY_GRADIENT = 'linear-gradient(135deg, #0b2b65 0%, #0a1f4d 100%)';

const buttonBase = {
  fontWeight: '600',
  color: 'white',
  border: 'none',
  borderRadius: '8px',
  padding: '0.65rem 1.35rem',
  fontSize: '0.9rem',
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '0.5rem',
  boxShadow: '0 6px 16px rgba(11, 43, 101, 0.35)',
  transform: 'none',
  outline: 'none',
  transition: 'none',
};

const modalStyles = {
  container: {
    position: 'fixed',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    background: 'linear-gradient(180deg, #0f172a 0%, #1e3a8a 50%, #2563eb 100%)',
    border: '3px solid rgba(255, 255, 255, 0.4)',
    borderRadius: '20px',
    boxShadow: '0 25px 70px rgba(0, 0, 0, 0.5), inset 0 2px 0 rgba(255, 255, 255, 0.3), 0 0 100px rgba(96, 165, 250, 0.3)',
    padding: '40px',
    zIndex: 9999,
    width: '90%',
    maxWidth: '500px',
    maxHeight: '80vh',
    overflowY: 'auto',
    animation: 'modalSlideIn 0.4s ease-out',
  },
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 20, 60, 0.6)',
    backdropFilter: 'blur(4px)',
    zIndex: 9998,
  },
  innerContainer: {
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
  },
  title: {
    color: 'white',
    fontSize: '24px',
    fontWeight: '700',
    marginBottom: '10px',
    textShadow: '0 2px 10px rgba(0, 0, 0, 0.3)',
    letterSpacing: '0.5px',
  },
  subtitle: {
    color: 'rgba(255, 255, 255, 0.8)',
    fontSize: '14px',
    marginBottom: '25px',
    lineHeight: '1.6',
  },
  snowContainer: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    top: 0,
    left: 0,
    overflow: 'hidden',
    borderRadius: '17px',
    pointerEvents: 'none',
  },
  icon: {
    fontSize: '50px',
    marginBottom: '15px',
    animation: 'iconFloat 2s ease-in-out infinite',
  },
  buttons: {
    display: 'flex',
    gap: '10px',
    width: '100%',
    marginTop: '25px',
  },
  button: {
    flex: 1,
    padding: '12px 20px',
    background: 'rgba(255, 255, 255, 0.2)',
    border: '2px solid rgba(255, 255, 255, 0.3)',
    color: 'white',
    borderRadius: '8px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    fontSize: '14px',
  },
  buttonConfirm: {
    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    border: '2px solid rgba(255, 255, 255, 0.4)',
    boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)',
  },
};

const QuickLessonButton = ({ onSuccess, className = '', text = 'Быстрый урок' }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [lessonData, setLessonData] = useState(null);
  const [error, setError] = useState(null);

  // Добавляем CSS при монтировании
  useEffect(() => {
    const styleElement = document.createElement('style');
    styleElement.textContent = winterStyles;
    document.head.appendChild(styleElement);
    return () => document.head.removeChild(styleElement);
  }, []);

  const handleClick = async () => {
    if (isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await startQuickLesson();
      
      // axios возвращает данные в response.data
      if (response.data && response.data.zoom_start_url) {
        setLessonData(response.data);
        setShowModal(true);
        
        // Вызываем callback если передан
        if (onSuccess) {
          onSuccess(response.data);
        }
        
        setTimeout(() => {
          if (response.data.zoom_start_url) {
            window.open(response.data.zoom_start_url, '_blank');
          }
        }, 1500);
      } else {
        setError('Не удалось запустить урок');
        setShowModal(true);
      }
    } catch (err) {
      console.error('Quick lesson error:', err);
      const errorMessage = err.response?.data?.detail || err.response?.data?.error || err.message || 'Произошла ошибка';
      setError(errorMessage);
      setShowModal(true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleModalClose = () => {
    setShowModal(false);
    setLessonData(null);
    setError(null);
  };

  const handleConfirm = () => {
    if (lessonData?.zoom_start_url) {
      window.open(lessonData.zoom_start_url, '_blank');
      handleModalClose();
    } else {
      handleModalClose();
    }
  };

  return (
    <>
      <style>{winterStyles}</style>
      
      <button
        onClick={handleClick}
        disabled={isLoading}
        className={className}
        style={{
          ...buttonBase,
          background: PRIMARY_GRADIENT,
          opacity: isLoading ? 0.7 : 1,
          pointerEvents: isLoading ? 'none' : 'auto',
        }}
      >
        <span style={{ fontSize: '16px' }}>⚡</span>
        {isLoading ? 'Загрузка...' : text}
      </button>

      {showModal && (
        <>
          <div style={modalStyles.overlay} onClick={handleModalClose} />
          <div style={modalStyles.container}>
            <style>{winterStyles}</style>
            
            {/* Контейнер со снегом */}
            <div style={modalStyles.snowContainer}>
              {Array.from({ length: 8 }).map((_, i) => (
                <Snowflake
                  key={i}
                  delay={Math.random() * 2}
                  duration={3 + Math.random() * 2}
                  left={Math.random() * 100}
                />
              ))}
            </div>

            <div style={modalStyles.innerContainer}>
              <div style={modalStyles.icon}>
                {error ? '❌' : '❄️'}
              </div>
              
              <h2 style={modalStyles.title}>
                {error ? 'Ошибка' : 'Зимняя сказка'}
              </h2>
              
              <p style={modalStyles.subtitle}>
                {error 
                  ? error
                  : lessonData 
                    ? `Урок готов! Переходим в Zoom...`
                    : 'Снежная база для будущего леса знаний. Снег укрывает землю, готовясь к весне.'
                }
              </p>

              <div style={modalStyles.buttons}>
                <button
                  style={modalStyles.button}
                  onClick={handleModalClose}
                >
                  Отмена
                </button>
                <button
                  style={{ ...modalStyles.button, ...modalStyles.buttonConfirm }}
                  onClick={handleConfirm}
                  disabled={!lessonData && !error}
                >
                  {lessonData ? 'Присоединиться' : 'OK'}
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default QuickLessonButton;
