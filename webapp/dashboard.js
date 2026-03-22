// Dashboard JavaScript
class InstagramDashboard {
    constructor() {
        this.botStatus = 'offline';
        this.accounts = [];
        this.stats = {
            total: 0,
            successful: 0,
            failed: 0,
            pending: 0,
            successRate: 0
        };
        this.isRunning = false;
        this.updateInterval = null;
        
        // Get bot API URL - FIXED to use correct Render URL
        this.BOT_API_URL = window.BOT_API_URL || 'https://instagram-automation-cj8a.onrender.com';
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startStatusUpdates();
    }
    
    setupEventListeners() {
        // Control buttons
        document.getElementById('start-btn').addEventListener('click', () => this.startAutomation());
        document.getElementById('stop-btn').addEventListener('click', () => this.stopAutomation());
        document.getElementById('refresh-btn').addEventListener('click', () => this.refreshStatus());
        
        // Search and filter
        document.getElementById('search-accounts').addEventListener('input', (e) => this.filterAccounts(e.target.value));
        document.getElementById('filter-status').addEventListener('change', (e) => this.filterAccountsByStatus(e.target.value));
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'r') {
                e.preventDefault();
                this.refreshStatus();
            }
        });
    }
    
    async loadInitialData() {
        this.showLoading(true);
        try {
            await this.fetchBotStatus();
            await this.fetchAccounts();
            this.updateUI();
        } catch (error) {
            this.showToast('Error loading initial data: ' + error.message, 'error');
            console.error('Initial load error:', error);
        } finally {
            this.showLoading(false);
        }
    }
    
    async fetchBotStatus() {
        try {
            const url = `${this.BOT_API_URL}/api/bot/status`;
            console.log('Fetching bot status from:', url);
            
            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();
                this.botStatus = data.status;
                this.isRunning = data.is_running;
                this.stats = data.stats;
                console.log('Bot status:', data);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Error fetching bot status:', error);
            // Fallback to offline status
            this.botStatus = 'offline';
            this.isRunning = false;
            this.stats = {
                total: 0,
                successful: 0,
                failed: 0,
                pending: 0,
                successRate: 0
            };
        }
    }
    
    async fetchAccounts() {
        try {
            const url = `${this.BOT_API_URL}/api/accounts`;
            console.log('Fetching accounts from:', url);
            
            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();
                this.accounts = data.accounts || [];
                console.log('Accounts loaded:', this.accounts.length);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Error fetching accounts:', error);
            this.accounts = [];
        }
    }
    
    async startAutomation() {
        const startIndex = parseInt(document.getElementById('start-index').value) || 0;
        
        if (this.isRunning) {
            this.showToast('Automation is already running!', 'error');
            return;
        }
        
        this.showLoading(true);
        try {
            const response = await fetch(`${this.BOT_API_URL}/api/bot/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ startIndex })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.isRunning = true;
                this.botStatus = 'processing';
                this.updateUI();
                this.showToast(data.message || 'Automation started successfully!', 'success');
                this.addActivityLog('Automation started from index ' + startIndex);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to start automation');
            }
        } catch (error) {
            this.showToast('Error starting automation: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async stopAutomation() {
        if (!this.isRunning) {
            this.showToast('No automation is currently running!', 'error');
            return;
        }
        
        this.showLoading(true);
        try {
            const response = await fetch(`${this.BOT_API_URL}/api/bot/stop`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.isRunning = false;
                this.botStatus = 'offline';
                this.updateUI();
                this.showToast(data.message || 'Automation stopped successfully!', 'success');
                this.addActivityLog('Automation stopped by user');
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to stop automation');
            }
        } catch (error) {
            this.showToast('Error stopping automation: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async refreshStatus() {
        this.showLoading(true);
        try {
            await this.fetchBotStatus();
            await this.fetchAccounts();
            this.updateUI();
            this.showToast('Status refreshed successfully!', 'success');
            this.addActivityLog('Status refreshed manually');
        } catch (error) {
            this.showToast('Error refreshing status: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    updateUI() {
        this.updateStatusIndicator();
        this.updateStatistics();
        this.updateProgress();
        this.updateControlButtons();
        this.updateAccountsList();
    }
    
    updateStatusIndicator() {
        const statusDot = document.getElementById('bot-status');
        const statusText = document.getElementById('status-text');
        
        statusDot.className = 'status-dot ' + this.botStatus;
        
        switch (this.botStatus) {
            case 'online':
                statusText.textContent = 'Online';
                break;
            case 'processing':
                statusText.textContent = 'Processing';
                break;
            case 'offline':
            default:
                statusText.textContent = 'Offline';
                break;
        }
    }
    
    updateStatistics() {
        document.getElementById('total-accounts').textContent = this.stats.total;
        document.getElementById('successful-accounts').textContent = this.stats.successful;
        document.getElementById('failed-accounts').textContent = this.stats.failed;
        document.getElementById('success-rate').textContent = this.stats.successRate.toFixed(1) + '%';
    }
    
    updateProgress() {
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const progressPercentage = document.getElementById('progress-percentage');
        
        const processed = this.stats.successful + this.stats.failed;
        const percentage = this.stats.total > 0 ? (processed / this.stats.total) * 100 : 0;
        
        progressFill.style.width = percentage + '%';
        progressText.textContent = `${processed} / ${this.stats.total} accounts processed`;
        progressPercentage.textContent = percentage.toFixed(1) + '%';
    }
    
    updateControlButtons() {
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        
        if (this.isRunning) {
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }
    
    updateAccountsList() {
        const accountsList = document.getElementById('accounts-list');
        
        if (this.accounts.length === 0) {
            accountsList.innerHTML = `
                <div class="no-accounts">
                    <i class="fas fa-inbox"></i>
                    <p>No accounts loaded yet</p>
                </div>
            `;
            return;
        }
        
        accountsList.innerHTML = this.accounts.map(account => `
            <div class="account-item ${account.status}">
                <div class="account-info">
                    <div class="account-username">@${account.username}</div>
                    <div class="account-email">${account.temp_email || account.email}</div>
                    <div class="account-time">${account.created_at || 'N/A'}</div>
                </div>
                <div class="account-status ${account.status}">${account.status}</div>
            </div>
        `).join('');
    }
    
    filterAccounts(searchTerm) {
        const accounts = document.querySelectorAll('.account-item');
        const filterStatus = document.getElementById('filter-status').value;
        
        accounts.forEach(account => {
            const username = account.querySelector('.account-username').textContent.toLowerCase();
            const email = account.querySelector('.account-email').textContent.toLowerCase();
            const status = account.classList.contains(filterStatus) || filterStatus === 'all';
            const matchesSearch = username.includes(searchTerm.toLowerCase()) || 
                                email.includes(searchTerm.toLowerCase());
            
            if (matchesSearch && status) {
                account.style.display = 'flex';
            } else {
                account.style.display = 'none';
            }
        });
    }
    
    filterAccountsByStatus(status) {
        const accounts = document.querySelectorAll('.account-item');
        const searchTerm = document.getElementById('search-accounts').value.toLowerCase();
        
        accounts.forEach(account => {
            const username = account.querySelector('.account-username').textContent.toLowerCase();
            const email = account.querySelector('.account-email').textContent.toLowerCase();
            const matchesStatus = account.classList.contains(status) || status === 'all';
            const matchesSearch = username.includes(searchTerm) || email.includes(searchTerm);
            
            if (matchesStatus && matchesSearch) {
                account.style.display = 'flex';
            } else {
                account.style.display = 'none';
            }
        });
    }
    
    addActivityLog(message) {
        const activityLog = document.getElementById('activity-log');
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        activityItem.innerHTML = `
            <i class="fas fa-info-circle"></i>
            <span>${message}</span>
            <span class="activity-time">${new Date().toLocaleTimeString()}</span>
        `;
        
        activityLog.insertBefore(activityItem, activityLog.firstChild);
        
        // Keep only last 10 activities
        while (activityLog.children.length > 10) {
            activityLog.removeChild(activityLog.lastChild);
        }
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
    }
    
    showToast(message, type = 'info') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.style.cssText = `
            background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
            color: white;
            padding: 12px 20px;
            margin-bottom: 10px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideIn 0.3s ease;
        `;
        
        const icon = type === 'success' ? 'check-circle' : 
                    type === 'error' ? 'times-circle' : 'info-circle';
        
        toast.innerHTML = `
            <i class="fas fa-${icon}"></i>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }
        }, 5000);
    }
    
    startStatusUpdates() {
        // Update status every 30 seconds
        if (this.updateInterval) clearInterval(this.updateInterval);
        this.updateInterval = setInterval(() => {
            this.fetchBotStatus().then(() => {
                this.updateUI();
            }).catch(err => console.error('Status update failed:', err));
        }, 30000);
    }
    
    stopStatusUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new InstagramDashboard();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        if (window.dashboard) window.dashboard.stopStatusUpdates();
    } else {
        if (window.dashboard) window.dashboard.startStatusUpdates();
    }
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboard) window.dashboard.stopStatusUpdates();
});
