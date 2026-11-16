// Atualiza os dados do catálogo Next.js depois de copiar o data.js gerado.
import { readFile, writeFile } from "node:fs/promises";
const source = await readFile("public/catalogo/data.js", "utf8");
const catalog = JSON.parse(source.replace(/^window\.CATALOG=/, "").replace(/;\s*$/, ""));
const pocket = new Map(JSON.parse(await readFile("research/pocketphysio/exercicios.json", "utf8")).map((exercise) => [exercise.id, exercise]));
const sourceVideos = JSON.parse(await readFile("tool/mannequin/catalog.json", "utf8")).exercises;
const linkedIds = new Map(sourceVideos.map((video) => [video.slug, new Set(video.pocketphysio)]));
const items = catalog.items.flatMap(({ id, nome, desc, foco, area, props, lote, pp, man, lottie, r3d, val, val_txt, vis, vis_txt, fix, pend }) => {
  const linked = linkedIds.get(id);
  if (!linked) throw new Error(`Vídeo ausente do catálogo de origem: ${id}`);
  const groups = new Map();
  for (const reference of pp) {
    if (!linked.has(reference.id)) continue;
    const exercise = pocket.get(reference.id);
    if (!exercise) throw new Error(`Exercício PocketPhysio ausente: ${reference.id}`);
    const name = exercise.nome_pt.trim();
    if (!groups.has(name)) groups.set(name, []);
    groups.get(name).push({ reference, exercise });
  }
  if (new Set([...groups.values()].flat().map(({ reference }) => reference.id)).size !== linked.size) throw new Error(`Referências incompletas para ${id}`);
  const common = { videoId: id, area, props, lote, man, lottie, r3d, val, val_txt, vis, vis_txt, fix, pend };
  if (!groups.size) return [{ id, nome, desc, foco, pp: [], ...common }];
  return [...groups].map(([name, group]) => {
    const main = group.reduce((a, b) => (b.exercise.descricao_pt ?? "").length > (a.exercise.descricao_pt ?? "").length ? b : a).exercise;
    const firstId = group.map(({ reference }) => reference.id).sort()[0];
    return { id: `${id}--${firstId}`, nome: name, desc: main.descricao_pt ?? "", foco: main.objetivo_pt ?? "", pp: group.map(({ reference }) => reference), ...common };
  });
});
if (new Set(items.map((item) => item.id)).size !== items.length) throw new Error("IDs duplicados no catálogo");
await writeFile("app/(app)/catalogo/catalogo.json", JSON.stringify({ stamp: catalog.stamp, items }));
console.log(`${items.length} exercícios atualizados.`);
