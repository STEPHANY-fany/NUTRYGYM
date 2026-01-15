# NUTRYGYM
Aplicaciòn web 

link a la guia: https://google.github.io/adk-docs/

Comandos necesarios para instalar dependencias 
# 1. Creaciòn de entorno virtual
    python -m venv venv
     activaciòn del entorno
      venv\Scripts\activate

# 2. instalaciòn de adk
   pip install google-adk

# 3. instalacion de dependencias
   pip install requests python-dotenv streamlit
   
# 4. Probar el agente desde el puerto 8000 (adk)
   adk web
   
# 5. Probar el agente ya con la interfaz
   streamlit run app_streamlit.py
   
   como resultado se abre la app web en el puerto 8501   
   


