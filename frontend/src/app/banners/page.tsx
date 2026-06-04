"use client";

import { useEffect, useState } from "react";
import { adminFetch, API_BASE } from "../../lib/apiClient";

export default function BannersPage() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [detailCache, setDetailCache] = useState<Record<string, any>>({});
  const [zoom, setZoom] = useState(false);

  const projectId = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

  useEffect(() => {
    adminFetch(`${API_BASE}/banners/${projectId}`)
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  async function openDetail(index: number) {
    const item = data[index];

    if (!detailCache[item.id]) {
      const res = await adminFetch(`${API_BASE}/banners/item/${item.id}`);
      const json = await res.json();

      setDetailCache((prev) => ({
        ...prev,
        [item.id]: json,
      }));
    }

    setSelectedIndex(index);
  }

  function current() {
    if (selectedIndex === null) return null;
    return detailCache[data[selectedIndex]?.id] || data[selectedIndex];
  }

  function next() {
    if (selectedIndex === null) return;
    setSelectedIndex((prev) =>
      prev! < data.length - 1 ? prev! + 1 : prev
    );
  }

  function prev() {
    if (selectedIndex === null) return;
    setSelectedIndex((prev) => (prev! > 0 ? prev! - 1 : prev));
  }

  function close() {
    setSelectedIndex(null);
    setZoom(false);
  }

  return (
    <main style={{ padding: 24 }}>
      <h1 style={{ fontSize: 28 }}>Evidências de banners</h1>

      {loading && <p>Carregando...</p>}

      {!loading && (
        <table style={{ width: "100%", marginTop: 20 }}>
          <thead>
            <tr>
              <th>Preview</th>
              <th>Anunciante</th>
              <th>Portal</th>
              <th>Confiança</th>
              <th>Valor</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            {data.map((item, i) => (
              <tr key={item.id}>
                <td>
                  <img
                    src={item.screenshot_banner_url}
                    width={80}
                    style={{ borderRadius: 6 }}
                  />
                </td>

                <td>{item.advertiser_name}</td>
                <td>{item.source_name}</td>
                <td>
                  <span
                    style={{
                      padding: "4px 8px",
                      borderRadius: 6,
                      background:
                        item.detection_confidence === "alta"
                          ? "#d1fae5"
                          : item.detection_confidence === "media"
                          ? "#fef3c7"
                          : "#fee2e2",
                    }}
                  >
                    {item.detection_confidence}
                  </span>
                </td>

                <td>R$ {item.estimated_value}</td>

                <td>
                  <button onClick={() => openDetail(i)}>
                    Ver detalhe
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* MODAL */}
      {selectedIndex !== null && current() && (
        <div style={overlay}>
          <div style={modal}>
            <button onClick={close} style={closeBtn}>✕</button>

            {/* HEADER */}
            <div style={header}>
              <div>
                <h2>{current().advertiser_name}</h2>
                <p>{current().source_name}</p>
              </div>

              <div style={badgeRow}>
                <Badge label={current().detection_confidence} />
                <Badge label={current().classification} />
              </div>
            </div>

            {/* IMAGEM */}
            <div style={{ textAlign: "center" }}>
              <img
                src={current().screenshot_banner_url}
                style={{
                  width: zoom ? "100%" : "60%",
                  cursor: "zoom-in",
                }}
                onClick={() => setZoom(!zoom)}
              />
            </div>

            {/* AÇÕES */}
            <div style={actions}>
              <a href={current().page_url} target="_blank">
                Página original
              </a>

              <a href={current().screenshot_banner_url} target="_blank">
                Abrir imagem
              </a>

              <a href={current().screenshot_banner_url} download>
                Baixar
              </a>
            </div>

            {/* DADOS */}
            <div style={grid}>
              <Info label="Valor" value={`R$ ${current().estimated_value}`} />
              <Info label="Data" value={current().created_at} />
              <Info label="Dimensão" value={`${current().width}x${current().height}`} />
            </div>

            {/* OCR */}
            <div style={ocr}>
              <b>Texto detectado</b>
              <p>{current().ocr_text || "Nenhum texto detectado"}</p>
            </div>

            {/* NAVEGAÇÃO */}
            <div style={nav}>
              <button onClick={prev}>Anterior</button>
              <button onClick={next}>Próximo</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

// COMPONENTES

function Badge({ label }: { label: string }) {
  return (
    <span
      style={{
        padding: "4px 10px",
        borderRadius: 6,
        background: "#eee",
        marginLeft: 8,
      }}
    >
      {label}
    </span>
  );
}

function Info({ label, value }: any) {
  return (
    <div>
      <small>{label}</small>
      <div><b>{value}</b></div>
    </div>
  );
}

// STYLES

const overlay = {
  position: "fixed" as const,
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
};

const modal = {
  background: "#fff",
  width: "90%",
  maxWidth: 900,
  padding: 20,
  borderRadius: 12,
};

const closeBtn = {
  float: "right" as const,
  border: "none",
  background: "transparent",
  fontSize: 20,
};

const header = {
  display: "flex",
  justifyContent: "space-between",
};

const badgeRow = {
  display: "flex",
  alignItems: "center",
};

const actions = {
  display: "flex",
  gap: 10,
  marginTop: 10,
};

const grid = {
  display: "flex",
  gap: 20,
  marginTop: 10,
};

const ocr = {
  marginTop: 20,
  background: "#f5f5f5",
  padding: 10,
};

const nav = {
  display: "flex",
  justifyContent: "space-between",
  marginTop: 20,
};
