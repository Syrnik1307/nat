import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../auth';
import { apiClient } from '../apiService';
import { getFinanceDashboard, getFinanceWallets, depositToWallet, chargeFromWallet, adjustWalletBalance, getWalletTransactions } from '../financeService';
import './FinancePage.css';

// SVG Icons
const IconOverview = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
);

const IconWallet = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 4H3c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2z"/>
        <path d="M16 12a2 2 0 1 0 4 0 2 2 0 0 0-4 0z"/>
    </svg>
);

const IconDebtors = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
);

const IconHistory = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
    </svg>
);

const IconSearch = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
);

const IconPlus = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <line x1="12" y1="5" x2="12" y2="19"/>
        <line x1="5" y1="12" x2="19" y2="12"/>
    </svg>
);

const IconMinus = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <line x1="5" y1="12" x2="19" y2="12"/>
    </svg>
);

const IconEdit = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
    </svg>
);

const IconTrendUp = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
        <polyline points="17 6 23 6 23 12"/>
    </svg>
);

const IconTrendDown = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/>
        <polyline points="17 18 23 18 23 12"/>
    </svg>
);

const IconClose = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
);

const TABS = [
    { id: 'overview', label: 'Обзор', Icon: IconOverview },
    { id: 'students', label: 'Все ученики', Icon: IconWallet },
    { id: 'debtors', label: 'Должники', Icon: IconDebtors },
    { id: 'history', label: 'История', Icon: IconHistory },
];

const QUICK_AMOUNTS = [500, 1000, 2000, 5000, 10000];

const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(amount);
};

const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
};

// Modal Components
const Modal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;
    
    return (
        <div className="finance-modal-overlay" onClick={onClose}>
            <div className="finance-modal" onClick={e => e.stopPropagation()}>
                <div className="finance-modal-header">
                    <h3>{title}</h3>
                    <button className="modal-close-btn" onClick={onClose}>
                        <IconClose />
                    </button>
                </div>
                <div className="finance-modal-content">
                    {children}
                </div>
            </div>
        </div>
    );
};

const DepositModal = ({ isOpen, onClose, wallet, onSuccess }) => {
    const [amount, setAmount] = useState('');
    const [description, setDescription] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!amount || parseFloat(amount) <= 0) {
            setError('Введите сумму');
            return;
        }
        
        setLoading(true);
        setError('');
        
        try {
            await depositToWallet(wallet.id, parseFloat(amount), description);
            onSuccess();
            onClose();
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка при пополнении');
        } finally {
            setLoading(false);
        }
    };
    
    const handleQuickAmount = (val) => {
        setAmount(val.toString());
    };
    
    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Пополнить баланс">
            <form onSubmit={handleSubmit}>
                <div className="modal-student-info">
                    <span className="student-name">{wallet?.student_name}</span>
                    <span className="current-balance">
                        Текущий баланс: <strong>{formatCurrency(wallet?.balance || 0)}</strong>
                    </span>
                </div>
                
                <div className="quick-amounts">
                    {QUICK_AMOUNTS.map(val => (
                        <button
                            key={val}
                            type="button"
                            className={`quick-amount-btn ${amount === val.toString() ? 'active' : ''}`}
                            onClick={() => handleQuickAmount(val)}
                        >
                            {formatCurrency(val)}
                        </button>
                    ))}
                </div>
                
                <div className="form-group">
                    <label>Сумма</label>
                    <input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        placeholder="Введите сумму"
                        min="0"
                        step="100"
                    />
                </div>
                
                <div className="form-group">
                    <label>Комментарий (необязательно)</label>
                    <input
                        type="text"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Например: Оплата за октябрь"
                    />
                </div>
                
                {error && <div className="modal-error">{error}</div>}
                
                <div className="modal-actions">
                    <button type="button" className="btn-secondary" onClick={onClose}>
                        Отмена
                    </button>
                    <button type="submit" className="btn-primary" disabled={loading}>
                        {loading ? 'Пополнение...' : 'Пополнить'}
                    </button>
                </div>
            </form>
        </Modal>
    );
};

