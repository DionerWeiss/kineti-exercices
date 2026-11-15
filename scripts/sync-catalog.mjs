// Atualiza os dados do catálogo Next.js depois de copiar o data.js gerado.
import { readFile, writeFile } from "node:fs/promises";
const source = await readFile("public/catalogo/data.js", "utf8");
const catalog = JSON.parse(source.replace(/^window\.CATALOG=/, "").replace(/;\s*$/, ""));
const items = catalog.items.map(({ id, nome, desc, foco, area, props, lote, pp, man, lottie, r3d, val, val_txt, vis, vis_txt, fix, pend }) => ({ id, nome, desc, foco, area, props, lote, pp, man, lottie, r3d, val, val_txt, vis, vis_txt, fix, pend }));
await writeFile("app/(app)/catalogo/catalogo.json", JSON.stringify({ stamp: catalog.stamp, items }));
console.log(`${items.length} exercícios atualizados.`);
