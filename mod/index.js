(function () {
  try {
  const api = window.SubwayBuilderAPI;
  if (!api) throw new Error('[Jabodetabek] SubwayBuilderAPI unavailable');
  // 1.7.2's data loader uses the game's own local data server, not arbitrary URLs.
  const data = '/data/JKT';
  const tiles = 'http://127.0.0.1:18766';
  api.registerCity({
    name: 'Jabodetabek', code: 'JKT',
    description: 'Lightweight Jakarta, Bogor, Depok, Tangerang & Bekasi map. Up to 30,000 sampled buildings. © OpenMapTiles © OpenStreetMap contributors. Local-government population controls; estimated workplace locations using business data where available. OD and driving times are modelled.',
    initialViewState: {longitude: 106.8272, latitude: -6.1754, zoom: 11.5, bearing: 0},
    minZoom: 8,
    difficulty: null
  });
  api.map.setTileURLOverride({
    cityCode: 'JKT', tilesUrl: tiles + '/JKT/{z}/{x}/{y}.mvt',
    foundationTilesUrl: tiles + '/JKT_foundations/{z}/{x}/{y}.mvt', maxZoom: 13
  });
  const files = {
    buildingsIndex: data + '/buildings_index.bin.gz',
    demandData: data + '/demand_data.json.gz',
    roads: data + '/roads.geojson.gz',
    runwaysTaxiways: data + '/runways_taxiways.geojson.gz'
  };
  api.cities.setCityDataFiles('JKT', files);
  // Compatibility with 1.7.2's internal UID-keyed data lookup.
  api.cities.setCityDataFiles('local.faiz.jabodetabek:JKT', files);
  api.map.setDefaultLayerVisibility('JKT', {oceanFoundations: false});
  // Depot stores parks/airports under landuse. Adapt this map instance only;
  // global setLayerOverride would also change the user's other cities.
  api.hooks.onMapReady(map => {
    map = map || api.utils.getMap();
    if (!map) return;
    let applying = false;
    const apply = () => {
      if (applying) return;
      const container = map.getContainer?.();
      if (api.utils.getCityCode() !== 'JKT') {
        container?.querySelector('[data-jkt-credit]')?.remove();
        return;
      }
      applying = true;
      try {
        if (container && !container.querySelector('[data-jkt-credit]')) {
          const credit = document.createElement('div');
          credit.dataset.jktCredit = 'true';
          credit.style.cssText = 'position:absolute;left:50%;transform:translateX(-50%);bottom:72px;z-index:5;padding:3px 6px;background:rgba(255,255,255,.88);color:#222;font:10px sans-serif;border-radius:3px;pointer-events:auto;white-space:nowrap';
          for (const [text, href] of [['© OpenMapTiles','https://openmaptiles.org/'],
                                    [' © OpenStreetMap contributors','https://www.openstreetmap.org/copyright'],
                                    [' © ESA WorldCover2021','https://esa-worldcover.org/en/data-access']]) {
            const link = document.createElement('a');
            link.textContent = text; link.href = href; link.target = '_blank';
            link.rel = 'noopener noreferrer'; link.style.color = '#222';
            credit.appendChild(link);
          }
          container.appendChild(credit);
        }
        for (const [id, kind] of [['parks-large','park'], ['airports','aerodrome']]) {
          const layers = map.getStyle().layers;
          const index = layers.findIndex(layer => layer.id === id);
          if (index < 0 || layers[index]['source-layer'] === 'landuse') continue;
          const replacement = {...layers[index], 'source-layer':'landuse',
                               filter:['==',['get','kind'],kind]};
          const before = layers[index+1]?.id;
          map.removeLayer(id);
          map.addLayer(replacement, before);
        }
      } finally { applying = false; }
    };
    map.on('styledata', apply);
    apply();
  });
  api.hooks.onGameInit(() => {
    if (api.utils.getCityCode() === 'JKT') {
      api.ui.showNotification('© OpenMapTiles © OpenStreetMap contributors. Jabodetabek v4.1 S0: corrected organic demand; population controls conserved. Workplaces/OD remain estimates.', 'info');
    }
  });
  console.log('[Jabodetabek] Registered JKT; asset servers required on ports 18765/18766.');
  } catch (error) {
    console.error('[Jabodetabek]', error);
  }
})();
