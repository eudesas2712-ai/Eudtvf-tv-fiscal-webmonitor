"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from "recharts";

type ChartDatum = {
  name: string;
  value: number;
};

type MediaChartsProps = {
  editorialSources: ChartDatum[];
  bannerSources: ChartDatum[];
  advertisers: ChartDatum[];
  terms: ChartDatum[];
  formats: ChartDatum[];
};

const COLORS = ["#b00020", "#1f4e79", "#198754", "#6f42c1", "#fd7e14", "#6c757d"];

function SimpleBarChart({
  title,
  data,
}: {
  title: string;
  data: ChartDatum[];
}) {
  return (
    <section style={panelStyle}>
      <h2 style={titleStyle}>{title}</h2>
      <div style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" hide />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#b00020" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
        {data.map((item) => (
          <div
            key={item.name}
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 14,
            }}
          >
            <strong>{item.name}</strong>
            <span>{item.value}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function SimplePieChart({
  title,
  data,
}: {
  title: string;
  data: ChartDatum[];
}) {
  return (
    <section style={panelStyle}>
      <h2 style={titleStyle}>{title}</h2>
      <div style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              outerRadius={95}
              label
            >
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
        {data.map((item) => (
          <div
            key={item.name}
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 14,
            }}
          >
            <strong>{item.name}</strong>
            <span>{item.value}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function MediaCharts({
  editorialSources,
  bannerSources,
  advertisers,
  terms,
  formats,
}: MediaChartsProps) {
  return (
    <div style={{ display: "grid", gap: 24 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <SimpleBarChart title="Origens editoriais" data={editorialSources} />
        <SimpleBarChart title="Origens publicitárias" data={bannerSources} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <SimplePieChart title="Top anunciantes" data={advertisers} />
        <SimplePieChart title="Top termos monitorados" data={terms} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24 }}>
        <SimpleBarChart title="Formatos de banner mais usados" data={formats} />
      </div>
    </div>
  );
}

const panelStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 16,
  padding: 22,
  boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
  border: "1px solid #eef1f5",
};

const titleStyle: React.CSSProperties = {
  marginTop: 0,
  color: "#b00020",
  fontSize: 20,
};