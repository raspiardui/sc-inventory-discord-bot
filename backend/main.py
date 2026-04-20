from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import motor.motor_asyncio
import os
from datetime import datetime
import secrets
import httpx

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://192.168.1.200:5174",
        "https://invcruzsur.csroy.es"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client.sc_inventory
inventory_collection = db.inventory

ITEMS_DB = {
    "Agricium":"Mineral", "Aluminum":"Mineral", "Baryl":"Mineral", "Bexalite":"Mineral",
    "Borase":"Mineral", "Copper":"Mineral", "Corundum":"Mineral", "Diamond":"Mineral",
    "Gold":"Mineral", "Hephaestanite":"Mineral", "Iron":"Mineral", "Laranite":"Mineral",
    "Magnesite":"Mineral", "Platinum":"Mineral", "Quantanium":"Mineral", "Quartz":"Mineral",
    "Silver":"Mineral", "Taranite":"Mineral", "Titanium":"Mineral", "Tungsten":"Mineral",
    "Aphorite":"Gema", "Dolivine":"Gema", "Hadanite":"Gema", "Janalite":"Gema",
    "RMC":"Salvage", "Recycled Material Composite":"Salvage", "Construction Materials":"Salvage",
    "Circuit Boards":"Componente", "Power Cells":"Componente", "Compboards":"Componente",
    "Optical components":"Componente", "Cooling Manifolds":"Componente", "Polymer Sheets":"Componente",
    "Reinforced Plates":"Componente", "Wire Spools":"Componente", "Pressure Valves":"Componente",
    "Carbon":"Gas", "Fluorine":"Gas", "Hydrogen":"Gas", "Iodine":"Gas", "Nitrogen":"Gas",
    "Oxygen":"Gas", "Sulfur":"Gas",
    "Valakar Eye":"Trofeo", "Valakar Tongue":"Trofeo",
    "Aslarite":"Mineral", "Beradom":"Mineral", "Carinite":"Mineral", "Ouratite":"Mineral", "Riccite":"Mineral", "Sadaryx":"Mineral",
}

def get_category(item_name):
    if item_name.startswith("Refined "):
        return "Refinado"
    return ITEMS_DB.get(item_name, "Otro")

@app.on_event("startup")
async def init_db():
    await inventory_collection.create_index([("guild_id", 1), ("item_name", 1)], unique=True)
    await inventory_collection.create_index([("guild_id", 1), ("category", 1)])
    print("Índices multi-guild creados/verificados", flush=True)

class ItemAdd(BaseModel):
    guild_id: str
    item_name: str
    cantidad: float
    calidad: int
    discord_name: str
    location: str

class ItemRemove(BaseModel):
    guild_id: str
    item_name: str
    cantidad: float
    calidad: int
    discord_name: str
    location: str

@app.get("/inventory")
async def get_inventory(guild_id: str = Query(...)):
    items = await inventory_collection.find({"guild_id": guild_id}).to_list(1000)
    for i in items:
        i["_id"] = str(i["_id"])
    return items

@app.get("/inventory/history/{item_name}")
async def get_history(item_name: str, guild_id: str = Query(...)):
    existing = await inventory_collection.find_one({"guild_id": guild_id, "item_name": item_name})
    if not existing:
        raise HTTPException(404, "Item no encontrado")
    return existing.get("history", [])

@app.post("/inventory/add")
async def add_item(item: ItemAdd):
    existing = await inventory_collection.find_one({"guild_id": item.guild_id, "item_name": item.item_name})
    now = datetime.utcnow().isoformat() + "Z"
    category = get_category(item.item_name)
    entry = {
        "discord_name": item.discord_name,
        "cantidad": item.cantidad,
        "calidad": item.calidad,
        "location": item.location,
        "date": now,
        "action": "add"
    }
    if existing:
        new_cantidad = round(existing["cantidad"] + item.cantidad, 4)
        history = existing.get("history", [])
        history.append(entry)
        avg_calidad = round((existing.get("calidad", item.calidad) + item.calidad) / 2)
        await inventory_collection.update_one(
            {"_id": existing["_id"]},
            {"$set": {"cantidad": new_cantidad, "calidad": avg_calidad, "history": history,
                      "last_updated": now, "last_added_by": item.discord_name, "category": category,
                      "location": item.location}}
        )
    else:
        await inventory_collection.insert_one({
            "guild_id": item.guild_id,
            "item_name": item.item_name,
            "cantidad": item.cantidad,
            "calidad": item.calidad,
            "category": category,
            "location": item.location,
            "history": [entry],
            "last_updated": now,
            "last_added_by": item.discord_name
        })
    return {"success": True}

