import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button, Notification } from '../shared/components';
import './AuthPage.css'; // используем те же стили

const EmailVerificationPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const email = location.state?.email || '';
  
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [timer, setTimer] = useState(60);
  const [canResend, setCanResend] = useState(false);
  const [notification, setNotification] = useState({
    isOpen: false,
    type: 'info',
    title: '',
    message: '',
  });

  useEffect(() => {
    if (!email) {
      navigate('/auth-new');
    }
  }, [email, navigate]);

  useEffect(() => {
    let interval;
    if (timer > 0) {
      interval = setInterval(() => {
        setTimer(prev => {
          if (prev <= 1) {
            setCanResend(true);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [timer]);

  const showNotification = (type, title, message) => {
    setNotification({ isOpen: true, type, title, message });
  };

  const closeNotification = () => {
    setNotification({ ...notification, isOpen: false });
  };

  const handleCodeChange = (index, value) => {
    if (!/^\d*$/.test(value)) return;
    
    const newCode = [...code];
    newCode[index] = value.slice(-1);
    setCode(newCode);

    // Автоматический переход на следующее поле
    if (value && index < 5) {
      const nextInput = document.getElementById(`code-${index + 1}`);
      if (nextInput) nextInput.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      const prevInput = document.getElementById(`code-${index - 1}`);
      if (prevInput) prevInput.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    const newCode = pastedData.split('').concat(Array(6).fill('')).slice(0, 6);
    setCode(newCode);
    
    const lastFilledIndex = pastedData.length - 1;
    const nextInput = document.getElementById(`code-${Math.min(lastFilledIndex + 1, 5)}`);
    if (nextInput) nextInput.focus();
  };

  const handleVerify = async () => {
    const verificationCode = code.join('');
    
    if (verificationCode.length !== 6) {
      showNotification('error', 'Ошибка', 'Введите полный 6-значный код');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/accounts/api/email/verify-code/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          code: verificationCode
        })
      });

      const data = await response.json();

      if (response.ok) {
        showNotification('success', 'Email подтвержден!', 'Теперь вы можете войти в систему');
        setTimeout(() => {
          navigate('/auth-new', { state: { mode: 'login', email: email } });
        }, 2000);
      } else {
        showNotification('error', 'Ошибка верификации', data.message || 'Неверный код');
      }
    } catch (err) {
      console.error('Ошибка верификации:', err);
      showNotification('error', 'Ошибка', 'Не удалось проверить код. Попробуйте еще раз.');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (!canResend) return;

    setResending(true);
    try {
      const response = await fetch('http://localhost:8000/accounts/api/email/send-verification/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email })
      });

      const data = await response.json();

      if (response.ok) {
        showNotification('success', 'Код отправлен', `Новый код отправлен на ${email}`);
        setTimer(60);
        setCanResend(false);
        setCode(['', '', '', '', '', '']);
        document.getElementById('code-0')?.focus();
      } else {
        showNotification('error', 'Ошибка', data.message || 'Не удалось отправить код');
      }
    } catch (err) {
      console.error('Ошибка отправки кода:', err);
      showNotification('error', 'Ошибка', 'Не удалось отправить код. Попробуйте позже.');
    } finally {
      setResending(false);
    }
  };

  const containerStyle = {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #312e81 0%, #9333ea 50%, #f472b6 100%)',
    padding: 'var(--space-xxl)',
    position: 'relative',
    overflow: 'hidden',
  };

  const blobBaseStyle = {
    position: 'absolute',
    width: '420px',
    height: '420px',
    background: 'rgba(255, 255, 255, 0.08)',
    filter: 'blur(90px)',
    borderRadius: '50%',
    zIndex: 0,
  };

  const backgroundBlobs = [
    { top: '-15%', left: '-5%' },
    { bottom: '-20%', right: '-10%' },
    { top: '30%', right: '20%', width: '320px', height: '320px' },
  ];

  const cardStyle = {
    background: 'rgba(255, 255, 255, 0.92)',
    borderRadius: '36px',
    boxShadow: '0 35px 80px -30px rgba(15, 23, 42, 0.45)',
    padding: 'var(--space-xxl)',
    maxWidth: '520px',
    width: '100%',
    textAlign: 'center',
    position: 'relative',
    zIndex: 1,
    backdropFilter: 'blur(18px)',
  };

  const iconStyle = {
    fontSize: '4rem',
    marginBottom: 'var(--space-lg)',
  };

  const titleStyle = {
    fontSize: '1.75rem',
    fontWeight: 600,
    color: 'var(--gray-900)',
    marginBottom: 'var(--space-md)',
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
    letterSpacing: '-0.02em',
  };

  const subtitleStyle = {
    fontSize: '0.875rem',
    color: 'var(--gray-600)',
    marginBottom: 'var(--space-xl)',
    lineHeight: 1.5,
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  };

  const emailHighlightStyle = {
    color: 'var(--accent-500)',
    fontWeight: 600,
  };

  const codeContainerStyle = {
    display: 'flex',
    gap: 'var(--space-md)',
    justifyContent: 'center',
    marginBottom: 'var(--space-xl)',
  };

  const codeInputStyle = {
    width: '64px',
    height: '64px',
    fontSize: '2rem',
    fontWeight: 700,
    textAlign: 'center',
    border: '1px solid rgba(148, 163, 184, 0.5)',
    borderRadius: '24px',
    outline: 'none',
    transition: 'all var(--transition-base)',
    background: 'rgba(255, 255, 255, 0.9)',
    boxShadow: '0 20px 40px -20px rgba(79, 70, 229, 0.5)',
  };

  const resendStyle = {
    marginTop: 'var(--space-lg)',
    fontSize: '0.8125rem',
    color: 'var(--gray-600)',
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  };

  const backLinkStyle = {
    marginTop: 'var(--space-lg)',
    fontSize: '0.8125rem',
    color: 'var(--gray-600)',
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  };

  const primaryButtonStyle = {
    width: 'auto',
    minWidth: '180px',
    margin: '0 auto',
    display: 'block',
    background: 'linear-gradient(120deg, #7c5dfa, #7c3aed, #ec4899)',
    boxShadow: '0 10px 25px rgba(124, 93, 250, 0.25)',
    border: 'none',
    padding: '12px 32px',
    fontSize: '0.9375rem',
    fontWeight: 500,
    borderRadius: '24px',
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
    color: 'white',
  };

  const ghostButtonStyle = {
    padding: 0,
    minHeight: 'auto',
    opacity: canResend ? 1 : 0.5,
    cursor: canResend ? 'pointer' : 'not-allowed',
    background: 'none',
    boxShadow: 'none',
    fontSize: '0.8125rem',
    color: 'var(--accent-500)',
    fontWeight: 500,
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  };

  const linkButtonStyle = {
    padding: 0,
    minHeight: 'auto',
    background: 'none',
    boxShadow: 'none',
    fontSize: '0.8125rem',
    color: 'var(--accent-500)',
    fontWeight: 500,
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
  };

  return (
    <>
      <Notification
        isOpen={notification.isOpen}
        onClose={closeNotification}
        type={notification.type}
        title={notification.title}
        message={notification.message}
      />
      
      <div style={containerStyle}>
        {backgroundBlobs.map((style, index) => (
          <div key={index} style={{ ...blobBaseStyle, ...style }} />
        ))}
        <div style={cardStyle}>
          <div style={iconStyle}>📧</div>
          <h1 style={titleStyle}>Подтверждение Email</h1>
          <p style={subtitleStyle}>
            Мы отправили 6-значный код на<br />
            <span style={emailHighlightStyle}>{email}</span>
          </p>

          <div style={codeContainerStyle} onPaste={handlePaste}>
            {code.map((digit, index) => (
              <input
                key={index}
                id={`code-${index}`}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleCodeChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                style={{
                  ...codeInputStyle,
                  borderColor: digit ? 'var(--accent-500)' : 'var(--gray-300)',
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'var(--accent-500)';
                  e.target.style.boxShadow = '0 0 0 3px rgba(102, 126, 234, 0.1)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = digit ? 'var(--accent-500)' : 'var(--gray-300)';
                  e.target.style.boxShadow = 'none';
                }}
              />
            ))}
          </div>

          <Button
            type="button"
            variant="primary"
            size="large"
            loading={loading}
            disabled={loading || code.some(d => !d)}
            onClick={handleVerify}
            style={primaryButtonStyle}
          >
            {loading ? 'Проверка...' : 'Подтвердить'}
          </Button>

          <div style={resendStyle}>
            Не получили код?{' '}
            <Button
              type="button"
              variant="text"
              size="small"
              onClick={handleResend}
              disabled={!canResend || resending}
              style={ghostButtonStyle}
            >
              {resending ? 'Отправка...' : canResend ? 'Отправить снова' : `Подождите ${timer}с`}
            </Button>
          </div>

          <div style={backLinkStyle}>
            <Button
              type="button"
              variant="text"
              size="small"
              onClick={() => navigate('/auth-new')}
              style={linkButtonStyle}
            >
              ← Вернуться ко входу
            </Button>
          </div>
        </div>
      </div>
    </>
  );
};

export default EmailVerificationPage;
