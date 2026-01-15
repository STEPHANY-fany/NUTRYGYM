from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService, Session
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.genai.types import Content, Part
import tools 


APP_NAME = "nutrigym_app"
USER_ID = "default_user"

prompt_instrucciones = """
REGLA CRÍTICA NÚMERO 1:
NUNCA uses herramientas sin tener TODA la información necesaria del usuario.
Si falta información, PREGUNTA primero. NO ASUMAS NADA.

FLUJO OBLIGATORIO Y DE PERSISTENCIA:

0. Carga de Perfil (Prioridad Máxima):
   Antes de hacer CUALQUIER otra cosa o preguntar al usuario, usa `obtener_perfil`.
   - Si el perfil existe: Saluda usando los datos que ya tienes (ej: "Hola usuario, ¿veo que tu objetivo es...?") y no vuelvas a preguntar peso, altura, edad, sexo, o actividad.
   - Si el perfil no existe: Pasa al punto 1.

1. Recopilación:
   Si `obtener_perfil` falla o el usuario pide actualizar, pregunta por el objetivo, peso, altura, edad, sexo y nivel de actividad (sedentario, ligero, moderado, intenso).

2. Cálculo y Guardado:
   Solo con todos los datos completos, usa `calcular_calorias`.
   INMEDIATAMENTE DESPUÉS, llama a `guardar_perfil` para guardar el peso y los datos estáticos del perfil, asegurando la persistencia.

3. Acción:
   - Usa `registrar_peso` si el usuario ha proporcionado un peso nuevo o si se acaba de calcular el perfil inicial.
   - Si pide dieta -> `generar_dieta`. 
   - Si pide rutina -> `generar_rutina` (pregunta días y equipo antes).
   - Si el usuario pide un reporte de progreso o un archivo de datos: usa `generar_reporte_csv`.
   - Para dudas de alimentos: `buscar_alimento_usda`.
   - Para dudas de ejercicios: `buscar_ejercicios`.

4. Notificaciones (Opcional): Si hay un gran logro, usa `enviar_telegram` (Úsala si la has logrado activar, de lo contrario, ignora esta instrucción).

CUÁNDO USAR CADA HERRAMIENTA:
- calcular_calorias: SOLO con los 5 datos exactos.
- guardar_perfil: Única vez después de un cálculo exitoso para guardar los datos.
- obtener_perfil: Única vez al inicio de cada nueva sesión para cargar la memoria.
"""

# agente principal 
nutri_agent = Agent(
    name="NutriGym_Agent",
    description="Coach experto en nutrición y fitness, proactivo y basado en datos.",
    instruction=prompt_instrucciones,
    model=LiteLlm(model="ollama_chat/llama3.1:8b"),
    tools=[
        tools.calcular_calorias,
        tools.generar_dieta,
        tools.registrar_peso,
        tools.obtener_progreso,
        tools.buscar_alimento_usda,
        tools.buscar_ejercicios,
        tools.generar_rutina,
        tools.enviar_telegram, 
        tools.guardar_perfil,   
        tools.obtener_perfil, 
        tools.generar_reporte_csv
    ],
)


session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

async def chat_nutrigym(user_message: str, session_id: str = "default_session"):
    """
    Función principal para interactuar con NutriGym con memoria persistente
    """
    if session_id not in session_service.sessions:
        new_session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id
        )
        print(f"✅ Sesión creada: {session_id}")
        print(f"   Sesiones actuales: {list(session_service.sessions.keys())}")
    
    runner = Runner(
        agent=nutri_agent,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service
    )
    
    user_content = Content(parts=[Part(text=user_message)], role="user")
    
    print(f"\n👤 Usuario: {user_message}")
    print("🤖 NutriGym: ", end="", flush=True)
    
    final_response = ""
    
    try:
        async for event in runner.run_async(
            user_id=USER_ID, 
            session_id=session_id, 
            new_message=user_content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text
                print(final_response)
                
        if not final_response:
            final_response = "Lo siento, no pude generar una respuesta. Intenta de nuevo."
        
        
        try:
            
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=session_id
            )
            
            
            await memory_service.add_session_to_memory(session)
            print(f"💾 Memoria guardada para sesión: {session_id}")
            
        except Exception as mem_error:
            print(f"⚠️ Advertencia: No se pudo guardar en memoria: {mem_error}")
            
    except Exception as e:
        print(f"\n❌ Error en runner: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return final_response
