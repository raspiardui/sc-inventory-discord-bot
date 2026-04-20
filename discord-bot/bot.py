import discord
from discord import app_commands
import httpx
import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = os.getenv("API_BASE_URL", "http://backend:8000")

ALL_ITEMS = [
    "Agricium", "Aluminum", "Beryl", "Bexalite", "Borase", "Copper", "Corundum",
    "Gold", "Hephaestanite", "Ice", "Iron", "Laranite", "Lindinium", "Quantanium",
    "Quartz", "Riccite", "Savrilium", "Silicon", "Stileron", "Taranite", "Tin",
    "Titanium", "Torite", "Tungsten", "Debris",
    "Aphorite", "Dolivine", "Hadanite", "Janalite",
    "RMC", "Recycled Material Composite", "Construction Materials",
    "Circuit Boards", "Power Cells", "Compboards", "Optical components",
    "Cooling Manifolds", "Polymer Sheets", "Reinforced Plates", "Wire Spools",
    "Pressure Valves",
    "Carbon", "Fluorine", "Hydrogen", "Iodine", "Nitrogen", "Oxygen", "Sulfur",
    "Refined Agricium", "Refined Aluminum", "Refined Bexalite", "Refined Borase",
    "Refined Copper", "Refined Gold", "Refined Hephaestanite", "Refined Iron",
    "Refined Laranite", "Refined Quantanium", "Refined Silver", "Refined Taranite",
    "Refined Titanium", "Refined Tungsten"
]

LOCATIONS = [
    "HUR-L1", "HUR-L2", "ARC-L1", "ARC-L2", "CRU-L1", "MIC-L1", "MIC-L2",
    "Pyro Gateway", "Magnus Gateway", "Terra Gateway", "Nyx Gateway",
    "Ruin Station", "Checkmate", "Orbituary", "Patchwork",
    "Delamar", "Reclamation Station"
]

MINERALES_CON_FIRMA = [
    "Agricium", "Aluminum", "Beryl", "Bexalite", "Borase", "Copper", "Corundum",
    "Gold", "Hephaestanite", "Ice", "Iron", "Laranite", "Lindinium", "Quantanium",
    "Quartz", "Riccite", "Savrilium", "Silicon", "Stileron", "Taranite", "Tin",
    "Titanium", "Torite", "Tungsten", "Debris"
]

async def item_autocomplete(interaction: discord.Interaction, current: str):
    filtered = [i for i in ALL_ITEMS if current.lower() in i.lower()][:25]
    return [app_commands.Choice(name=i, value=i) for i in filtered]

async def location_autocomplete(interaction: discord.Interaction, current: str):
    filtered = [loc for loc in LOCATIONS if current.lower() in loc.lower()][:25]
    return [app_commands.Choice(name=loc, value=loc) for loc in filtered]

async def mineral_autocomplete(interaction: discord.Interaction, current: str):
    filtered = [m for m in MINERALES_CON_FIRMA if current.lower() in m.lower()][:25]
    return [app_commands.Choice(name=m, value=m) for m in filtered]

class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("Comandos sincronizados globalmente.")

    async def on_ready(self):
        print(f"Bot {self.user} conectado.")
        for guild in self.guilds:
            print(f"  Servidor: {guild.name} (ID: {guild.id})")

    async def on_guild_join(self, guild):
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"Unido a {guild.name}, comandos sincronizados: {len(synced)}")

bot = MyBot()

# ---- Comandos ----
@bot.tree.command(name="add_item", description="Añade items al inventario")
@app_commands.describe(
    item_name="Nombre del item",
    cantidad="Cantidad en SCU",
    calidad="Calidad (1-1000)",
    ubicacion="Lugar donde está almacenado"
)
@app_commands.autocomplete(item_name=item_autocomplete, ubicacion=location_autocomplete)
async def add_item(interaction: discord.Interaction, item_name: str, cantidad: str, calidad: int, ubicacion: str):
    await interaction.response.defer()
    if interaction.guild_id is None:
        await interaction.followup.send("Este comando solo funciona en servidores.", ephemeral=True)
        return
    try:
        cantidad_f = float(cantidad.replace(",", "."))
    except:
        await interaction.followup.send("Cantidad inválida.", ephemeral=True)
        return
    if cantidad_f <= 0:
        await interaction.followup.send("Cantidad positiva requerida.", ephemeral=True)
        return
    if not (1 <= calidad <= 1000):
        await interaction.followup.send("Calidad entre 1 y 1000.", ephemeral=True)
        return
    if ubicacion not in LOCATIONS:
        await interaction.followup.send("Ubicación no válida.", ephemeral=True)
        return
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{API_URL}/inventory/add", json={
            "guild_id": str(interaction.guild_id),
            "item_name": item_name,
            "cantidad": cantidad_f,
            "calidad": calidad,
            "discord_name": interaction.user.display_name,
            "location": ubicacion
        })
    if resp.status_code == 200:
        await interaction.followup.send(f"✅ Añadido **{cantidad_f} SCU** de **{item_name}** (calidad {calidad}) en **{ubicacion}** por {interaction.user.display_name}.")
    else:
        await interaction.followup.send(f"❌ Error: {resp.text}", ephemeral=True)

