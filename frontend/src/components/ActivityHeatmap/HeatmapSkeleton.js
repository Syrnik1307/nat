import React from 'react';

/**
 * HeatmapSkeleton - скелетон загрузки для Activity Heatmap
 * Показывает серую сетку точно такого же размера как реальный heatmap
 * Предотвращает Layout Shifts (CLS)
 */
function HeatmapSkeleton() {
    // Генерируем 53 колонки (недели в году) по 7 ячеек
    const columns = Array.from({ length: 53 }, (_, i) => i);
    const rows = Array.from({ length: 7 }, (_, i) => i);
    
    return (
        <div className="heatmap-skeleton">
            {/* Grid skeleton */}
            <div className="heatmap-skeleton__grid">
                {columns.map(col => (
                    <div key={col} className="heatmap-skeleton__column">
                        {rows.map(row => (
                            <div 
                                key={row} 
                                className="heatmap-skeleton__cell"
                                style={{ 
                                    animationDelay: `${(col * 0.01)}s` 
                                }}
                            />
                        ))}
                    </div>
                ))}
            </div>
            
            {/* Stats skeleton */}
            <div className="heatmap-skeleton__stats">
                {[1, 2, 3, 4].map(i => (
                    <div key={i} className="heatmap-skeleton__stat-card">
                        <div className="heatmap-skeleton__stat-icon" />
                        <div className="heatmap-skeleton__stat-value" />
                        <div className="heatmap-skeleton__stat-label" />
                    </div>
                ))}
            </div>
        </div>
    );
}

export default HeatmapSkeleton;
