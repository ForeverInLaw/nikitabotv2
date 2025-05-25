class BotManagementSystem {
    constructor() {
        this.botStatus = 'disconnected';
        this.logs = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupTabs();
        this.checkSystemStatus();
        this.loadDashboardData();
        this.startLogUpdates();
    }

    setupEventListeners() {
        // Bot control buttons
        document.getElementById('start-bot').addEventListener('click', () => {
            this.startBot();
        });

        document.getElementById('stop-bot').addEventListener('click', () => {
            this.stopBot();
        });

        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const tabName = e.target.getAttribute('data-tab');
                this.switchTab(tabName);
            });
        });
    }

    setupTabs() {
        // Initialize first tab as active
        this.switchTab('overview');
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active', 'border-blue-500', 'text-blue-600');
            button.classList.add('border-transparent', 'text-gray-500');
        });

        const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
        activeButton.classList.add('active', 'border-blue-500', 'text-blue-600');
        activeButton.classList.remove('border-transparent', 'text-gray-500');

        // Update tab contents
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.add('hidden');
        });

        document.getElementById(`${tabName}-tab`).classList.remove('hidden');

        // Load tab-specific data
        this.loadTabData(tabName);
    }

    async loadTabData(tabName) {
        switch (tabName) {
            case 'products':
                await this.loadProducts();
                break;
            case 'orders':
                await this.loadOrders();
                break;
            case 'users':
                await this.loadUsers();
                break;
            case 'overview':
                await this.loadDashboardData();
                break;
        }
    }

    async startBot() {
        try {
            this.addLog('Starting Telegram bot...', 'info');
            this.updateBotStatus('connecting');
            
            // Simulate API call to start bot
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            this.updateBotStatus('connected');
            this.addLog('Bot started successfully', 'success');
        } catch (error) {
            this.addLog(`Failed to start bot: ${error.message}`, 'error');
            this.updateBotStatus('error');
        }
    }

    async stopBot() {
        try {
            this.addLog('Stopping Telegram bot...', 'info');
            this.updateBotStatus('disconnecting');
            
            // Simulate API call to stop bot
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            this.updateBotStatus('disconnected');
            this.addLog('Bot stopped successfully', 'info');
        } catch (error) {
            this.addLog(`Failed to stop bot: ${error.message}`, 'error');
        }
    }

    updateBotStatus(status) {
        const botStatusElement = document.getElementById('bot-status');
        const indicator = botStatusElement.querySelector('div');
        const text = botStatusElement.querySelector('span');

        indicator.className = 'w-3 h-3 rounded-full mr-2';
        
        switch (status) {
            case 'connected':
                indicator.classList.add('bg-green-500');
                text.textContent = 'Connected';
                break;
            case 'connecting':
                indicator.classList.add('bg-yellow-500');
                text.textContent = 'Connecting...';
                break;
            case 'disconnecting':
                indicator.classList.add('bg-yellow-500');
                text.textContent = 'Disconnecting...';
                break;
            case 'error':
                indicator.classList.add('bg-red-500');
                text.textContent = 'Error';
                break;
            default:
                indicator.classList.add('bg-gray-400');
                text.textContent = 'Disconnected';
        }
        
        this.botStatus = status;
    }

    async checkSystemStatus() {
        // Check database status
        try {
            await new Promise(resolve => setTimeout(resolve, 1000));
            this.updateServiceStatus('db-status', 'connected', 'Database Connected');
        } catch (error) {
            this.updateServiceStatus('db-status', 'error', 'Database Error');
        }

        // Check Redis status
        try {
            await new Promise(resolve => setTimeout(resolve, 800));
            this.updateServiceStatus('redis-status', 'connected', 'Redis Connected');
        } catch (error) {
            this.updateServiceStatus('redis-status', 'error', 'Redis Error');
        }
    }

    updateServiceStatus(elementId, status, text) {
        const element = document.getElementById(elementId);
        const indicator = element.querySelector('div');
        const textSpan = element.querySelector('span');

        indicator.className = 'w-3 h-3 rounded-full mr-2';
        
        switch (status) {
            case 'connected':
                indicator.classList.add('bg-green-500');
                break;
            case 'error':
                indicator.classList.add('bg-red-500');
                break;
            default:
                indicator.classList.add('bg-gray-400');
        }
        
        textSpan.textContent = text;
    }

    async loadDashboardData() {
        try {
            // Simulate loading dashboard statistics
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            document.getElementById('total-users').textContent = '127';
            document.getElementById('active-orders').textContent = '23';
            document.getElementById('total-products').textContent = '456';
            document.getElementById('total-locations').textContent = '8';

            this.loadRecentActivity();
        } catch (error) {
            this.addLog(`Failed to load dashboard data: ${error.message}`, 'error');
        }
    }

    loadRecentActivity() {
        const activities = [
            { type: 'order', message: 'New order #1234 received from user @john_doe', time: '2 minutes ago' },
            { type: 'user', message: 'New user registered: @jane_smith', time: '5 minutes ago' },
            { type: 'system', message: 'Database backup completed successfully', time: '15 minutes ago' },
            { type: 'order', message: 'Order #1233 completed and delivered', time: '20 minutes ago' }
        ];

        const activityElement = document.getElementById('recent-activity');
        activityElement.innerHTML = activities.map(activity => `
            <div class="bg-gray-50 rounded-lg p-4 flex justify-between items-center">
                <div>
                    <p class="text-gray-900">${activity.message}</p>
                    <p class="text-sm text-gray-500">${activity.time}</p>
                </div>
                <div class="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                    ${activity.type}
                </div>
            </div>
        `).join('');
    }

    async loadProducts() {
        const productsContainer = document.getElementById('products-list');
        productsContainer.innerHTML = '<div class="loading bg-gray-50 rounded-lg p-4"><p class="text-gray-600">Loading products...</p></div>';

        try {
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            const products = [
                { id: 1, name: 'Product Alpha', manufacturer: 'Company A', price: 29.99, stock: 150 },
                { id: 2, name: 'Product Beta', manufacturer: 'Company B', price: 49.99, stock: 75 },
                { id: 3, name: 'Product Gamma', manufacturer: 'Company A', price: 19.99, stock: 200 }
            ];

            productsContainer.innerHTML = products.map(product => `
                <div class="card bg-white border rounded-lg p-4 flex justify-between items-center">
                    <div>
                        <h3 class="font-semibold text-gray-900">${product.name}</h3>
                        <p class="text-gray-600">${product.manufacturer}</p>
                        <p class="text-sm text-gray-500">Stock: ${product.stock} units</p>
                    </div>
                    <div class="text-right">
                        <p class="text-lg font-bold text-green-600">$${product.price}</p>
                        <button class="mt-2 px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600">
                            Edit
                        </button>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            productsContainer.innerHTML = '<div class="bg-red-50 rounded-lg p-4"><p class="text-red-600">Failed to load products</p></div>';
        }
    }

    async loadOrders() {
        const ordersContainer = document.getElementById('orders-list');
        ordersContainer.innerHTML = '<div class="loading bg-gray-50 rounded-lg p-4"><p class="text-gray-600">Loading orders...</p></div>';

        try {
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            const orders = [
                { id: 1234, user: '@john_doe', status: 'Pending', total: 79.97, date: '2024-01-15 14:30' },
                { id: 1233, user: '@jane_smith', status: 'Delivered', total: 149.99, date: '2024-01-15 12:15' },
                { id: 1232, user: '@bob_wilson', status: 'Processing', total: 29.99, date: '2024-01-15 10:45' }
            ];

            ordersContainer.innerHTML = orders.map(order => {
                const statusColor = order.status === 'Delivered' ? 'green' : 
                                   order.status === 'Processing' ? 'yellow' : 'blue';
                
                return `
                    <div class="card bg-white border rounded-lg p-4">
                        <div class="flex justify-between items-start mb-2">
                            <h3 class="font-semibold text-gray-900">Order #${order.id}</h3>
                            <span class="px-2 py-1 bg-${statusColor}-100 text-${statusColor}-800 text-sm rounded">
                                ${order.status}
                            </span>
                        </div>
                        <div class="grid grid-cols-3 gap-4 text-sm">
                            <div>
                                <p class="text-gray-500">User:</p>
                                <p class="font-medium">${order.user}</p>
                            </div>
                            <div>
                                <p class="text-gray-500">Total:</p>
                                <p class="font-medium">$${order.total}</p>
                            </div>
                            <div>
                                <p class="text-gray-500">Date:</p>
                                <p class="font-medium">${order.date}</p>
                            </div>
                        </div>
                        <div class="mt-3 flex space-x-2">
                            <button class="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600">
                                View Details
                            </button>
                            ${order.status === 'Pending' ? 
                                '<button class="px-3 py-1 bg-green-500 text-white text-sm rounded hover:bg-green-600">Confirm</button>' : 
                                ''
                            }
                        </div>
                    </div>
                `;
            }).join('');
        } catch (error) {
            ordersContainer.innerHTML = '<div class="bg-red-50 rounded-lg p-4"><p class="text-red-600">Failed to load orders</p></div>';
        }
    }

    async loadUsers() {
        const usersContainer = document.getElementById('users-list');
        usersContainer.innerHTML = '<div class="loading bg-gray-50 rounded-lg p-4"><p class="text-gray-600">Loading users...</p></div>';

        try {
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            const users = [
                { id: 123456789, username: '@john_doe', language: 'English', orders: 5, joined: '2024-01-10' },
                { id: 987654321, username: '@jane_smith', language: 'Russian', orders: 3, joined: '2024-01-12' },
                { id: 456789123, username: '@bob_wilson', language: 'Polish', orders: 8, joined: '2024-01-08' }
            ];

            usersContainer.innerHTML = users.map(user => `
                <div class="card bg-white border rounded-lg p-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h3 class="font-semibold text-gray-900">${user.username}</h3>
                            <p class="text-sm text-gray-500">ID: ${user.id}</p>
                            <div class="mt-2 grid grid-cols-3 gap-4 text-sm">
                                <div>
                                    <p class="text-gray-500">Language:</p>
                                    <p class="font-medium">${user.language}</p>
                                </div>
                                <div>
                                    <p class="text-gray-500">Orders:</p>
                                    <p class="font-medium">${user.orders}</p>
                                </div>
                                <div>
                                    <p class="text-gray-500">Joined:</p>
                                    <p class="font-medium">${user.joined}</p>
                                </div>
                            </div>
                        </div>
                        <button class="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600">
                            Block User
                        </button>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            usersContainer.innerHTML = '<div class="bg-red-50 rounded-lg p-4"><p class="text-red-600">Failed to load users</p></div>';
        }
    }

    addLog(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = `[${timestamp}] ${type.toUpperCase()}: ${message}`;
        
        this.logs.push(logEntry);
        
        // Keep only last 100 logs
        if (this.logs.length > 100) {
            this.logs = this.logs.slice(-100);
        }
        
        this.updateLogsDisplay();
    }

    updateLogsDisplay() {
        const logsContent = document.getElementById('logs-content');
        if (logsContent) {
            logsContent.textContent = this.logs.join('\n');
            logsContent.scrollTop = logsContent.scrollHeight;
        }
    }

    startLogUpdates() {
        // Add periodic system logs
        setInterval(() => {
            if (this.botStatus === 'connected') {
                const messages = [
                    'Bot heartbeat check passed',
                    'Database connection pool status: healthy',
                    'Redis connection status: active',
                    'Memory usage within normal parameters'
                ];
                
                const randomMessage = messages[Math.floor(Math.random() * messages.length)];
                this.addLog(randomMessage, 'debug');
            }
        }, 30000); // Every 30 seconds
    }
}

// Initialize the management system when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new BotManagementSystem();
});






