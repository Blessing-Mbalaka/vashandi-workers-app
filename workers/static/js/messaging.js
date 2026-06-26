/**
 * Messaging Module
 * Reusable messaging interface for contacting providers/workers.
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
    }

    getCsrfToken() {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, 'csrftoken='.length + 1) === 'csrftoken=') {
                    cookieValue = decodeURIComponent(cookie.substring('csrftoken='.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

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

    createModal() {
        const existingModal = document.getElementById('messagingModal');
        if (existingModal) {
            existingModal.remove();
        }

        const name = this.currentConversation?.userName || 'Conversation';
        const initials = this.currentConversation?.userInitials || '??';
        const subtitle = this.currentConversation?.contextTitle || 'Private conversation';
        const firstMessagePrompt = `This is the start of your conversation with ${name}. Type your message below and press Send.`;

        const modalHTML = `
            <div class="modal" id="messagingModal">
                <div class="modal-content" style="width: 600px; max-width: 96%; max-height: 88vh; display: flex; flex-direction: column; background: #fffdf8; color: #17130d;">
                    <div class="modal-header">
                        <button class="modal-close" onclick="messagingModule.closeModal()">&times;</button>
                        <div style="display: flex; align-items: center; gap: 15px;">
                            <div style="width: 50px; height: 50px; border-radius: 50%; background: linear-gradient(145deg, #c7961a, #9c7310); display: flex; align-items: center; justify-content: center; color: #ffffff; font-weight: 700; font-size: 1.1em;">
                                ${initials}
                            </div>
                            <div>
                                <h2 style="margin: 0; margin-bottom: 0.3rem;">${name}</h2>
                                <p style="margin: 0; color: #746754; font-size: 0.9em;">${subtitle}</p>
                            </div>
                        </div>
                    </div>
                    <div class="modal-body" style="flex: 1; overflow-y: auto; padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; background: #f8f2e6;">
                        <div id="messagesContainer" style="display: flex; flex-direction: column; gap: 1rem;">
                            <div style="text-align: center; color: #746754; background: rgba(255, 255, 255, 0.72); border: 1px dashed rgba(199, 150, 26, 0.4); border-radius: 12px; padding: 1rem 1.25rem;">
                                <p style="margin: 0; font-weight: 700; color: #17130d;">No messages yet</p>
                                <p style="margin: 0.5rem 0 0;">${firstMessagePrompt}</p>
                            </div>
                        </div>
                    </div>
                    <div style="padding: 1.5rem; border-top: 1px solid rgba(199, 150, 26, 0.22); background: rgba(255, 255, 255, 0.92);">
                        <form id="messageForm" onsubmit="messagingModule.sendMessage(event)" style="display: flex; gap: 10px;">
                            <input
                                type="text"
                                id="messageInput"
                                placeholder="Write your first message here..."
                                style="flex: 1; padding: 12px; border: 1px solid rgba(199, 150, 26, 0.34); background: #ffffff; color: #17130d; border-radius: 12px; font-size: 1em; font-family: inherit; transition: all 0.3s;"
                                onkeyup="this.style.borderColor = '#c7961a'"
                                onblur="this.style.borderColor = 'rgba(199, 150, 26, 0.34)'"
                            >
                            <button
                                type="submit"
                                style="padding: 12px 24px; background: linear-gradient(145deg, #c7961a, #9c7310); color: #17130d; border: none; border-radius: 12px; font-weight: 700; cursor: pointer; text-transform: uppercase; letter-spacing: 0.5px; transition: all 0.3s; box-shadow: 0 4px 12px rgba(199, 150, 26, 0.24);"
                                onmouseover="this.style.boxShadow = '0 6px 20px rgba(199, 150, 26, 0.35)'"
                                onmouseout="this.style.boxShadow = '0 4px 12px rgba(199, 150, 26, 0.24)'"
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
        setTimeout(() => {
            const messageInput = document.getElementById('messageInput');
            if (messageInput) {
                messageInput.focus();
            }
        }, 50);
        this.startAutoRefresh();
    }

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

    async sendMessage(event) {
        event.preventDefault();

        if (!this.currentConversation || !this.currentConversation.userId) {
            this.showErrorAlert('Please select who you want to message.');
            return;
        }

        const messageInput = document.getElementById('messageInput');
        const content = messageInput.value.trim();

        if (!content) {
            this.showErrorAlert('Please enter a message.');
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
                this.showSuccessAlert('Message sent successfully.');
                const container = document.getElementById('messagesContainer');
                if (container?.parentElement) {
                    container.parentElement.scrollTop = container.parentElement.scrollHeight;
                }
                if (typeof refreshDashboardAlerts === 'function') {
                    refreshDashboardAlerts();
                }
            } else {
                const errorData = await response.json();
                const errorMessage = errorData.error || 'Failed to send message.';
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
        if (typeof refreshDashboardAlerts === 'function') {
            refreshDashboardAlerts();
        }
    }

    showDetailedError(statusCode, message) {
        let fullMessage = message;

        if (statusCode === 401) {
            fullMessage = `Authentication Error\n\n${message}\n\nPlease log in again.`;
        } else if (statusCode === 403) {
            fullMessage = `Permission Denied\n\n${message}\n\nYou may not have permission to send this message.`;
        } else if (statusCode === 404) {
            fullMessage = `Not Found\n\n${message}\n\nPlease refresh the page and try again.`;
        } else if (statusCode === 400) {
            fullMessage = `Invalid Request\n\n${message}\n\nPlease check your input and try again.`;
        } else if (statusCode >= 500) {
            fullMessage = `Server Error\n\n${message}\n\nPlease try again later.`;
        }

        this.showErrorAlert(fullMessage);
    }

    showSuccessAlert(message) {
        const alertId = `messagingAlert_${Date.now()}`;
        const alertHTML = `
            <div id="${alertId}" style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #22c55e, #16a34a);
                color: white;
                padding: 16px 24px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(34, 197, 94, 0.3);
                z-index: 10000;
                max-width: 400px;
                word-wrap: break-word;
                white-space: pre-wrap;
                font-size: 0.95em;
                border-left: 4px solid #10b981;
            ">
                ${message}
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

    showErrorAlert(message) {
        const alertId = `messagingAlert_${Date.now()}`;
        const alertHTML = `
            <div id="${alertId}" style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #ef4444, #dc2626);
                color: white;
                padding: 16px 24px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(239, 68, 68, 0.3);
                z-index: 10000;
                max-width: 400px;
                word-wrap: break-word;
                white-space: pre-wrap;
                font-size: 0.95em;
                border-left: 4px solid #b91c1c;
            ">
                ${message}
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

    renderMessages() {
        const container = document.getElementById('messagesContainer');
        const name = this.currentConversation?.userName || 'this provider';

        if (this.messages.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; color: #746754; background: rgba(255, 255, 255, 0.72); border: 1px dashed rgba(199, 150, 26, 0.4); border-radius: 12px; padding: 1rem 1.25rem;">
                    <p style="margin: 0; font-weight: 700; color: #17130d;">No messages yet</p>
                    <p style="margin: 0.5rem 0 0;">This is the start of your conversation with ${name}. Type your message below and press Send.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.messages.map((msg) => {
            const isOwn = msg.is_sent_by_user !== undefined ? msg.is_sent_by_user : true;
            const timestamp = new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            return `
                <div style="display: flex; ${isOwn ? 'justify-content: flex-end' : 'justify-content: flex-start'};">
                    <div style="max-width: 80%; background: ${isOwn ? 'linear-gradient(145deg, #c7961a, #9c7310)' : '#ffffff'}; color: #17130d; padding: 12px 16px; border-radius: 12px; word-wrap: break-word; border: 1px solid ${isOwn ? 'rgba(199, 150, 26, 0.3)' : 'rgba(199, 150, 26, 0.18)'}; box-shadow: 0 10px 24px rgba(81, 60, 31, 0.08);">
                        <p style="margin: 0; margin-bottom: 0.5rem; line-height: 1.5;">${this.escapeHtml(msg.content)}</p>
                        <p style="margin: 0; font-size: 0.75em; opacity: 0.7;">${timestamp}</p>
                    </div>
                </div>
            `;
        }).join('');

        const modalBody = container.parentElement;
        setTimeout(() => {
            modalBody.scrollTop = modalBody.scrollHeight;
        }, 100);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

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

let messagingModule;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        messagingModule = new MessagingModule();
    });
} else {
    messagingModule = new MessagingModule();
}