@app.post("/inventory/remove")
async def remove_item(item: ItemRemove):
    existing = await inventory_collection.find_one({"guild_id": item.guild_id, "item_name": item.item_name})
    if not existing:
        raise HTTPException(404, "Item no encontrado")
    if existing["cantidad"] < item.cantidad:
        raise HTTPException(400, "Cantidad insuficiente")
    now = datetime.utcnow().isoformat() + "Z"
    new_cantidad = round(existing["cantidad"] - item.cantidad, 4)
    history = existing.get("history", [])
    history.append({
        "discord_name": item.discord_name,
        "cantidad": -item.cantidad,
        "calidad": item.calidad,
        "location": item.location,
        "date": now,
        "action": "remove"
    })
    if new_cantidad <= 0:
        await inventory_collection.delete_one({"_id": existing["_id"]})
    else:
        await inventory_collection.update_one(
            {"_id": existing["_id"]},
            {"$set": {"cantidad": new_cantidad, "history": history, "last_updated": now,
                      "last_added_by": item.discord_name, "location": item.location}}
        )
    return {"success": True}

@app.get("/health")
async def health():
    return {"status": "ok"}

# ========== ADMIN PANEL ==========
security = HTTPBasic()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(401, "Credenciales incorrectas", headers={"WWW-Authenticate": "Basic"})
    return True

@app.get("/admin/guilds")
async def admin_get_guilds(_=Depends(verify_admin)):
    pipeline = [{"$group": {"_id": "$guild_id", "total_items": {"$sum": 1},
                "total_scu": {"$sum": "$cantidad"}, "last_update": {"$max": "$last_updated"}}},
                {"$sort": {"_id": 1}}]
    guilds = await inventory_collection.aggregate(pipeline).to_list(1000)
    return guilds

@app.get("/admin/inventory/{guild_id}")
async def admin_get_inventory(guild_id: str, _=Depends(verify_admin)):
    items = await inventory_collection.find({"guild_id": guild_id}).to_list(1000)
    for i in items:
        i["_id"] = str(i["_id"])
    return items

@app.delete("/admin/inventory/{guild_id}/{item_name}")
async def admin_delete_item(guild_id: str, item_name: str, _=Depends(verify_admin)):
    result = await inventory_collection.delete_one({"guild_id": guild_id, "item_name": item_name})
    if result.deleted_count == 0:
        raise HTTPException(404, "Item no encontrado")
    return {"success": True}

@app.put("/admin/inventory/{guild_id}/{item_name}")
async def admin_update_item(guild_id: str, item_name: str, cantidad: float = None, calidad: int = None, _=Depends(verify_admin)):
    update_data = {}
    if cantidad is not None:
        update_data["cantidad"] = round(cantidad, 4)
    if calidad is not None:
        update_data["calidad"] = calidad
    if not update_data:
        raise HTTPException(400, "No hay datos para actualizar")
    result = await inventory_collection.update_one({"guild_id": guild_id, "item_name": item_name}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(404, "Item no encontrado")
    return {"success": True}

# ========== CHULETA DE MINERALES ==========

@app.get("/minerales")
async def get_minerales():
    return MINERAL_DATA

@app.get("/minerales/{nombre}")
async def get_mineral(nombre: str):
    mineral = MINERAL_DATA.get(nombre)
    if not mineral:
        raise HTTPException(404, "Mineral no encontrado")
    return mineral

@app.get("/minerales/por_firma/{firma}")
async def buscar_mineral_por_firma(firma: int):
    from math import inf
    mejor_coincidencia = None
    menor_diferencia = inf
    resultados = []
    for nombre, datos in MINERAL_DATA.items():
        dif = abs(datos["firma"] - firma)
        if dif < menor_diferencia:
            menor_diferencia = dif
            mejor_coincidencia = (nombre, datos)
        if dif <= datos["firma"] * 0.05:
            resultados.append((nombre, datos, dif))
    if not resultados and mejor_coincidencia:
        resultados.append((mejor_coincidencia[0], mejor_coincidencia[1], menor_diferencia))
    resultados.sort(key=lambda x: x[2])
    return [{"nombre": r[0], "firma_tipica": r[1]["firma"], "tier": r[1]["tier"], "nota": r[1].get("nota", "")} for r in resultados[:3]]

# ========== OBTENER NOMBRE DEL SERVIDOR ==========
@app.get("/guild/{guild_id}")
async def get_guild_info(guild_id: str):
    DISCORD_TOKEN_BACKEND = os.getenv("DISCORD_TOKEN")
    if not DISCORD_TOKEN_BACKEND:
        raise HTTPException(500, "Token de Discord no configurado en el backend")
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            f"https://discord.com/api/v10/guilds/{guild_id}",
            headers={"Authorization": f"Bot {DISCORD_TOKEN_BACKEND}"}
        )
    if resp.status_code != 200:
        raise HTTPException(404, "Servidor no encontrado o el bot no está en él")
    data = resp.json()
    icon_hash = data.get("icon")
    icon_url = f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png" if icon_hash else None
    return {"name": data.get("name", "Servidor desconocido"), "icon": icon_url}