@bot.tree.command(name="remove_item", description="Retira items del inventario")
@app_commands.describe(
    item_name="Nombre del item",
    cantidad="Cantidad en SCU",
    calidad="Calidad retirada (1-1000)",
    ubicacion="Ubicación de donde se retira"
)
@app_commands.autocomplete(item_name=item_autocomplete, ubicacion=location_autocomplete)
async def remove_item(interaction: discord.Interaction, item_name: str, cantidad: str, calidad: int, ubicacion: str):
    await interaction.response.defer()
    if interaction.guild_id is None:
        await interaction.followup.send("Este comando solo funciona en servidores.", ephemeral=True)
        return
    try:
        cantidad_f = float(cantidad.replace(",", "."))
    except:
        await interaction.followup.send("Cantidad inválida.", ephemeral=True)
        return
    if cantidad_f <= 0:
        await interaction.followup.send("Cantidad positiva requerida.", ephemeral=True)
        return
    if not (1 <= calidad <= 1000):
        await interaction.followup.send("Calidad entre 1 y 1000.", ephemeral=True)
        return
    if ubicacion not in LOCATIONS:
        await interaction.followup.send("Ubicación no válida.", ephemeral=True)
        return
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{API_URL}/inventory/remove", json={
            "guild_id": str(interaction.guild_id),
            "item_name": item_name,
            "cantidad": cantidad_f,
            "calidad": calidad,
            "discord_name": interaction.user.display_name,
            "location": ubicacion
        })
    if resp.status_code == 200:
        await interaction.followup.send(f"✅ Retirado **{cantidad_f} SCU** de **{item_name}** (calidad {calidad}) desde **{ubicacion}** por {interaction.user.display_name}.")
    elif resp.status_code == 404:
        await interaction.followup.send(f"❌ **{item_name}** no existe.", ephemeral=True)
    elif resp.status_code == 400:
        await interaction.followup.send("❌ Cantidad insuficiente.", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ Error: {resp.text}", ephemeral=True)

@bot.tree.command(name="inventory", description="Muestra el inventario")
async def inventory(interaction: discord.Interaction):
    await interaction.response.defer()
    if interaction.guild_id is None:
        await interaction.followup.send("Este comando solo funciona en servidores.", ephemeral=True)
        return
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{API_URL}/inventory", params={"guild_id": str(interaction.guild_id)})
    if resp.status_code != 200:
        await interaction.followup.send("Error al obtener inventario.", ephemeral=True)
        return
    data = resp.json()
    if not data:
        await interaction.followup.send("El inventario está vacío.")
        return
    embed = discord.Embed(title="📦 Inventario Cruz del Sur", color=0x00aaff)
    categories = {}
    for item in data:
        cat = item.get("category", "Otro")
        loc = item.get("location", "Sin ubicación")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f"{item['item_name']}: **{item['cantidad']} SCU** (calidad {item.get('calidad','?')}) - 📍 {loc}")
    for cat, items in categories.items():
        embed.add_field(name=f"── {cat} ──", value="\n".join(items[:8]), inline=True)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="orgweb", description="Obtén el enlace web del inventario")
async def orgweb(interaction: discord.Interaction):
    if interaction.guild_id is None:
        await interaction.response.send_message("Este comando solo funciona en servidores.", ephemeral=True)
        return
    web_url = f"https://invcruzsur.csroy.es/?guild={interaction.guild_id}"
    embed = discord.Embed(title="🌐 Web del Inventario", description=f"Inventario de **{interaction.guild.name}**", color=0x44aaff)
    embed.add_field(name="🔗 Enlace", value=f"[Haz clic aquí]({web_url})", inline=False)
    await interaction.response.send_message(embed=embed)

