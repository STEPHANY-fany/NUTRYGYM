import os
import json
import datetime
import socket
import requests
import copy
import pandas as pd
from typing import Optional, List
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ============================
#       CONFIGURACIÓN Y KEYS
# ============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY")
USDA_API_KEY = os.getenv("USDA_API_KEY")


# ============================
# TOOL 1: Notificaciones (Telegram)
# ============================
def enviar_telegram(mensaje: str, chat_id: str) -> dict:
    """
    Envía un mensaje a Telegram.
    Fuerza IPv4 para evitar errores de conexión en ciertas redes.
    """
    if not TELEGRAM_TOKEN:
        return {"error": "Falta configurar el TELEGRAM_TOKEN en el archivo .env"}

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Si chat_id viene vacío, usar el valor por defecto en el código
    if not chat_id:
        chat_id = "8504254528"
    
    payload = {
        "chat_id": chat_id, 
        "text": mensaje
    }

    try:
        # Truco para forzar IPv4 (útil en Windows/ciertas redes)
        old_family = requests.packages.urllib3.util.connection.allowed_gai_family
        requests.packages.urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET

        res = requests.post(url, data=payload, timeout=10)
        
        if res.status_code != 200:
            return {"error": f"Telegram error {res.status_code}: {res.text}"}

        return {"status": "Enviado", "destinatario": chat_id}

    except Exception as e:
        return {"error": f"Fallo al enviar Telegram: {str(e)}"}
    finally:
        # Restauramos la configuración de red original
        requests.packages.urllib3.util.connection.allowed_gai_family = old_family

# ============================
# TOOL 2: Calculadora Metabólica
# ============================
def calcular_calorias(peso: float, estatura: float, edad: int, sexo: str, actividad: str):
    """
    Calcula TMB y calorías de mantenimiento (Mifflin-St Jeor).
    """
    try:
        peso = float(peso)
        estatura = float(estatura)
        edad = int(float(edad))
    except:
        return {"error": "Los valores deben ser números (peso, estatura, edad)."}

    if estatura < 3.0:
        estatura = estatura * 100

    sexo = sexo.strip().lower()
    actividad = actividad.strip().lower()

    if sexo == "m":
        tmb = 10 * peso + 6.25 * estatura - 5 * edad + 5
    elif sexo == "f":
        tmb = 10 * peso + 6.25 * estatura - 5 * edad - 161
    else:
        return {"error": "Sexo inválido. Usa 'M' o 'F'."}

    factores = {"sedentario": 1.2, "ligero": 1.375, "moderado": 1.55, "intenso": 1.725}
    factor = factores.get(actividad, 1.2)
    mantenimiento = tmb * factor

    return {
        "TMB": round(tmb, 2),
        "Calorias_mantenimiento": round(mantenimiento, 2),
        "Recomendaciones": {
            "deficit": round(mantenimiento - 350, 2),
            "volumen": round(mantenimiento + 300, 2),
            "mantenimiento": round(mantenimiento, 2)
        }
    }

# ============================
# TOOL 3: Registro de Peso
# ============================
def registrar_peso(peso: float):
    """Guarda el peso con fecha en progreso.json"""
    file = "progreso.json"
    try:
        peso = float(peso)
    except ValueError:
        return {"error": "El peso debe ser numérico."}

    # Cargar o crear archivo
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {"peso": []}
    else:
        data = {"peso": []}

    data["peso"].append({
        "fecha": datetime.datetime.now().isoformat(),
        "peso": peso
    })

    with open(file, "w") as f:
        json.dump(data, f, indent=4)

    return {"status": "OK", "registrado": peso}


def obtener_progreso(limite: int):
    """Devuelve los últimos registros de peso."""
    file = "progreso.json"
    if not os.path.exists(file):
        return {"error": "Sin registros. Usa registrar_peso primero."}
    
    # Manejar límite dentro de la función
    try:
        limite = int(limite) if limite else 5
    except:
        limite = 5
    
    try:
        with open(file, "r") as f:
            data = json.load(f)
            registros = data.get("peso", [])
            if not registros: 
                return {"error": "Archivo vacío."}
            return {"progreso": registros[-limite:], "total": len(registros)}
    except:
        return {"error": "Error leyendo el archivo."}

# ============================
# TOOL 4: Nutrición (Dieta y USDA)
# ============================
def generar_dieta(objetivo: str):
    """Devuelve un menú base según objetivo."""
    base = {
        "déficit": ["Desayuno: Avena+yogur", "Comida: Pollo+verduras", "Cena: Ensalada+atún"],
        "volumen": ["Desayuno: Avena+huevos+pan", "Comida: Pasta+carne", "Cena: Arroz+pollo"],
        "mantenimiento": ["Desayuno: Tostadas+huevo", "Comida: Legumbres+arroz", "Cena: Pescado+verdura"]
    }
    obj = objetivo.lower() if objetivo else "mantenimiento"
    return {"objetivo": obj, "dieta": base.get(obj, base["mantenimiento"])}


def buscar_alimento_usda(nombre: str):
    """Busca en USDA API."""
    if not USDA_API_KEY:
        return {"error": "Falta USDA_API_KEY."}
        
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {"query": nombre, "api_key": USDA_API_KEY, "pageSize": 3}
    
    try:
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if "foods" in data:
                return data["foods"][:3]
        return {"error": "No encontrado o error de API."}
    except Exception as e:
        return {"error": str(e)}

