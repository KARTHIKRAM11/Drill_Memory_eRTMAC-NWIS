import React from 'react'
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, Tooltip } from 'react-leaflet'

const STATUS_COLOR = {
  producing: '#22c55e',
  drilling: '#f5a524',
  abandoned: '#93a4b8',
}

export default function MapView({ wells, selectedWell, onSelectWell, radiusKm }) {
  const center = wells.length
    ? [wells.reduce((s, w) => s + w.latitude, 0) / wells.length, wells.reduce((s, w) => s + w.longitude, 0) / wells.length]
    : [27.3, 95.3]

  return (
    <MapContainer center={center} zoom={11} style={{ height: '100%', width: '100%' }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {wells.map((w) => (
        <CircleMarker
          key={w.id}
          center={[w.latitude, w.longitude]}
          radius={selectedWell?.id === w.id ? 10 : 6}
          pathOptions={{
            color: selectedWell?.id === w.id ? '#2dd4bf' : STATUS_COLOR[w.status] || '#fff',
            fillColor: STATUS_COLOR[w.status] || '#fff',
            fillOpacity: 0.85,
            weight: selectedWell?.id === w.id ? 3 : 1.5,
          }}
          eventHandlers={{ click: () => onSelectWell(w) }}
        >
          <Tooltip direction="top" offset={[0, -6]}>{w.name}</Tooltip>
          <Popup>
            <strong>{w.name}</strong><br />
            Field: {w.field_name}<br />
            Status: {w.status}<br />
            TD: {w.total_depth_m}m
          </Popup>
        </CircleMarker>
      ))}
      {selectedWell && (
        <Circle
          center={[selectedWell.latitude, selectedWell.longitude]}
          radius={radiusKm * 1000}
          pathOptions={{ color: '#2dd4bf', fillOpacity: 0.05, dashArray: '6 6' }}
        />
      )}
    </MapContainer>
  )
}
