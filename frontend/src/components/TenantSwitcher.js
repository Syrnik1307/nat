/**
 * TenantSwitcher — выпадающий компонент для переключения между организациями (tenant).
 * Встраивается в NavBar. Показывает название текущей организации и позволяет сменить.
 */
import React, { useState, useRef, useEffect } from 'react';
import { useTenant } from '../TenantContext';

const TenantSwitcher = () => {
    const { tenants, currentTenant, switchTenant, loading } = useTenant();
    const [open, setOpen] = useState(false);
    const ref = useRef(null);

    // Закрыть при клике вне компонента
    useEffect(() => {
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false);
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    if (loading) return <span style={styles.label}>Загрузка...</span>;
    if (!currentTenant) return null;
    if (tenants.length <= 1) {
        // Один тенант — просто показываем имя
        return (
            <span style={styles.label} title={currentTenant.name}>
                🏢 {currentTenant.name}
            </span>
        );
    }

    return (
        <div ref={ref} style={styles.wrapper}>
            <button style={styles.button} onClick={() => setOpen(!open)}>
                🏢 {currentTenant.name} ▾
            </button>
            {open && (
                <div style={styles.dropdown}>
                    {tenants.map(m => (
                        <div
                            key={m.tenant.slug}
                            style={{
                                ...styles.item,
                                ...(m.tenant.slug === currentTenant.slug ? styles.itemActive : {}),
                            }}
                            onClick={() => { switchTenant(m.tenant.slug); setOpen(false); }}
                        >
                            <span style={styles.itemName}>{m.tenant.name}</span>
                            <span style={styles.itemRole}>{m.role}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

const styles = {
    wrapper: {
        position: 'relative',
        display: 'inline-block',
    },
    label: {
        fontSize: '14px',
        color: '#e0e7ff',
        padding: '4px 10px',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        maxWidth: '200px',
        display: 'inline-block',
    },
    button: {
        background: 'rgba(255,255,255,0.1)',
        border: '1px solid rgba(255,255,255,0.2)',
        borderRadius: '6px',
        color: '#e0e7ff',
        padding: '6px 14px',
        cursor: 'pointer',
        fontSize: '14px',
        whiteSpace: 'nowrap',
        maxWidth: '220px',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
    },
    dropdown: {
        position: 'absolute',
        top: '100%',
        left: 0,
        marginTop: '4px',
        background: '#1e293b',
        border: '1px solid rgba(255,255,255,0.15)',
        borderRadius: '8px',
        minWidth: '220px',
        zIndex: 1000,
        boxShadow: '0 8px 16px rgba(0,0,0,0.3)',
    },
    item: {
        padding: '10px 14px',
        cursor: 'pointer',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        transition: 'background 0.15s',
    },
    itemActive: {
        background: 'rgba(59,130,246,0.2)',
    },
    itemName: {
        color: '#e0e7ff',
        fontSize: '14px',
        fontWeight: '500',
    },
    itemRole: {
        color: '#94a3b8',
        fontSize: '12px',
        marginLeft: '10px',
    },
};

export default TenantSwitcher;