# Comando identificar mejorado con firmas por tamaño
@bot.tree.command(name="identificar", description="Identifica un mineral por el número de firma del escáner")
@app_commands.describe(
    firma="Número que ves en el pico del escáner",
    masa_scu="Opcional: masa total de la roca en SCU para calcular SCU estimado"
)
async def identificar(interaction: discord.Interaction, firma: int, masa_scu: float = None):
    await interaction.response.defer()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{API_URL}/minerales/por_firma/{firma}")
    if resp.status_code != 200:
        await interaction.followup.send("❌ No se pudo identificar ningún mineral con esa firma.")
        return
    minerales = resp.json()
    if not minerales:
        await interaction.followup.send("❌ No hay minerales cercanos a esa firma.")
        return
    mejor = minerales[0]
    nombre = mejor["nombre"]
    firma_tipica = mejor["firma_tipica"]
    firma_tamano = mejor["firma_tamano"]
    tamano = mejor["tamano_roca"]
    tier = mejor["tier"]
    nota = mejor.get("nota", "")
    embed = discord.Embed(title=f"🔍 Identificación de roca", color=0x44aaff)
    embed.add_field(name="📡 Firma introducida", value=f"{firma}", inline=True)
    embed.add_field(name="💎 Mineral", value=f"**{nombre}**", inline=True)
    embed.add_field(name="📊 Firma típica", value=f"{firma_tipica}", inline=True)
    embed.add_field(name="🔢 Tamaño estimado", value=f"Tamaño {tamano} (firma {firma_tamano})", inline=True)
    embed.add_field(name="🏷️ Tier", value=f"{tier}", inline=True)
    if nota:
        embed.add_field(name="📝 Nota", value=nota, inline=False)
    if masa_scu is not None and masa_scu > 0:
        proporcion = firma / firma_tamano
        scu_estimado = round(proporcion * masa_scu, 2)
        embed.add_field(name="📦 Masa de la roca", value=f"{masa_scu} SCU", inline=True)
        embed.add_field(name="⚙️ Proporción", value=f"{proporcion:.2%}", inline=True)
        embed.add_field(name="💰 SCU estimado", value=f"**{scu_estimado} SCU**", inline=False)
        embed.set_footer(text="Estimación basada en firma por tamaño de roca.")
    else:
        embed.set_footer(text="Usa /identificar <firma> <masa> para calcular SCU estimado.")
    await interaction.followup.send(embed=embed)

# Nuevo comando /tabla
@bot.tree.command(name="tabla", description="Muestra los valores de firma por tamaño para un mineral")
@app_commands.describe(mineral="Nombre del mineral (opcional, si no se pone lista todos)")
async def tabla(interaction: discord.Interaction, mineral: str = None):
    await interaction.response.defer()
    async with httpx.AsyncClient(timeout=10.0) as client:
        if mineral:
            resp = await client.get(f"{API_URL}/minerales/{mineral}")
            if resp.status_code != 200:
                await interaction.followup.send(f"❌ Mineral '{mineral}' no encontrado.")
                return
            data = resp.json()
            firmas = data.get("firmas", [])
            if not firmas:
                await interaction.followup.send(f"❌ {mineral} no tiene datos de firma por tamaño.")
                return
            embed = discord.Embed(title=f"📊 Tabla de firmas para {mineral}", color=0xffaa44)
            for i, f in enumerate(firmas, start=1):
                embed.add_field(name=f"Tamaño {i}", value=f"{f}", inline=True)
            await interaction.followup.send(embed=embed)
        else:
            resp = await client.get(f"{API_URL}/minerales")
            if resp.status_code != 200:
                await interaction.followup.send("❌ Error al obtener la lista de minerales.")
                return
            data = resp.json()
            embed = discord.Embed(title="📋 Minerales disponibles", color=0xffaa44)
            for nombre, info in data.items():
                embed.add_field(name=nombre, value=f"Base: {info['firma_base']} | Tier: {info['tier']}", inline=False)
            await interaction.followup.send(embed=embed)

# Comando estimar (sin cambios importantes)
@bot.tree.command(name="estimar", description="Calcula SCU estimado para un mineral concreto")
@app_commands.describe(
    mineral="Nombre del mineral",
    firma_pico="Firma que ves en el escáner",
    masa_scu="Masa total de la roca en SCU"
)
@app_commands.autocomplete(mineral=mineral_autocomplete)
async def estimar(interaction: discord.Interaction, mineral: str, firma_pico: int, masa_scu: float):
    await interaction.response.defer()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{API_URL}/minerales/{mineral}")
    if resp.status_code != 200:
        await interaction.followup.send(f"❌ Mineral '{mineral}' no encontrado en la base de datos.", ephemeral=True)
        return
    data = resp.json()
    firmas = data.get("firmas", [])
    if not firmas:
        await interaction.followup.send(f"❌ {mineral} no tiene datos de firma por tamaño.", ephemeral=True)
        return
    # Buscar el tamaño más cercano
    mejor_tam = 1
    mejor_dif = abs(firmas[0] - firma_pico)
    for idx, f in enumerate(firmas):
        dif = abs(f - firma_pico)
        if dif < mejor_dif:
            mejor_dif = dif
            mejor_tam = idx + 1
    firma_referencia = firmas[mejor_tam-1]
    proporcion = firma_pico / firma_referencia
    scu_estimado = round(proporcion * masa_scu, 2)
    embed = discord.Embed(title=f"📊 Estimación para {mineral}", color=0xffaa44)
    embed.add_field(name="Tamaño estimado", value=f"Tamaño {mejor_tam} (firma {firma_referencia})", inline=True)
    embed.add_field(name="Firma del pico", value=firma_pico, inline=True)
    embed.add_field(name="Proporción", value=f"{proporcion:.2%}", inline=True)
    embed.add_field(name="Masa de la roca", value=f"{masa_scu} SCU", inline=True)
    embed.add_field(name="SCU estimado", value=f"**{scu_estimado} SCU**", inline=False)
    await interaction.followup.send(embed=embed)

bot.run(DISCORD_TOKEN)