const ChargeModal = ({ isOpen, onClose, wallet, onSuccess }) => {
    const [amount, setAmount] = useState(wallet?.default_lesson_price?.toString() || '');
    const [description, setDescription] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    useEffect(() => {
        if (wallet?.default_lesson_price) {
            setAmount(wallet.default_lesson_price.toString());
        }
    }, [wallet]);
    
    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!amount || parseFloat(amount) <= 0) {
            setError('Введите сумму');
            return;
        }
        
        setLoading(true);
        setError('');
        
        try {
            await chargeFromWallet(wallet.id, parseFloat(amount), description);
            onSuccess();
            onClose();
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка при списании');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Списать за урок">
            <form onSubmit={handleSubmit}>
                <div className="modal-student-info">
                    <span className="student-name">{wallet?.student_name}</span>
                    <span className="current-balance">
                        Текущий баланс: <strong>{formatCurrency(wallet?.balance || 0)}</strong>
                    </span>
                </div>
                
                <div className="form-group">
                    <label>Сумма</label>
                    <input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        placeholder="Введите сумму"
                        min="0"
                        step="100"
                    />
                    <span className="form-hint">
                        Цена по умолчанию: {formatCurrency(wallet?.default_lesson_price || 0)}
                    </span>
                </div>
                
                <div className="form-group">
                    <label>Комментарий (необязательно)</label>
                    <input
                        type="text"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Например: Ручное списание"
                    />
                </div>
                
                {error && <div className="modal-error">{error}</div>}
                
                <div className="modal-actions">
                    <button type="button" className="btn-secondary" onClick={onClose}>
                        Отмена
                    </button>
                    <button type="submit" className="btn-primary btn-danger" disabled={loading}>
                        {loading ? 'Списание...' : 'Списать'}
                    </button>
                </div>
            </form>
        </Modal>
    );
};

const AdjustModal = ({ isOpen, onClose, wallet, onSuccess }) => {
    const [amount, setAmount] = useState('');
    const [reason, setReason] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!amount || parseFloat(amount) === 0) {
            setError('Введите сумму корректировки');
            return;
        }
        if (!reason.trim()) {
            setError('Укажите причину корректировки');
            return;
        }
        
        setLoading(true);
        setError('');
        
        try {
            await adjustWalletBalance(wallet.id, parseFloat(amount), reason);
            onSuccess();
            onClose();
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка при корректировке');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Корректировка баланса">
            <form onSubmit={handleSubmit}>
                <div className="modal-student-info">
                    <span className="student-name">{wallet?.student_name}</span>
                    <span className="current-balance">
                        Текущий баланс: <strong>{formatCurrency(wallet?.balance || 0)}</strong>
                    </span>
                </div>
                
                <div className="form-group">
                    <label>Сумма (положительная или отрицательная)</label>
                    <input
                        type="number"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        placeholder="+500 или -500"
                        step="100"
                    />
                    <span className="form-hint">
                        Положительное число увеличивает баланс, отрицательное - уменьшает
                    </span>
                </div>
                
                <div className="form-group">
                    <label>Причина корректировки *</label>
                    <input
                        type="text"
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder="Например: Скидка за раннюю оплату"
                        required
                    />
                </div>
                
                {error && <div className="modal-error">{error}</div>}
                
                <div className="modal-actions">
                    <button type="button" className="btn-secondary" onClick={onClose}>
                        Отмена
                    </button>
                    <button type="submit" className="btn-primary" disabled={loading}>
                        {loading ? 'Сохранение...' : 'Применить'}
                    </button>
                </div>
            </form>
        </Modal>
    );
};

