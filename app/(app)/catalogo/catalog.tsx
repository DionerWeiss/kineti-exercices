"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Choice = "manequim" | "lottie" | "render3d" | "";
type Item = {
  id: string; videoId: string; nome: string; desc: string; foco: string; area: string; props: string; lote: string;
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
  const exerciseHeading = useRef<HTMLHeadingElement>(null);

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
    const text = normalize([item.nome, item.videoId, item.desc, ...item.pp.flatMap((p) => [p.nome, p.id])].join(" "));
    if (!normalize(query).trim().split(/\s+/).every((word) => text.includes(word))) return false;
    if (area && item.area !== area) return false;
    if (filter === "notes" && !saved[item.videoId]?.note.trim()) return false;
    if (filter === "pending" && !item.pend.length && item.fix?.status !== "não corrigido" && item.vis !== "pendente") return false;
    if (filter === "missing" && (!item.man || !item.lottie.video || item.r3d === "sem vídeo")) return true;
    return filter !== "missing";
  }), [items, query, area, filter, saved]);
  const item = items.find((entry) => entry.id === selected);
  const sharedCount = items.filter((entry) => entry.videoId === item?.videoId).length;
  const selectedIndex = filtered.findIndex((entry) => entry.id === selected);
  const reviewId = item?.videoId ?? "";
  const current = drafts[reviewId] ?? empty;
  const persisted = saved[reviewId] ?? empty;
  const dirty = current.note !== persisted.note || current.choice !== persisted.choice;

  useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (Object.keys(drafts).some((id) => (drafts[id]?.note ?? "") !== (saved[id]?.note ?? "") || (drafts[id]?.choice ?? "") !== (saved[id]?.choice ?? ""))) event.preventDefault();
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [drafts, saved]);

  function update(patch: Partial<Review>) { setDrafts((previous) => ({ ...previous, [reviewId]: { ...(previous[reviewId] ?? empty), ...patch } })); setStatus(""); }
  function open(id: string) { videos.current.forEach((video) => video?.pause()); setPlaying(false); setSelected(id); setStatus(""); }
  function navigate(id: string) { open(id); exerciseHeading.current?.focus(); }
  function toggle() {
    const all = videos.current.filter((video): video is HTMLVideoElement => !!video);
    if (playing) all.forEach((video) => video.pause());
    else all.forEach((video) => { video.playbackRate = speed; void video.play().catch(() => {}); });
    setPlaying(!playing);
  }
  async function save() {
    const id = reviewId, review = current;
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
    <div><h1 className="text-2xl font-semibold">Catálogo de exercícios</h1><p className="mt-1 text-sm text-muted">Escolha um exercício, compare as três versões e selecione sua favorita. Dados de {stamp}.</p></div>
    <div className="flex flex-wrap gap-2">
      <input className={`${field} min-w-0 basis-full flex-1 sm:basis-auto`} type="search" placeholder="Buscar exercício ou ID" aria-label="Buscar exercício" value={query} onChange={(e) => setQuery(e.target.value)} />
      <select className={field} aria-label="Área" value={area} onChange={(e) => setArea(e.target.value)}><option value="">Todas as áreas</option>{areas.map((value) => <option key={value}>{value}</option>)}</select>
      <select className={field} aria-label="Situação" value={filter} onChange={(e) => setFilter(e.target.value)}><option value="">Toda situação</option><option value="pending">Com pendência</option><option value="missing">Com vídeo ausente</option><option value="notes">Com minha nota</option></select>
    </div>
    <div className="grid items-start gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
      <aside className="overflow-hidden rounded-xl border border-border bg-surface"><p className="border-b border-border px-3 py-2 text-xs text-muted">Escolha um exercício · {filtered.length} de {items.length}</p><div className="max-h-48 overflow-y-auto lg:max-h-[75vh]">{filtered.length === 0 && <p className="p-4 text-sm text-muted">Nenhum exercício encontrado. Ajuste a busca ou os filtros.</p>}{filtered.map((entry) => <button key={entry.id} type="button" onClick={() => open(entry.id)} aria-current={entry.id === selected ? "true" : undefined} className={`block w-full border-b border-border px-3 py-3 text-left text-sm hover:bg-brand-soft ${entry.id === selected ? "bg-brand-soft text-brand" : ""}`}><span className="block font-medium">{entry.nome}</span><span className="block truncate text-xs text-muted">{entry.videoId}{saved[entry.videoId]?.note.trim() ? " · com nota" : ""}</span></button>)}</div></aside>
      {item ? <div className="min-w-0 space-y-4">
        <div><h2 ref={exerciseHeading} tabIndex={-1} className="scroll-mt-32 text-xl font-semibold">{item.nome}</h2><p className="mt-1 break-all font-mono text-xs text-muted">{item.videoId}{item.lote ? ` · lote ${item.lote}` : ""}</p></div>
        <div className="flex flex-wrap items-center gap-2"><button className={button} onClick={toggle}>{playing ? "Pausar" : "Tocar juntos"}</button><button className={button} onClick={() => { videos.current.forEach((video) => { if (video) video.currentTime = 0; }); }}>Recomeçar</button><label className="text-sm text-muted">Velocidade <select className={field} value={speed} onChange={(e) => { const value = Number(e.target.value); setSpeed(value); videos.current.forEach((video) => { if (video) video.playbackRate = value; }); }}>{[0.5, 0.75, 1, 1.25, 1.5, 2].map((value) => <option key={value} value={value}>{value}×</option>)}</select></label></div>
        <fieldset><legend className="mb-1 text-base font-semibold">Escolha sua versão favorita</legend><p className="mb-3 text-sm text-muted">Assista aos vídeos e selecione uma opção. Depois, salve sua avaliação.</p><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{formats.map((format, index) => <section key={format.key} className={`overflow-hidden rounded-xl border bg-surface ${current.choice === format.key ? "border-brand ring-1 ring-brand" : "border-border"}`}><h3 className="px-3 py-3 text-sm font-semibold">{format.label}</h3><div className="flex aspect-video items-center justify-center bg-ink text-center text-xs text-white/70">{format.available ? <video key={`${item.id}-${format.key}`} ref={(node) => { videos.current[index] = node; }} className="h-full w-full object-contain" src={`/api/catalogo/video/${format.key}/${encodeURIComponent(item.videoId)}`} controls muted loop playsInline preload="metadata" /> : "Vídeo indisponível"}</div>{format.detail && <p className="px-3 pt-3 text-xs text-muted">{format.detail}</p>}<label className={`flex min-h-12 items-center gap-2 px-3 py-3 text-sm font-medium ${format.available && ready ? "cursor-pointer" : "text-muted"}`}><input type="radio" name="choice" value={format.key} checked={current.choice === format.key} onChange={() => update({ choice: format.key })} disabled={!ready || !format.available} className="h-4 w-4 accent-brand" />{current.choice === format.key ? "Selecionado" : format.available ? "Escolher esta versão" : "Indisponível"}</label></section>)}</div></fieldset>
        <div className="grid gap-4 md:grid-cols-2"><section className="rounded-xl border border-border bg-surface p-4"><h3 className="font-semibold">Exercício</h3><p className="mt-2 text-sm">{item.desc}</p><dl className="mt-3 space-y-1 text-sm"><div><dt className="inline font-medium">Foco: </dt><dd className="inline">{item.foco || "—"}</dd></div><div><dt className="inline font-medium">Área: </dt><dd className="inline">{item.area || "—"}</dd></div><div><dt className="inline font-medium">Acessórios: </dt><dd className="inline">{item.props || "—"}</dd></div></dl>{(item.val_txt || item.vis_txt || item.fix?.motivo || item.pend.length > 0) && <div className="mt-4 border-t border-border pt-3 text-sm text-muted"><p className="font-medium text-foreground">Situação</p>{[item.val_txt, item.vis_txt, item.fix?.correcao, item.fix?.motivo, ...item.pend].filter(Boolean).map((text, index) => <p className="mt-1" key={index}>{text}</p>)}</div>}</section>
          <section className="rounded-xl border border-border bg-surface p-4"><h3 className="font-semibold">Sua avaliação</h3>{sharedCount > 1 && <p className="mt-2 text-sm text-muted">Esta avaliação é compartilhada pelos {sharedCount} exercícios que usam este vídeo.</p>}<p className="mt-2 text-sm text-muted">{current.choice ? `Versão escolhida: ${formats.find((format) => format.key === current.choice)?.label}` : "Nenhuma versão escolhida ainda."}</p>{current.choice && <button type="button" className="mt-1 min-h-11 text-sm font-medium text-brand hover:underline" onClick={() => update({ choice: "" })} disabled={!ready}>Limpar escolha</button>}<label className="mt-3 block text-sm font-medium" htmlFor="note">Minha nota</label><textarea id="note" className={`${field} mt-1 min-h-28 w-full`} value={current.note} maxLength={10000} onChange={(e) => update({ note: e.target.value })} disabled={!ready} placeholder="Anote o que precisa mudar" /><div className="mt-3 flex flex-wrap items-center gap-3"><button className="min-h-11 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-50" onClick={save} disabled={!ready || saving || !dirty}>Salvar avaliação</button><span className="text-sm text-muted" role="status">{status || (dirty ? "Alterações não salvas" : "")}</span></div></section></div>
        <nav aria-label="Navegação entre exercícios" className="flex items-center justify-between gap-3 border-t border-border pt-4">
          <button type="button" className={`${button} min-h-11`} disabled={selectedIndex <= 0} onClick={() => navigate(filtered[selectedIndex - 1].id)}>Anterior</button>
          <span className="text-center text-sm text-muted">{selectedIndex >= 0 ? `${selectedIndex + 1} de ${filtered.length}` : "Exercício fora do filtro"}</span>
          <button type="button" className={`${button} min-h-11`} disabled={filtered.length === 0 || selectedIndex === filtered.length - 1} onClick={() => navigate(filtered[selectedIndex + 1].id)}>Próximo</button>
        </nav>
      </div> : <p className="text-sm text-muted">Nenhum exercício disponível.</p>}
    </div>
  </div>;
}
