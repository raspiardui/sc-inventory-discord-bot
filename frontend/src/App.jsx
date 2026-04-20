import React, { useState, useEffect } from 'react';

function App() {
  const [guildId, setGuildId] = useState(null);
  const [serverName, setServerName] = useState(null);
  const [inventory, setInventory] = useState([]);
  const [filteredItems, setFilteredItems] = useState([]);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [locationFilter, setLocationFilter] = useState('all');
  const [sortBy, setSortBy] = useState('name');
  const [selectedItem, setSelectedItem] = useState(null);
  const [history, setHistory] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [showBreakdownModal, setShowBreakdownModal] = useState(false);
  const [breakdown, setBreakdown] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [locations, setLocations] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    let gid = params.get('guild');
    if (!gid) {
      gid = prompt('🌟 Introduce el ID del servidor de Discord:');
      if (!gid) {
        setError('Necesitas un ID de servidor.');
        setLoading(false);
        return;
      }
      const newUrl = `${window.location.pathname}?guild=${gid}`;
      window.history.pushState({}, '', newUrl);
    }
    setGuildId(gid);
    fetch(`/guild/${gid}`)
      .then(res => res.ok ? res.json() : Promise.reject())
      .then(data => setServerName(data.name))
      .catch(() => setServerName('Servidor'));
  }, []);

  useEffect(() => {
    if (!guildId) return;
    fetchInventory();
    const interval = setInterval(fetchInventory, 10000);
    return () => clearInterval(interval);
  }, [guildId]);

  const fetchInventory = async () => {
    if (!guildId) return;
    try {
      setError(null);
      const res = await fetch(`/inventory?guild_id=${guildId}`);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      let data = await res.json();
      // Agrupar por item_name (sumar cantidades) para la vista principal
      const grouped = {};
      data.forEach(item => {
        if (!grouped[item.item_name]) {
          grouped[item.item_name] = {
            item_name: item.item_name,
            category: item.category,
            cantidad: 0,
            locations: [],
            last_updated: item.last_updated
          };
        }
        grouped[item.item_name].cantidad += item.cantidad;
        grouped[item.item_name].locations.push(item.location);
      });
      const groupedArray = Object.values(grouped);
      setInventory(groupedArray);
      const uniqueLocations = [...new Set(data.map(item => item.location).filter(l => l))];
      setLocations(uniqueLocations);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async (itemName) => {
    if (!guildId) return;
    try {
      const res = await fetch(`/inventory/history/${encodeURIComponent(itemName)}?guild_id=${guildId}`);
      const data = await res.json();
      setHistory(data);
      setCurrentPage(1);
    } catch (err) {
      console.error(err);
      setHistory([]);
    }
  };

  const fetchBreakdown = async (itemName) => {
    if (!guildId) return;
    try {
      const res = await fetch(`/inventory/breakdown_detailed/${encodeURIComponent(itemName)}?guild_id=${guildId}`);
      if (!res.ok) throw new Error('Error al cargar desglose');
      const data = await res.json();
      setBreakdown(data);
      setShowBreakdownModal(true);
    } catch (err) {
      console.error(err);
      alert('No se pudo cargar el desglose');
    }
  };

  const handleItemClick = (item) => {
    setSelectedItem(item);
    fetchHistory(item.item_name);
    setShowModal(true);
  };

  const exportToCSV = () => {
    if (!filteredItems.length) return;
    const headers = ['Item', 'Categoría', 'Cantidad (SCU)', 'Ubicaciones', 'Última actualización'];
    const rows = filteredItems.map(item => [
      item.item_name,
      item.category,
      item.cantidad,
      item.locations.join(', '),
      new Date(item.last_updated).toLocaleString()
    ]);
    const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.setAttribute('download', `inventario_${guildId}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const exportHistoryToCSV = () => {
    if (!history.length) return;
    const headers = ['Usuario', 'Acción', 'Cantidad', 'Calidad', 'Ubicación', 'Fecha'];
    const rows = history.map(entry => [
      entry.discord_name,
      entry.action === 'add' ? 'Añadió' : 'Retiró',
      Math.abs(entry.cantidad),
      entry.calidad,
      entry.location || 'Sin ubicación',
      new Date(entry.date).toLocaleString()
    ]);
    const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.setAttribute('download', `historial_${selectedItem.item_name}_${guildId}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const totalPages = Math.ceil(history.length / itemsPerPage);
  const paginatedHistory = history.slice((currentPage-1)*itemsPerPage, currentPage*itemsPerPage);

  useEffect(() => {
    let filtered = [...inventory];
    if (search.trim()) {
      filtered = filtered.filter(item =>
        item.item_name.toLowerCase().includes(search.toLowerCase())
      );
    }
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(item => item.category === categoryFilter);
    }
    if (locationFilter !== 'all') {
      filtered = filtered.filter(item => item.locations.includes(locationFilter));
    }
    switch (sortBy) {
      case 'name':
        filtered.sort((a, b) => a.item_name.localeCompare(b.item_name));
        break;
      case 'quality-desc':
        filtered.sort((a, b) => (b.calidad || 0) - (a.calidad || 0));
        break;
      case 'quality-asc':
        filtered.sort((a, b) => (a.calidad || 0) - (b.calidad || 0));
        break;
      case 'quantity-desc':
        filtered.sort((a, b) => b.cantidad - a.cantidad);
        break;
      case 'quantity-asc':
        filtered.sort((a, b) => a.cantidad - b.cantidad);
        break;
      default:
        break;
    }
    setFilteredItems(filtered);
  }, [search, categoryFilter, locationFilter, sortBy, inventory]);

  const categories = ['all', ...new Set(inventory.map(i => i.category))];
  const locationOptions = ['all', ...locations];

  const getQualityColor = (quality) => {
    const q = Number(quality);
    if (q >= 800) return '#ff4d4d';
    if (q >= 600) return '#ffaa44';
    if (q >= 400) return '#ffdd44';
    if (q >= 200) return '#88ff88';
    return '#44ff44';
  };

  const formatUTC = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (loading) return <div style={styles.loadingContainer}>Cargando inventario...</div>;
  if (error) return <div style={styles.error}>⚠️ {error}</div>;
  if (!guildId) return <div style={styles.error}>❌ ID de servidor no válido</div>;

  return (
    <div style={styles.container}>
      <div style={styles.hero}>
        <h1 style={styles.title}>🚀 Inventario de {serverName || '...'}</h1>
        <p style={styles.subtitle}>Recursos minerales y refinados de la organización</p>
        <p style={styles.guildId}>🔰 Servidor ID: {guildId}</p>
      </div>

      <div style={styles.controls}>
        <input
          type="text"
          placeholder="🔍 Buscar material..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={styles.searchInput}
        />
        <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} style={styles.select}>
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat === 'all' ? '📁 Todas las categorías' : cat}</option>
          ))}
        </select>
        <select value={locationFilter} onChange={(e) => setLocationFilter(e.target.value)} style={styles.select}>
          {locationOptions.map(loc => (
            <option key={loc} value={loc}>{loc === 'all' ? '📍 Todas las ubicaciones' : loc}</option>
          ))}
        </select>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} style={styles.select}>
          <option value="name">🔤 Nombre (A-Z)</option>
          <option value="quality-desc">✨ Calidad (mayor a menor)</option>
          <option value="quality-asc">✨ Calidad (menor a mayor)</option>
          <option value="quantity-desc">📦 Cantidad (mayor a menor)</option>
          <option value="quantity-asc">📦 Cantidad (menor a mayor)</option>
        </select>
        <button onClick={exportToCSV} style={styles.exportBtn}>📎 Exportar CSV</button>
        <button onClick={fetchInventory} style={styles.refreshBtn}>⟳ Refrescar</button>
      </div>

      <div style={styles.grid}>
        {filteredItems.map(item => (
          <div key={item.item_name} style={styles.card}>
            <h3 style={styles.itemName}>{item.item_name}</h3>
            <p style={styles.category}>📂 {item.category}</p>
            <p style={styles.amount}>📦 {item.cantidad} SCU</p>
            <div style={styles.cardButtons}>
              <button onClick={() => handleItemClick(item)} style={styles.historyBtn}>📜 Historial</button>
              <button onClick={() => fetchBreakdown(item.item_name)} style={styles.breakdownBtn}>📊 Desglose</button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal de historial (sin cambios) */}
      {showModal && selectedItem && (
        <div style={styles.modalOverlay} onClick={() => setShowModal(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 style={styles.modalTitle}>{selectedItem.item_name}</h2>
            <button style={styles.closeBtn} onClick={() => setShowModal(false)}>✖</button>
            <div style={styles.historyHeader}>
              <h3>📜 Historial de movimientos</h3>
              <button onClick={exportHistoryToCSV} style={styles.exportHistoryBtn}>📎 Exportar CSV</button>
            </div>
            {history.length === 0 ? (
              <p>No hay movimientos registrados.</p>
            ) : (
              <>
                <ul style={styles.historyList}>
                  {paginatedHistory.map((entry, idx) => (
                    <li key={idx} style={entry.action === 'add' ? styles.addEntry : styles.removeEntry}>
                      <strong>{entry.discord_name}</strong> - {entry.action === 'add' ? '➕ Añadió' : '➖ Retiró'} {Math.abs(entry.cantidad)} SCU (calidad {entry.calidad})
                      <br />📍 {entry.location || 'Sin ubicación'}
                      <br /><small>{formatUTC(entry.date)}</small>
                    </li>
                  ))}
                </ul>
                {totalPages > 1 && (
                  <div style={styles.pagination}>
                    <button onClick={() => setCurrentPage(p => Math.max(1, p-1))} disabled={currentPage === 1}>Anterior</button>
                    <span>Página {currentPage} de {totalPages}</span>
                    <button onClick={() => setCurrentPage(p => Math.min(totalPages, p+1))} disabled={currentPage === totalPages}>Siguiente</button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Modal de desglose detallado con tarjetas y barras de calidad */}
      {showBreakdownModal && (
        <div style={styles.modalOverlay} onClick={() => setShowBreakdownModal(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 style={styles.modalTitle}>Desglose de stock actual</h2>
            <button style={styles.closeBtn} onClick={() => setShowBreakdownModal(false)}>✖</button>
            {breakdown.length === 0 ? (
              <p>No hay stock actual para este material.</p>
            ) : (
              <div style={styles.breakdownGrid}>
                {breakdown.map((entry, idx) => (
                  <div key={idx} style={styles.breakdownCard}>
                    <p style={styles.breakdownLocation}>📍 {entry.location}</p>
                    <p style={styles.breakdownAmount}>📦 {entry.cantidad} SCU</p>
                    <div style={styles.breakdownQualityBar}>
                      <div style={{
                        width: `${(entry.calidad / 1000) * 100}%`,
                        backgroundColor: getQualityColor(entry.calidad),
                        height: '100%',
                        borderRadius: '10px'
                      }} />
                    </div>
                    <p style={styles.breakdownQuality}>✨ Calidad: {entry.calidad}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    backgroundImage: 'url("https://images.unsplash.com/photo-1534796636912-3b95b3ab5986?q=80&w=2071&auto=format&fit=crop")',
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundAttachment: 'fixed',
    fontFamily: "'Segoe UI', system-ui, sans-serif",
    color: '#f0f0f0'
  },
  hero: {
    textAlign: 'center',
    marginBottom: '40px',
    padding: '20px',
    background: 'rgba(0,0,0,0.6)',
    backdropFilter: 'blur(8px)',
    borderRadius: '30px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center'
  },
  title: {
    fontSize: '2.8rem',
    fontWeight: 'bold',
    background: 'linear-gradient(135deg, #FFD966, #FF8C42)',
    WebkitBackgroundClip: 'text',
    backgroundClip: 'text',
    color: 'transparent'
  },
  subtitle: {
    fontSize: '1.1rem',
    opacity: 0.9
  },
  guildId: {
    fontSize: '0.8rem',
    background: 'rgba(255,255,255,0.2)',
    display: 'inline-block',
    padding: '5px 12px',
    borderRadius: '20px'
  },
  controls: {
    display: 'flex',
    gap: '15px',
    marginBottom: '30px',
    flexWrap: 'wrap',
    justifyContent: 'center'
  },
  searchInput: {
    flex: 1,
    minWidth: '200px',
    padding: '12px 18px',
    borderRadius: '40px',
    border: 'none',
    background: 'rgba(255,255,255,0.15)',
    color: 'white',
    fontSize: '1rem'
  },
  select: {
    padding: '12px 18px',
    borderRadius: '40px',
    border: '1px solid rgba(255,255,255,0.3)',
    background: 'rgba(0,0,0,0.6)',
    color: '#f0f0f0',
    cursor: 'pointer'
  },
  exportBtn: {
    padding: '12px 24px',
    borderRadius: '40px',
    border: 'none',
    background: '#2c7da0',
    color: 'white',
    fontWeight: 'bold',
    cursor: 'pointer'
  },
  refreshBtn: {
    padding: '12px 24px',
    borderRadius: '40px',
    border: 'none',
    background: 'linear-gradient(95deg, #FF8C42, #FF3B3F)',
    color: 'white',
    fontWeight: 'bold',
    cursor: 'pointer'
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(270px, 1fr))',
    gap: '25px'
  },
  card: {
    background: 'rgba(20, 25, 45, 0.7)',
    backdropFilter: 'blur(12px)',
    borderRadius: '24px',
    padding: '20px',
    transition: 'transform 0.2s'
  },
  cardButtons: {
    display: 'flex',
    gap: '10px',
    marginTop: '15px',
    justifyContent: 'center'
  },
  historyBtn: {
    background: '#44aaff',
    border: 'none',
    padding: '6px 12px',
    borderRadius: '20px',
    color: 'white',
    cursor: 'pointer',
    fontWeight: 'bold'
  },
  breakdownBtn: {
    background: '#ffaa44',
    border: 'none',
    padding: '6px 12px',
    borderRadius: '20px',
    color: '#1a1f2e',
    cursor: 'pointer',
    fontWeight: 'bold'
  },
  itemName: {
    fontSize: '1.5rem',
    margin: '0 0 8px',
    color: '#FFD966'
  },
  category: {
    fontSize: '0.8rem',
    textTransform: 'uppercase',
    color: '#aaa'
  },
  amount: {
    fontSize: '1.6rem',
    fontWeight: 'bold',
    margin: '10px 0'
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    backdropFilter: 'blur(5px)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000
  },
  modal: {
    background: 'linear-gradient(145deg, #1e1f2c, #14151f)',
    borderRadius: '28px',
    padding: '25px',
    maxWidth: '700px',
    width: '90%',
    maxHeight: '80%',
    overflow: 'auto',
    position: 'relative'
  },
  modalTitle: {
    fontSize: '1.8rem',
    color: '#FFD966',
    marginBottom: '10px'
  },
  closeBtn: {
    position: 'absolute',
    top: '15px',
    right: '20px',
    background: 'none',
    border: 'none',
    color: '#fff',
    fontSize: '24px',
    cursor: 'pointer'
  },
  historyHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '10px',
    marginBottom: '10px'
  },
  exportHistoryBtn: {
    background: '#2c7da0',
    border: 'none',
    padding: '6px 12px',
    borderRadius: '20px',
    color: 'white',
    cursor: 'pointer'
  },
  historyList: {
    listStyle: 'none',
    padding: 0,
    maxHeight: '400px',
    overflowY: 'auto'
  },
  addEntry: {
    borderLeft: '4px solid #44ff44',
    padding: '10px',
    marginBottom: '10px',
    background: 'rgba(68,255,68,0.1)',
    borderRadius: '12px'
  },
  removeEntry: {
    borderLeft: '4px solid #ff4444',
    padding: '10px',
    marginBottom: '10px',
    background: 'rgba(255,68,68,0.1)',
    borderRadius: '12px'
  },
  pagination: {
    display: 'flex',
    justifyContent: 'center',
    gap: '15px',
    marginTop: '15px',
    alignItems: 'center'
  },
  breakdownGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '15px',
    marginTop: '10px'
  },
  breakdownCard: {
    background: 'rgba(20, 25, 45, 0.8)',
    borderRadius: '16px',
    padding: '12px',
    border: '1px solid rgba(255,255,255,0.1)'
  },
  breakdownLocation: {
    fontSize: '0.9rem',
    color: '#88aaff',
    marginBottom: '5px'
  },
  breakdownAmount: {
    fontSize: '1.2rem',
    fontWeight: 'bold',
    marginBottom: '8px'
  },
  breakdownQualityBar: {
    height: '8px',
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: '10px',
    overflow: 'hidden',
    margin: '8px 0'
  },
  breakdownQuality: {
    fontSize: '0.8rem',
    textAlign: 'right'
  },
  loadingContainer: {
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    background: '#020024',
    color: 'white'
  },
  error: {
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    fontSize: '1.5rem',
    backgroundColor: '#2a0000',
    color: '#ff8888'
  }
};

export default App;
