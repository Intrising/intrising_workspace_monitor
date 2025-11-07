#!/usr/bin/env python3
"""
Workspace Monitor Gateway - HTML Templates
包含所有 Web UI 的 HTML 模板函數
"""


def index_template() -> str:
    """首頁 HTML - 統一 Dashboard"""
    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Workspace Monitor - Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255,255,255,0.3);
            }
            .services {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .service-card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .service-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 15px;
                border-bottom: 2px solid #eee;
            }
            .service-title {
                font-size: 1.5em;
                font-weight: bold;
                color: #333;
            }
            .service-status {
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.9em;
                font-weight: bold;
            }
            .status-online { background: #32cd32; color: white; }
            .status-offline { background: #dc143c; color: white; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin-bottom: 15px;
            }
            .stat-box {
                background: #f5f5f5;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-number {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                color: #666;
                margin-top: 5px;
                font-size: 0.9em;
            }
            .view-details {
                display: inline-block;
                margin-top: 15px;
                padding: 8px 20px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                transition: background 0.3s;
            }
            .view-details:hover {
                background: #764ba2;
            }
            .refresh-btn {
                position: fixed;
                bottom: 30px;
                right: 30px;
                background: #667eea;
                color: white;
                border: none;
                padding: 15px 25px;
                border-radius: 50px;
                font-size: 1em;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                transition: all 0.3s;
            }
            .refresh-btn:hover {
                background: #764ba2;
                transform: translateY(-2px);
                box-shadow: 0 6px 8px rgba(0,0,0,0.3);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Workspace Monitor Dashboard</h1>

                        <div class="nav">
                <a href="/" class="active">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="services" id="services">
                <!-- 動態載入 -->
            </div>
        </div>

        <button class="refresh-btn" onclick="loadData()">🔄 重新整理</button>

        <script>
            async function loadData() {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();

                    const services = document.getElementById('services');

                    // PR Reviewer Card
                    const prData = data.pr_reviewer || {};
                    const prOnline = prData.total !== undefined;
                    const prStats = prData.stats || {};
                    // 計算實際總數（從 stats 計算）
                    const prTotal = (prStats.queued || 0) + (prStats.processing || 0) + (prStats.completed || 0) + (prStats.failed || 0);

                    // Issue Copier Card
                    const issueData = data.issue_copier || {};
                    const issueOnline = issueData.total !== undefined;
                    const issueStats = issueData.stats || {};

                    // Comment Sync Card
                    const commentStats = issueData.comment_stats || {};
                    const commentOnline = commentStats.total !== undefined;

                    // Issue Scorer Card
                    const scorerData = data.issue_scorer || {};
                    const scorerOnline = scorerData.total !== undefined;
                    const scorerStats = scorerData.stats || {};

                    services.innerHTML = `
                        <div class="service-card">
                            <div class="service-header">
                                <div class="service-title">🤖 PR Auto-Reviewer</div>
                                <span class="service-status status-${prOnline ? 'online' : 'offline'}">
                                    ${prOnline ? 'Online' : 'Offline'}
                                </span>
                            </div>
                            ${prOnline ? `
                                <div class="stats-grid">
                                    <div class="stat-box">
                                        <div class="stat-number">${prTotal}</div>
                                        <div class="stat-label">總任務數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${prStats.processing || 0}</div>
                                        <div class="stat-label">處理中</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${prStats.completed || 0}</div>
                                        <div class="stat-label">已完成</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${prStats.failed || 0}</div>
                                        <div class="stat-label">失敗</div>
                                    </div>
                                </div>
                                <a href="/pr-tasks" class="view-details">查看詳情 →</a>
                            ` : '<p style="color: #999;">服務離線</p>'}
                        </div>

                        <div class="service-card">
                            <div class="service-header">
                                <div class="service-title">📋 Issue Auto-Copier</div>
                                <span class="service-status status-${issueOnline ? 'online' : 'offline'}">
                                    ${issueOnline ? 'Online' : 'Offline'}
                                </span>
                            </div>
                            ${issueOnline ? `
                                <div class="stats-grid">
                                    <div class="stat-box">
                                        <div class="stat-number">${issueStats.total || 0}</div>
                                        <div class="stat-label">總複製數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${issueStats.success || 0}</div>
                                        <div class="stat-label">成功</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${issueStats.failed || 0}</div>
                                        <div class="stat-label">失敗</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${issueStats.total_images || 0}</div>
                                        <div class="stat-label">圖片處理</div>
                                    </div>
                                </div>
                                <a href="/issue-copies" class="view-details">查看詳情 →</a>
                            ` : '<p style="color: #999;">服務離線</p>'}
                        </div>

                        <div class="service-card">
                            <div class="service-header">
                                <div class="service-title">💬 Comment Sync</div>
                                <span class="service-status status-${commentOnline ? 'online' : 'offline'}">
                                    ${commentOnline ? 'Online' : 'Offline'}
                                </span>
                            </div>
                            ${commentOnline ? `
                                <div class="stats-grid">
                                    <div class="stat-box">
                                        <div class="stat-number">${commentStats.total || 0}</div>
                                        <div class="stat-label">評論同步數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${commentStats.total_synced || 0}</div>
                                        <div class="stat-label">已同步次數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${commentStats.success || 0}</div>
                                        <div class="stat-label">成功</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${commentStats.failed || 0}</div>
                                        <div class="stat-label">失敗</div>
                                    </div>
                                </div>
                                <a href="/comment-syncs" class="view-details">查看詳情 →</a>
                            ` : '<p style="color: #999;">服務離線</p>'}
                        </div>

                        <div class="service-card">
                            <div class="service-header">
                                <div class="service-title">📊 Issue Quality Scorer</div>
                                <span class="service-status status-${scorerOnline ? 'online' : 'offline'}">
                                    ${scorerOnline ? 'Online' : 'Offline'}
                                </span>
                            </div>
                            ${scorerOnline ? `
                                <div class="stats-grid">
                                    <div class="stat-box">
                                        <div class="stat-number">${scorerStats.total || 0}</div>
                                        <div class="stat-label">總評分數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${scorerStats.completed || 0}</div>
                                        <div class="stat-label">已完成</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${scorerStats.average_score !== null ? scorerStats.average_score : 'N/A'}</div>
                                        <div class="stat-label">平均分數</div>
                                    </div>
                                    <div class="stat-box">
                                        <div class="stat-number">${scorerStats.processing || 0}</div>
                                        <div class="stat-label">處理中</div>
                                    </div>
                                </div>
                                <a href="/issue-scores" class="view-details">查看詳情 →</a>
                            ` : '<p style="color: #999;">服務離線</p>'}
                        </div>
                    `;

                } catch (error) {
                    console.error('載入數據失敗:', error);
                }
            }

            // 頁面載入時執行
            loadData();

        </script>
    </body>
    </html>
    """


def pr_tasks_template() -> str:
    """PR 審查任務列表頁面 HTML"""
    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PR 審查任務 - Workspace Monitor</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255,255,255,0.3);
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .task-item {
                padding: 15px;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .task-item:last-child { border-bottom: none; }
            .task-info h3 {
                color: #333;
                margin-bottom: 5px;
            }
            .task-info h3 a:hover {
                color: #4a90e2 !important;
                text-decoration: underline !important;
            }
            .task-info p {
                color: #666;
                font-size: 0.9em;
            }
            .task-info p a:hover {
                text-decoration: underline !important;
            }
            .status {
                padding: 5px 15px;
                border-radius: 15px;
                font-size: 0.85em;
                font-weight: bold;
            }
            .status.queued { background: #ffd93d; color: #333; }
            .status.pending { background: #ffd93d; color: #333; }
            .status.processing { background: #6bcf7f; color: white; }
            .status.completed { background: #4a90e2; color: white; }
            .status.failed { background: #e74c3c; color: white; }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-box h3 {
                font-size: 2em;
                margin-bottom: 5px;
            }
            .stat-box p {
                font-size: 0.9em;
                opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 PR 審查任務</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks" class="active">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">審查任務列表</h2>
                <div id="tasks">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            async function loadTasks() {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();

                    // 計算總任務數
                    const stats = data.pr_reviewer.stats;
                    const total = (stats.queued || 0) + (stats.processing || 0) + (stats.completed || 0) + (stats.failed || 0);

                    // 顯示統計
                    const statsHtml = `
                        <div class="stat-box">
                            <h3>${total}</h3>
                            <p>總任務數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${stats.queued || 0}</h3>
                            <p>待處理</p>
                        </div>
                        <div class="stat-box">
                            <h3>${stats.processing || 0}</h3>
                            <p>處理中</p>
                        </div>
                        <div class="stat-box">
                            <h3>${stats.completed || 0}</h3>
                            <p>已完成</p>
                        </div>
                        <div class="stat-box">
                            <h3>${stats.failed || 0}</h3>
                            <p>失敗</p>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 顯示任務列表
                    const tasks = data.pr_reviewer.tasks;
                    if (tasks.length === 0) {
                        document.getElementById('tasks').innerHTML = '<p style="text-align: center; color: #666;">暫無任務</p>';
                        return;
                    }

                    const tasksHtml = tasks.map(task => {
                        // 顯示評分（如果有的話）
                        let scoreDisplay = '';
                        if (task.score !== null && task.score !== undefined && task.status === 'completed') {
                            scoreDisplay = `<span style="padding: 5px 15px; background: #667eea; color: white; border-radius: 15px; font-weight: bold;">${task.score}/100</span>`;
                        }

                        // PR 編號連結（優先使用 review_comment_url）
                        const prLink = task.review_comment_url
                            ? `<a href="${task.review_comment_url}" target="_blank" style="color: #4a90e2; text-decoration: none;" title="查看審查評論">#${task.pr_number} 📝</a>`
                            : `#${task.pr_number}`;

                        return `
                        <div class="task-item">
                            <div class="task-info">
                                <h3>
                                    <a href="${task.pr_url}" target="_blank" style="color: #333; text-decoration: none;">${task.pr_title}</a>
                                </h3>
                                <p>
                                    <strong>倉庫:</strong> ${task.repo} |
                                    <strong>PR:</strong> ${prLink} |
                                    <strong>作者:</strong> ${task.pr_author} |
                                    <strong>創建時間:</strong> ${new Date(task.created_at).toLocaleString('zh-TW')}
                                </p>
                                ${task.error_message ? `<p style="color: red;">錯誤: ${task.error_message}</p>` : ''}
                            </div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                ${scoreDisplay}
                                <span class="status ${task.status}">${getStatusText(task.status)}</span>
                            </div>
                        </div>
                        `;
                    }).join('');

                    document.getElementById('tasks').innerHTML = tasksHtml;
                } catch (error) {
                    document.getElementById('tasks').innerHTML = '<p style="text-align: center; color: red;">載入失敗: ' + error.message + '</p>';
                }
            }

            function getStatusText(status) {
                const statusMap = {
                    'queued': '待處理',
                    'pending': '待處理',
                    'processing': '處理中',
                    'completed': '已完成',
                    'failed': '失敗'
                };
                return statusMap[status] || status;
            }

            // 初始載入
            loadTasks();

        </script>
    </body>
    </html>
    """


def issue_copies_template() -> str:
    """Issue 複製記錄頁面 HTML"""
    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Issue 複製記錄 - Workspace Monitor</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255,255,255,0.3);
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .record-item {
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            .record-item:last-child { border-bottom: none; }
            .record-info h3 {
                color: #333;
                margin-bottom: 10px;
            }
            .record-info p {
                color: #666;
                font-size: 0.9em;
                margin: 5px 0;
            }
            .record-info a {
                color: #4a90e2;
                text-decoration: none;
            }
            .record-info a:hover {
                text-decoration: underline;
            }
            .status {
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: bold;
                margin-left: 10px;
            }
            .status.success { background: #6bcf7f; color: white; }
            .status.failed { background: #e74c3c; color: white; }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-box h3 {
                font-size: 2em;
                margin-bottom: 5px;
            }
            .stat-box p {
                font-size: 0.9em;
                opacity: 0.9;
            }
            .labels {
                margin-top: 8px;
            }
            .label {
                display: inline-block;
                padding: 2px 8px;
                margin: 2px;
                border-radius: 10px;
                font-size: 0.75em;
                background: #f0f0f0;
                color: #333;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📋 Issue 複製記錄</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies" class="active">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">複製記錄 (最近 50 筆)</h2>
                <div id="records">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            async function loadRecords() {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();

                    // 顯示統計
                    const statsHtml = `
                        <div class="stat-box">
                            <h3>${data.issue_copier.stats.total}</h3>
                            <p>Issue 複製數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${data.issue_copier.stats.success}</h3>
                            <p>複製成功</p>
                        </div>
                        <div class="stat-box">
                            <h3>${data.issue_copier.stats.failed}</h3>
                            <p>複製失敗</p>
                        </div>
                        <div class="stat-box">
                            <h3>${data.issue_copier.stats.total_images}</h3>
                            <p>圖片處理</p>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 顯示記錄列表
                    const records = data.issue_copier.records;
                    if (records.length === 0) {
                        document.getElementById('records').innerHTML = '<p style="text-align: center; color: #666;">暫無記錄</p>';
                        return;
                    }

                    const recordsHtml = records.map(record => `
                        <div class="record-item">
                            <div class="record-info">
                                <h3>
                                    ${record.source_issue_title}
                                    <span class="status ${record.status}">${record.status === 'success' ? '✓ 成功' : '✗ 失敗'}</span>
                                </h3>
                                <p>
                                    <strong>來源:</strong> <a href="${record.source_issue_url}" target="_blank">${record.source_repo}#${record.source_issue_number}</a> →
                                    <strong>目標:</strong> <a href="${record.target_issue_url}" target="_blank">${record.target_repo}#${record.target_issue_number}</a>
                                </p>
                                <p>
                                    <strong>創建時間:</strong> ${new Date(record.created_at).toLocaleString('zh-TW')}
                                    ${record.completed_at ? ` | <strong>完成時間:</strong> ${new Date(record.completed_at).toLocaleString('zh-TW')}` : ''}
                                    ${record.images_count > 0 ? ` | <strong>圖片:</strong> ${record.images_count} 張` : ''}
                                </p>
                                ${record.source_labels && record.source_labels.length > 0 ? `
                                    <div class="labels">
                                        ${record.source_labels.map(label => `<span class="label">${label}</span>`).join('')}
                                    </div>
                                ` : ''}
                                ${record.error_message ? `<p style="color: red; margin-top: 5px;">錯誤: ${record.error_message}</p>` : ''}
                            </div>
                        </div>
                    `).join('');

                    document.getElementById('records').innerHTML = recordsHtml;

                } catch (error) {
                    document.getElementById('records').innerHTML = '<p style="text-align: center; color: red;">載入失敗: ' + error.message + '</p>';
                }
            }

            // 初始載入
            loadRecords();

        </script>
    </body>
    </html>
    """


def comment_syncs_template() -> str:
    """評論同步記錄頁面 HTML"""
    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>評論同步記錄 - Workspace Monitor</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255,255,255,0.3);
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .record-item {
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            .record-item:last-child { border-bottom: none; }
            .record-info h3 {
                color: #333;
                margin-bottom: 10px;
            }
            .record-info p {
                color: #666;
                font-size: 0.9em;
                margin: 5px 0;
            }
            .record-info a {
                color: #4a90e2;
                text-decoration: none;
            }
            .record-info a:hover {
                text-decoration: underline;
            }
            .status {
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: bold;
                margin-left: 10px;
            }
            .status.success { background: #6bcf7f; color: white; }
            .status.failed { background: #e74c3c; color: white; }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-box h3 {
                font-size: 2em;
                margin-bottom: 5px;
            }
            .stat-box p {
                font-size: 0.9em;
                opacity: 0.9;
            }
            .comment-body {
                color: #666;
                font-style: italic;
                margin-top: 8px;
                padding: 8px;
                background: #f9f9f9;
                border-left: 3px solid #f093fb;
                border-radius: 4px;
            }
            .synced-repos {
                margin-top: 8px;
            }
            .repo-badge {
                display: inline-block;
                padding: 4px 10px;
                margin: 2px;
                background: #e3f2fd;
                color: #1976d2;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: 500;
                text-decoration: none;
                transition: background 0.2s, transform 0.2s;
            }
            a.repo-badge:hover {
                background: #bbdefb;
                transform: translateY(-2px);
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💬 評論同步記錄</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs" class="active">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">同步記錄 (最近 50 筆)</h2>
                <div id="records">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            async function loadRecords() {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();

                    // 顯示統計
                    const commentStats = data.issue_copier.comment_stats || {};
                    const statsHtml = `
                        <div class="stat-box">
                            <h3>${commentStats.total || 0}</h3>
                            <p>評論同步數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${commentStats.total_synced || 0}</h3>
                            <p>已同步次數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${commentStats.success || 0}</h3>
                            <p>成功</p>
                        </div>
                        <div class="stat-box">
                            <h3>${commentStats.failed || 0}</h3>
                            <p>失敗</p>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 顯示 Comment Sync 記錄
                    const commentSyncs = data.issue_copier.comment_syncs || [];
                    if (commentSyncs.length === 0) {
                        document.getElementById('records').innerHTML = '<p style="text-align: center; color: #666;">暫無評論同步記錄</p>';
                        return;
                    }

                    const recordsHtml = commentSyncs.slice(0, 50).map(sync => `
                        <div class="record-item">
                            <div class="record-info">
                                <h3>
                                    💬 ${sync.comment_author} 的評論
                                    <span class="status ${sync.status}">${sync.status === 'success' ? '✓ 成功' : '✗ 失敗'}</span>
                                </h3>
                                <p>
                                    <strong>來源 Issue:</strong> <a href="${sync.source_issue_url}" target="_blank">${sync.source_repo}#${sync.source_issue_number}</a>
                                </p>
                                <div class="synced-repos">
                                    <strong>同步到:</strong>
                                    ${sync.synced_to_repos.map(repo => {
                                        // 從 "Intrising/test-switch#6991" 解析出 URL
                                        const match = repo.match(/^(.+)#(\\d+)$/);
                                        if (match) {
                                            const repoName = match[1];
                                            const issueNum = match[2];
                                            const url = `https://github.com/${repoName}/issues/${issueNum}`;
                                            return `<a href="${url}" target="_blank" class="repo-badge">${repo}</a>`;
                                        }
                                        return `<span class="repo-badge">${repo}</span>`;
                                    }).join(' ')}
                                    <span style="color: #999; font-size: 0.9em;">(${sync.synced_count} 個倉庫)</span>
                                </div>
                                <div class="comment-body">
                                    ${sync.comment_body.length > 300 ? sync.comment_body.substring(0, 300) + '...' : sync.comment_body}
                                </div>
                                <p style="font-size: 0.85em; color: #999; margin-top: 8px;">
                                    <strong>同步時間:</strong> ${new Date(sync.created_at).toLocaleString('zh-TW')}
                                </p>
                                ${sync.error_message ? `<p style="color: red; margin-top: 5px;">錯誤: ${sync.error_message}</p>` : ''}
                            </div>
                        </div>
                    `).join('');

                    document.getElementById('records').innerHTML = recordsHtml;

                } catch (error) {
                    document.getElementById('records').innerHTML = '<p style="text-align: center; color: red;">載入失敗: ' + error.message + '</p>';
                }
            }

            // 初始載入
            loadRecords();

        </script>
    </body>
    </html>
    """


def history_template() -> str:
    """Webhook 歷史記錄頁面 HTML"""
    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>Webhook 歷史 - Workspace Monitor</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1600px; margin: 0 auto; }
            h1 { color: white; text-align: center; margin-bottom: 30px; font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active { background: rgba(255,255,255,0.3); }
            .card {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .stat-box:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.2);
            }
            .stat-box:active {
                transform: translateY(-1px);
            }
            .stat-box h3 { font-size: 2em; margin-bottom: 5px; }
            .stat-box p { font-size: 0.9em; opacity: 0.9; }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            th {
                background: #f5f5f5;
                font-weight: 600;
            }
            .badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: 500;
            }
            .badge.pull_request { background: #e3f2fd; color: #1976d2; }
            .badge.issues { background: #fff3e0; color: #f57c00; }
            .badge.issue_comment { background: #f3e5f5; color: #7b1fa2; }
            .badge.processed { background: #e8f5e9; color: #388e3c; }
            .badge.failed { background: #ffebee; color: #d32f2f; }
            .loading { text-align: center; padding: 40px; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📜 Webhook 歷史記錄</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history" class="active">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">Webhook 事件 (最近 100 筆)</h2>
                <div id="events">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            let allEvents = [];
            let currentFilter = { type: null, status: null };

            async function loadHistory() {
                try {
                    const response = await fetch('/api/webhooks?limit=100');
                    const data = await response.json();
                    allEvents = data.events || [];

                    // 顯示統計（帶過濾功能）
                    const stats = data.stats || {};
                    const statsHtml = `
                        <div class="stat-box" onclick="filterEvents(null, null)" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.total || 0}</h3>
                            <p>總事件數</p>
                        </div>
                        <div class="stat-box" onclick="filterEvents('pull_request', null)" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.by_type?.pull_request || 0}</h3>
                            <p>PR 事件</p>
                        </div>
                        <div class="stat-box" onclick="filterEvents('issues', null)" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.by_type?.issues || 0}</h3>
                            <p>Issue 事件</p>
                        </div>
                        <div class="stat-box" onclick="filterEvents('issue_comment', null)" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.by_type?.issue_comment || 0}</h3>
                            <p>評論事件</p>
                        </div>
                        <div class="stat-box" onclick="filterEvents(null, 'processed')" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.by_status?.processed || 0}</h3>
                            <p>已處理</p>
                        </div>
                        <div class="stat-box" onclick="filterEvents(null, 'failed')" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <h3>${stats.by_status?.failed || 0}</h3>
                            <p>失敗</p>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 初始顯示所有事件
                    renderEvents(allEvents);

                } catch (error) {
                    document.getElementById('events').innerHTML = '<p style="text-align: center; color: red;">載入失敗: ' + error.message + '</p>';
                }
            }

            function filterEvents(type, status) {
                currentFilter.type = type;
                currentFilter.status = status;

                let filtered = allEvents;

                // 根據事件類型過濾
                if (type) {
                    filtered = filtered.filter(e => e.event_type === type);
                }

                // 根據狀態過濾
                if (status) {
                    filtered = filtered.filter(e => e.status === status);
                }

                renderEvents(filtered);

                // 顯示當前過濾條件
                let filterText = '所有事件';
                if (type || status) {
                    const parts = [];
                    if (type) {
                        const typeNames = {
                            'pull_request': 'PR',
                            'issues': 'Issue',
                            'issue_comment': '評論'
                        };
                        parts.push(typeNames[type] || type);
                    }
                    if (status) {
                        const statusNames = {
                            'processed': '已處理',
                            'failed': '失敗'
                        };
                        parts.push(statusNames[status] || status);
                    }
                    filterText = parts.join(' - ');
                }

                document.querySelector('h2').textContent = `Webhook 事件 (${filterText}: ${filtered.length} 筆)`;
            }

            function renderEvents(events) {
                if (events.length === 0) {
                    document.getElementById('events').innerHTML = '<p style="text-align: center; color: #666;">暫無符合條件的記錄</p>';
                    return;
                }

                const eventsHtml = `
                    <table>
                        <thead>
                            <tr>
                                <th>時間</th>
                                <th>事件類型</th>
                                <th>倉庫</th>
                                <th>PR/Issue</th>
                                <th>動作</th>
                                <th>發送者</th>
                                <th>處理服務</th>
                                <th>狀態</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${events.map(event => `
                                <tr>
                                    <td>${new Date(event.created_at).toLocaleString('zh-TW')}</td>
                                    <td><span class="badge ${event.event_type}">${event.event_type}</span></td>
                                    <td>${event.repo_name || '-'}</td>
                                    <td>${event.pr_number ? '#' + event.pr_number : (event.issue_number ? '#' + event.issue_number : '-')}</td>
                                    <td>${event.action || '-'}</td>
                                    <td>${event.sender || '-'}</td>
                                    <td>${event.processed_by || '-'}</td>
                                    <td><span class="badge ${event.status}">${event.status}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
                document.getElementById('events').innerHTML = eventsHtml;
            }

            // 初始載入
            loadHistory();

        </script>
    </body>
    </html>
    """


def issue_scores_template() -> str:
    """Issue 品質評分頁面 HTML"""
    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Issue 品質評分 - Workspace Monitor</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                display: inline-block;
                padding: 10px 20px;
                margin: 0 5px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                text-decoration: none;
                border-radius: 25px;
                transition: all 0.3s;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255, 255, 255, 0.4);
                transform: translateY(-2px);
            }
            .card {
                background: white;
                border-radius: 15px;
                padding: 30px;
                margin-bottom: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }
            .stat-number { font-size: 2em; font-weight: bold; margin-bottom: 5px; }
            .stat-label { font-size: 0.9em; opacity: 0.9; }
            .loading {
                text-align: center;
                padding: 40px;
                color: #999;
                font-size: 1.1em;
            }
            .score-item {
                border-bottom: 1px solid #eee;
                padding: 20px 0;
            }
            .score-item:last-child { border-bottom: none; }
            .score-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .score-title {
                font-size: 1.2em;
                font-weight: 600;
                color: #333;
            }
            .score-meta {
                font-size: 0.9em;
                color: #666;
                margin-bottom: 15px;
            }
            .score-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
                margin: 15px 0;
            }
            .score-dimension {
                background: #f8f9fa;
                padding: 12px;
                border-radius: 8px;
                text-align: center;
            }
            .dimension-label {
                font-size: 0.85em;
                color: #666;
                margin-bottom: 5px;
            }
            .dimension-score {
                font-size: 1.5em;
                font-weight: bold;
                color: #667eea;
            }
            .overall-score {
                font-size: 2em;
                font-weight: bold;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .suggestions {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin-top: 15px;
                border-radius: 5px;
            }
            .suggestions h4 {
                color: #856404;
                margin-bottom: 10px;
            }
            .suggestions ul {
                margin-left: 20px;
                color: #856404;
            }
            .status {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: 600;
            }
            .status.completed { background: #d4edda; color: #155724; }
            .status.processing { background: #fff3cd; color: #856404; }
            .status.queued { background: #d1ecf1; color: #0c5460; }
            .status.failed { background: #f8d7da; color: #721c24; }
            .content-type {
                display: inline-block;
                padding: 3px 10px;
                background: #e7f1ff;
                color: #004085;
                border-radius: 12px;
                font-size: 0.8em;
                margin-left: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Issue 品質評分</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores" class="active">📊 Issue 評分</a>
                <a href="/all-scores">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">評分記錄 (最近 50 筆)</h2>
                <div id="scores">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            // HTML 轉義函數
            function escapeHtml(text) {
                if (!text) return '';
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            async function loadScores() {
                try {
                    // 從 Issue Scorer 服務獲取數據
                    const response = await fetch('/api/issue-scorer/scores?limit=50');
                    const data = await response.json();

                    // 更新統計數據
                    const stats = data.stats || {};
                    const statsHtml = `
                        <div class="stat-box">
                            <div class="stat-number">${stats.total || 0}</div>
                            <div class="stat-label">總評分數</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-number">${stats.completed || 0}</div>
                            <div class="stat-label">已完成</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-number">${stats.processing || 0}</div>
                            <div class="stat-label">處理中</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-number">${stats.average_score !== null && stats.average_score !== undefined ? stats.average_score : 'N/A'}</div>
                            <div class="stat-label">平均分數</div>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 更新評分記錄列表
                    const scores = data.scores || [];
                    if (scores.length === 0) {
                        document.getElementById('scores').innerHTML = '<p style="text-align: center; color: #999;">暫無評分記錄</p>';
                        return;
                    }

                    const scoresHtml = scores.map(score => {
                        const createdAt = new Date(score.created_at).toLocaleString('zh-TW');
                        const statusText = score.status === 'completed' ? '已完成' :
                                         score.status === 'processing' ? '處理中' :
                                         score.status === 'failed' ? '失敗' : '等待中';

                        const scoreDisplay = score.status === 'completed' && score.overall_score
                            ? `${score.overall_score}分`
                            : '';

                        // Issue 編號連結 (優先使用 score_comment_url)
                        const issueLink = score.score_comment_url
                            ? `<a href="${escapeHtml(score.score_comment_url)}" target="_blank" style="color: #667eea; text-decoration: none;" title="查看評分評論">#${score.issue_number}</a>`
                            : `<a href="${escapeHtml(score.issue_url)}" target="_blank" style="color: #667eea; text-decoration: none;">#${score.issue_number}</a>`;

                        const hasDetails = score.status === 'completed' && score.overall_score;
                        const detailsId = `details-${score.score_id.replace(/[^a-zA-Z0-9]/g, '-')}`;

                        return `
                            <div class="score-item">
                                <div class="score-header">
                                    <div>
                                        <a href="${escapeHtml(score.issue_url)}" target="_blank" style="color: #333; text-decoration: none;">
                                            <span class="score-title">${escapeHtml(score.title || 'N/A')}</span>
                                        </a>
                                        <span class="content-type">${score.content_type === 'issue' ? 'Issue' : 'Comment'}</span>
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        ${scoreDisplay ? `<span style="padding: 5px 15px; background: #667eea; color: white; border-radius: 15px; font-weight: bold;">${scoreDisplay}</span>` : ''}
                                        <span class="status ${score.status}">${statusText}</span>
                                        ${hasDetails ? `<button onclick="toggleDetails('${detailsId}')" style="padding: 5px 10px; background: #6c757d; color: white; border: none; border-radius: 5px; cursor: pointer;">詳細</button>` : ''}
                                    </div>
                                </div>
                                <div class="score-meta">
                                    <strong>倉庫:</strong> ${escapeHtml(score.repo_name)} |
                                    <strong>Issue:</strong> ${issueLink} |
                                    <strong>作者:</strong> ${escapeHtml(score.author)} |
                                    <strong>創建時間:</strong> ${createdAt}
                                </div>
                                ${hasDetails ? `
                                    <div id="${detailsId}" style="display: none; margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 15px;">
                                            <div><strong>📝 格式:</strong> ${score.format_score}分 - ${escapeHtml(score.format_feedback || '')}</div>
                                            <div><strong>📋 內容:</strong> ${score.content_score}分 - ${escapeHtml(score.content_feedback || '')}</div>
                                            <div><strong>🎯 清晰度:</strong> ${score.clarity_score}分 - ${escapeHtml(score.clarity_feedback || '')}</div>
                                            <div><strong>⚙️ 可操作性:</strong> ${score.actionability_score}分 - ${escapeHtml(score.actionability_feedback || '')}</div>
                                        </div>
                                        ${score.suggestions ? `
                                            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin-bottom: 15px; border-radius: 4px;">
                                                <strong style="color: #856404;">💡 改進建議:</strong>
                                                <ul style="margin: 10px 0 0 20px; color: #856404;">
                                                    ${score.suggestions.split('\\n').filter(s => s.trim()).map(s => '<li>' + escapeHtml(s) + '</li>').join('')}
                                                </ul>
                                            </div>
                                        ` : ''}
                                        <div style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
                                            <label style="display: block; font-weight: bold; margin-bottom: 8px; color: #495057;">
                                                🗣️ 你的意見（用於訓練改進）:
                                            </label>
                                            <textarea id="feedback-${detailsId}" style="width: 100%; min-height: 80px; padding: 10px; border: 1px solid #ced4da; border-radius: 4px; font-size: 14px; resize: vertical;" placeholder="例如：這個評分太高/太低，因為...">${escapeHtml(score.user_feedback || '')}</textarea>
                                            <div style="display: flex; gap: 10px; margin-top: 10px;">
                                                <button onclick="saveFeedback('${score.score_id}', '${detailsId}')" style="padding: 8px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
                                                    💾 儲存意見
                                                </button>
                                                <button onclick="toggleIgnore('${score.score_id}', ${score.ignored || false})" id="ignore-btn-${detailsId}" style="padding: 8px 20px; background: ${score.ignored ? '#6c757d' : '#dc3545'}; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
                                                    ${score.ignored ? '✓ 已忽略' : '🚫 標記忽略'}
                                                </button>
                                            </div>
                                            <span id="feedback-msg-${detailsId}" style="margin-top: 10px; display: inline-block; color: #28a745;"></span>
                                        </div>
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    }).join('');

                    document.getElementById('scores').innerHTML = scoresHtml;

                } catch (error) {
                    console.error('載入評分記錄失敗:', error);
                    document.getElementById('scores').innerHTML = '<p style="color: #dc3545; text-align: center;">載入失敗，請稍後再試</p>';
                }
            }

            // 展開/收合詳細資訊
            function toggleDetails(detailsId) {
                const element = document.getElementById(detailsId);
                if (element.style.display === 'none') {
                    element.style.display = 'block';
                } else {
                    element.style.display = 'none';
                }
            }

            // 儲存使用者反饋
            async function saveFeedback(scoreId, detailsId) {
                const feedbackTextarea = document.getElementById(`feedback-${detailsId}`);
                const messageSpan = document.getElementById(`feedback-msg-${detailsId}`);
                const feedback = feedbackTextarea.value.trim();

                try {
                    // URL encode the scoreId to handle special characters like # and /
                    const encodedScoreId = encodeURIComponent(scoreId);
                    const response = await fetch(`/api/issue-scorer/scores/${encodedScoreId}/feedback`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ user_feedback: feedback })
                    });

                    if (response.ok) {
                        messageSpan.textContent = '✅ 已儲存';
                        messageSpan.style.color = '#28a745';
                        setTimeout(() => { messageSpan.textContent = ''; }, 3000);
                    } else {
                        throw new Error('儲存失敗');
                    }
                } catch (error) {
                    messageSpan.textContent = '❌ 儲存失敗';
                    messageSpan.style.color = '#dc3545';
                    console.error('儲存反饋失敗:', error);
                }
            }

            async function toggleIgnore(scoreId, currentIgnored) {
                try {
                    const encodedScoreId = encodeURIComponent(scoreId);
                    const response = await fetch(`/api/issue-scorer/scores/${encodedScoreId}/ignore`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ ignored: !currentIgnored })
                    });

                    if (response.ok) {
                        // 重新加載數據以更新 UI
                        loadScores();
                    } else {
                        alert('操作失敗，請重試');
                    }
                } catch (error) {
                    console.error('切換忽略狀態失敗:', error);
                    alert('操作失敗，請重試');
                }
            }

            // 頁面載入時執行
            loadScores();

        </script>
    </body>
    </html>
    """