@app.get("/inventory/breakdown/{item_name}")
async def get_item_breakdown(item_name: str, guild_id: str = Query(...)):
    """
    Calcula el stock actual del item desglosado por calidad y ubicación,
    a partir del historial de movimientos (sin depender de documentos agregados).
    """
    # Obtener todos los documentos de este item en este guild (de la nueva colección inventario_v2)
    # Si usas la colección antigua (inventory), ajusta.
    items = await inventory_collection.find({
        "guild_id": guild_id,
        "item_name": item_name
    }).to_list(1000)
    
    # Si no hay documentos, intentamos calcular desde el historial global? 
    # Pero como ya tenemos los documentos individuales por calidad/ubicación, los usamos directamente.
    # (Nota: en la estructura actual, cada documento ya es una combinación única calidad+ubicación, 
    # pero el usuario no quiere verlos todos en la vista principal, solo en el desglose.)
    breakdown = []
    for doc in items:
        breakdown.append({
            "calidad": doc.get("calidad"),
            "location": doc.get("location", "Sin ubicación"),
            "cantidad": doc.get("cantidad", 0),
            "last_updated": doc.get("last_updated")
        })
    # Ordenar por calidad descendente
    breakdown.sort(key=lambda x: x["calidad"], reverse=True)
    return breakdown

@app.get("/minerales/por_firma/{firma}")
async def buscar_mineral_por_firma(firma: int):
    from math import inf
    mejores = []
    for nombre, datos in MINERAL_DATA.items():
        firmas = datos.get("firmas", [])
        for idx, valor in enumerate(firmas):
            dif = abs(valor - firma)
            if dif <= 100:  # margen de 100 unidades
                mejores.append((nombre, datos, idx+1, dif, valor))
    if not mejores:
        # Si no hay cerca, devolver el más cercano de cualquier tamaño
        mejor = None
        mejor_dif = inf
        mejor_tam = None
        mejor_valor = None
        for nombre, datos in MINERAL_DATA.items():
            for idx, valor in enumerate(datos.get("firmas", [])):
                dif = abs(valor - firma)
                if dif < mejor_dif:
                    mejor_dif = dif
                    mejor = (nombre, datos, idx+1, dif, valor)
        if mejor:
            mejores.append(mejor)
    # Ordenar por diferencia
    mejores.sort(key=lambda x: x[3])
    resultados = []
    for nombre, datos, tam, dif, valor in mejores[:3]:
        resultados.append({
            "nombre": nombre,
            "firma_tipica": datos["firma_base"],
            "firma_tamano": valor,
            "tamano_roca": tam,
            "tier": datos["tier"],
            "nota": datos.get("nota", "")
        })
    return resultados


