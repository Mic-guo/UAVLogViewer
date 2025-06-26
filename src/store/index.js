import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
    state: {
        messages: [
            {
                type: 'system',
                role: 'system',
                sender: 'System',
                text: 'Welcome to UAV Log Viewer Chat! How can I help you analyze this log file?',
                time: new Date().toLocaleTimeString(),
                icon: 'fas fa-info-circle'
            }
        ],
        isLoading: false
    },
    mutations: {
        ADD_MESSAGE (state, message) {
            state.messages.push(message)
        },
        SET_LOADING (state, isLoading) {
            state.isLoading = isLoading
        }
    },
    actions: {
        addMessage ({ commit }, message) {
            commit('ADD_MESSAGE', message)
        },
        setLoading ({ commit }, isLoading) {
            commit('SET_LOADING', isLoading)
        }
    }
})
