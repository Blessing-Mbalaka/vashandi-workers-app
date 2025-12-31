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
        this.currentConversation = {
            serviceId,
            serviceTitle,
            providerId,
            providerName,
            providerInitials
        };

        // Create and show modal
        this.createModal();
        this.loadMessages();
    }

    /**
     * Create the messaging modal HTML
     */
    createModal() {
        let modal = document.getElementById('messagingModal');
        
        if (modal) {
            modal.remove();
        }

        const modalHTML = `
            <div class="modal" id="messagingModal">
                <div class="modal-content" style="width: 600px; max-height: 800px; display: flex; flex-direction: column;">
                    <div class="modal-header">
                        <button class="modal-close" onclick="messagingModule.closeModal()">×</button>
                        <div style="display: flex; align-items: center; gap: 15px;">
                            <div style="width: 50px; height: 50px; border-radius: 50%; background: linear-gradient(135deg, #2563eb, #3b82f6); display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 1.2em;">
                                ${this.currentConversation.providerInitials}
                            </div>
                            <div>
                                <h2 style="margin: 0; margin-bottom: 0.3rem;">${this.currentConversation.providerName}</h2>
                                <p style="margin: 0; color: #94a3b8; font-size: 0.9em;">${this.currentConversation.serviceTitle}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="modal-body" style="flex: 1; overflow-y: auto; padding: 1.5rem; display: flex; flex-direction: column-reverse; gap: 1rem; background: rgba(15, 23, 42, 0.5);">
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
    }

    /**
     * Load existing messages
     */
    async loadMessages() {
        this.isLoading = true;
        try {
            const response = await fetch(
                `${this.options.apiEndpoint}?service=${this.currentConversation.serviceId}&recipient=${this.currentConversation.providerId}`,
                {
                    headers: {
                        'X-CSRFToken': this.options.csrfToken
                    }
                }
            );

            if (response.ok) {
                const data = await response.json();
                this.messages = data.results || data;
                this.renderMessages();
            }
        } catch (error) {
            console.error('Error loading messages:', error);
            this.options.onError('Failed to load messages');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Send a new message
     */
    async sendMessage(event) {
        event.preventDefault();

        const messageInput = document.getElementById('messageInput');
        const content = messageInput.value.trim();

        if (!content) {
            alert('Please enter a message');
            return;
        }

        this.isLoading = true;

        try {
            const response = await fetch(this.options.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.options.csrfToken
                },
                body: JSON.stringify({
                    recipient: this.currentConversation.providerId,
                    service: this.currentConversation.serviceId,
                    content: content
                })
            });

            if (response.ok) {
                messageInput.value = '';
                await this.loadMessages();
                this.options.onSuccess('Message sent successfully!');
                
                // Scroll to bottom
                const container = document.getElementById('messagesContainer');
                container.parentElement.scrollTop = container.parentElement.scrollHeight;
            } else {
                const error = await response.json();
                this.options.onError(error.error || 'Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.options.onError('Failed to send message');
        } finally {
            this.isLoading = false;
        }
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
        this.currentConversation = null;
        this.messages = [];
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
