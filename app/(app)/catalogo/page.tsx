import type { Metadata } from "next";
import catalog from "./catalogo.json";
import { Catalog } from "./catalog";

export const metadata: Metadata = { title: "Catálogo" };

export default function CatalogPage() {
  return <Catalog items={catalog.items} stamp={catalog.stamp} />;
}
