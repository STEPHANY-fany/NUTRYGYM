import streamlit as st
import asyncio
from agent import chat_nutrigym
import uuid
from datetime import datetime

st.set_page_config(
    page_title="NutriGym - Tu Coach Personal",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Fondo principal */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Contenedor del chat */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Input del chat */
    .stChatInputContainer {
        border-top: 2px solid #e0e0e0;
        padding-top: 1rem;
    }
    
    /* Botones */
    .stButton button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* Mensajes del chat */
    [data-testid="stChatMessage"] {
        background-color: #f8f9fa;
        border-radius: 15px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Texto de los mensajes - NEGRO */
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div {
        color: #1a1a1a !important;
    }
    
    /* Asegurar que el markdown también sea negro */
    [data-testid="stMarkdown"] {
        color: #1a1a1a !important;
    }
</style>
""", unsafe_allow_html=True)

if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'session_id' not in st.session_state:
    st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []  # Lista de conversaciones previas

# Sidebar
with st.sidebar:
    st.markdown("# 💪 NutriGym")
    st.markdown("### Tu Coach Personal de IA")
    
    st.markdown("---")
    st.markdown("### 🎯 Capacidades")
    st.markdown("""
    - 🔥 Cálculo de calorías (TMB)
    - 🥗 Planes nutricionales
    - 🏋️ Rutinas de ejercicio
    - 📊 Seguimiento de progreso
    - 🍎 Información nutricional (USDA)
    """)
    
    st.markdown("---")
    
    if st.button("🆕 Nueva Conversación", use_container_width=True):
        if st.session_state.messages:
            st.session_state.conversation_history.append({
                'session_id': st.session_state.session_id,
                'messages': st.session_state.messages.copy(),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        
        st.session_state.messages = []
        st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"
        st.rerun()
    
    if st.button("🗑️ Limpiar Conversación Actual", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    if st.session_state.conversation_history:
        st.markdown("---")
        st.markdown("### 📚 Conversaciones Anteriores")
        
        for idx, conv in enumerate(reversed(st.session_state.conversation_history[-5:])):
            with st.expander(f"💬 {conv['timestamp']} ({len(conv['messages'])} mensajes)"):
                if st.button(f"📂 Cargar esta conversación", key=f"load_{idx}"):
                    st.session_state.messages = conv['messages'].copy()
                    st.session_state.session_id = conv['session_id']
                    st.rerun()
                
                # Mostrar preview
                st.caption("Vista previa:")
                for msg in conv['messages'][:2]:
                    role = "👤" if msg['role'] == 'user' else "💪"
                    preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                    st.text(f"{role}: {preview}")
                
                if st.button(f"🗑️ Eliminar", key=f"del_{idx}"):
                    actual_idx = len(st.session_state.conversation_history) - 1 - idx
                    del st.session_state.conversation_history[actual_idx]
                    st.rerun()
    
    st.markdown("---")
    st.caption(f"Session: {st.session_state.session_id[:12]}...")

st.title("💬 Chat con NutriGym")
st.caption("Pregúntame sobre nutrición, ejercicios, calorías y más")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input del usuario
if prompt := st.chat_input("Escribe tu mensaje aquí... (ej: Quiero calcular mis calorías)"):
    # Agregar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Obtener respuesta del agente
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # Ejecutar la función async
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            with st.spinner("🤔 NutriGym está pensando..."):
                response = loop.run_until_complete(
                    chat_nutrigym(prompt, st.session_state.session_id)
                )
            
            loop.close()
            
            # Verificar si la respuesta está vacía
            if not response or response.strip() == "":
                response = "Lo siento, no pude generar una respuesta. ¿Podrías reformular tu pregunta?"
            
            # Mostrar respuesta
            message_placeholder.markdown(response)
            
            # Guardar respuesta
            st.session_state.messages.append({"role": "assistant", "content": response})
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            error_msg = f"❌ **Error al procesar tu mensaje**\n\n```\n{str(e)}\n```"
            message_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            
            # Mostrar detalles en expandible
            with st.expander("Ver detalles del error"):
                st.code(error_detail)

# Acciones rápidas (solo al inicio)
if len(st.session_state.messages) == 0:
    st.markdown("---")
    st.markdown("### 🚀 Acciones Rápidas")
    st.caption("Haz clic en cualquier botón para comenzar:")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("👋 Empezar", use_container_width=True):
            prompt = "Hola, quiero empezar mi transformación"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
    
    with col2:
        if st.button("🔥 Calcular Calorías", use_container_width=True):
            prompt = "Quiero calcular mis calorías diarias"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
    
    with col3:
        if st.button("🏋️ Crear Rutina", use_container_width=True):
            prompt = "Necesito una rutina de ejercicios personalizada"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
    
    with col4:
        if st.button("🥗 Plan Nutricional", use_container_width=True):
            prompt = "Dame un plan de alimentación"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
    
    # Mensaje de bienvenida
    st.info("💡 **Tip:** Sé específico con tus objetivos para obtener mejores recomendaciones personalizadas.")
