/**
 * AuraBI - Enterprise AI Sales Assistant Controller
 * Features: Vibrant Chart.js theming, Dark/Light mode, Interactive Analytics
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const queryInput = document.getElementById('query-input');
    const btnSubmit = document.getElementById('btn-submit-query');
    const querySpinner = document.getElementById('query-spinner');
    const btnText = btnSubmit.querySelector('.btn-text');
    const btnIcon = btnSubmit.querySelector('.btn-icon');
    const pillsTrack = document.getElementById('pills-track');

    const resultsWorkspace = document.getElementById('results-workspace');
    const answerContent = document.getElementById('answer-content');
    const execTimeBadge = document.getElementById('exec-time-badge');
    const guardrailBadge = document.getElementById('guardrail-badge');
    const btnCopyAnswer = document.getElementById('btn-copy-answer');

    const chartCard = document.getElementById('chart-container-card');
    const chartCanvas = document.getElementById('analyticsChart');
    const chartTypeSelector = document.getElementById('chart-type-selector');
    const chartSubtitle = document.getElementById('chart-subtitle');

    const toggleSqlBtn = document.getElementById('toggle-sql-btn');
    const sqlBody = document.getElementById('sql-body');
    const sqlArrow = document.getElementById('sql-arrow');
    const sqlCodeDisplay = document.getElementById('sql-code-display');
    const btnCopySql = document.getElementById('btn-copy-sql');
    const queryMetaDetails = document.getElementById('query-meta-details');

    const tableHeadRow = document.getElementById('table-head-row');
    const tableBody = document.getElementById('table-body');
    const btnExportCsv = document.getElementById('btn-export-csv');

    // KPI Elements
    const kpiValRevenue = document.getElementById('kpi-val-revenue');
    const kpiValProduct = document.getElementById('kpi-val-product');
    const kpiSubProduct = document.getElementById('kpi-sub-product');
    const kpiValRegion = document.getElementById('kpi-val-region');
    const kpiSubRegion = document.getElementById('kpi-sub-region');
    const kpiValMonth = document.getElementById('kpi-val-month');
    const kpiSubMonth = document.getElementById('kpi-sub-month');

    // Theme Toggle
    const btnThemeToggle = document.getElementById('btn-theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    // Modals
    const btnSchema = document.getElementById('btn-schema');
    const schemaModal = document.getElementById('schema-modal');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const schemaModalBody = document.getElementById('schema-modal-body');

    const btnReingest = document.getElementById('btn-reingest');
    const etlModal = document.getElementById('etl-modal');
    const btnCloseEtlModal = document.getElementById('btn-close-etl-modal');
    const etlModalBody = document.getElementById('etl-modal-body');

    // State
    let currentChart = null;
    let currentData = null;
    let currentChartConfig = null;

    // Initialize Theme
    initTheme();

    // Load initial KPIs
    loadKPIs();

    // Event Listeners
    btnSubmit.addEventListener('click', () => handleQuery(queryInput.value));
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleQuery(queryInput.value);
    });

    // Theme Switcher Click
    if (btnThemeToggle) {
        btnThemeToggle.addEventListener('click', toggleTheme);
    }

    // Sample Query Pills
    pillsTrack.addEventListener('click', (e) => {
        const pill = e.target.closest('.pill');
        if (pill) {
            const query = pill.getAttribute('data-query');
            queryInput.value = query;
            handleQuery(query);
        }
    });

    // Toggle SQL Inspector
    toggleSqlBtn.addEventListener('click', () => {
        const isHidden = sqlBody.style.display === 'none';
        sqlBody.style.display = isHidden ? 'block' : 'none';
        sqlArrow.textContent = isHidden ? '▲' : '▼';
    });

    // Copy SQL
    btnCopySql.addEventListener('click', () => {
        navigator.clipboard.writeText(sqlCodeDisplay.textContent).then(() => {
            btnCopySql.textContent = 'Copied!';
            setTimeout(() => { btnCopySql.textContent = 'Copy SQL'; }, 2000);
        });
    });

    // Copy Answer
    btnCopyAnswer.addEventListener('click', () => {
        navigator.clipboard.writeText(answerContent.innerText).then(() => {
            showToast('Answer copied to clipboard!');
        });
    });

    // Export CSV
    btnExportCsv.addEventListener('click', () => {
        if (!currentData || !currentData.rows || currentData.rows.length === 0) return;
        downloadCSV(currentData.columns, currentData.rows);
    });

    // Chart Type Selector
    chartTypeSelector.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-toggle');
        if (btn && currentChartConfig) {
            chartTypeSelector.querySelectorAll('.btn-toggle').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const newType = btn.getAttribute('data-chart-type');
            renderChart(newType, currentChartConfig);
        }
    });

    // Schema Modal
    btnSchema.addEventListener('click', openSchemaModal);
    btnCloseModal.addEventListener('click', () => { schemaModal.style.display = 'none'; });
    schemaModal.addEventListener('click', (e) => {
        if (e.target === schemaModal) schemaModal.style.display = 'none';
    });

    // ETL Modal
    btnReingest.addEventListener('click', openEtlModal);
    btnCloseEtlModal.addEventListener('click', () => { etlModal.style.display = 'none'; });
    etlModal.addEventListener('click', (e) => {
        if (e.target === etlModal) etlModal.style.display = 'none';
    });

    /**
     * Theme Management - Clean Colorful Bright Default
     */
    function initTheme() {
        localStorage.removeItem('aurabi_theme');
        document.body.classList.remove('dark-theme');
        document.body.classList.remove('light-theme');
    }

    /**
     * Executes Query against API
     */
    async function handleQuery(question) {
        if (!question || !question.trim()) return;

        setLoading(true);
        resultsWorkspace.style.display = 'none';

        try {
            const resp = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: question.trim() })
            });

            const result = await resp.json();
            currentData = result;

            if (result.status === 'error') {
                renderError(result);
            } else {
                renderSuccess(result);
            }
        } catch (err) {
            renderError({
                question: question,
                error: `Network / Server connection error: ${err.message}`
            });
        } finally {
            setLoading(false);
            resultsWorkspace.style.display = 'flex';
            resultsWorkspace.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    function renderSuccess(res) {
        // AI Answer with colorful highlight formatting
        answerContent.innerHTML = formatMarkdown(res.answer);
        execTimeBadge.textContent = `${res.execution_time_ms} ms`;
        guardrailBadge.innerHTML = '🛡️ AST Read-Only Verified';
        guardrailBadge.className = 'guardrail-badge';

        // SQL Code
        sqlCodeDisplay.textContent = res.sql_query;
        queryMetaDetails.innerHTML = `
            <strong>Engine:</strong> <span style="color: #a855f7;">${res.engine_mode}</span> &bull; 
            <strong>Rows:</strong> <span style="color: #06b6d4;">${res.row_count}</span> &bull; 
            <strong>Intent:</strong> <span style="color: #10b981;">${res.intent || 'custom'}</span> &bull;
            <em>${res.explanation || ''}</em>
        `;

        // Render Chart
        if (res.chart_config) {
            chartCard.style.display = 'block';
            currentChartConfig = res.chart_config;
            chartSubtitle.textContent = `${res.chart_config.x_axis_label} vs ${res.chart_config.y_axis_label}`;
            
            // Set active toggle
            chartTypeSelector.querySelectorAll('.btn-toggle').forEach(b => {
                b.classList.toggle('active', b.getAttribute('data-chart-type') === res.chart_config.type);
            });

            renderChart(res.chart_config.type, res.chart_config);
        } else {
            chartCard.style.display = 'none';
        }

        // Render Data Table with colorful status badges
        renderTable(res.columns || [], res.rows || []);
    }

    function renderError(res) {
        answerContent.innerHTML = `
            <div style="color: #f43f5e; font-weight: 500;">
                <p>⚠️ <strong>Query Could Not Be Processed:</strong></p>
                <p style="margin-top: 8px;">${res.error || 'An unexpected error occurred.'}</p>
            </div>
        `;
        execTimeBadge.textContent = '0.0 ms';
        guardrailBadge.innerHTML = '⚠️ Rejected';
        guardrailBadge.className = 'guardrail-badge' + (res.security_flag ? ' danger' : '');
        
        sqlCodeDisplay.textContent = res.sql_query || '-- No SQL executed';
        queryMetaDetails.textContent = 'Execution stopped by security or validator guardrail.';
        chartCard.style.display = 'none';
        renderTable([], []);
    }

    function renderChart(type, config) {
        if (currentChart) {
            currentChart.destroy();
        }

        const ctx = chartCanvas.getContext('2d');
        const isDoughnut = type === 'doughnut';
        const isLine = type === 'line';
        const isLight = document.body.classList.contains('light-theme');

        // Vivid distinct color palette
        const palette = [
            '#10b981', // Emerald
            '#06b6d4', // Cyan
            '#a855f7', // Purple
            '#f59e0b', // Amber
            '#ec4899', // Pink
            '#3b82f6', // Blue
            '#f43f5e', // Rose
            '#14b8a6'  // Teal
        ];

        let bgColors;
        let borderColors;

        if (isDoughnut) {
            bgColors = palette;
            borderColors = isLight ? '#ffffff' : '#111827';
        } else if (type === 'bar') {
            // Give each bar its own vibrant gradient!
            bgColors = config.labels.map((_, i) => {
                const color = palette[i % palette.length];
                const grad = ctx.createLinearGradient(0, 400, 0, 0);
                grad.addColorStop(0, color + '55'); // transparent at bottom
                grad.addColorStop(1, color);       // solid vivid at top
                return grad;
            });
            borderColors = config.labels.map((_, i) => palette[i % palette.length]);
        } else {
            // Line Chart: Luminous violet-cyan gradient stroke with smooth area glow
            const strokeGrad = ctx.createLinearGradient(0, 0, 600, 0);
            strokeGrad.addColorStop(0, '#a855f7');
            strokeGrad.addColorStop(1, '#06b6d4');
            borderColors = strokeGrad;

            const areaGrad = ctx.createLinearGradient(0, 0, 0, 380);
            areaGrad.addColorStop(0, 'rgba(168, 85, 247, 0.35)');
            areaGrad.addColorStop(0.7, 'rgba(6, 182, 212, 0.12)');
            areaGrad.addColorStop(1, 'rgba(6, 182, 212, 0.0)');
            bgColors = areaGrad;
        }

        const textColor = '#475569';
        const gridColor = 'rgba(0, 0, 0, 0.06)';

        currentChart = new Chart(ctx, {
            type: type,
            data: {
                labels: config.labels,
                datasets: [{
                    label: config.datasets[0].label,
                    data: config.datasets[0].data,
                    backgroundColor: bgColors,
                    borderColor: borderColors,
                    borderWidth: isLine ? 3 : 2,
                    borderRadius: type === 'bar' ? 8 : 0,
                    pointBackgroundColor: '#06b6d4',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    pointHoverRadius: 9,
                    tension: 0.38,
                    fill: isLine
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: isDoughnut,
                        labels: { color: textColor, font: { family: 'Inter', size: 12, weight: '600' } }
                    },
                    tooltip: {
                        backgroundColor: '#ffffff',
                        titleColor: '#0f172a',
                        bodyColor: '#334155',
                        borderColor: '#e2e8f0',
                        borderWidth: 1.5,
                        padding: 12,
                        boxPadding: 6,
                        usePointStyle: true,
                        callbacks: {
                            label: function(context) {
                                let val = context.raw;
                                if (typeof val === 'number') {
                                    return ` ${context.dataset.label}: ₹${val.toLocaleString('en-IN')}`;
                                }
                                return ` ${context.dataset.label}: ${val}`;
                            }
                        }
                    }
                },
                scales: isDoughnut ? {} : {
                    x: {
                        grid: { color: gridColor },
                        ticks: { color: textColor, font: { family: 'Inter', weight: '500' } }
                    },
                    y: {
                        grid: { color: gridColor },
                        ticks: {
                            color: textColor,
                            font: { family: 'Inter', weight: '500' },
                            callback: function(value) {
                                if (value >= 1000) return '₹' + (value / 1000).toLocaleString() + 'k';
                                return '₹' + value;
                            }
                        }
                    }
                }
            }
        });
    }

    function renderTable(columns, rows) {
        if (!columns || columns.length === 0 || !rows || rows.length === 0) {
            tableHeadRow.innerHTML = '<th>No Records</th>';
            tableBody.innerHTML = '<tr><td style="color: var(--text-muted); padding: 18px;">No supporting records to display.</td></tr>';
            return;
        }

        // Header
        tableHeadRow.innerHTML = columns.map(c => `<th>${c.replace(/_/g, ' ').toUpperCase()}</th>`).join('');

        // Rows with colorful badges
        tableBody.innerHTML = rows.map(r => {
            const cells = columns.map(col => {
                let rawVal = r[col];
                let displayVal = rawVal !== null && rawVal !== undefined ? rawVal : '-';

                // Status Column
                if (col.toLowerCase() === 'status') {
                    if (String(rawVal).toLowerCase() === 'completed') {
                        return `<td><span class="badge-status completed">● Completed</span></td>`;
                    } else if (String(rawVal).toLowerCase() === 'returned') {
                        return `<td><span class="badge-status returned">● Returned</span></td>`;
                    }
                }

                // Category Column
                if (col.toLowerCase() === 'category') {
                    const catClass = String(rawVal).toLowerCase();
                    return `<td><span class="badge-category ${catClass}">${rawVal}</span></td>`;
                }

                // Sales Channel Column
                if (col.toLowerCase() === 'sales_channel') {
                    const chanClass = String(rawVal).toLowerCase();
                    return `<td><span class="badge-channel ${chanClass}">${rawVal}</span></td>`;
                }

                // Currency formatting
                if (typeof rawVal === 'number') {
                    if (col.includes('revenue') || col.includes('price') || col.includes('discount')) {
                        return `<td><span style="font-weight: 700; color: var(--emerald-val);">₹${rawVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></td>`;
                    } else {
                        return `<td><span style="font-weight: 600;">${rawVal.toLocaleString()}</span></td>`;
                    }
                }

                return `<td>${displayVal}</td>`;
            }).join('');
            return `<tr>${cells}</tr>`;
        }).join('');
    }

    async function loadKPIs() {
        try {
            const resp = await fetch('/api/kpis');
            if (!resp.ok) return;
            const data = await resp.json();

            kpiValRevenue.textContent = '₹' + Number(data.total_revenue).toLocaleString('en-IN');
            if (data.top_product) {
                kpiValProduct.textContent = data.top_product.name;
                kpiSubProduct.textContent = '₹' + Number(data.top_product.revenue).toLocaleString('en-IN') + ' Net Revenue';
            }
            if (data.top_region) {
                kpiValRegion.textContent = data.top_region.name;
                kpiSubRegion.textContent = '₹' + Number(data.top_region.revenue).toLocaleString('en-IN') + ' Territory Sales';
            }
            if (data.peak_month) {
                kpiValMonth.textContent = formatMonth(data.peak_month.month);
                kpiSubMonth.textContent = '₹' + Number(data.peak_month.revenue).toLocaleString('en-IN') + ' Record Monthly Volume';
            }
        } catch (err) {
            console.warn('Failed to load KPIs:', err);
        }
    }

    async function openSchemaModal() {
        schemaModal.style.display = 'flex';
        schemaModalBody.innerHTML = '<div class="spinner" style="display:block; margin: 20px auto;"></div>';
        try {
            const resp = await fetch('/api/schema');
            const data = await resp.json();

            schemaModalBody.innerHTML = `
                <div style="font-size: 0.92rem;">
                    <p style="margin-bottom: 12px;"><strong>Table:</strong> <code style="color: #38bdf8;">${data.table_name}</code> (${data.total_rows} records)</p>
                    <p style="margin-bottom: 12px;"><strong>Date Span:</strong> <span style="color: #10b981; font-weight: 600;">${data.date_range.min_date} to ${data.date_range.max_date}</span></p>
                    
                    <h4 style="margin: 18px 0 10px; color: #a855f7;">Schema Columns</h4>
                    <table class="data-table" style="margin-bottom: 20px;">
                        <thead><tr><th>Column</th><th>Data Type</th></tr></thead>
                        <tbody>
                            ${data.columns.map(c => `<tr><td><code>${c.name}</code></td><td style="color: #06b6d4; font-weight: 600;">${c.type}</td></tr>`).join('')}
                        </tbody>
                    </table>

                    <h4 style="margin: 18px 0 10px; color: #a855f7;">Catalog Entities</h4>
                    <p><strong>Products:</strong> ${data.products.map(p => `<span class="badge-category accessories" style="margin: 2px;">${p}</span>`).join(' ')}</p>
                    <p style="margin-top: 10px;"><strong>Regions:</strong> ${data.regions.map(r => `<span class="badge-category electronics" style="margin: 2px;">${r}</span>`).join(' ')}</p>
                    <p style="margin-top: 10px;"><strong>Categories:</strong> ${data.categories.map(c => `<span class="badge-category furniture" style="margin: 2px;">${c}</span>`).join(' ')}</p>
                    <p style="margin-top: 10px;"><strong>Sales Channels:</strong> ${data.sales_channels.map(s => `<span class="badge-channel online" style="margin: 2px;">${s}</span>`).join(' ')}</p>
                </div>
            `;
        } catch (e) {
            schemaModalBody.innerHTML = `<p style="color: #f43f5e">Error loading schema: ${e.message}</p>`;
        }
    }

    async function openEtlModal() {
        etlModal.style.display = 'flex';
        etlModalBody.innerHTML = '<div class="spinner" style="display:block; margin: 20px auto;"></div>';
        try {
            const resp = await fetch('/api/reingest', { method: 'POST' });
            const data = await resp.json();

            etlModalBody.innerHTML = `
                <div style="font-size: 0.92rem;">
                    <div style="padding: 14px; background: rgba(16, 185, 129, 0.12); border: 1.5px solid #10b981; border-radius: 10px; margin-bottom: 18px;">
                        <strong style="color: #10b981; font-size: 1.05rem;">ETL Ingestion Status: ${data.status.toUpperCase()}</strong>
                        <p style="margin-top: 6px;">Loaded <strong>${data.records_inserted}</strong> rows into SQLite. Total Net Realized Revenue: <strong style="color: #10b981;">₹${Number(data.total_completed_net_revenue).toLocaleString('en-IN')}</strong></p>
                    </div>

                    <h4 style="margin-bottom: 10px; color: var(--text-primary);">Data Quality Audit Findings:</h4>
                    <ul style="padding-left: 20px; line-height: 1.9; color: var(--text-secondary);">
                        ${data.audit_log.map(log => `<li>${log}</li>`).join('')}
                    </ul>
                </div>
            `;
            // Refresh KPIs after reingest
            loadKPIs();
        } catch (e) {
            etlModalBody.innerHTML = `<p style="color: #f43f5e">Error triggering reingest: ${e.message}</p>`;
        }
    }

    function formatMarkdown(text) {
        if (!text) return '';
        let html = text
            // Markdown bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Bullet points
            .replace(/^• (.*$)/gim, '<li style="margin-left: 20px; margin-bottom: 6px;">$1</li>')
            // Highlight Rupee figures with emerald pill
            .replace(/(₹[0-9,]+(?:\.[0-9]{2})?)/g, '<span class="answer-stat-pill stat-pill-green">$1</span>')
            // Highlight percentages with amber pill
            .replace(/([+-]?[0-9]+(?:\.[0-9]+)?%)/g, '<span class="answer-stat-pill stat-pill-amber">$1</span>')
            // Spacing
            .replace(/\n\n/g, '<br><br>');
        return html;
    }

    function formatMonth(ym) {
        const months = {
            '2026-01': 'Jan 2026', '2026-02': 'Feb 2026', '2026-03': 'Mar 2026',
            '2026-04': 'Apr 2026', '2026-05': 'May 2026', '2026-06': 'Jun 2026'
        };
        return months[ym] || ym;
    }

    function downloadCSV(columns, rows) {
        const header = columns.join(',');
        const csvRows = rows.map(r => columns.map(c => `"${String(r[c] !== null ? r[c] : '').replace(/"/g, '""')}"`).join(','));
        const csvContent = 'data:text/csv;charset=utf-8,' + [header, ...csvRows].join('\n');
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute('download', `sales_bi_export_${Date.now()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function setLoading(isLoading) {
        btnSubmit.disabled = isLoading;
        querySpinner.style.display = isLoading ? 'block' : 'none';
        btnText.style.display = isLoading ? 'none' : 'inline';
        btnIcon.style.display = isLoading ? 'none' : 'inline';
    }

    function showToast(message) {
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.position = 'fixed';
        toast.style.bottom = '24px';
        toast.style.right = '24px';
        toast.style.background = 'linear-gradient(135deg, #10b981, #06b6d4)';
        toast.style.color = '#fff';
        toast.style.padding = '12px 20px';
        toast.style.borderRadius = '10px';
        toast.style.boxShadow = '0 6px 20px rgba(0,0,0,0.35)';
        toast.style.zIndex = '1000';
        toast.style.fontSize = '0.9rem';
        toast.style.fontWeight = '600';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2500);
    }
});