@app.get("/minerales/por_firma/{firma}")
async def buscar_mineral_por_firma(firma: int):
    from math import inf
    mejores = []
    for nombre, datos in MINERAL_DATA.items():
        firmas = datos.get("firmas", [])
        for idx, valor in enumerate(firmas):
            dif = abs(valor - firma)
            if dif <= 100:
                mejores.append((nombre, datos, idx+1, dif, valor))
    if not mejores:
        mejor = None
        mejor_dif = inf
        mejor_tam = None
        mejor_valor = None
        for nombre, datos in MINERAL_DATA.items():
            for idx, valor in enumerate(datos.get("firmas", [])):
                dif = abs(valor - firma)
                if dif < mejor_dif:
                    mejor_dif = dif
                    mejor = (nombre, datos, idx+1, dif, valor)
        if mejor:
            mejores.append(mejor)
    mejores.sort(key=lambda x: x[3])
    resultados = []
    for nombre, datos, tam, dif, valor in mejores[:3]:
        resultados.append({
            "nombre": nombre,
            "firma_tipica": datos["firma_base"],
            "firma_tamano": valor,
            "tamano_roca": tam,
            "tier": datos["tier"],
            "nota": datos.get("nota", "")
        })
    return resultados

MINERAL_DATA = {
    "Agricium": {"tier": 2, "firma_base": 3885, "firmas": [3885, 7770, 11655, 15440, 19245], "nota": "Componentes de precisión"},
    "Aluminum": {"tier": 3, "firma_base": 4285, "firmas": [4285, 8570, 12855, 17140, 21425], "nota": "Piezas ligeras"},
    "Beryl": {"tier": 3, "firma_base": 3540, "firmas": [3540, 7080, 10620, 14160, 17880], "nota": ""},
    "Bexalite": {"tier": 1, "firma_base": 3600, "firmas": [3600, 7200, 10800, 14400, 18000], "nota": "Grupos grandes, firma muy alta"},
    "Borase": {"tier": 2, "firma_base": 3570, "firmas": [3570, 7140, 10710, 14280, 17970], "nota": ""},
    "Copper": {"tier": 3, "firma_base": 4240, "firmas": [4240, 8480, 12720, 16960, 21120], "nota": "Cables y electrónica básica"},
    "Corundum": {"tier": 3, "firma_base": 4225, "firmas": [4225, 8450, 12675, 16900, 21075], "nota": ""},
    "Gold": {"tier": 1, "firma_base": 3585, "firmas": [3585, 7170, 10755, 14340, 18135], "nota": "Múltiplo común: 3600 o 3585"},
    "Hephaestanite": {"tier": 2, "firma_base": 4180, "firmas": [4180, 8360, 12540, 16720, 20920], "nota": "Refuerzos de casco"},
    "Ice": {"tier": 3, "firma_base": 4300, "firmas": [4300, 8600, 12900, 17200, 21600], "nota": ""},
    "Iron": {"tier": 3, "firma_base": 4270, "firmas": [4270, 8540, 12810, 17080, 21530], "nota": "El estándar de la galaxia"},
    "Laranite": {"tier": 1, "firma_base": 3825, "firmas": [3825, 7650, 11475, 15300, 19350], "nota": "Muy buscado para electrónica"},
    "Lindinium": {"tier": 2, "firma_base": 3400, "firmas": [3400, 6800, 10200, 13600, 17400], "nota": ""},
    "Quantanium": {"tier": 1, "firma_base": 3170, "firmas": [3170, 6340, 9510, 12680, 16380], "nota": "Inestable, fluctúa"},
    "Quartz": {"tier": 3, "firma_base": 4210, "firmas": [4210, 8420, 12630, 16840, 21730], "nota": ""},
    "Riccite": {"tier": 2, "firma_base": 3385, "firmas": [3385, 6770, 10155, 13540, 17540], "nota": ""},
    "Savrilium": {"tier": 2, "firma_base": 3200, "firmas": [3200, 6400, 9600, 12800, 16560], "nota": ""},
    "Silicon": {"tier": 3, "firma_base": 4255, "firmas": [4255, 8510, 12765, 17020, 21865], "nota": ""},
    "Stileron": {"tier": 2, "firma_base": 3185, "firmas": [3185, 6370, 9555, 12740, 16440], "nota": ""},
    "Taranite": {"tier": 1, "firma_base": 3555, "firmas": [3555, 7110, 10665, 14220, 18390], "nota": "Múltiplo de 3: 10125"},
    "Tin": {"tier": 3, "firma_base": 4195, "firmas": [4195, 8390, 12585, 16780, 21585], "nota": ""},
    "Titanium": {"tier": 2, "firma_base": 3855, "firmas": [3855, 7710, 11565, 15420, 19815], "nota": "Fundamental para blindajes"},
    "Torite": {"tier": 1, "firma_base": 3900, "firmas": [3900, 7800, 11700, 15600, 20100], "nota": ""},
    "Tungsten": {"tier": 2, "firma_base": 3870, "firmas": [3870, 7740, 11610, 15480, 19980], "nota": ""},
    "Debris": {"tier": "Escombro", "firma_base": 2000, "firmas": [2000, 4000, 6000, 8000, 10000], "nota": "Restos de roca sin valor"},
}

