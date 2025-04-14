document.addEventListener('DOMContentLoaded', function () {
    const toolCards = document.querySelectorAll('.tool-card');
    const chatContainer = document.getElementById('chat-container');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    // Animación de entrada
    toolCards.forEach((card, index) => {
        card.style.opacity = 0;
        card.style.transform = 'translateY(20px)';

        setTimeout(() => {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = 1;
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });

    // Manejo de clics en las tarjetas
    toolCards.forEach(card => {
        card.addEventListener('click', function () {
            const toolName = this.querySelector('h3').textContent;
            showChatInterface(toolName);
        });
    });

    // Mostrar interfaz de chat
    function showChatInterface(toolName) {
        chatContainer.classList.remove('hidden');
        chatContainer.classList.add('visible');
        addMessage('system', `Has seleccionado: ${toolName}. ¿En qué puedo ayudarte?`);
    }

    // Foco automático en el input al cargar
    userInput.focus();

    // Enviar mensaje
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const message = userInput.value.trim();
        if (message) {
            // Obtener hora actual para el mensaje
            const now = new Date();
            const timeString = now.getHours() + ':' + 
                (now.getMinutes() < 10 ? '0' : '') + now.getMinutes();
            
            // Añadir mensaje del usuario al chat
            addUserMessage(message, timeString);
            userInput.value = '';
            
            // Mostrar indicador de escritura
            showTypingIndicator();
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message
                    })
                });

                // Eliminar indicador de escritura
                removeTypingIndicator();

                if (!response.ok) {
                    throw new Error('Error en la respuesta del servidor');
                }

                const data = await response.json();
                addSystemMessage(data.response);
            } catch (error) {
                // Eliminar indicador de escritura en caso de error
                removeTypingIndicator();
                console.error('Error:', error);
                addSystemMessage('Lo siento, ha ocurrido un error. Por favor, intenta de nuevo.');
            }
        }
    }

    function addUserMessage(content, time) {
        const messageHTML = `
            <div class="message user">
                <div class="message-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-sender">Tú</span>
                        <span class="message-time">${time}</span>
                    </div>
                    <div class="message-text">
                        ${content}
                    </div>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', messageHTML);
        scrollToBottom();
    }

    function addSystemMessage(content) {
        // Obtener hora actual
        const now = new Date();
        const timeString = now.getHours() + ':' + 
            (now.getMinutes() < 10 ? '0' : '') + now.getMinutes();
        
        const messageHTML = `
            <div class="message system">
                <div class="message-avatar">
                    <i class="fas fa-scale-balanced"></i>
                </div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-sender">Legal Guardian</span>
                        <span class="message-time">${timeString}</span>
                    </div>
                    <div class="message-text">
                        ${content}
                    </div>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', messageHTML);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const typingHTML = `
            <div class="message system" id="typing-indicator">
                <div class="message-avatar">
                    <i class="fas fa-scale-balanced"></i>
                </div>
                <div class="message-content">
                    <div class="message-text typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', typingHTML);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}); 