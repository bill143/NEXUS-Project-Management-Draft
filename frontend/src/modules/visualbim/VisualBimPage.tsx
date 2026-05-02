/**
 * VisualBIM page — Plotly.js scatter3d over BIM project parameters.
 *
 * Each BIM element becomes one point. The user picks five dimensions:
 *   - x / y / z axes (numeric — usually volume, area, length)
 *   - color  (categorical — element_type, storey, discipline, name)
 *   - size   (numeric — defaults to "count" for uniform points)
 *
 * The frontend hits GET /api/v1/visualbim/projects/{project_id}/cloud and
 * passes the dim_x/y/z/color/size query params straight through. The
 * backend resolves each dim against BIMElement.quantities then properties.
 */
import { useEffect, useMemo, useState } from 'react';
import Plot from 'react-plotly.js';

interface CloudPoint {
  id: string;
  label: string;
  x: number;
  y: number;
  z: number;
  color: string;
  size: number;
}

interface CloudResponse {
  project_id: string;
  point_count: number;
  dim_x: string;
  dim_y: string;
  dim_z: string;
  dim_color: string;
  dim_size: string;
  points: CloudPoint[];
  available_dims: { color_categories?: string[] };
}

const NUMERIC_DIMS = ['volume', 'area', 'length', 'count'];
const CATEGORICAL_DIMS = ['element_type', 'storey', 'discipline', 'name'];

const COLOR_PALETTE = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
];

export default function VisualBimPage() {
  const [projectId, setProjectId] = useState('');
  const [dimX, setDimX] = useState('volume');
  const [dimY, setDimY] = useState('area');
  const [dimZ, setDimZ] = useState('length');
  const [dimColor, setDimColor] = useState('element_type');
  const [dimSize, setDimSize] = useState('count');
  const [cloud, setCloud] = useState<CloudResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      dim_x: dimX,
      dim_y: dimY,
      dim_z: dimZ,
      dim_color: dimColor,
      dim_size: dimSize,
    });
    fetch(
      `/api/v1/visualbim/projects/${encodeURIComponent(projectId)}/cloud?${params.toString()}`,
      { credentials: 'include' },
    )
      .then((res) => {
        if (!res.ok) throw new Error(`API ${res.status}`);
        return res.json() as Promise<CloudResponse>;
      })
      .then((data) => {
        if (!cancelled) setCloud(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, dimX, dimY, dimZ, dimColor, dimSize]);

  const traces = useMemo(() => {
    if (!cloud || cloud.points.length === 0) return [];
    // Group points by color category — Plotly draws one trace per group so
    // the legend is meaningful and the user can toggle categories on/off.
    const groups = new Map<string, CloudPoint[]>();
    for (const p of cloud.points) {
      if (!groups.has(p.color)) groups.set(p.color, []);
      groups.get(p.color)!.push(p);
    }
    return Array.from(groups.entries()).map(([category, pts], i) => ({
      type: 'scatter3d' as const,
      mode: 'markers' as const,
      name: category,
      x: pts.map((p) => p.x),
      y: pts.map((p) => p.y),
      z: pts.map((p) => p.z),
      text: pts.map((p) => p.label),
      hovertemplate:
        `<b>%{text}</b><br>${cloud.dim_x}: %{x}<br>${cloud.dim_y}: %{y}<br>${cloud.dim_z}: %{z}<extra>${category}</extra>`,
      marker: {
        size: pts.map((p) => Math.min(Math.max(Math.sqrt(p.size) * 4, 4), 24)),
        color: COLOR_PALETTE[i % COLOR_PALETTE.length],
        opacity: 0.8,
      },
    }));
  }, [cloud]);

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <header className="flex flex-wrap items-center gap-3 px-4 py-3 border-b bg-white">
        <h1 className="text-lg font-semibold mr-4">BIM Analytics</h1>

        <input
          type="text"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          placeholder="Project UUID"
          className="px-3 py-1 text-sm border rounded w-72 font-mono"
        />

        <DimSelect label="X" value={dimX} onChange={setDimX} options={NUMERIC_DIMS} />
        <DimSelect label="Y" value={dimY} onChange={setDimY} options={NUMERIC_DIMS} />
        <DimSelect label="Z" value={dimZ} onChange={setDimZ} options={NUMERIC_DIMS} />
        <DimSelect
          label="color"
          value={dimColor}
          onChange={setDimColor}
          options={CATEGORICAL_DIMS}
        />
        <DimSelect label="size" value={dimSize} onChange={setDimSize} options={NUMERIC_DIMS} />

        {cloud && (
          <span className="ml-auto text-xs text-gray-500">
            {cloud.point_count} points · {cloud.available_dims.color_categories?.length ?? 0}{' '}
            categories
          </span>
        )}
      </header>

      <div className="flex-1 relative min-h-[400px]">
        {!projectId && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm">
            Enter a project UUID to load its BIM elements as a 3D point cloud.
          </div>
        )}
        {loading && (
          <div className="absolute top-4 right-4 text-xs text-gray-500">loading…</div>
        )}
        {error && (
          <div className="absolute top-4 left-4 right-4 px-4 py-2 rounded bg-red-50 border border-red-200 text-red-800 text-sm">
            {error}
          </div>
        )}
        {cloud && cloud.points.length > 0 && (
          <Plot
            data={traces}
            layout={{
              autosize: true,
              margin: { l: 0, r: 0, t: 0, b: 0 },
              scene: {
                xaxis: { title: { text: cloud.dim_x } },
                yaxis: { title: { text: cloud.dim_y } },
                zaxis: { title: { text: cloud.dim_z } },
              },
              legend: { orientation: 'h', y: -0.1 },
            }}
            useResizeHandler
            style={{ width: '100%', height: '100%' }}
          />
        )}
        {cloud && cloud.points.length === 0 && projectId && !loading && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm">
            No BIM elements in this project yet.
          </div>
        )}
      </div>
    </div>
  );
}

function DimSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="inline-flex items-center gap-1 text-xs text-gray-600">
      <span className="font-medium">{label}:</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-2 py-1 border rounded text-sm bg-white"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}