@app.get("/minerales/por_firma/{firma}")
async def buscar_mineral_por_firma(firma: int):
    from math import inf
    mejores = []
    for nombre, datos in MINERAL_DATA.items():
        firmas = datos.get("firmas", [])
        for idx, valor in enumerate(firmas):
            dif = abs(valor - firma)
            if dif <= 100:
                mejores.append((nombre, datos, idx+1, dif, valor))
    if not mejores:
        mejor = None
        mejor_dif = inf
        mejor_tam = None
        mejor_valor = None
        for nombre, datos in MINERAL_DATA.items():
            for idx, valor in enumerate(datos.get("firmas", [])):
                dif = abs(valor - firma)
                if dif < mejor_dif:
                    mejor_dif = dif
                    mejor = (nombre, datos, idx+1, dif, valor)
        if mejor:
            mejores.append(mejor)
    mejores.sort(key=lambda x: x[3])
    resultados = []
    for nombre, datos, tam, dif, valor in mejores[:3]:
        resultados.append({
            "nombre": nombre,
            "firma_tipica": datos["firma_base"],
            "firma_tamano": valor,
            "tamano_roca": tam,
            "tier": datos["tier"],
            "nota": datos.get("nota", "")
        })
    return resultados

@app.get("/inventory/breakdown_detailed/{item_name}")
async def get_breakdown_detailed(item_name: str, guild_id: str = Query(...)):
    """
    Calcula el stock actual del item desglosado por calidad y ubicación,
    recorriendo todo el historial de movimientos.
    """
    # Obtener el documento del item (contiene el historial completo)
    doc = await inventory_collection.find_one({"guild_id": guild_id, "item_name": item_name})
    if not doc:
        raise HTTPException(404, "Item no encontrado")
    history = doc.get("history", [])
    # Diccionario para acumular por (calidad, location)
    breakdown = {}
    for entry in history:
        calidad = entry.get("calidad")
        location = entry.get("location", "Sin ubicación")
        cantidad = entry.get("cantidad", 0)
        key = f"{calidad}|{location}"
        if key not in breakdown:
            breakdown[key] = {"calidad": calidad, "location": location, "cantidad": 0}
        breakdown[key]["cantidad"] += cantidad
    # Filtrar solo los que tienen cantidad > 0
    result = [v for v in breakdown.values() if v["cantidad"] > 0]
    # Ordenar por calidad descendente
    result.sort(key=lambda x: x["calidad"], reverse=True)
    return result

# Nuevos minerales sin datos de firma aún (solo para inventario)
MINERAL_DATA["Aslarite"] = {"tier": 2, "firma_base": 0, "firmas": [], "nota": "Sin datos de firma"}
MINERAL_DATA["Beradom"] = {"tier": 2, "firma_base": 0, "firmas": [], "nota": "Sin datos de firma"}
MINERAL_DATA["Carinite"] = {"tier": 2, "firma_base": 0, "firmas": [], "nota": "Sin datos de firma"}
MINERAL_DATA["Ouratite"] = {"tier": 2, "firma_base": 0, "firmas": [], "nota": "Sin datos de firma"}
MINERAL_DATA["Riccite"] = {"tier": 2, "firma_base": 0, "firmas": [], "nota": "Sin datos de firma"}
MINERAL_DATA["Sadaryx"] = {"tier": 2, "firma_base": 0, "firmas": [], "nota": "Sin datos de firma"}
