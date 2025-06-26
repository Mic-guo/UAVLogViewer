<template>
    <div class="chat-container">
        <div class="chat-messages" ref="messageContainer">
            <div v-for="(message, index) in messages"
                :key="index"
                :class="['message', message.type]">
                <div class="message-content">
                    <div class="message-header">
                        <i :class="message.icon"></i>
                        <span class="message-sender">{{ message.sender }}</span>
                        <span class="message-time">{{ message.time }}</span>
                    </div>
                    <div class="message-text">{{ message.text }}</div>
                </div>
            </div>
            <div v-if="isLoading" class="message system">
                <div class="message-content">
                    <div class="message-header">
                        <i class="fas fa-spinner fa-spin"></i>
                        <span class="message-sender">System</span>
                    </div>
                    <div class="message-text">Processing your request...</div>
                </div>
            </div>
        </div>
        <div class="chat-input">
            <input type="text"
                v-model="newMessage"
                @keyup.enter="sendMessage"
                placeholder="Type your message..."
                class="message-input"
                :disabled="isLoading"
                ref="messageInput" />
            <button @click="sendMessage"
                class="send-button"
                :disabled="isLoading">
                <i class="fas fa-paper-plane"></i>
            </button>
        </div>
        <!-- Debug Section -->
        <div class="debug-section">
            <button @click="showDebug = !showDebug" class="debug-toggle">
                <i class="fas fa-bug"></i> Debug
            </button>
            <div v-if="showDebug" class="debug-content">
                <h4>Vuex Store Messages:</h4>
                <pre>{{ JSON.stringify(messages, null, 2) }}</pre>
            </div>
        </div>
    </div>
</template>

<script>
import axios from 'axios'

export default {
    name: 'Chat',
    data () {
        return {
            baseUrl: 'http://localhost:8000',
            newMessage: '',
            showDebug: false,
            stage3Context: null,
            isExpectingClarification: false
        }
    },
    computed: {
        messages () {
            return this.$store.state.messages
        },
        isLoading () {
            return this.$store.state.isLoading
        }
    },
    methods: {
        async sendMessage () {
            if (!this.newMessage.trim() || this.isLoading) return

            const userMessage = {
                type: 'user',
                role: 'user',
                sender: 'You',
                text: this.newMessage,
                time: this.getCurrentTime(),
                icon: 'fas fa-user'
            }

            this.$store.dispatch('addMessage', userMessage)

            const messagePayload = this.newMessage
            this.newMessage = ''
            this.$store.dispatch('setLoading', true)

            try {
                let response
                if (this.isExpectingClarification && this.stage3Context) {
                    // Follow-up clarification
                    response = await axios.post(`${this.baseUrl}/api/chat/clarify`, {
                        clarification: messagePayload,
                        stage3Context: this.stage3Context
                    })
                } else {
                    // New question
                    const chatHistory = this.messages
                        .filter(m => m.role === 'user' || m.role === 'assistant')
                        .map(m => ({
                            role: m.role,
                            content: m.text
                        }))
                    response = await axios.post(`${this.baseUrl}/api/chat`, {
                        messages: chatHistory
                    })
                }

                const assistantResponse = {
                    type: 'system',
                    role: 'assistant',
                    sender: 'AI Assistant',
                    text: response.data.message,
                    time: this.getCurrentTime(),
                    icon: 'fas fa-robot'
                }

                this.$store.dispatch('addMessage', assistantResponse)
                this.isExpectingClarification = !!response.data.expecting_clarification
                this.stage3Context = response.data.stage3Context || null
            } catch (error) {
                this.$store.dispatch('addMessage', {
                    type: 'system',
                    role: 'system',
                    sender: 'System',
                    text: 'Sorry, there was an error processing your request. Please try again.',
                    time: this.getCurrentTime(),
                    icon: 'fas fa-exclamation-circle'
                })
                console.error('Chat error:', error)
            } finally {
                this.$store.dispatch('setLoading', false)
                this.$nextTick(() => {
                    this.scrollToBottom()
                    this.$refs.messageInput.focus()
                })
            }
        },
        getCurrentTime () {
            return new Date().toLocaleTimeString()
        },
        scrollToBottom () {
            const container = this.$refs.messageContainer
            container.scrollTop = container.scrollHeight
        }
    },
    mounted () {
        this.scrollToBottom()
    },
    watch: {
        '$parent.selected': {
            handler (newVal) {
                if (newVal === 'chat') {
                    this.$nextTick(() => {
                        this.scrollToBottom()
                        this.$forceUpdate()
                    })
                }
            },
            immediate: true
        }
    }
}
</script>

<style scoped>
.chat-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    background-color: rgb(29, 36, 52);
    color: white;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
}

.message {
    margin-bottom: 15px;
    display: flex;
    flex-direction: column;
}

.message-content {
    max-width: 80%;
    padding: 10px 15px;
    border-radius: 10px;
    background-color: rgba(47, 60, 83, 0.63);
}

.message.user .message-content {
    margin-left: auto;
    background-color: rgba(52, 70, 100, 0.8);
}

.message.system .message-content {
    background-color: rgba(47, 60, 83, 0.4);
}

.message-header {
    display: flex;
    align-items: center;
    margin-bottom: 5px;
    font-size: 0.9em;
}

.message-sender {
    font-weight: bold;
    margin: 0 8px;
}

.message-time {
    color: rgba(255, 255, 255, 0.6);
    font-size: 0.8em;
}

.message-text {
    word-wrap: break-word;
}

.chat-input {
    display: flex;
    padding: 15px;
    background-color: rgb(20, 25, 36);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.message-input {
    flex: 1;
    padding: 10px;
    border: none;
    border-radius: 20px;
    background-color: rgba(255, 255, 255, 0.1);
    color: white;
    margin-right: 10px;
}

.message-input::placeholder {
    color: rgba(255, 255, 255, 0.5);
}

.send-button {
    background-color: rgba(47, 60, 83, 0.63);
    border: none;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.3s;
}

.send-button:hover {
    background-color: rgba(58, 71, 94, 0.63);
    box-shadow: 0px 0px 12px 0px rgba(24, 106, 173, 0.281);
}

.send-button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
}

.message-input:disabled {
    opacity: 0.7;
    cursor: not-allowed;
}

.chat-messages::-webkit-scrollbar {
    width: 12px;
    background-color: rgba(0, 0, 0, 0);
}

.chat-messages::-webkit-scrollbar-thumb {
    border-radius: 5px;
    box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
    background: rgb(60, 75, 112);
    background: linear-gradient(0deg, rgb(67, 95, 155) 51%, rgb(61, 79, 121) 100%);
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.fa-spinner {
    animation: spin 1s linear infinite;
}

.debug-section {
    padding: 10px;
    background-color: rgb(20, 25, 36);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.debug-toggle {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.6);
    cursor: pointer;
    font-size: 0.9em;
    padding: 5px 10px;
}

.debug-toggle:hover {
    color: white;
}

.debug-content {
    margin-top: 10px;
    padding: 10px;
    background-color: rgba(0, 0, 0, 0.2);
    border-radius: 5px;
    max-height: 200px;
    overflow-y: auto;
}

.debug-content h4 {
    margin: 0 0 10px 0;
    color: rgba(255, 255, 255, 0.8);
}

.debug-content pre {
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    color: rgba(255, 255, 255, 0.7);
    font-size: 0.8em;
}
</style>