def all_scores_template() -> str:
    """統一評分統計頁面 HTML - Issue 和 PR 評分"""
    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>評分統計 - Workspace Monitor</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 1600px; margin: 0 auto; }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .nav {
                text-align: center;
                margin-bottom: 30px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                padding: 12px 25px;
                margin: 0 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 5px;
                transition: background 0.3s;
                display: inline-block;
            }
            .nav a:hover, .nav a.active {
                background: rgba(255,255,255,0.3);
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .stat-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-box h3 {
                font-size: 2em;
                margin-bottom: 5px;
            }
            .stat-box p {
                font-size: 0.9em;
                opacity: 0.9;
            }
            .score-item {
                padding: 15px;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .score-item:last-child { border-bottom: none; }
            .score-info h3 {
                color: #333;
                margin-bottom: 5px;
                font-size: 1.1em;
            }
            .score-info p {
                color: #666;
                font-size: 0.9em;
                margin: 3px 0;
            }
            .score-info a {
                color: #4a90e2;
                text-decoration: none;
            }
            .score-info a:hover {
                text-decoration: underline;
            }
            .score-badge {
                padding: 8px 15px;
                border-radius: 20px;
                font-size: 1.2em;
                font-weight: bold;
                min-width: 70px;
                text-align: center;
            }
            .score-90 { background: #6bcf7f; color: white; }
            .score-80 { background: #85e085; color: white; }
            .score-70 { background: #ffd93d; color: #333; }
            .score-60 { background: #ffb84d; color: #333; }
            .score-low { background: #e74c3c; color: white; }
            .type-badge {
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.8em;
                font-weight: bold;
                margin-left: 10px;
            }
            .type-issue { background: #3498db; color: white; }
            .type-pr { background: #9b59b6; color: white; }
            .type-comment { background: #1abc9c; color: white; }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .filter-tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            .filter-tab {
                padding: 10px 20px;
                background: #f0f0f0;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .filter-tab.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .stat-box {
                cursor: pointer;
                transition: transform 0.3s, box-shadow 0.3s, border 0.3s, background 0.3s;
                border: 5px solid transparent;
                position: relative;
            }
            .stat-box:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.2);
            }
            .stat-box.selected {
                border: 5px solid #ff9800;
                box-shadow: 0 0 30px 5px rgba(255, 152, 0, 0.8), 0 0 60px 10px rgba(255, 152, 0, 0.4);
                transform: scale(1.1);
                background: linear-gradient(135deg, #ff9800 0%, #ff5722 100%) !important;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% {
                    box-shadow: 0 0 30px 5px rgba(255, 152, 0, 0.8), 0 0 60px 10px rgba(255, 152, 0, 0.4);
                }
                50% {
                    box-shadow: 0 0 40px 8px rgba(255, 152, 0, 1), 0 0 80px 15px rgba(255, 152, 0, 0.6);
                }
            }
            .export-btn {
                padding: 8px 16px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .export-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            }
            .export-btn:active {
                transform: translateY(0);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 評分統計總覽</h1>

                        <div class="nav">
                <a href="/">📊 Dashboard</a>
                <a href="/pr-tasks">🔍 PR 審查</a>
                <a href="/issue-copies">📋 Issue 複製</a>
                <a href="/comment-syncs">💬 評論同步</a>
                <a href="/issue-scores">📊 Issue 評分</a>
                <a href="/all-scores" class="active">📈 評分統計</a>
                <a href="/history">📜 歷史記錄</a>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計圖表</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px;">
                    <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h3 style="text-align: center; margin-bottom: 15px; color: #333;">類型分布</h3>
                        <canvas id="typeChart" style="max-height: 250px;"></canvas>
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h3 style="text-align: center; margin-bottom: 15px; color: #333;">分數分布</h3>
                        <canvas id="scoreChart" style="max-height: 250px;"></canvas>
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h3 style="text-align: center; margin-bottom: 15px; color: #333;">人員貢獻占比</h3>
                        <canvas id="authorChart" style="max-height: 250px;"></canvas>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">統計數據</h2>
                <div class="stats" id="stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 20px;">人員統計</h2>
                <div class="stats" id="author-stats">
                    <div class="loading">載入中...</div>
                </div>
            </div>

            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h2 style="margin: 0;">評分記錄</h2>
                    <div style="display: flex; gap: 10px;">
                        <button onclick="exportPDF(event)" class="export-btn">📄 匯出 PDF 報表</button>
                        <button onclick="exportCompleteCSV()" class="export-btn">📥 匯出完整報表 (CSV)</button>
                    </div>
                </div>
                <div class="filter-tabs" id="filter-tabs">
                    <button class="filter-tab active" data-filter="all">全部</button>
                    <button class="filter-tab" data-filter="issue">Issue</button>
                    <button class="filter-tab" data-filter="pr">PR</button>
                </div>
                <div id="scores">
                    <div class="loading">載入中...</div>
                </div>
            </div>
        </div>

        <script>
            let allScores = [];
            let currentFilter = 'all';
            let currentAuthor = null; // 當前選中的作者

            async function loadScores() {
                try {
                    const response = await fetch('/api/all-scores?limit=200');
                    const data = await response.json();

                    allScores = data.scores || [];

                    // 計算統計數據
                    const totalScores = allScores.length;
                    const avgScore = totalScores > 0
                        ? Math.round(allScores.reduce((sum, s) => sum + (s.score || 0), 0) / totalScores)
                        : 0;

                    const issueCount = allScores.filter(s => s.type === 'issue').length;
                    const prCount = allScores.filter(s => s.type === 'pr').length;

                    const highScores = allScores.filter(s => s.score >= 80).length;
                    const lowScores = allScores.filter(s => s.score < 60).length;

                    // 按人員統計
                    const byAuthor = {};
                    allScores.forEach(s => {
                        if (!byAuthor[s.author]) {
                            byAuthor[s.author] = { total: 0, sum: 0 };
                        }
                        byAuthor[s.author].total++;
                        byAuthor[s.author].sum += s.score || 0;
                    });

                    // 顯示統計數據
                    const statsHtml = `
                        <div class="stat-box">
                            <h3>${totalScores}</h3>
                            <p>總評分數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${avgScore}</h3>
                            <p>平均分數</p>
                        </div>
                        <div class="stat-box">
                            <h3>${issueCount}</h3>
                            <p>Issue 評分</p>
                        </div>
                        <div class="stat-box">
                            <h3>${prCount}</h3>
                            <p>PR 評分</p>
                        </div>
                        <div class="stat-box">
                            <h3>${highScores}</h3>
                            <p>高分 (≥80)</p>
                        </div>
                        <div class="stat-box">
                            <h3>${lowScores}</h3>
                            <p>低分 (<60)</p>
                        </div>
                    `;
                    document.getElementById('stats').innerHTML = statsHtml;

                    // 按人員統計平均分數（分開顯示）
                    const authorStats = Object.entries(byAuthor)
                        .map(([author, stats]) => ({
                            author,
                            avg: Math.round(stats.sum / stats.total),
                            count: stats.total
                        }))
                        .sort((a, b) => b.avg - a.avg);

                    let authorStatsHtml = '';
                    authorStats.forEach(stat => {
                        authorStatsHtml += `
                            <div class="stat-box" data-author="${stat.author}" onclick="filterByAuthor('${stat.author}')">
                                <h3>${stat.avg}</h3>
                                <p>${stat.author} (${stat.count})</p>
                            </div>
                        `;
                    });

                    document.getElementById('author-stats').innerHTML = authorStatsHtml || '<p style="text-align: center; color: #666;">暫無人員統計</p>';

                    // 繪製圓餅圖
                    renderCharts(issueCount, prCount, highScores, lowScores, authorStats);

                    // 顯示評分列表
                    renderScores();

                } catch (error) {
                    document.getElementById('scores').innerHTML = '<p style="text-align: center; color: red;">載入失敗: ' + error.message + '</p>';
                }
            }

            // 儲存圖表實例以便更新
            let typeChart = null;
            let scoreChart = null;
            let authorChart = null;

            function renderCharts(issueCount, prCount, highScores, lowScores, authorStats) {
                const mediumScores = allScores.filter(s => s.score >= 60 && s.score < 80).length;

                // 1. 類型分布圓餅圖
                const typeCtx = document.getElementById('typeChart').getContext('2d');
                if (typeChart) typeChart.destroy();
                typeChart = new Chart(typeCtx, {
                    type: 'pie',
                    data: {
                        labels: ['Issue', 'PR'],
                        datasets: [{
                            data: [issueCount, prCount],
                            backgroundColor: ['#3498db', '#9b59b6'],
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 15,
                                    font: { size: 12 }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = issueCount + prCount;
                                        const percent = Math.round((context.parsed / total) * 100);
                                        return context.label + ': ' + context.parsed + ' (' + percent + '%)';
                                    }
                                }
                            }
                        }
                    }
                });

                // 2. 分數分布圓餅圖
                const scoreCtx = document.getElementById('scoreChart').getContext('2d');
                if (scoreChart) scoreChart.destroy();
                scoreChart = new Chart(scoreCtx, {
                    type: 'pie',
                    data: {
                        labels: ['高分 (≥80)', '中分 (60-79)', '低分 (<60)'],
                        datasets: [{
                            data: [highScores, mediumScores, lowScores],
                            backgroundColor: ['#6bcf7f', '#ffd93d', '#e74c3c'],
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 15,
                                    font: { size: 12 }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = highScores + mediumScores + lowScores;
                                        const percent = Math.round((context.parsed / total) * 100);
                                        return context.label + ': ' + context.parsed + ' (' + percent + '%)';
                                    }
                                }
                            }
                        }
                    }
                });

                // 3. 人員貢獻占比圓餅圖 (顯示前8名,其他合併)
                const topAuthors = authorStats.slice(0, 8);
                const othersCount = authorStats.slice(8).reduce((sum, a) => sum + a.count, 0);

                const authorLabels = topAuthors.map(a => a.author);
                const authorData = topAuthors.map(a => a.count);

                if (othersCount > 0) {
                    authorLabels.push('其他');
                    authorData.push(othersCount);
                }

                // 生成漂亮的顏色
                const colors = [
                    '#3498db', '#9b59b6', '#1abc9c', '#f39c12',
                    '#e74c3c', '#34495e', '#16a085', '#27ae60',
                    '#95a5a6'
                ];

                const authorCtx = document.getElementById('authorChart').getContext('2d');
                if (authorChart) authorChart.destroy();
                authorChart = new Chart(authorCtx, {
                    type: 'pie',
                    data: {
                        labels: authorLabels,
                        datasets: [{
                            data: authorData,
                            backgroundColor: colors,
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 10,
                                    font: { size: 11 }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = authorData.reduce((sum, v) => sum + v, 0);
                                        const percent = Math.round((context.parsed / total) * 100);
                                        return context.label + ': ' + context.parsed + ' 筆 (' + percent + '%)';
                                    }
                                }
                            }
                        }
                    }
                });
            }

            function renderScores() {
                let filteredScores = currentFilter === 'all'
                    ? allScores
                    : allScores.filter(s => s.type === currentFilter);

                // 如果有選中的作者,進一步過濾
                if (currentAuthor) {
                    filteredScores = filteredScores.filter(s => s.author === currentAuthor);
                }

                if (filteredScores.length === 0) {
                    document.getElementById('scores').innerHTML = '<p style="text-align: center; color: #666;">暫無評分記錄</p>';
                    return;
                }

                const scoresHtml = filteredScores.map(score => {
                    const scoreClass = score.score >= 90 ? 'score-90' :
                                     score.score >= 80 ? 'score-80' :
                                     score.score >= 70 ? 'score-70' :
                                     score.score >= 60 ? 'score-60' : 'score-low';

                    const typeClass = score.type === 'issue' ? 'type-issue' :
                                    score.content_type === 'comment' ? 'type-comment' : 'type-pr';
                    const typeText = score.type === 'issue' ?
                                   (score.content_type === 'comment' ? 'Comment' : 'Issue') : 'PR';

                    // 如果被忽略，添加灰色半透明覆蓋
                    const ignoredStyle = score.ignored ? 'opacity: 0.5; background-color: #f0f0f0;' : '';
                    const ignoredBadge = score.ignored ? '<span class="type-badge" style="background-color: #6c757d; color: white; margin-left: 10px;">已忽略</span>' : '';

                    return `
                        <div class="score-item" style="${ignoredStyle}">
                            <div class="score-info">
                                <h3>
                                    <a href="${score.url}" target="_blank">${score.title || 'N/A'}</a>
                                    <span class="type-badge ${typeClass}">${typeText}</span>
                                    ${ignoredBadge}
                                </h3>
                                <p>
                                    <strong>作者:</strong> ${score.author} |
                                    <strong>倉庫:</strong> ${score.repo} |
                                    <strong>編號:</strong> <a href="${score.url}" target="_blank">#${score.number}</a> |
                                    <strong>時間:</strong> ${new Date(score.created_at).toLocaleString('zh-TW')}
                                </p>
                                <p>
                                    <strong>連結:</strong> <a href="${score.url}" target="_blank">${score.url}</a>
                                </p>
                            </div>
                            <div class="score-badge ${scoreClass}">${score.score}</div>
                        </div>
                    `;
                }).join('');

                document.getElementById('scores').innerHTML = scoresHtml;
            }

            // 按作者過濾
            function filterByAuthor(author) {
                // 如果點擊同一個作者,取消選擇
                if (currentAuthor === author) {
                    currentAuthor = null;
                    // 移除所有 selected class
                    document.querySelectorAll('.stat-box.selected').forEach(box => {
                        box.classList.remove('selected');
                    });
                } else {
                    currentAuthor = author;
                    // 移除所有 selected class
                    document.querySelectorAll('.stat-box.selected').forEach(box => {
                        box.classList.remove('selected');
                    });
                    // 添加 selected class 到點擊的卡片
                    document.querySelectorAll('.stat-box').forEach(box => {
                        if (box.dataset.author === author) {
                            box.classList.add('selected');
                        }
                    });
                }
                renderScores();
            }

            // 匯出 PDF 報表函數(使用圖片替代中文文字)
            async function exportPDF(event) {
                const button = event.currentTarget;
                const originalText = button.textContent;

                try {
                    button.textContent = '⏳ 生成中...';
                    button.disabled = true;

                    if (allScores.length === 0) {
                        alert('目前沒有可匯出的資料');
                        return;
                    }

                    // 使用 jsPDF
                    const { jsPDF } = window.jspdf;
                    const doc = new jsPDF('p', 'mm', 'a4');
                    let yPos = 20;
                    const pageWidth = doc.internal.pageSize.getWidth();
                    const pageHeight = doc.internal.pageSize.getHeight();

                    // 計算日期範圍
                    const dates = allScores.map(s => new Date(s.created_at)).sort((a, b) => a - b);
                    const startDate = dates[0].toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
                    const endDate = dates[dates.length - 1].toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
                    const dateRange = `${startDate} - ${endDate}`;

                    // 計算統計數據
                    const totalScores = allScores.length;
                    const issueCount = allScores.filter(s => s.type === 'issue').length;
                    const prCount = allScores.filter(s => s.type === 'pr').length;
                    const highScores = allScores.filter(s => s.score >= 80).length;
                    const mediumScores = allScores.filter(s => s.score >= 60 && s.score < 80).length;
                    const lowScores = allScores.filter(s => s.score < 60).length;

                    // 計算每個人的統計
                    const byAuthor = {};
                    allScores.forEach(s => {
                        if (!byAuthor[s.author]) {
                            byAuthor[s.author] = { total: 0, sum: 0 };
                        }
                        byAuthor[s.author].total++;
                        byAuthor[s.author].sum += s.score || 0;
                    });

                    const authorStats = Object.entries(byAuthor)
                        .map(([author, data]) => ({
                            author,
                            count: data.total,
                            avg: Math.round(data.sum / data.total)
                        }))
                        .sort((a, b) => b.avg - a.avg);

                    // 第一頁：標題和日期範圍
                    doc.setFontSize(20);
                    doc.text('Scoring Report', pageWidth / 2, yPos, { align: 'center' });
                    yPos += 10;
                    doc.setFontSize(10);
                    doc.text(dateRange, pageWidth / 2, yPos, { align: 'center' });
                    yPos += 15;

                    // 擷取圖表為圖片並加入 PDF（改進版：加上日期範圍）
                    const chartContainers = [
                        { id: 'typeChart', title: `Type Distribution (${dateRange})` },
                        { id: 'scoreChart', title: 'Score Distribution' },
                        { id: 'authorChart', title: 'Author Contribution' }
                    ];

                    for (const chart of chartContainers) {
                        const canvas = document.getElementById(chart.id);
                        if (canvas) {
                            try {
                                // 使用 html2canvas 轉換圖表
                                const chartImage = await html2canvas(canvas.parentElement, {
                                    backgroundColor: '#ffffff',
                                    scale: 2
                                });

                                const imgData = chartImage.toDataURL('image/png');
                                const imgWidth = 90;
                                const imgHeight = (chartImage.height * imgWidth) / chartImage.width;

                                // 檢查是否需要換頁
                                if (yPos + imgHeight > pageHeight - 20) {
                                    doc.addPage();
                                    yPos = 20;
                                }

                                doc.setFontSize(12);
                                doc.text(chart.title, pageWidth / 2, yPos, { align: 'center' });
                                yPos += 8;
                                doc.addImage(imgData, 'PNG', (pageWidth - imgWidth) / 2, yPos, imgWidth, imgHeight);
                                yPos += imgHeight + 15;
                            } catch (err) {
                                console.warn(`Failed to capture chart ${chart.id}:`, err);
                            }
                        }
                    }

                    // 新頁面：統計摘要（加入每個人的平均分數和數量）
                    doc.addPage();
                    yPos = 20;
                    doc.setFontSize(16);
                    doc.text('Statistics Summary', pageWidth / 2, yPos, { align: 'center' });
                    yPos += 15;

                    // 總體統計
                    doc.setFontSize(11);
                    doc.setFont(undefined, 'bold');
                    doc.text('Overall Statistics:', 20, yPos);
                    yPos += 7;
                    doc.setFont(undefined, 'normal');

                    const stats = [
                        `Total Scores: ${totalScores}`,
                        `Issues: ${issueCount} (${Math.round((issueCount/totalScores)*100)}%)`,
                        `PRs: ${prCount} (${Math.round((prCount/totalScores)*100)}%)`,
                        '',
                        `High Scores (>=80): ${highScores} (${Math.round((highScores/totalScores)*100)}%)`,
                        `Medium Scores (60-79): ${mediumScores} (${Math.round((mediumScores/totalScores)*100)}%)`,
                        `Low Scores (<60): ${lowScores} (${Math.round((lowScores/totalScores)*100)}%)`
                    ];

                    stats.forEach(line => {
                        doc.text(line, 25, yPos);
                        yPos += 7;
                    });

                    yPos += 5;

                    // 每個人的平均分數和數量（改進版：更漂亮的表格）
                    doc.setFont(undefined, 'bold');
                    doc.text('Author Statistics:', 20, yPos);
                    yPos += 10;

                    // 繪製表格框線和背景
                    const tableStartY = yPos;
                    const rowHeight = 7;
                    const colWidths = [15, 60, 30, 25]; // Rank, Author, Avg Score, Count
                    const colStartX = [15, 30, 90, 120];

                    // 表頭背景
                    doc.setFillColor(70, 130, 180); // Steel blue
                    doc.rect(15, yPos - 5, 130, rowHeight, 'F');

                    // 表頭文字（白色）
                    doc.setTextColor(255, 255, 255);
                    doc.setFontSize(10);
                    doc.text('Rank', colStartX[0] + 2, yPos);
                    doc.text('Author', colStartX[1] + 2, yPos);
                    doc.text('Avg Score', colStartX[2] + 2, yPos);
                    doc.text('Count', colStartX[3] + 2, yPos);
                    yPos += rowHeight;

                    // 恢復黑色文字
                    doc.setTextColor(0, 0, 0);
                    doc.setFont(undefined, 'normal');
                    doc.setFontSize(9);

                    // 每個作者的數據（帶條紋背景）
                    authorStats.forEach((stat, index) => {
                        if (yPos > pageHeight - 20) {
                            doc.addPage();
                            yPos = 20;
                        }

                        // 交替背景色
                        if (index % 2 === 0) {
                            doc.setFillColor(245, 245, 245); // Light gray
                            doc.rect(15, yPos - 5, 130, rowHeight, 'F');
                        }

                        // 排名（根據分數設定顏色）
                        if (index === 0) {
                            doc.setTextColor(218, 165, 32); // Gold
                            doc.setFont(undefined, 'bold');
                        } else if (index === 1) {
                            doc.setTextColor(192, 192, 192); // Silver
                            doc.setFont(undefined, 'bold');
                        } else if (index === 2) {
                            doc.setTextColor(205, 127, 50); // Bronze
                            doc.setFont(undefined, 'bold');
                        } else {
                            doc.setTextColor(0, 0, 0);
                            doc.setFont(undefined, 'normal');
                        }

                        doc.text(String(index + 1), colStartX[0] + 5, yPos);

                        // 其他欄位（黑色）
                        doc.setTextColor(0, 0, 0);
                        doc.setFont(undefined, 'normal');
                        doc.text((stat.author || '').substring(0, 28), colStartX[1] + 2, yPos);

                        // 平均分數（根據分數設定顏色）
                        if (stat.avg >= 80) {
                            doc.setTextColor(0, 128, 0); // Green
                        } else if (stat.avg >= 60) {
                            doc.setTextColor(255, 140, 0); // Orange
                        } else {
                            doc.setTextColor(255, 0, 0); // Red
                        }
                        doc.setFont(undefined, 'bold');
                        doc.text(String(stat.avg), colStartX[2] + 2, yPos);

                        doc.setTextColor(0, 0, 0);
                        doc.setFont(undefined, 'normal');
                        doc.text(String(stat.count), colStartX[3] + 2, yPos);

                        yPos += rowHeight;
                    });

                    // 繪製表格外框
                    doc.setDrawColor(0, 0, 0);
                    doc.rect(15, tableStartY - 5, 130, (authorStats.length + 1) * rowHeight);

                    // 新頁面：全部詳細記錄
                    doc.addPage();
                    yPos = 20;
                    doc.setFontSize(16);
                    doc.text(`All Records (${totalScores} items)`, pageWidth / 2, yPos, { align: 'center' });
                    yPos += 15;

                    doc.setFontSize(8);
                    const records = allScores; // 全部記錄，不限制數量

                    // 表頭
                    doc.setFont(undefined, 'bold');
                    doc.text('Type', 12, yPos);
                    doc.text('Score', 30, yPos);
                    doc.text('Author', 48, yPos);
                    doc.text('Repo', 85, yPos);
                    doc.text('Num', 135, yPos);
                    doc.text('Date', 155, yPos);
                    yPos += 5;
                    doc.setFont(undefined, 'normal');

                    // 記錄（Num 欄位加上超連結）
                    records.forEach((score, index) => {
                        if (yPos > pageHeight - 15) {
                            doc.addPage();
                            yPos = 20;
                            // 重新繪製表頭
                            doc.setFont(undefined, 'bold');
                            doc.text('Type', 12, yPos);
                            doc.text('Score', 30, yPos);
                            doc.text('Author', 48, yPos);
                            doc.text('Repo', 85, yPos);
                            doc.text('Num', 135, yPos);
                            doc.text('Date', 155, yPos);
                            yPos += 5;
                            doc.setFont(undefined, 'normal');
                        }

                        const dateStr = new Date(score.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

                        doc.text(score.type === 'issue' ? 'Issue' : 'PR', 12, yPos);
                        doc.text(String(score.score || 0), 30, yPos);
                        doc.text((score.author || '').substring(0, 18), 48, yPos);
                        doc.text((score.repo || '').split('/').pop().substring(0, 25), 85, yPos);

                        // Num 欄位加上超連結（藍色、底線）
                        const numText = String(score.number || '');
                        if (score.url) {
                            doc.setTextColor(0, 0, 255); // Blue
                            doc.textWithLink(numText, 135, yPos, { url: score.url });
                            doc.setTextColor(0, 0, 0); // Reset to black
                        } else {
                            doc.text(numText, 135, yPos);
                        }

                        doc.text(dateStr, 155, yPos);
                        yPos += 5;
                    });

                    // 儲存 PDF
                    const now = new Date();
                    const timestamp = now.toISOString().split('T')[0];
                    doc.save(`Scoring_Report_${timestamp}.pdf`);

                } catch (error) {
                    console.error('PDF 生成失敗:', error);
                    alert('PDF 生成失敗: ' + error.message);
                } finally {
                    button.textContent = originalText;
                    button.disabled = false;
                }
            }

            // 匯出完整報表 CSV 函數(包含統計摘要和詳細記錄)
            function exportCompleteCSV() {
                if (allScores.length === 0) {
                    alert('目前沒有可匯出的資料');
                    return;
                }

                // 計算統計數據
                const totalScores = allScores.length;
                const totalSum = allScores.reduce((sum, s) => sum + (s.score || 0), 0);
                const avgScore = totalScores > 0 ? Math.round(totalSum / totalScores) : 0;
                const issueCount = allScores.filter(s => s.type === 'issue').length;
                const prCount = allScores.filter(s => s.type === 'pr').length;
                const highScores = allScores.filter(s => s.score >= 80).length;
                const mediumScores = allScores.filter(s => s.score >= 60 && s.score < 80).length;
                const lowScores = allScores.filter(s => s.score < 60).length;

                // 按人員統計
                const byAuthor = {};
                allScores.forEach(s => {
                    if (!byAuthor[s.author]) {
                        byAuthor[s.author] = {
                            total: 0,
                            sum: 0,
                            high: 0,
                            medium: 0,
                            low: 0,
                            issues: 0,
                            prs: 0
                        };
                    }
                    byAuthor[s.author].total++;
                    byAuthor[s.author].sum += s.score || 0;
                    if (s.score >= 80) byAuthor[s.author].high++;
                    else if (s.score >= 60) byAuthor[s.author].medium++;
                    else byAuthor[s.author].low++;

                    if (s.type === 'issue') byAuthor[s.author].issues++;
                    else byAuthor[s.author].prs++;
                });

                const authorStats = Object.entries(byAuthor)
                    .map(([author, data]) => ({
                        author,
                        count: data.total,
                        avg: Math.round(data.sum / data.total),
                        high: data.high,
                        medium: data.medium,
                        low: data.low,
                        issues: data.issues,
                        prs: data.prs,
                        highPercent: Math.round((data.high / data.total) * 100)
                    }))
                    .sort((a, b) => b.avg - a.avg);

                // 建立 CSV 內容
                const csvRows = [];

                // 報表標題
                csvRows.push('評分完整報表');
                csvRows.push(`生成時間,${new Date().toLocaleString('zh-TW')}`);
                csvRows.push('');
                csvRows.push('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                csvRows.push('');

                // 第一部分：總體統計
                csvRows.push('📊 統計摘要');
                csvRows.push('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                csvRows.push('');
                csvRows.push('統計項目,數值,占比');
                csvRows.push(`總評分數,${totalScores},100%`);
                csvRows.push(`平均分數,${avgScore},—`);
                csvRows.push('');
                csvRows.push('【類型分布】');
                csvRows.push(`Issue 評分,${issueCount},${Math.round((issueCount/totalScores)*100)}%`);
                csvRows.push(`PR 評分,${prCount},${Math.round((prCount/totalScores)*100)}%`);
                csvRows.push('');
                csvRows.push('【分數分布】');
                csvRows.push(`高分 (≥80),${highScores},${Math.round((highScores/totalScores)*100)}%`);
                csvRows.push(`中分 (60-79),${mediumScores},${Math.round((mediumScores/totalScores)*100)}%`);
                csvRows.push(`低分 (<60),${lowScores},${Math.round((lowScores/totalScores)*100)}%`);
                csvRows.push('');
                csvRows.push('');

                // 第二部分：人員統計
                csvRows.push('👥 人員統計');
                csvRows.push('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                csvRows.push('');
                csvRows.push('排名,作者,平均分數,總數,高分,中分,低分,Issue,PR,高分率');
                authorStats.forEach((stat, index) => {
                    csvRows.push(`${index + 1},${stat.author},${stat.avg},${stat.count},${stat.high},${stat.medium},${stat.low},${stat.issues},${stat.prs},${stat.highPercent}%`);
                });
                csvRows.push('');
                csvRows.push('');

                // 第三部分：詳細記錄
                csvRows.push('📋 詳細記錄');
                csvRows.push('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                csvRows.push('');
                csvRows.push('類型,評分,等級,作者,倉庫,編號,標題,建立日期,建立時間,URL');

                allScores.forEach(score => {
                    // 格式化日期時間
                    const dateObj = new Date(score.created_at);
                    const date = dateObj.toLocaleDateString('zh-TW');
                    const time = dateObj.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' });

                    // 判斷等級
                    let grade = '低分';
                    if (score.score >= 80) grade = '高分';
                    else if (score.score >= 60) grade = '中分';

                    const row = [
                        score.type === 'issue' ? 'Issue' : 'PR',
                        score.score || 0,
                        grade,
                        score.author || '',
                        score.repo || '',
                        score.number || '',
                        `"${(score.title || '').replace(/"/g, '""')}"`,
                        date,
                        time,
                        score.url || ''
                    ];
                    csvRows.push(row.join(','));
                });

                csvRows.push('');
                csvRows.push('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                csvRows.push(`報表結束 | 總計 ${totalScores} 筆記錄`);

                // 建立 CSV 內容
                const csvContent = csvRows.join('\\n');

                // 建立 Blob 並觸發下載
                const blob = new Blob(['\\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
                const link = document.createElement('a');
                const url = URL.createObjectURL(blob);

                // 生成檔案名稱
                const now = new Date();
                const timestamp = now.toISOString().split('T')[0];
                const filename = `評分完整報表_${timestamp}.csv`;

                link.setAttribute('href', url);
                link.setAttribute('download', filename);
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }

            // 過濾器事件
            document.getElementById('filter-tabs').addEventListener('click', (e) => {
                if (e.target.classList.contains('filter-tab')) {
                    document.querySelectorAll('.filter-tab').forEach(tab => tab.classList.remove('active'));
                    e.target.classList.add('active');
                    currentFilter = e.target.dataset.filter;
                    renderScores();
                }
            });

            // 初始載入
            loadScores();

        </script>
    </body>
    </html>
    """
