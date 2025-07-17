class GlobalMessages {
    constructor() {
        this.container = null;
        this.messageCounter = 0;
        this.init();
    }

    init() {
        this.container = document.getElementById('globalMessages');
        if (!this.container) {
            this.createContainer();
        }
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'globalMessages';
        this.container.className = 'global-messages-container';
        
        const nav = document.querySelector('nav');
        if (nav) {
            nav.parentNode.insertBefore(this.container, nav.nextSibling);
        } else {
            document.body.insertBefore(this.container, document.body.firstChild);
        }
    }

    show(text, type = 'info', duration = 5000) {
        if (!this.container) {
            this.init();
        }

        const messageId = ++this.messageCounter;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `global-message global-message-${type}`;
        messageDiv.setAttribute('data-message-id', messageId);
        
        const iconClass = this.getIconClass(type);
        
        messageDiv.innerHTML = `
            <div class="global-message-content">
                <i class="global-message-icon fas ${iconClass}"></i>
                <span class="global-message-text">${this.escapeHtml(text)}</span>
            </div>
            <button class="global-message-close" onclick="globalMessages.close(${messageId})">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        this.container.appendChild(messageDiv);
        
        if (duration > 0) {
            setTimeout(() => {
                this.close(messageId);
            }, duration);
        }
        
        return messageId;
    }

    close(messageId) {
        const message = this.container.querySelector(`[data-message-id="${messageId}"]`);
        if (message) {
            message.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                if (message.parentNode) {
                    message.remove();
                }
            }, 300);
        }
    }

    closeAll() {
        const messages = this.container.querySelectorAll('.global-message');
        messages.forEach((message, index) => {
            setTimeout(() => {
                if (message.parentNode) {
                    message.style.animation = 'slideOut 0.3s ease forwards';
                    setTimeout(() => {
                        if (message.parentNode) {
                            message.remove();
                        }
                    }, 300);
                }
            }, index * 100);
        });
    }

    getIconClass(type) {
        const icons = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'warning': 'fa-exclamation-triangle',
            'info': 'fa-info-circle'
        };
        return icons[type] || icons['info'];
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    success(text, duration = 5000) {
        return this.show(text, 'success', duration);
    }

    error(text, duration = 7000) {
        return this.show(text, 'error', duration);
    }

    warning(text, duration = 6000) {
        return this.show(text, 'warning', duration);
    }

    info(text, duration = 5000) {
        return this.show(text, 'info', duration);
    }
}

const globalMessages = new GlobalMessages();

window.showGlobalMessage = (text, type, duration) => {
    return globalMessages.show(text, type, duration);
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = GlobalMessages;
}