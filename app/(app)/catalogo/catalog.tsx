"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Choice = "manequim" | "lottie" | "render3d" | "";
type Item = {
  id: string; nome: string; desc: string; foco: string; area: string; props: string; lote: string;
  pp: { id: string; nome: string }[];
  man: boolean; lottie: { video: boolean; view: string; status: string; motivo: string }; r3d: string;
  val: string; val_txt: string; vis: string; vis_txt: string;
  fix: { lote: string; status: string; correcao: string; motivo: string } | null; pend: string[];
};
type Review = { note: string; choice: Choice };
type Reviews = Record<string, Review>;
const empty: Review = { note: "", choice: "" };
const field = "rounded-lg border border-border bg-surface px-3 py-2 text-sm";
const button = "rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium hover:border-brand disabled:opacity-50";
const normalize = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

export function Catalog({ items, stamp }: { items: Item[]; stamp: string }) {
  const [query, setQuery] = useState("");
  const [area, setArea] = useState("");
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState(items[0]?.id ?? "");
  const [saved, setSaved] = useState<Reviews>({});
  const [drafts, setDrafts] = useState<Reviews>({});
  const [status, setStatus] = useState("Carregando avaliações…");
  const [ready, setReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const videos = useRef<Array<HTMLVideoElement | null>>([]);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/catalogo/avaliacoes", { signal: controller.signal }).then(async (response) => {
      if (!response.ok) throw new Error();
      const rows: { exercise_id: string; note: string; choice: Choice | null }[] = await response.json();
      const reviews = Object.fromEntries(rows.map((row) => [row.exercise_id, { note: row.note, choice: row.choice ?? "" }]));
      setSaved(reviews); setDrafts(reviews); setStatus(""); setReady(true);
    }).catch((error) => { if (error.name !== "AbortError") setStatus("Não foi possível carregar as avaliações. Recarregue a página."); });
    return () => controller.abort();
  }, []);

  const areas = useMemo(() => [...new Set(items.map((item) => item.area).filter(Boolean))].sort(), [items]);
  const filtered = useMemo(() => items.filter((item) => {
    const text = normalize([item.nome, item.id, item.desc, ...item.pp.flatMap((p) => [p.nome, p.id])].join(" "));
    if (!normalize(query).trim().split(/\s+/).every((word) => text.includes(word))) return false;
    if (area && item.area !== area) return false;
    if (filter === "notes" && !saved[item.id]?.note.trim()) return false;
    if (filter === "pending" && !item.pend.length && item.fix?.status !== "não corrigido" && item.vis !== "pendente") return false;
    if (filter === "missing" && (!item.man || !item.lottie.video || item.r3d === "sem vídeo")) return true;
    return filter !== "missing";
  }), [items, query, area, filter, saved]);
  const item = items.find((entry) => entry.id === selected);
  const current = drafts[selected] ?? empty;
  const persisted = saved[selected] ?? empty;
  const dirty = current.note !== persisted.note || current.choice !== persisted.choice;

  useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (Object.keys(drafts).some((id) => (drafts[id]?.note ?? "") !== (saved[id]?.note ?? "") || (drafts[id]?.choice ?? "") !== (saved[id]?.choice ?? ""))) event.preventDefault();
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [drafts, saved]);

  function update(patch: Partial<Review>) { setDrafts((previous) => ({ ...previous, [selected]: { ...(previous[selected] ?? empty), ...patch } })); setStatus(""); }
  function open(id: string) { videos.current.forEach((video) => video?.pause()); setPlaying(false); setSelected(id); setStatus(""); }
  function toggle() {
    const all = videos.current.filter((video): video is HTMLVideoElement => !!video);
    if (playing) all.forEach((video) => video.pause());
    else all.forEach((video) => { video.playbackRate = speed; void video.play().catch(() => {}); });
    setPlaying(!playing);
  }
  async function save() {
    const id = selected, review = current;
    setSaving(true); setStatus("Salvando…");
    try {
      const response = await fetch("/api/catalogo/avaliacoes", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ exercise_id: id, note: review.note, choice: review.choice || null }) });
      if (!response.ok) throw new Error();
      setSaved((previous) => ({ ...previous, [id]: review })); setStatus("Avaliação salva.");
    } catch { setStatus("Não foi possível salvar. Tente novamente."); }
    finally { setSaving(false); }
  }
  const formats: { key: Exclude<Choice, "">; label: string; available: boolean; detail: string }[] = item ? [
    { key: "manequim", label: "Manequim", available: item.man, detail: "" },
    { key: "lottie", label: "Lottie", available: item.lottie.video, detail: [item.lottie.view === "front" ? "Vista frontal" : item.lottie.view === "side" ? "Vista lateral" : "", item.lottie.motivo].filter(Boolean).join(" · ") },
    { key: "render3d", label: "Render 3D", available: item.r3d !== "sem vídeo", detail: item.r3d === "aguardando re-render" ? "Versão anterior, aguardando re-render" : "" },
  ] : [];

  return <div className="space-y-5">
    <div><h1 className="text-2xl font-semibold">Catálogo de exercícios</h1><p className="mt-1 text-sm text-muted">Compare as versões, escolha seu vídeo e registre suas observações. Dados de {stamp}.</p></div>
    <div className="flex flex-wrap gap-2">
      <input className={`${field} min-w-56 flex-1`} type="search" placeholder="Buscar exercício ou ID" aria-label="Buscar exercício" value={query} onChange={(e) => setQuery(e.target.value)} />
      <select className={field} aria-label="Área" value={area} onChange={(e) => setArea(e.target.value)}><option value="">Todas as áreas</option>{areas.map((value) => <option key={value}>{value}</option>)}</select>
      <select className={field} aria-label="Situação" value={filter} onChange={(e) => setFilter(e.target.value)}><option value="">Toda situação</option><option value="pending">Com pendência</option><option value="missing">Com vídeo ausente</option><option value="notes">Com minha nota</option></select>
    </div>
    <div className="grid items-start gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
      <aside className="overflow-hidden rounded-xl border border-border bg-surface"><p className="border-b border-border px-3 py-2 text-xs text-muted">{filtered.length} de {items.length} exercícios</p><div className="max-h-80 overflow-y-auto lg:max-h-[75vh]">{filtered.map((entry) => <button key={entry.id} type="button" onClick={() => open(entry.id)} aria-current={entry.id === selected ? "true" : undefined} className={`block w-full border-b border-border px-3 py-3 text-left text-sm hover:bg-brand-soft ${entry.id === selected ? "bg-brand-soft text-brand" : ""}`}><span className="block font-medium">{entry.nome}</span><span className="block truncate text-xs text-muted">{entry.id}{saved[entry.id]?.note.trim() ? " · com nota" : ""}</span></button>)}</div></aside>
      {item ? <div className="min-w-0 space-y-4">
        <div><h2 className="text-xl font-semibold">{item.nome}</h2><p className="mt-1 break-all font-mono text-xs text-muted">{item.id}{item.lote ? ` · lote ${item.lote}` : ""}</p></div>
        <div className="flex flex-wrap items-center gap-2"><button className={button} onClick={toggle}>{playing ? "Pausar" : "Tocar juntos"}</button><button className={button} onClick={() => { videos.current.forEach((video) => { if (video) video.currentTime = 0; }); }}>Recomeçar</button><label className="text-sm text-muted">Velocidade <select className={field} value={speed} onChange={(e) => { const value = Number(e.target.value); setSpeed(value); videos.current.forEach((video) => { if (video) video.playbackRate = value; }); }}>{[0.5, 0.75, 1, 1.25, 1.5, 2].map((value) => <option key={value} value={value}>{value}×</option>)}</select></label></div>
        <div className="grid gap-3 md:grid-cols-3">{formats.map((format, index) => <section key={format.key} className="overflow-hidden rounded-xl border border-border bg-surface"><h3 className="px-3 py-2 text-sm font-semibold">{format.label}</h3><div className="flex aspect-video items-center justify-center bg-ink text-center text-xs text-white/70">{format.available ? <video key={`${item.id}-${format.key}`} ref={(node) => { videos.current[index] = node; }} className="h-full w-full object-contain" src={`/api/catalogo/video/${format.key}/${encodeURIComponent(item.id)}`} controls muted loop playsInline preload="metadata" /> : "Vídeo indisponível"}</div><p className="min-h-8 px-3 py-2 text-xs text-muted">{format.detail}</p></section>)}</div>
        <div className="grid gap-4 md:grid-cols-2"><section className="rounded-xl border border-border bg-surface p-4"><h3 className="font-semibold">Exercício</h3><p className="mt-2 text-sm">{item.desc}</p><dl className="mt-3 space-y-1 text-sm"><div><dt className="inline font-medium">Foco: </dt><dd className="inline">{item.foco || "—"}</dd></div><div><dt className="inline font-medium">Área: </dt><dd className="inline">{item.area || "—"}</dd></div><div><dt className="inline font-medium">Acessórios: </dt><dd className="inline">{item.props || "—"}</dd></div></dl>{(item.val_txt || item.vis_txt || item.fix?.motivo || item.pend.length > 0) && <div className="mt-4 border-t border-border pt-3 text-sm text-muted"><p className="font-medium text-foreground">Situação</p>{[item.val_txt, item.vis_txt, item.fix?.correcao, item.fix?.motivo, ...item.pend].filter(Boolean).map((text, index) => <p className="mt-1" key={index}>{text}</p>)}</div>}</section>
          <section className="rounded-xl border border-border bg-surface p-4"><h3 className="font-semibold">Escolha e nota</h3><label className="mt-3 block text-sm font-medium" htmlFor="choice">Vídeo escolhido</label><select id="choice" className={`${field} mt-1 w-full`} value={current.choice} onChange={(e) => update({ choice: e.target.value as Choice })} disabled={!ready}><option value="">Nenhum</option>{formats.map((format) => <option key={format.key} value={format.key} disabled={!format.available}>{format.label}{format.available ? "" : " (indisponível)"}</option>)}</select><label className="mt-3 block text-sm font-medium" htmlFor="note">Minha nota</label><textarea id="note" className={`${field} mt-1 min-h-28 w-full`} value={current.note} maxLength={10000} onChange={(e) => update({ note: e.target.value })} disabled={!ready} placeholder="Anote o que precisa mudar" /><div className="mt-3 flex flex-wrap items-center gap-3"><button className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50" onClick={save} disabled={!ready || saving || !dirty}>Salvar avaliação</button><span className="text-sm text-muted" role="status">{status || (dirty ? "Alterações não salvas" : "")}</span></div></section></div>
      </div> : <p className="text-sm text-muted">Nenhum exercício disponível.</p>}
    </div>
  </div>;
}