# ============================
# TOOL 5: Ejercicios (API Ninjas)
# ============================
def buscar_ejercicios(musculo: Optional[str], tipo: Optional[str], dificultad: Optional[str], 
                     equipo: Optional[str], nombre: Optional[str], limite: int):
    """Busca ejercicios en API Ninjas."""
    if not API_NINJAS_KEY:
        return {"error": "Falta API_NINJAS_KEY."}
    
    # Manejar límite por defecto
    if not limite:
        limite = 3
        
    url = "https://api.api-ninjas.com/v1/exercises"
    headers = {"X-Api-Key": API_NINJAS_KEY}
    
    params = {}
    if musculo:
        params["muscle"] = musculo
    if tipo:
        params["type"] = tipo
    if dificultad:
        params["difficulty"] = dificultad
    if equipo:
        params["equipment"] = equipo
    if nombre:
        params["name"] = nombre
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {"ejercicios": data[:limite]} if data else {"error": "No hay resultados."}
        return {"error": f"API Error: {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def generar_rutina(objetivo: str, nivel: str, dias_semana: int, equipo_disponible: Optional[List[str]]):
    """Genera rutina llamando a buscar_ejercicios internamente."""
    
    # Manejar valores por defecto dentro de la función
    if not nivel:
        nivel = "beginner"
    if not dias_semana:
        dias_semana = 3
    
    rutinas_base = {
        "fuerza": ["chest", "back", "legs", "shoulders"],
        "hipertrofia": ["chest", "back", "legs", "shoulders", "biceps", "triceps"],
        "resistencia": ["cardio", "full_body"],
        "perdida_peso": ["cardio", "legs", "back"]
    }
    
    grupo_obj = rutinas_base.get(objetivo.lower(), rutinas_base["resistencia"])
    rutina = []
    
    # Limitamos los días a 7
    dias = max(1, min(int(dias_semana), 7))
    eq = equipo_disponible[0] if equipo_disponible else None

    for i in range(dias):
        grupo = grupo_obj[i % len(grupo_obj)]  # Ciclar grupos musculares
        res = buscar_ejercicios(
            musculo=grupo if grupo != "cardio" else None, 
            tipo="cardio" if grupo == "cardio" else "strength",
            dificultad=nivel, 
            equipo=eq,
            nombre=None,
            limite=3
        )
        
        rutina.append({
            "dia": i + 1,
            "enfoque": grupo,
            "ejercicios": res.get("ejercicios", [])
        })
        
    return {"plan": rutina}

# ============================
# TOOL 6: Persistencia de Perfil
# ============================
def guardar_perfil(perfil: dict):
    """Guarda los datos estáticos del perfil del usuario (edad, altura, sexo, objetivo, actividad)."""
    file = "perfil.json"
    
    # Prepara los datos a guardar, asegurando que la fecha de actualización sea correcta
    data = perfil.copy()
    data["fecha_actualizacion"] = datetime.datetime.now().isoformat()
    
    try:
        with open(file, "w") as f:
            json.dump(data, f, indent=4)
        return {"status": "Perfil guardado", "datos": data}
    except Exception as e:
        return {"error": f"Fallo al guardar el perfil: {str(e)}"}


def obtener_perfil():
    """Recupera los datos del perfil guardado."""
    file = "perfil.json"
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                data = json.load(f)
                return {"status": "Perfil recuperado", "datos": data}
        except json.JSONDecodeError:
            return {"error": "El archivo de perfil está corrupto."}
        except Exception as e:
            return {"error": f"Fallo al leer el perfil: {str(e)}"}
    return {"status": "Perfil no encontrado"}

# ============================
# TOOL 7: Generación de Reportes
# ============================
def generar_reporte_csv():
    """
    Lee los registros de peso de 'progreso.json', los datos de perfil de 'perfil.json', 
    y genera un archivo de reporte CSV llamado 'reporte_progreso.csv'.
    """
    progreso_file = "progreso.json"
    perfil_file = "perfil.json"
    
    # 1. Leer los datos de progreso de peso
    if not os.path.exists(progreso_file):
        return {"error": "No hay registros de peso para generar el reporte."}
        
    try:
        with open(progreso_file, "r") as f:
            progreso_data = json.load(f)
        registros = progreso_data.get("peso", [])
        if not registros:
            return {"error": "El archivo de progreso está vacío."}
    except Exception as e:
        return {"error": f"Error al leer el progreso: {str(e)}"}

    # 2. Leer los datos del perfil (para metadatos en el reporte)
    perfil_info = "Perfil no encontrado"
    if os.path.exists(perfil_file):
        try:
            with open(perfil_file, "r") as f:
                perfil_data = json.load(f)
            # Creamos una cadena de metadatos legible
            perfil_info = f"Objetivo: {perfil_data.get('objetivo', 'N/A')}, Actividad: {perfil_data.get('actividad', 'N/A')}"
        except:
            pass  # Ignoramos el error si el perfil está corrupto

    # 3. Crear el DataFrame
    df = pd.DataFrame(registros)
    
    # Añadir los metadatos del perfil como filas iniciales
    metadata = pd.DataFrame({
        'fecha': ['METADATO', 'METADATO'], 
        'peso': [f"Reporte generado: {datetime.datetime.now().strftime('%Y-%m-%d')}", perfil_info]
    })
    
    # Combinar metadatos y registros
    df_final = pd.concat([metadata, df], ignore_index=True)
    
    # 4. Guardar el archivo CSV
    reporte_nombre = "reporte_progreso.csv"
    try:
        df_final.to_csv(reporte_nombre, index=False, encoding='utf-8')
        return {"status": "Reporte generado", "archivo": reporte_nombre, "registros_exportados": len(registros)}
    except Exception as e:
        return {"error": f"Fallo al escribir el CSV: {str(e)}"}
