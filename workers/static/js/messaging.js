/**
 * Messaging Module
 * Reusable messaging interface for contacting providers/workers
 * Can be used across the application
 */

class MessagingModule {
    constructor(options = {}) {
        this.options = {
            apiEndpoint: '/api/messages/',
            csrfToken: options.csrfToken || this.getCsrfToken(),
            onSuccess: options.onSuccess || (() => {}),
            onError: options.onError || (() => {}),
            ...options
        };
        
        this.currentConversation = null;
        this.messages = [];
        this.isLoading = false;
        this.refreshInterval = null;
        this.lastMessageId = null;
        
        // Log initialization
        console.log('[MessagingModule] Initialized with CSRF token:', this.options.csrfToken ? 'Present' : 'Missing');
        if (!this.options.csrfToken) {
            console.warn('[MessagingModule] Warning: CSRF token not found. This may cause 403 errors.');
        }
    }

    /**
     * Get CSRF token from cookies
     */
    getCsrfToken() {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, 'csrftoken='.length + 1) === ('csrftoken=')) {
                    cookieValue = decodeURIComponent(cookie.substring('csrftoken='.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    /**
     * Open messaging modal to contact a provider
     */
    async openContactModal(serviceId, serviceTitle, providerId, providerName, providerInitials) {
        this.setConversation({
            serviceId,
            contextTitle: serviceTitle,
            userId: providerId,
            userName: providerName,
            userInitials: providerInitials
        });
        this.createModal();
        this.loadMessages();
    }

    openConversationFromInbox(conversation) {
        this.setConversation({
            serviceId: conversation.service_id,
            jobId: conversation.job_id,
            userId: conversation.user_id,
            userName: conversation.user_name,
            userInitials: conversation.user_initials,
            contextTitle: conversation.service_title || conversation.job_title || 'Direct Conversation'
        });
        this.createModal();
        this.loadMessages();
    }

    setConversation(conversation) {
        this.currentConversation = {
            serviceId: conversation.serviceId || null,
            jobId: conversation.jobId || null,
            userId: conversation.userId,
            userName: conversation.userName,
            userInitials: conversation.userInitials || '??',
            contextTitle: conversation.contextTitle || conversation.jobTitle || ''
        };
        this.lastMessageId = null;
    }

    /**
     * Create the messaging modal HTML
     */
    createModal() {
        let modal = document.getElementById('messagingModal');
        
        if (modal) {
            modal.remove();
        }
        const name = this.currentConversation?.userName || 'Conversation';
        const initials = this.currentConversation?.userInitials || '??';
        const subtitle = this.currentConversation?.contextTitle || 'Private conversation';

        const modalHTML = `
            <div class="modal" id="messagingModal">
                <div class="modal-content" style="width: 600px; max-height: 800px; display: flex; flex-direction: column;">
                    <div class="modal-header">
                        <button class="modal-close" onclick="messagingModule.closeModal()">A-</button>
                        <div style="display: flex; align-items: center; gap: 15px;">
                            <div style="width: 50px; height: 50px; border-radius: 50%; background: linear-gradient(135deg, #2563eb, #3b82f6); display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 1.2em;">
                                ${initials}
                            </div>
                            <div>
                                <h2 style="margin: 0; margin-bottom: 0.3rem;">${name}</h2>
                                <p style="margin: 0; color: #94a3b8; font-size: 0.9em;">${subtitle}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="modal-body" style="flex: 1; overflow-y: auto; padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; background: rgba(15, 23, 42, 0.5);">
                        <div id="messagesContainer" style="display: flex; flex-direction: column; gap: 1rem;">
                            <p style="text-align: center; color: #64748b;">No messages yet. Start the conversation!</p>
                        </div>
                    </div>

                    <div style="padding: 1.5rem; border-top: 1px solid rgba(51, 65, 85, 0.5);">
                        <form id="messageForm" onsubmit="messagingModule.sendMessage(event)" style="display: flex; gap: 10px;">
                            <input 
                                type="text" 
                                id="messageInput" 
                                placeholder="Type your message..." 
                                style="flex: 1; padding: 12px; border: 2px solid rgba(51, 65, 85, 0.8); background: rgba(15, 23, 42, 0.6); color: #f1f5f9; border-radius: 6px; font-size: 1em; font-family: inherit; transition: all 0.3s;"
                                onkeyup="this.style.borderColor = '#3b82f6'"
                                onblur="this.style.borderColor = 'rgba(51, 65, 85, 0.8)'"
                            >
                            <button 
                                type="submit" 
                                style="padding: 12px 24px; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 6px; font-weight: 700; cursor: pointer; text-transform: uppercase; letter-spacing: 0.5px; transition: all 0.3s; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);"
                                onmouseover="this.style.boxShadow = '0 6px 20px rgba(59, 130, 246, 0.5)'"
                                onmouseout="this.style.boxShadow = '0 4px 12px rgba(59, 130, 246, 0.3)'"
                            >
                                Send
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        document.getElementById('messagingModal').classList.add('show');
        this.startAutoRefresh();
    }

    /**
     * Load existing messages
     */
    async loadMessages(isAutoRefresh = false) {
        if (!this.currentConversation || !this.currentConversation.userId) {
            this.showErrorAlert('Select a conversation before loading messages.');
            return;
        }

        this.isLoading = true;
        const previousLastId = this.lastMessageId;
        try {
            const params = new URLSearchParams();
            params.append('conversation_with', this.currentConversation.userId);
            if (this.currentConversation.serviceId) {
                params.append('service', this.currentConversation.serviceId);
            }
            if (this.currentConversation.jobId) {
                params.append('job', this.currentConversation.jobId);
            }

            const response = await fetch(`${this.options.apiEndpoint}?${params.toString()}`, {
                headers: {
                    'X-CSRFToken': this.options.csrfToken
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.messages = Array.isArray(data) ? data : (data.results || []);
                this.renderMessages();
                const latestMessage = this.messages[this.messages.length - 1];
                if (latestMessage) {
                    this.lastMessageId = latestMessage.id;
                    if (isAutoRefresh && previousLastId && latestMessage.id !== previousLastId && !latestMessage.is_sent_by_user) {
                        this.showNewMessageIndicator(latestMessage.sender_name || 'New message');
                    }
                }
            } else if (response.status === 401) {
                this.showErrorAlert('Session expired. Please refresh the page and log in again.');
            } else {
                const errorData = await response.json();
                const message = errorData.error || 'Failed to load messages. Please try again.';
                this.showErrorAlert(message);
            }
        } catch (error) {
            console.error('Error loading messages:', error);
            this.showErrorAlert('Network error: Failed to load messages. Please check your connection.');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Send a new message
     */
    async sendMessage(event) {
        event.preventDefault();

        if (!this.currentConversation || !this.currentConversation.userId) {
            this.showErrorAlert('Please select who you want to message.');
            return;
        }

        const messageInput = document.getElementById('messageInput');
        const content = messageInput.value.trim();

        if (!content) {
            this.showErrorAlert('Please enter a message');
            return;
        }

        if (!this.currentConversation.serviceId && !this.currentConversation.jobId) {
            this.showErrorAlert('Messages must be linked to a service or job. Please start the conversation from the relevant card.');
            return;
        }

        this.isLoading = true;

        const messageData = {
            recipient: this.currentConversation.userId,
            content: content
        };
        if (this.currentConversation.serviceId) {
            messageData.service = this.currentConversation.serviceId;
        }
        if (this.currentConversation.jobId) {
            messageData.job = this.currentConversation.jobId;
        }
        
        try {
            const response = await fetch(this.options.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.options.csrfToken || ''
                },
                body: JSON.stringify(messageData)
            });

            if (response.ok) {
                messageInput.value = '';
                await this.loadMessages();
                this.showSuccessAlert('Message sent successfully!');
                const container = document.getElementById('messagesContainer');
                if (container?.parentElement) {
                    container.parentElement.scrollTop = container.parentElement.scrollHeight;
                }
            } else {
                const errorData = await response.json();
                const errorMessage = errorData.error || 'Failed to send message';
                this.showDetailedError(response.status, errorMessage);
                this.options.onError(errorMessage);
            }
        } catch (error) {
            console.error('[MessagingModule] Network error:', error);
            this.showErrorAlert('Network error: Failed to send message. Please check your connection and try again.');
            this.options.onError('Failed to send message');
        } finally {
            this.isLoading = false;
        }
    }

    startAutoRefresh() {
        this.stopAutoRefresh();
        this.refreshInterval = setInterval(() => {
            if (!this.isLoading && this.currentConversation) {
                this.loadMessages(true);
            }
        }, 5000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    showNewMessageIndicator(senderName) {
        this.showSuccessAlert(`New message from ${senderName}`);
    }

    /**
     * Show a detailed error alert with helpful information
     */
    showDetailedError(statusCode, message) {
        let fullMessage = message;
        
        if (statusCode === 401) {
            fullMessage = `⚠️ Authentication Error\n\n${message}\n\nPlease log in again.`;
        } else if (statusCode === 403) {
            fullMessage = `🔒 Permission Denied\n\n${message}\n\nYou may not have permission to send this message.`;
        } else if (statusCode === 404) {
            fullMessage = `❌ Not Found\n\n${message}\n\nPlease refresh the page and try again.`;
        } else if (statusCode === 400) {
            fullMessage = `⚠️ Invalid Request\n\n${message}\n\nPlease check your input and try again.`;
        } else if (statusCode >= 500) {
            fullMessage = `⛔ Server Error\n\n${message}\n\nPlease try again later.`;
        }
        
        this.showErrorAlert(fullMessage);
    }

    /**
     * Show success alert with styling
     */
    showSuccessAlert(message) {
        const alertId = 'messagingAlert_' + Date.now();
        const alertHTML = `
            <div id="${alertId}" style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #22c55e, #16a34a);
                color: white;
                padding: 16px 24px;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(34, 197, 94, 0.4);
                z-index: 10000;
                max-width: 400px;
                word-wrap: break-word;
                white-space: pre-wrap;
                font-size: 0.95em;
                border-left: 4px solid #10b981;
            ">
                ✓ ${message}
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', alertHTML);
        
        setTimeout(() => {
            const element = document.getElementById(alertId);
            if (element) {
                element.style.opacity = '0';
                element.style.transition = 'opacity 0.3s';
                setTimeout(() => element.remove(), 300);
            }
        }, 4000);
    }

    /**
     * Show error alert with styling
     */
    showErrorAlert(message) {
        const alertId = 'messagingAlert_' + Date.now();
        const alertHTML = `
            <div id="${alertId}" style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #ef4444, #dc2626);
                color: white;
                padding: 16px 24px;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(239, 68, 68, 0.4);
                z-index: 10000;
                max-width: 400px;
                word-wrap: break-word;
                white-space: pre-wrap;
                font-size: 0.95em;
                border-left: 4px solid #b91c1c;
            ">
                ✕ ${message}
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', alertHTML);
        
        setTimeout(() => {
            const element = document.getElementById(alertId);
            if (element) {
                element.style.opacity = '0';
                element.style.transition = 'opacity 0.3s';
                setTimeout(() => element.remove(), 300);
            }
        }, 5000);
    }

    /**
     * Render messages in the modal
     */
    renderMessages() {
        const container = document.getElementById('messagesContainer');

        if (this.messages.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #64748b;">No messages yet. Start the conversation!</p>';
            return;
        }

        container.innerHTML = this.messages.map(msg => {
            const isOwn = msg.is_sent_by_user !== undefined ? msg.is_sent_by_user : true;
            const timestamp = new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            return `
                <div style="display: flex; ${isOwn ? 'justify-content: flex-end' : 'justify-content: flex-start'};">
                    <div style="max-width: 80%; background: ${isOwn ? 'linear-gradient(135deg, #3b82f6, #2563eb)' : 'rgba(30, 41, 59, 0.8)'}; color: ${isOwn ? 'white' : '#cbd5e1'}; padding: 12px 16px; border-radius: 12px; word-wrap: break-word; border: 1px solid ${isOwn ? 'rgba(59, 130, 246, 0.5)' : 'rgba(51, 65, 85, 0.5)'};">
                        <p style="margin: 0; margin-bottom: 0.5rem; line-height: 1.5;">${this.escapeHtml(msg.content)}</p>
                        <p style="margin: 0; font-size: 0.75em; opacity: 0.7;">${timestamp}</p>
                    </div>
                </div>
            `;
        }).join('');

        // Scroll to bottom
        const modalBody = container.parentElement;
        setTimeout(() => {
            modalBody.scrollTop = modalBody.scrollHeight;
        }, 100);
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Close the messaging modal
     */
    closeModal() {
        const modal = document.getElementById('messagingModal');
        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        }
        this.stopAutoRefresh();
        this.currentConversation = null;
        this.messages = [];
        this.lastMessageId = null;
    }
}

// Global instance
let messagingModule;

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        messagingModule = new MessagingModule();
    });
} else {
    messagingModule = new MessagingModule();
}
