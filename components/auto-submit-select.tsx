"use client";

export function AutoSubmitSelect(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      onChange={(e) => {
        const form = e.currentTarget.form;
        // Trocar de filtro volta para a primeira página.
        const page = form?.elements.namedItem("pagina");
        if (page instanceof HTMLInputElement) page.value = "1";
        form?.requestSubmit();
      }}
    />
  );
}
