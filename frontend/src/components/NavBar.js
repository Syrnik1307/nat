import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth';
import './Navbar.css';

const NavBar = () => {
  const { accessTokenValid, role, logout } = useAuth();
  const [messages, setMessages] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [hideStatus, setHideStatus] = useState(false);

  useEffect(() => {
    if (accessTokenValid) {
      loadMessages();
      const interval = setInterval(loadMessages, 30000);
      return () => clearInterval(interval);
    }
  }, [accessTokenValid]);

  useEffect(() => {
    if (messages.length > 1) {
      const interval = setInterval(() => {
        setCurrentIndex((prev) => (prev + 1) % messages.length);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [messages.length]);

  const loadMessages = async () => {
    try {
      const token = localStorage.getItem('tp_access_token');
      console.log('Loading messages, token:', token ? 'exists' : 'missing');
      const response = await fetch('/accounts/api/status-messages/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      console.log('Response status:', response.status);
      const data = await response.json();
      console.log('Messages data:', data);
      const activeMessages = data.filter(msg => msg.is_active);
      console.log('Active messages:', activeMessages);
      setMessages(activeMessages);
    } catch (error) {
      console.error('Ошибка загрузки сообщений:', error);
    }
  };

  const currentMessage = messages.length > 0 ? messages[currentIndex] : null;

  return (
    <>
      <nav style={styles.nav}>
        <div style={styles.container}>
          <div style={styles.left}>
            📚 Easy Teaching
          </div>
          <div style={styles.center}>
            <Link style={styles.link} to="/">🏠 Главная</Link>
            {accessTokenValid && role === 'teacher' && <Link style={styles.link} to="/teacher">👨‍🏫 Преподаватель</Link>}
            {accessTokenValid && role === 'teacher' && <Link style={styles.linkHighlight} to="/groups/manage">👥 Группы и ученики</Link>}
            {accessTokenValid && role === 'teacher' && <Link style={styles.link} to="/homework/manage">📝 Домашки</Link>}
            {accessTokenValid && role === 'teacher' && <Link style={styles.link} to="/recurring-lessons/manage">📅 Расписание</Link>}
            {accessTokenValid && role === 'teacher' && <Link style={styles.link} to="/calendar">📆 Календарь</Link>}
            {accessTokenValid && role === 'student' && <Link style={styles.link} to="/student">📚 Ученик</Link>}
            {accessTokenValid && role === 'student' && <Link style={styles.link} to="/homework">📝 Мои ДЗ</Link>}
            {accessTokenValid && role === 'student' && <Link style={styles.link} to="/calendar">📆 Календарь</Link>}
            {accessTokenValid && role === 'admin' && <Link style={styles.linkHighlight} to="/admin-home">🔧 Админ-панель</Link>}
          </div>
          <div style={styles.right}>
            {!accessTokenValid && <Link style={styles.loginBtn} to="/login">Войти</Link>}
            {!accessTokenValid && <Link style={styles.registerBtn} to="/register">Регистрация</Link>}
            {accessTokenValid && (
              <div style={styles.userSection}>
                <div style={styles.avatar}>
                  <span style={styles.avatarText}>👤</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Status Bar Messages */}
      {accessTokenValid && currentMessage && !hideStatus && (
        <div className="navbar-status">
          <div className="status-inner">
            <span className="status-message">
              {currentMessage.message}
            </span>
            <button className="status-action" onClick={() => setHideStatus(true)}>
              скрыть
            </button>
          </div>
        </div>
      )}
    </>
  );
};

const styles = {
  nav: { 
    background:'#fff', 
    borderBottom:'1px solid #e5e7eb',
    position:'sticky', 
    top:0, 
    zIndex:100,
    boxShadow:'0 1px 3px rgba(0,0,0,0.05)'
  },
  container: {
    display:'flex', 
    alignItems:'center', 
    justifyContent:'space-between', 
    padding:'0.75rem 2rem',
    maxWidth:'1400px',
    margin:'0 auto'
  },
  left: { 
    display:'flex',
    alignItems:'center',
    fontWeight:600,
    fontSize:'1.1rem',
    color:'#111827'
  },
  center: { 
    display:'flex', 
    gap:'2rem',
    alignItems:'center'
  },
  right: { 
    display:'flex', 
    gap:'1rem',
    alignItems:'center'
  },
  link: { 
    color:'#374151', 
    textDecoration:'none', 
    fontSize:'0.95rem',
    fontWeight:500,
    transition:'color 0.2s ease',
    ':hover': {
      color:'#FF6B35'
    }
  },
  linkHighlight: {
    color:'#FF6B35',
    textDecoration:'none',
    fontSize:'0.95rem',
    fontWeight:600,
    padding:'0.5rem 1rem',
    background:'#fff7ed',
    borderRadius:8,
    border:'1px solid #ffedd5',
    transition:'all 0.2s ease'
  },
  loginBtn: { 
    color:'#fff', 
    background:'#FF6B35', 
    padding:'0.5rem 1.25rem', 
    textDecoration:'none', 
    borderRadius:8,
    fontSize:'0.9rem',
    fontWeight:500,
    transition:'all 0.2s ease'
  },
  registerBtn: {
    color:'#FF6B35',
    background:'transparent',
    border:'1px solid #FF6B35',
    padding:'0.5rem 1.25rem',
    textDecoration:'none',
    borderRadius:8,
    fontSize:'0.9rem',
    fontWeight:500,
    transition:'all 0.2s ease'
  },
  userSection: {
    display:'flex',
    alignItems:'center',
    gap:'0.75rem'
  },
  avatar: {
    width:'36px',
    height:'36px',
    borderRadius:'50%',
    background:'#f3f4f6',
    display:'flex',
    alignItems:'center',
    justifyContent:'center',
    cursor:'pointer',
    border:'2px solid #e5e7eb',
    transition:'all 0.2s ease'
  },
  avatarText: {
    fontSize:'1.25rem'
  }
};

export default NavBar;
