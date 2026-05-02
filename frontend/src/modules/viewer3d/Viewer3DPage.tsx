/**
 * 3D Viewer page — Online3DViewer wrapper for NEXUS.
 *
 * Online3DViewer is a vanilla JS / three.js library; we instantiate its
 * embedded engine inside a React effect, attach it to a div ref, and
 * point it at one of two sources:
 *
 *  1. Local file picker — drop the file straight into the viewer's
 *     `LoadModelFromInputFiles` so the user can browse without an upload.
 *  2. Server upload — POST to /api/v1/viewer3d/upload and feed the
 *     returned signed URL into `LoadModelFromUrlList`. This is what
 *     persists across sessions and allows linking from BOQ rows.
 *
 * Supported formats: obj, 3ds, stl, ply, gltf/glb, off, 3dm, fbx, dae,
 * wrl, 3mf, ifc — same set as the upstream Online3DViewer.
 */
import { useEffect, useRef, useState } from 'react';
import { Upload, FolderOpen, Loader2 } from 'lucide-react';

// Online3DViewer is exposed as both a UMD bundle and ES module. The
// `dist/o3dv.module.min.js` build is the smallest browser-ready bundle
// and is the one we ship.
//
// The library does not provide TypeScript types (as of 0.18.0), so we
// import as `any`. This is intentional and isolated to this module.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let OV: any | null = null;
async function loadO3DV() {
  if (OV) return OV;
  // dynamic import keeps it out of the main bundle until the page mounts
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mod: any = await import('online-3d-viewer/build/engine/o3dv.module.js');
  OV = mod;
  if (typeof OV.SetExternalLibLocation === 'function') {
    OV.SetExternalLibLocation('libs');
  }
  return OV;
}

const ALLOWED_EXTENSIONS = '.obj,.3ds,.stl,.ply,.gltf,.glb,.off,.3dm,.fbx,.dae,.wrl,.3mf,.ifc';

interface UploadInfo {
  id: string;
  original_name: string;
  size_bytes: number;
  download_url: string;
}

export default function Viewer3DPage() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const viewerRef = useRef<any | null>(null);
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [lastUpload, setLastUpload] = useState<UploadInfo | null>(null);

  // Mount: instantiate the viewer once.
  useEffect(() => {
    let disposed = false;
    (async () => {
      const lib = await loadO3DV();
      if (disposed || !containerRef.current) return;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const Viewer = lib.EmbeddedViewer ?? lib.default?.EmbeddedViewer;
      if (!Viewer) {
        setErrorMsg('Online3DViewer engine entry-point not found');
        setStatus('error');
        return;
      }
      viewerRef.current = new Viewer(containerRef.current, {
        backgroundColor: lib.RGBAColor
          ? new lib.RGBAColor(243, 244, 246, 255)
          : undefined,
        defaultColor: lib.RGBColor ? new lib.RGBColor(160, 160, 160) : undefined,
      });
      setStatus('ready');
    })().catch((e: unknown) => {
      if (disposed) return;
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setStatus('error');
    });
    return () => {
      disposed = true;
      // The library doesn't expose a public dispose(); leaving the canvas
      // for the GC to reap when the React tree unmounts is fine for our scale.
      viewerRef.current = null;
    };
  }, []);

  const loadFromInputFiles = (files: FileList | null) => {
    if (!files || files.length === 0 || !viewerRef.current) return;
    setStatus('loading');
    setErrorMsg(null);
    try {
      // The library accepts a FileList directly via its
      // LoadModelFromInputFiles helper.
      viewerRef.current.LoadModelFromInputFiles(Array.from(files));
      setStatus('ready');
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setStatus('error');
    }
  };

  const loadFromUrl = (url: string) => {
    if (!viewerRef.current) return;
    setStatus('loading');
    setErrorMsg(null);
    try {
      viewerRef.current.LoadModelFromUrlList([url]);
      setStatus('ready');
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
      setStatus('error');
    }
  };

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    loadFromInputFiles(e.target.files);
  };

  const uploadAndLoad = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatus('loading');
    setErrorMsg(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/api/v1/viewer3d/upload', {
        method: 'POST',
        body: fd,
        credentials: 'include',
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Upload failed (${res.status}): ${txt}`);
      }
      const info = (await res.json()) as UploadInfo;
      setLastUpload(info);
      loadFromUrl(info.download_url);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setStatus('error');
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-gray-50">
      <header className="flex items-center gap-3 px-4 py-3 border-b bg-white">
        <h1 className="text-lg font-semibold flex-1">3D Viewer</h1>

        <label className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded border bg-white hover:bg-gray-50 cursor-pointer">
          <FolderOpen className="w-4 h-4" />
          <span>Open local file</span>
          <input
            type="file"
            accept={ALLOWED_EXTENSIONS}
            multiple
            className="hidden"
            onChange={handleFile}
          />
        </label>

        <label className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded border bg-blue-600 text-white hover:bg-blue-700 cursor-pointer">
          <Upload className="w-4 h-4" />
          <span>Upload &amp; load</span>
          <input
            type="file"
            accept={ALLOWED_EXTENSIONS}
            className="hidden"
            onChange={uploadAndLoad}
          />
        </label>
      </header>

      <div className="relative flex-1 min-h-[400px]">
        <div ref={containerRef} className="absolute inset-0 w-full h-full" />
        {status === 'loading' && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/60">
            <Loader2 className="w-6 h-6 animate-spin text-gray-700" />
          </div>
        )}
        {status === 'error' && errorMsg && (
          <div className="absolute top-4 left-4 right-4 px-4 py-2 rounded bg-red-50 border border-red-200 text-red-800 text-sm">
            {errorMsg}
          </div>
        )}
      </div>

      {lastUpload && (
        <footer className="px-4 py-2 text-xs text-gray-600 border-t bg-white">
          Loaded server upload <code>{lastUpload.id}</code> ·{' '}
          {Math.round(lastUpload.size_bytes / 1024)} KB · {lastUpload.original_name}
        </footer>
      )}
    </div>
  );
}