const TransactionHistoryModal = ({ isOpen, onClose, wallet }) => {
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        const loadTransactions = async () => {
            try {
                setLoading(true);
                const response = await getWalletTransactions(wallet.id);
                setTransactions(response.data.results || []);
            } catch (err) {
                console.error('Error loading transactions:', err);
            } finally {
                setLoading(false);
            }
        };
        
        if (isOpen && wallet) {
            loadTransactions();
        }
    }, [isOpen, wallet]);
    
    const getTypeLabel = (type) => {
        const labels = {
            'DEPOSIT': 'Пополнение',
            'LESSON_CHARGE': 'Урок',
            'ADJUSTMENT': 'Корректировка',
            'REFUND': 'Возврат',
        };
        return labels[type] || type;
    };
    
    const getTypeClass = (type) => {
        const classes = {
            'DEPOSIT': 'txn-deposit',
            'LESSON_CHARGE': 'txn-charge',
            'ADJUSTMENT': 'txn-adjustment',
            'REFUND': 'txn-refund',
        };
        return classes[type] || '';
    };
    
    return (
        <Modal isOpen={isOpen} onClose={onClose} title={`История: ${wallet?.student_name}`}>
            <div className="transaction-history">
                {loading ? (
                    <div className="loading-spinner">Загрузка...</div>
                ) : transactions.length === 0 ? (
                    <div className="empty-state">Транзакций пока нет</div>
                ) : (
                    <div className="transactions-list">
                        {transactions.map(txn => (
                            <div key={txn.id} className={`transaction-item ${getTypeClass(txn.transaction_type)}`}>
                                <div className="txn-main">
                                    <span className="txn-type">{getTypeLabel(txn.transaction_type)}</span>
                                    <span className={`txn-amount ${txn.amount >= 0 ? 'positive' : 'negative'}`}>
                                        {txn.amount >= 0 ? '+' : ''}{formatCurrency(txn.amount)}
                                    </span>
                                </div>
                                <div className="txn-details">
                                    <span className="txn-date">{formatDate(txn.created_at)}</span>
                                    {txn.description && (
                                        <span className="txn-description">{txn.description}</span>
                                    )}
                                </div>
                                <div className="txn-balance">
                                    Баланс после: {formatCurrency(txn.balance_after)}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </Modal>
    );
};

// Student Card Component
const StudentCard = ({ wallet, onDeposit, onCharge, onAdjust, onHistory }) => {
    const balanceStatus = wallet.balance < 0 
        ? (wallet.balance < -wallet.debt_limit ? 'critical' : 'warning')
        : wallet.balance < wallet.default_lesson_price * 2 
            ? 'low' 
            : 'ok';
    
    return (
        <div className={`student-card balance-${balanceStatus}`}>
            <div className="student-card-header">
                <div className="student-info">
                    <h4 className="student-name">{wallet.student_name}</h4>
                    {wallet.group_names && wallet.group_names.length > 0 && (
                        <span className="student-groups">
                            {wallet.group_names.join(', ')}
                        </span>
                    )}
                </div>
                <div className="balance-info">
                    <span className={`balance-amount ${balanceStatus}`}>
                        {formatCurrency(wallet.balance)}
                    </span>
                    <span className="lessons-left">
                        {wallet.lessons_left} урок{wallet.lessons_left === 1 ? '' : wallet.lessons_left < 5 ? 'а' : 'ов'}
                    </span>
                </div>
            </div>
            
            {balanceStatus === 'critical' && (
                <div className="balance-alert critical">
                    Превышен лимит долга ({formatCurrency(wallet.debt_limit)})
                </div>
            )}
            
            <div className="student-card-meta">
                <span>Цена урока: {formatCurrency(wallet.default_lesson_price)}</span>
                <span>Лимит долга: {formatCurrency(wallet.debt_limit)}</span>
            </div>
            
            <div className="student-card-actions">
                <button className="action-btn deposit" onClick={() => onDeposit(wallet)}>
                    <IconPlus /> Пополнить
                </button>
                <button className="action-btn charge" onClick={() => onCharge(wallet)}>
                    <IconMinus /> Списать
                </button>
                <button className="action-btn adjust" onClick={() => onAdjust(wallet)}>
                    <IconEdit /> Корректировка
                </button>
                <button className="action-btn history" onClick={() => onHistory(wallet)}>
                    <IconHistory /> История
                </button>
            </div>
        </div>
    );
};

// Summary Card Component
const SummaryCard = ({ title, value, subtitle, trend, trendValue, icon: Icon, variant = 'default' }) => {
    return (
        <div className={`summary-card ${variant}`}>
            <div className="summary-icon">
                <Icon />
            </div>
            <div className="summary-content">
                <span className="summary-title">{title}</span>
                <span className="summary-value">{value}</span>
                {subtitle && <span className="summary-subtitle">{subtitle}</span>}
            </div>
            {trend && (
                <div className={`summary-trend ${trendValue >= 0 ? 'positive' : 'negative'}`}>
                    {trendValue >= 0 ? <IconTrendUp /> : <IconTrendDown />}
                    <span>{Math.abs(trendValue)}%</span>
                </div>
            )}
        </div>
    );
};


const FinancePage = () => {
    const { role } = useAuth();
    const [activeTab, setActiveTab] = useState('overview');
    const [wallets, setWallets] = useState([]);
    const [dashboard, setDashboard] = useState(null);
    const [groups, setGroups] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [filterGroup, setFilterGroup] = useState('');
    
    // Modal states
    const [depositModal, setDepositModal] = useState({ open: false, wallet: null });
    const [chargeModal, setChargeModal] = useState({ open: false, wallet: null });
    const [adjustModal, setAdjustModal] = useState({ open: false, wallet: null });
    const [historyModal, setHistoryModal] = useState({ open: false, wallet: null });
    
    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            const [walletsRes, dashboardRes, groupsRes] = await Promise.all([
                getFinanceWallets(),
                getFinanceDashboard(),
                apiClient.get('/groups/'),
            ]);
            
            setWallets(walletsRes.data.results || walletsRes.data || []);
            setDashboard(dashboardRes.data);
            setGroups(groupsRes.data.results || groupsRes.data || []);
        } catch (err) {
            console.error('Error loading finance data:', err);
        } finally {
            setLoading(false);
        }
    }, []);
    
    useEffect(() => {
        loadData();
    }, [loadData]);
    
    const handleRefresh = () => {
        loadData();
    };
    
    // Filter wallets
    const filteredWallets = wallets.filter(w => {
        const matchesSearch = !searchQuery || 
            w.student_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            w.student_email?.toLowerCase().includes(searchQuery.toLowerCase());
        
        const matchesGroup = !filterGroup || 
            (w.group_names && w.group_names.includes(groups.find(g => g.id.toString() === filterGroup)?.name));
        
        return matchesSearch && matchesGroup;
    });
    
    // Debtors only
    const debtorWallets = filteredWallets.filter(w => w.balance < 0);
    
    // Get badge counts
    const debtorsCount = wallets.filter(w => w.balance < 0).length;
    
    const renderOverview = () => {
        if (!dashboard) return null;
        
        return (
            <div className="finance-overview">
                <div className="summary-cards">
                    <SummaryCard
                        title="Всего учеников"
                        value={dashboard.summary.total_students}
                        icon={IconWallet}
                    />
                    <SummaryCard
                        title="Общий баланс"
                        value={formatCurrency(dashboard.summary.total_balance)}
                        variant={dashboard.summary.total_balance >= 0 ? 'success' : 'danger'}
                        icon={IconWallet}
                    />
                    <SummaryCard
                        title="Должники"
                        value={dashboard.summary.debtors_count}
                        subtitle={`Долг: ${formatCurrency(Math.abs(dashboard.summary.total_debt))}`}
                        variant={dashboard.summary.debtors_count > 0 ? 'warning' : 'default'}
                        icon={IconDebtors}
                    />
                    <SummaryCard
                        title="Поступления за месяц"
                        value={formatCurrency(dashboard.earnings.current_month)}
                        trend={true}
                        trendValue={dashboard.earnings.growth_percent}
                        icon={IconTrendUp}
                    />
                </div>
                
                <div className="overview-grid">
                    <div className="overview-section">
                        <h3>Статистика за месяц</h3>
                        <div className="stats-list">
                            <div className="stat-item">
                                <span className="stat-label">Проведено уроков</span>
                                <span className="stat-value">{dashboard.earnings.lessons_conducted}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Списано за уроки</span>
                                <span className="stat-value">{formatCurrency(dashboard.earnings.lessons_revenue)}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Средняя цена урока</span>
                                <span className="stat-value">{formatCurrency(dashboard.average_lesson_price)}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Поступления прошлый месяц</span>
                                <span className="stat-value">{formatCurrency(dashboard.earnings.previous_month)}</span>
                            </div>
                        </div>
                    </div>
                    
                    {dashboard.top_debtors.length > 0 && (
                        <div className="overview-section debtors-section">
                            <h3>Топ должников</h3>
                            <div className="debtors-list">
                                {dashboard.top_debtors.map(d => (
                                    <div key={d.id} className={`debtor-item ${d.limit_exceeded ? 'critical' : ''}`}>
                                        <span className="debtor-name">{d.student_name}</span>
                                        <span className="debtor-balance">{formatCurrency(d.balance)}</span>
                                        {d.limit_exceeded && (
                                            <span className="debtor-warning">Превышен лимит</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                    
                    {dashboard.by_group.length > 0 && (
                        <div className="overview-section groups-section">
                            <h3>По группам</h3>
                            <div className="groups-list">
                                {dashboard.by_group.map(g => (
                                    <div key={g.group_id} className="group-item">
                                        <span className="group-name">{g.group_name}</span>
                                        <div className="group-stats">
                                            <span>{g.students_count} уч.</span>
                                            <span className={g.total_balance >= 0 ? 'positive' : 'negative'}>
                                                {formatCurrency(g.total_balance)}
                                            </span>
                                            {g.debtors_count > 0 && (
                                                <span className="debtors-badge">{g.debtors_count} долж.</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    };
    
    const renderStudents = (studentList = filteredWallets) => {
        return (
            <div className="students-section">
                <div className="section-toolbar">
                    <div className="search-box">
                        <IconSearch />
                        <input
                            type="text"
                            placeholder="Поиск по имени или email..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <select
                        value={filterGroup}
                        onChange={(e) => setFilterGroup(e.target.value)}
                        className="group-filter"
                    >
                        <option value="">Все группы</option>
                        {groups.map(g => (
                            <option key={g.id} value={g.id}>{g.name}</option>
                        ))}
                    </select>
                </div>
                
                {studentList.length === 0 ? (
                    <div className="empty-state">
                        <p>Ученики не найдены</p>
                    </div>
                ) : (
                    <div className="students-grid">
                        {studentList.map(wallet => (
                            <StudentCard
                                key={wallet.id}
                                wallet={wallet}
                                onDeposit={(w) => setDepositModal({ open: true, wallet: w })}
                                onCharge={(w) => setChargeModal({ open: true, wallet: w })}
                                onAdjust={(w) => setAdjustModal({ open: true, wallet: w })}
                                onHistory={(w) => setHistoryModal({ open: true, wallet: w })}
                            />
                        ))}
                    </div>
                )}
            </div>
        );
    };
    
    const renderHistory = () => {
        return (
            <div className="history-section">
                <p className="coming-soon">
                    Полная история транзакций по всем ученикам. 
                    Пока используйте историю в карточке каждого ученика.
                </p>
            </div>
        );
    };
    
    if (role !== 'teacher' && role !== 'admin') {
        return (
            <div className="finance-page">
                <div className="access-denied">
                    <h2>Доступ ограничен</h2>
                    <p>Эта страница доступна только для учителей</p>
                </div>
            </div>
        );
    }
    
    return (
        <div className="finance-page">
            <div className="finance-layout">
                {/* Sidebar */}
                <aside className="finance-sidebar">
                    <div className="sidebar-header">
                        <h1>Финансы</h1>
                    </div>
                    <nav className="sidebar-nav">
                        {TABS.map(({ id, label, Icon }) => (
                            <button
                                key={id}
                                className={`nav-item ${activeTab === id ? 'nav-item--active' : ''}`}
                                onClick={() => setActiveTab(id)}
                            >
                                <Icon />
                                <span>{label}</span>
                                {id === 'debtors' && debtorsCount > 0 && (
                                    <span className="nav-badge">{debtorsCount}</span>
                                )}
                            </button>
                        ))}
                    </nav>
                </aside>
                
                {/* Main Content */}
                <main className="finance-main">
                    {loading ? (
                        <div className="loading-state">
                            <div className="loading-spinner"></div>
                            <p>Загрузка данных...</p>
                        </div>
                    ) : (
                        <>
                            {activeTab === 'overview' && renderOverview()}
                            {activeTab === 'students' && renderStudents()}
                            {activeTab === 'debtors' && renderStudents(debtorWallets)}
                            {activeTab === 'history' && renderHistory()}
                        </>
                    )}
                </main>
            </div>
            
            {/* Modals */}
            <DepositModal
                isOpen={depositModal.open}
                wallet={depositModal.wallet}
                onClose={() => setDepositModal({ open: false, wallet: null })}
                onSuccess={handleRefresh}
            />
            <ChargeModal
                isOpen={chargeModal.open}
                wallet={chargeModal.wallet}
                onClose={() => setChargeModal({ open: false, wallet: null })}
                onSuccess={handleRefresh}
            />
            <AdjustModal
                isOpen={adjustModal.open}
                wallet={adjustModal.wallet}
                onClose={() => setAdjustModal({ open: false, wallet: null })}
                onSuccess={handleRefresh}
            />
            <TransactionHistoryModal
                isOpen={historyModal.open}
                wallet={historyModal.wallet}
                onClose={() => setHistoryModal({ open: false, wallet: null })}
            />
        </div>
    );
};

export default FinancePage;
